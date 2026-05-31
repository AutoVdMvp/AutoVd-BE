"""
영상 합성(편집) 서비스 모듈

각 씬의 이미지, TTS 음성, 나레이션 자막을 결합하여
최종 MP4 영상 파일을 생성합니다.

사용 라이브러리:
    - MoviePy: Python 영상 편집 라이브러리
    - ImageMagick: TextClip 렌더링에 필요 (Windows: 경로 수동 지정)

출력 파일 위치:
    temp_projects/{project_id}/{project_id}_final.mp4
"""

import os

# Windows 환경에서 ImageMagick 실행 파일 경로를 환경 변수로 지정
# MoviePy의 TextClip(자막)은 ImageMagick에 의존합니다.
if os.name == "nt":
    os.environ["IMAGEMAGICK_BINARY"] = (
        r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
    )

# Docker/Linux에서는 Dockerfile에서 설치한 나눔고딕을 사용하고,
# Windows 로컬 실행 시에는 맑은 고딕 경로를 기본값으로 사용합니다.
VIDEO_FONT_PATH = os.getenv(
    "VIDEO_FONT_PATH",
    r"C:\Windows\Fonts\malgun.ttf"
    if os.name == "nt"
    else "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
)

from moviepy.editor import (
    ImageClip,           # 이미지를 영상 클립으로 변환
    AudioFileClip,       # 오디오 파일을 클립으로 로드
    TextClip,            # 텍스트(자막) 클립 생성
    CompositeVideoClip,  # 여러 클립을 하나의 화면에 합성
    concatenate_videoclips,  # 여러 클립을 시간순으로 이어붙임
)


def merge_video(project_id: str, scene_assets: list) -> str:
    """
    각 씬의 에셋(이미지 + 음성 + 자막)을 합쳐 최종 MP4 영상을 생성합니다.

    씬별 처리 과정:
        1. TTS 오디오 파일 로드 → 재생 시간 결정
        2. 이미지 클립 생성 → 오디오 길이에 맞게 duration 설정
        3. 자막 TextClip 생성 → 화면 하단 중앙에 배치
        4. 이미지 + 자막을 CompositeVideoClip으로 합성 → 오디오 결합
    최종적으로 모든 씬 클립을 concatenate하여 mp4로 렌더링합니다.

    Args:
        project_id (str): 출력 파일 경로 및 이름에 사용되는 Project UUID
        scene_assets (list): generate_assets()가 반환한 씬 에셋 목록

    Returns:
        str: 생성된 최종 영상 파일 경로 (예: "temp_projects/proj-123/proj-123_final.mp4")

    Raises:
        ValueError: scene_assets가 비어있거나 유효한 클립이 하나도 없을 때
    """
    if not scene_assets:
        raise ValueError("Scene_assets 파일이 없습니다.")

    project_path = os.path.join("temp_projects", project_id)
    output_filename = f"{project_id}_final.mp4"
    output_path = os.path.join(project_path, output_filename)

    clips = []

    # 각 씬을 하나의 영상 클립으로 변환
    for asset in scene_assets:
        audio_path = asset.get("audio_path")
        image_path = asset.get("image_path")
        narration = asset.get("narration")
        scene_num = asset.get("scene_number")

        # 파일이 실제로 존재하는지 확인 (생성 실패한 에셋 건너뜀)
        if not os.path.exists(audio_path) or not os.path.exists(image_path):
            print(f"[Scene {scene_num}] 파일 누락으로 인해 건너뜁니다.")
            continue

        try:
            # TTS 오디오 클립 로드 (재생 시간이 씬 전체 길이를 결정)
            audio_clip = AudioFileClip(audio_path)

            # 이미지를 정적 영상 클립으로 변환 (오디오 길이와 동일하게 설정)
            image_clip = ImageClip(image_path).set_duration(audio_clip.duration)

            # 한국어 자막 클립 생성
            # - method="caption": 긴 텍스트를 자동 줄바꿈하여 지정 너비에 맞춤
            # - bg_color: 가독성을 위해 반투명 검정 배경 적용
            # - size=(이미지 너비의 85%, None): 좌우 여백 확보
            txt_clip = TextClip(
                narration,
                fontsize=32,
                color="white",
                bg_color="rgba(0,0,0,0.6)",
                font=VIDEO_FONT_PATH,  # 실행 환경별 한국어 지원 폰트 경로
                method="caption",
                size=(image_clip.w * 0.85, None),
            ).set_duration(audio_clip.duration)

            # 자막 위치: 화면 중앙 하단 (전체 높이의 65% 지점)
            txt_clip = txt_clip.set_position(("center", image_clip.h * 0.65))

            # 이미지 위에 자막을 올려 합성 후 오디오 결합
            video_clip = CompositeVideoClip([image_clip, txt_clip])
            video_clip = video_clip.set_audio(audio_clip)
            clips.append(video_clip)

        except Exception as e:
            print(f"[Scene {scene_num}] Clip 생성 중 오류 발생: {str(e)}")
            continue  # 이 씬은 건너뛰고 나머지 씬으로 계속

    # 유효한 클립이 하나도 없으면 영상 생성 불가
    if not clips:
        raise ValueError("Video Clip이 만들어지지 않아서 취소합니다.")

    # 모든 씬 클립을 순서대로 이어붙여 최종 영상 생성
    # method="compose": 클립 간 크기/FPS 차이를 자동으로 조율
    final_video = concatenate_videoclips(clips, method="compose")

    # MP4 파일로 렌더링
    # - preset="ultrafast": 렌더링 속도 최우선 (파일 크기는 커지지만 빠름)
    # - threads=4: 멀티스레드 인코딩으로 속도 향상
    # - logger=None: 콘솔 진행률 출력 비활성화 (Celery 로그와 혼재 방지)
    final_video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4,
        logger=None,
    )

    # 메모리 누수 방지를 위해 모든 클립 리소스 해제
    for clip in clips:
        clip.close()

    final_video.close()

    return output_path
