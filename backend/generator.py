import os
import re
import urllib.request
import urllib.parse
import time
import datetime
import zipfile
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from google import genai
from dotenv import load_dotenv

try:
    from moviepy import ImageClip, concatenate_videoclips
except ImportError:
    pass

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

FONT_PATH_REGULAR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "NanumGothic.ttf"))
FONT_PATH_BOLD = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "NanumGothic.ttf"))
OUTPUT_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))

def get_gemini_client(key_index=0):
    keys = []
    for key_name in ["GEMINI_API_KEY", "GEMINI_API_KEY_FALLBACK", "GEMINI_API_KEY_FALLBACK2", "GEMINI_API_KEY_FALLBACK3"]:
        val = os.environ.get(key_name)
        if val and val not in keys:
            keys.append(val)
    if not keys:
        raise Exception("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
    if key_index >= len(keys):
        return None
    client = genai.Client(api_key=keys[key_index])
    client._key_index = key_index
    client._keys_count = len(keys)
    return client

def generate_content_with_fallback(client, model, contents):
    current_client = client
    while True:
        try:
            return current_client.models.generate_content(model=model, contents=contents)
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "Quota exceeded" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                next_index = current_client._key_index + 1
                if next_index < current_client._keys_count:
                    print(f"API Key {current_client._key_index} limit reached. Switching to key {next_index}...")
                    current_client = get_gemini_client(next_index)
                else:
                    print("All API keys have reached their rate limits.")
                    raise e
            else:
                raise e

def parse_input_text(content: str) -> list[dict]:
    cards = []
    matches = re.finditer(r'(?:\[CARD \d+\]|카드 \d+\.)(.*?)(?=(?:\[CARD \d+\]|카드 \d+\.)|$)', content, re.DOTALL)
    for match in matches:
        part = match.group(1).strip()
        if not part:
            continue
            
        bg_prompt = ""
        text_content = part
        
        bg_match = re.search(r'배경\s*이미지\s*:(.*?)(?=텍스트\s*:|$)', part, re.DOTALL)
        if bg_match:
            bg_prompt = bg_match.group(1).strip()
            
        text_match = re.search(r'텍스트\s*:(.*)', part, re.DOTALL)
        if text_match:
            text_content = text_match.group(1).strip()
            
        # 텍스트 내용 중에 '주의사항:' 등 뒤에 붙은 불필요한 프롬프트 지시문 잘라내기
        caution_match = re.search(r'(주의사항\s*:|참고사항\s*:|이렇게 해도됨\?|이렇게 하면됨\?)', text_content)
        if caution_match:
            text_content = text_content[:caution_match.start()].strip()
            
        if text_content:
            cards.append({"text": text_content, "bg_prompt": bg_prompt})
    return cards

def process_links_in_text(text: str, client: genai.Client) -> tuple[str, str, str]:
    # 텍스트 내의 (@...) 주석 제거
    text = re.sub(r'\(@.*?\)', '', text).strip()
    
    url_pattern = re.compile(r'https?://[^\s]+')
    urls = url_pattern.findall(text)
    if not urls:
        return text, "", ""
    
    url = urls[0]
    try:
        req = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(req.content, 'html.parser')
        article_text = soup.get_text(separator=' ', strip=True)
        
        og_image = soup.find('meta', property='og:image')
        image_url = og_image['content'] if og_image and og_image.get('content') else ""
        
        if not image_url:
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and not src.startswith('data:') and 'icon' not in src and 'logo' not in src:
                    image_url = src
                    break
                    
        if image_url:
            image_url = urllib.parse.urljoin(url, image_url)
        
        page_title = soup.title.string if soup.title else ""
        
        prompt = f"""다음 기사의 내용을 인스타그램 카드뉴스 본문에 들어갈 수 있게 핵심만 2~4줄의 문장으로 요약하고, 기사가 발행된 언론사 이름(예: 네이버 뉴스, 한국경제, 조선일보 등 도메인이 아닌 한글 이름)을 찾아주세요. 부연 설명 없이 깔끔하게 출력해주세요.

[출력 형식]
언론사: (언론사 이름만 작성)
요약:
(요약 내용 작성)

[기사 정보]
URL: {url}
제목: {page_title}
본문:
{article_text[:5000]}
"""
        response = generate_content_with_fallback(
            client=client,
            model='gemini-2.5-flash',
            contents=prompt
        )
        resp_text = response.text.strip()
        
        summary = resp_text
        source_name = ""
        
        # 언론사, 요약 텍스트 추출 (마크다운 볼드체 등 제거)
        source_match = re.search(r'언론사\s*:\s*([^\n]+)', resp_text)
        summary_match = re.search(r'요약\s*:\s*(.*)', resp_text, re.DOTALL)
        
        if source_match:
            source_name = source_match.group(1).replace('*', '').strip()
        if summary_match:
            summary = summary_match.group(1).replace('*', '').strip()

        # 추출 실패했거나 도메인(예: n.news.naver.com)이 나온 경우의 폴백
        if not source_name or "." in source_name:
            og_author = soup.find('meta', property='og:article:author')
            og_site_name = soup.find('meta', property='og:site_name')
            
            if og_author and og_author.get('content'):
                # 보통 "파이낸셜뉴스 | 네이버" 형태로 나옴
                source_name = og_author['content'].split('|')[0].strip()
            elif og_site_name and og_site_name.get('content'):
                source_name = og_site_name['content']
            elif page_title:
                source_name = page_title.split('-')[0].strip()
            else:
                source_name = "관련 기사"

        # 마지막으로 또 도메인 형태면 그냥 '관련 기사'로 통일
        if '.' in source_name and any(x in source_name for x in ['com', 'kr', 'net']):
            source_name = "관련 기사"
                
        source_text = f"사진 출처={source_name}" if image_url else ""
        
        return text.replace(url, summary), image_url, source_text
    except Exception as e:
        print(f"URL 크롤링/요약 실패: {e}")
        return text, "", ""

def get_background_prompts(cards_text: list[str], client: genai.Client, provided_prompts: list[str]) -> list[str]:
    final_prompts = []
    for i, (text, provided) in enumerate(zip(cards_text, provided_prompts)):
        if provided and "내가 주는 기사에 어울리는" not in provided:
            prompt = f"Translate the following image description to a short English prompt (comma separated keywords) for an image generator. Output ONLY the English prompt, nothing else:\n{provided}"
        else:
            prompt = f"Here is the text for card {i+1}:\n{text}\nPlease provide a short English prompt (comma separated keywords) to generate a realistic background image for this card. Output ONLY the English prompt."
            
        response = generate_content_with_fallback(
            client=client,
            model='gemini-2.5-flash',
            contents=prompt
        )
        final_prompts.append(response.text.strip())
    return final_prompts

def add_dark_gradient(img):
    width, height = img.size
    gradient = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    start_y = int(height * 0.25)
    for y in range(start_y, height):
        alpha = int(240 * ((y - start_y) / (height - start_y)))
        draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert('RGBA'), gradient)

def create_card_image(bg_path, text, output_path, source_text=""):
    target_size = (1080, 1920)
    try:
        img = Image.open(bg_path).convert("RGBA")
    except FileNotFoundError:
        img = Image.new("RGBA", target_size, color=(50, 50, 50, 255))
        
    img_ratio = img.width / img.height
    target_ratio = target_size[0] / target_size[1]
    
    if img_ratio > target_ratio:
        new_h = target_size[1]
        new_w = int(new_h * img_ratio)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - target_size[0]) // 2
        img = img.crop((left, 0, left + target_size[0], target_size[1]))
    else:
        new_w = target_size[0]
        new_h = int(new_w / img_ratio)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        top = (new_h - target_size[1]) // 2
        img = img.crop((0, top, target_size[0], top + target_size[1]))

    img = add_dark_gradient(img)
    draw = ImageDraw.Draw(img)
    
    font_regular = ImageFont.truetype(FONT_PATH_REGULAR, 45)
    font_bold = ImageFont.truetype(FONT_PATH_BOLD, 65)
    
    padding_x = 80
    bottom_margin = 550  # 릴스 하단 UI(설명, 아이디 등)에 가리지 않도록 마진 증가
    lines = text.split('\n')
    
    rendered_lines = []
    total_height = 0
    
    for line in lines:
        if not line.strip():
            rendered_lines.append({'text': '', 'font': font_regular, 'height': 30})
            total_height += 30
            continue
            
        is_title = line == lines[0] or "오늘의" in line or "주요 시사" in line
        font_to_use = font_bold if is_title else font_regular
        
        words = line.split(' ')
        current_line = []
        for word in words:
            current_line.append(word)
            bbox = draw.textbbox((0, 0), " ".join(current_line), font=font_to_use)
            if bbox[2] > (target_size[0] - padding_x * 2):
                current_line.pop()
                wl = " ".join(current_line)
                bbox_wl = draw.textbbox((0, 0), wl, font=font_to_use)
                h = bbox_wl[3] - bbox_wl[1]
                rendered_lines.append({'text': wl, 'font': font_to_use, 'height': h})
                total_height += h + 20
                current_line = [word]
                
        if current_line:
            wl = " ".join(current_line)
            bbox_wl = draw.textbbox((0, 0), wl, font=font_to_use)
            h = bbox_wl[3] - bbox_wl[1]
            rendered_lines.append({'text': wl, 'font': font_to_use, 'height': h})
            total_height += h + 20
            
        rendered_lines.append({'text': '', 'font': font_regular, 'height': 10})
        total_height += 10
        
    current_y = target_size[1] - bottom_margin - total_height
    for item in rendered_lines:
        if item['text']:
            draw.text((padding_x, current_y), item['text'], font=item['font'], fill="white")
        current_y += item['height'] + 20
        if not item['text']:
            current_y -= 20
            
    if source_text:
        font_source = ImageFont.truetype(FONT_PATH_REGULAR, 28)
        # 좌측 상단, 인스타그램 상단 UI에 가리지 않을 정도의 위치 (padding_x, 150)
        draw.text((padding_x, 150), source_text, font=font_source, fill="white", stroke_width=2, stroke_fill="black")
            
    img.convert("RGB").save(output_path)
    return output_path

def generate_cardnews_job(text_prompt: str, progress_callback=None):
    if progress_callback: progress_callback("텍스트 파싱 및 크롤링 처리 중...")
    cards_data = parse_input_text(text_prompt)
    if not cards_data:
        raise Exception("카드 내용을 파싱할 수 없습니다. 형식을 확인해주세요.")
        
    client = get_gemini_client()
    
    # 텍스트 내의 URL 크롤링 및 요약
    cards_text = []
    cards_images = []
    cards_sources = []
    provided_bg_prompts = []
    for i, data in enumerate(cards_data):
        if progress_callback: progress_callback(f"카드 {i+1} 기사 내용 스캔 및 요약 중...")
        processed_text, img_url, src_txt = process_links_in_text(data["text"], client)
        cards_text.append(processed_text)
        cards_images.append(img_url)
        cards_sources.append(src_txt)
        provided_bg_prompts.append(data["bg_prompt"])
    
    if progress_callback: progress_callback("AI 배경 프롬프트 생성 중...")
    bg_prompts = get_background_prompts(cards_text, client, provided_bg_prompts)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(OUTPUT_BASE, timestamp)
    os.makedirs(output_dir, exist_ok=True)
    
    image_paths = []
    
    for i, (text, bg_prompt, img_url, src_txt) in enumerate(zip(cards_text, bg_prompts, cards_images, cards_sources)):
        card_num = i + 1
        bg_path = os.path.join(output_dir, f"bg_{card_num}.jpg")
        
        # 1순위: 기사 원본 이미지 사용
        if img_url:
            if progress_callback: progress_callback(f"카드 {card_num} 기사 원본 이미지 다운로드 중...")
            try:
                req = requests.get(img_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                with open(bg_path, 'wb') as out_file:
                    out_file.write(req.content)
            except Exception as e:
                print("이미지 다운로드 실패, AI 이미지로 대체")
                img_url = "" # fallback
        
        # 2순위: 기사 이미지가 없거나 다운로드 실패 시 AI 생성
        if not img_url:
            if progress_callback: progress_callback(f"카드 {card_num} 배경 이미지 생성 중...")
            encoded_prompt = urllib.parse.quote(f"high quality, aesthetic, empty sky at top, {bg_prompt}")
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true"
            for attempt in range(3):
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response:
                        with open(bg_path, 'wb') as out_file:
                            out_file.write(response.read())
                    break
                except Exception as e:
                    time.sleep(2)
        
        if progress_callback: progress_callback(f"카드 {card_num} 텍스트 합성 중...")
        out_path = os.path.join(output_dir, f"card_{card_num}.jpg")
        create_card_image(bg_path, text, out_path, source_text=src_txt)
        image_paths.append(out_path)
        
        if progress_callback:
            folder_name = os.path.basename(output_dir)
            panel_name = os.path.basename(out_path)
            progress_callback(f"카드 {card_num} 완성!", f"/output/{folder_name}/{panel_name}")
            
    if progress_callback: progress_callback("릴스 영상(20초) 렌더링 중...")
    
    clips = []
    for img_path in image_paths:
        clip = ImageClip(img_path).with_duration(5)
        clips.append(clip)
        
    final_video = concatenate_videoclips(clips, method="compose")
    video_path = os.path.join(output_dir, "video_reels_9x16.mp4")
    final_video.write_videofile(video_path, fps=12, codec="libx264", audio=False, preset="ultrafast", logger=None)
    
    final_img_path = os.path.join(output_dir, "final_webtoon_9x16.png")
    Image.open(image_paths[0]).save(final_img_path)
    
    return output_dir
