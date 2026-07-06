import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from generator import generate_images_from_script

script_data = {
  "panels": [
    {
      "panel_number": 1,
      "image_prompt": "Two young korean women sitting in a cafe, chatting. One woman looks confident and happy.",
      "dialogue": [
        "나 요즘 도수치료 매주 받잖아~",
        "어차피 실비보험 있어서 다 돌려받아! 완전 개꿀이야."
      ]
    },
    {
      "panel_number": 2,
      "image_prompt": "A young korean woman lying on a physical therapy bed, getting a massage, looking very relaxed.",
      "dialogue": [
        "비싼 MRI도 팍팍 찍고, 도수치료도 맘껏 받아야지~",
        "실비가 최고야 진짜!"
      ]
    },
    {
      "panel_number": 3,
      "image_prompt": "A young korean woman looking at a hospital bill on her smartphone, looking extremely shocked and panicked, holding her head.",
      "dialogue": [
        "네?! 통원치료 1회 한도가 25만원이라구요?",
        "연간 횟수 제한도 넘어서... 500만원을 제 돈으로 내야한다고요...?!"
      ]
    },
    {
      "panel_number": 4,
      "image_prompt": "A professional female financial advisor explaining with a warm smile, holding a document, looking directly at the camera.",
      "dialogue": [
        "실손보험만 믿다가는 이렇게 큰코 다칠 수 있어요.",
        "반드시 전문가와 함께 내 보험의 보장 한도와 빈틈을 정기적으로 점검하셔야 합니다!"
      ]
    }
  ]
}

def progress_cb(msg, url=None):
    print(f"[PROGRESS] {msg}")
    if url:
        print(f"[URL] {url}")

print("Generating custom webtoon...")
try:
    output_dir = generate_images_from_script(script_data, progress_callback=progress_cb)
    print(f"Webtoon generated successfully in: {output_dir}")
except Exception as e:
    print(f"Error: {e}")
