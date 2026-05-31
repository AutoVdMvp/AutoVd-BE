"""
미디어 에셋 생성 서비스 모듈

AI 영상 기획안(video_plan)을 받아 각 씬에 필요한
TTS 오디오 파일과 이미지 파일을 생성·다운로드합니다.

사용 외부 서비스:
    - Edge TTS (Microsoft): 한국어 나레이션 음성 합성 (무료)
    - Pollinations AI (https://pollinations.ai): 이미지 생성 AI (무료 API)

생성 파일 구조:
    temp_projects/
    └── {project_id}/
        ├── scene_1.mp3  (TTS 음성)
        ├── scene_1.jpg  (생성 이미지)
        ├── scene_2.mp3
        ├── scene_2.jpg
        └── ...
"""

import os
import time
import httpx
import random
import urllib.parse
import asyncio
import edge_tts

# 생성된 에셋 파일을 저장할 기본 디렉토리
BASE_DIR = "temp_projects"


def generate_assets(project_id: str, video_plan: dict) -> list:
    """
    영상 기획안의 각 씬에 대해 TTS 오디오와 이미지를 생성합니다.

    씬 처리 순서:
        1. Edge TTS로 나레이션 텍스트를 mp3 음성 파일로 변환
        2. Pollinations AI로 image_prompt에 맞는 이미지를 생성 및 다운로드

    Args:
        project_id (str): 파일 저장 경로 구분에 사용되는 Project UUID
        video_plan (dict): Gemini가 생성한 영상 기획안 (scenes 목록 포함)

    Returns:
        list: 각 씬의 에셋 경로 정보 목록
              [{"scene_number": 1, "audio_path": "...", "image_path": "...", "narration": "..."}, ...]
              TTS 또는 이미지 생성에 실패한 씬은 목록에서 제외됩니다.
    """
    # 프로젝트 전용 저장 디렉토리 생성 (이미 있으면 무시)
    project_path = os.path.join(BASE_DIR, project_id)
    os.makedirs(project_path, exist_ok=True)

    scene_assets = []
    scenes = video_plan.get("scenes", [])

    for scene in scenes:
        scene_num = scene.get("scene_number", 0)
        narration = scene.get("narration", "")
        image_prompt = scene.get("image_prompt", "")

        # ── TTS 음성 생성 ──────────────────────────────────────────────────
        audio_filename = f"scene_{scene_num}.mp3"
        audio_path = os.path.join(project_path, audio_filename)

        try:
            # ko-KR-SunHiNeural: Microsoft Azure의 한국어 여성 목소리
            voice = "ko-KR-SunHiNeural"
            communicate = edge_tts.Communicate(narration, voice)
            asyncio.run(communicate.save(audio_path))  # 비동기 저장을 동기로 실행
        except Exception as e:
            print(f"[Scene {scene_num}] 음성 저장 실패: {e}")
            continue  # 이 씬은 건너뛰고 다음 씬으로

        # ── 이미지 생성 및 다운로드 ────────────────────────────────────────
        image_filename = f"scene_{scene_num}.jpg"
        image_path = os.path.join(project_path, image_filename)

        # URL 인코딩 및 랜덤 시드로 이미지 다양성 확보
        safe_prompt = urllib.parse.quote(image_prompt)
        seed = random.randint(1, 100000)

        # 1080×1920 세로형(쇼츠/릴스) 비율로 이미지 요청
        image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1080&height=1920&nologo=true%seed={seed}"

        headers = {
            # 봇 차단 우회를 위한 브라우저 User-Agent 설정
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
        }

        # 네트워크 불안정을 대비한 재시도 로직 (최대 3회)
        max_retries = 3
        image_success = False

        for attempt in range(max_retries):
            try:
                response = httpx.get(
                    image_url, headers=headers, timeout=60.0, follow_redirects=True
                )
                response.raise_for_status()  # 4xx/5xx 응답 시 예외 발생

                # 이미지 바이너리를 파일로 저장
                with open(image_path, "wb") as f:
                    f.write(response.content)

                image_success = True
                break  # 성공 시 재시도 루프 탈출

            except Exception as e:
                print(
                    f"[Scene {scene_num}] Image Download Failed (Try {attempt+1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(5)  # 다음 재시도 전 5초 대기
                else:
                    print(f"[Scene {scene_num}] 최종 다운로드 실패")

        if not image_success:
            continue  # 이미지 다운로드 실패 시 이 씬을 최종 결과에서 제외

        # 성공한 씬의 에셋 경로 정보를 결과 목록에 추가
        scene_assets.append(
            {
                "scene_number": scene_num,
                "audio_path": audio_path,   # TTS mp3 파일 경로
                "image_path": image_path,   # 생성 이미지 파일 경로
                "narration": narration,     # 자막 생성에 재사용
            }
        )

        # Pollinations AI 서버 과부하 방지를 위한 씬 간 딜레이
        time.sleep(5)

    return scene_assets
