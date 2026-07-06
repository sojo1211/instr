import os
import re
import urllib.request
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, concatenate_videoclips

FONT_PATH_REGULAR = "NanumGothic.ttf"
FONT_PATH_BOLD = "NanumGothic.ttf"

def download_fonts():
    # 이미 로컬에 있는 NanumGothic.ttf를 사용하므로 다운로드 생략
    pass

def parse_input_text(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    cards = []
    # [CARD 1], [CARD 2] 등으로 분리
    parts = re.split(r'\[CARD \d+\]', content)
    for part in parts:
        text = part.strip()
        if text:
            cards.append(text)
    return cards

def add_dark_gradient(img):
    """아래에서 위로 올라오는 어두운 그라데이션 오버레이 적용 (하단 50%에만)"""
    width, height = img.size
    gradient = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    
    start_y = int(height * 0.4) # 40% 지점부터 어두워지기 시작
    for y in range(start_y, height):
        alpha = int(220 * ((y - start_y) / (height - start_y))) # 최대 220까지 어두워짐
        draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
        
    return Image.alpha_composite(img.convert('RGBA'), gradient)

def create_card_image(bg_path, text, output_path):
    # 1. 배경 이미지 로드 및 리사이즈/크롭 (1080x1920)
    target_size = (1080, 1920)
    try:
        img = Image.open(bg_path).convert("RGBA")
    except FileNotFoundError:
        print(f"경고: {bg_path} 파일을 찾을 수 없어 임시 색상 배경으로 대체합니다.")
        img = Image.new("RGBA", target_size, color=(50, 50, 50, 255))
        
    # 이미지 비율에 맞게 리사이즈 후 크롭
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

    # 2. 그라데이션 오버레이 추가
    img = add_dark_gradient(img)
    draw = ImageDraw.Draw(img)
    
    # 3. 텍스트 합성
    font_regular = ImageFont.truetype(FONT_PATH_REGULAR, 45)
    font_bold = ImageFont.truetype(FONT_PATH_BOLD, 65)
    
    padding_x = 80
    bottom_margin = 350 # 예시처럼 인스타그램 하단 UI(좋아요 등)를 피하기 위한 여백
    
    lines = text.split('\n')
    
    # 전체 텍스트 높이 계산을 위한 임시 렌더링 리스트
    rendered_lines = []
    total_height = 0
    
    for line in lines:
        if not line.strip():
            rendered_lines.append(({'text': '', 'font': font_regular, 'height': 30}))
            total_height += 30
            continue
            
        is_title = False
        if line == lines[0] or "오늘의" in line or "주요 시사" in line:
            is_title = True
            
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
            
        rendered_lines.append(({'text': '', 'font': font_regular, 'height': 10})) # 단락간 간격
        total_height += 10
        
    # 실제 그리기 (하단에서부터 위치 계산)
    current_y = target_size[1] - bottom_margin - total_height
    
    for item in rendered_lines:
        if item['text']:
            draw.text((padding_x, current_y), item['text'], font=item['font'], fill="white")
        current_y += item['height'] + 20
        if not item['text']:
            current_y -= 20 # 빈 줄이나 단락 간격일 때는 추가 20px(위치 조정용) 제거
            
    # RGB로 변환하여 저장
    img.convert("RGB").save(output_path)
    return output_path

def main():
    print("카드뉴스 생성을 시작합니다...")
    
    # 폰트 다운로드
    download_fonts()
    
    # 입력 텍스트 로드
    input_text_path = "input_text.txt"
    if not os.path.exists(input_text_path):
        print(f"오류: {input_text_path} 파일이 없습니다.")
        return
        
    texts = parse_input_text(input_text_path)
    
    # 폴더 준비
    os.makedirs("input_images", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    
    image_paths = []
    
    # 각 카드 생성
    for i, text in enumerate(texts):
        card_num = i + 1
        bg_path = os.path.join("input_images", f"{card_num}.jpg")
        out_path = os.path.join("output", f"card_{card_num}.jpg")
        
        print(f"카드 {card_num} 이미지 생성 중...")
        create_card_image(bg_path, text, out_path)
        image_paths.append(out_path)
        
    # 영상 제작
    print("릴스 영상(20초) 렌더링 중...")
    clips = []
    for img_path in image_paths:
        # 각 이미지를 5초 길이의 클립으로
        clip = ImageClip(img_path).with_duration(5)
        clips.append(clip)
        
    final_video = concatenate_videoclips(clips, method="compose")
    output_video_path = os.path.join("output", "reels.mp4")
    final_video.write_videofile(output_video_path, fps=24, codec="libx264", audio=False)
    
    print("작업 완료! 결과물은 output/ 폴더를 확인하세요.")

if __name__ == "__main__":
    main()
