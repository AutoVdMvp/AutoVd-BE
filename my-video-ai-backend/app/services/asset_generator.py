import os
import time
import httpx
import random
import urllib.parse
import asyncio
import edge_tts

# 작업물 저장 Server Folder
BASE_DIR = "temp_projects"

def generate_assets(project_id: str, video_plan: dict) -> list:
    # Project Folder 생성
    project_path = os.path.join(BASE_DIR, project_id)
    os.makedirs(project_path, exist_ok=True)

    scene_assets = []
    scenes = video_plan.get("scenes", [])

    for scene in scenes:
        scene_num = scene.get("scene_number", 0)
        narration = scene.get("narration", "")
        image_prompt = scene.get("image_prompt", "")

        # TTS 생성 및 저장
        audio_filename = f"scene_{scene_num}.mp3"
        audio_path = os.path.join(project_path, audio_filename)

        try:
            voice = "ko-KR-SunHiNeural"
            communicate = edge_tts.Communicate(narration, voice)
            asyncio.run(communicate.save(audio_path))
        except Exception as e:
            print(f"[Scene {scene_num}] 음성 저장 실패: {e}")
            continue

        # Image 생성 및 저장
        image_filename = f"scene_{scene_num}.jpg"
        image_path = os.path.join(project_path, image_filename)
        safe_prompt = urllib.parse.quote(image_prompt)
        seed = random.randint(1, 100000)
        image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1080&height=1920&nologo=true%seed={seed}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
        }

        # Image Download
        max_retries = 3
        image_success = False

        for attempt in range(max_retries):
            try:
                response = httpx.get(image_url, headers=headers, timeout=60.0, follow_redirects=True)
                response.raise_for_status()

                with open(image_path, 'wb') as f:
                    f.write(response.content)
                
                image_success = True
                break
            except Exception as e:
                print(f"[Scene {scene_num}] Image Download Failed (Try {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    print(f"[Scene {scene_num}] 최종 다운로드 실패")
        
        if not image_success:
            continue

        scene_assets.append({
            "scene_number": scene_num,
            "audio_path": audio_path,
            "image_path": image_path,
            "narration": narration
        })

        time.sleep(5)

    return scene_assets