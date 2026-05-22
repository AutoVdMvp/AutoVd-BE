import os

if os.name == 'nt':
    os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

from moviepy.editor import ImageClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips

def merge_video(project_id: str, scene_assets: list) -> str:
    # Scene이 없는 경우
    if not scene_assets:
        raise ValueError("Scene_assets 파일이 없습니다.")
    
    project_path = os.path.join("temp_projects", project_id)
    output_filename = f"{project_id}_final.mp4"
    output_path = os.path.join(project_path, output_filename)

    clips = []

    # Scene마다 Image와 Voice를 합친 Clip 생성
    for asset in scene_assets:
        audio_path = asset.get("audio_path")
        image_path = asset.get("image_path")
        narration = asset.get("narration")
        scene_num = asset.get("scene_number")

        if not os.path.exists(audio_path) or not os.path.exists(image_path):
            print(f"[Scene {scene_num}] 파일 누락으로 인해 건너뜁니다.")
            continue

        try:
            # Audio File 불러오기
            audio_clip = AudioFileClip(audio_path)

            # Image File 불러오기, 화면에 머무는 시간을 Audio와 맞춤
            image_clip = ImageClip(image_path).set_duration(audio_clip.duration)

            # 자막 Clip 생성
            txt_clip = TextClip(
                narration,
                fontsize=32,
                color='white',
                bg_color='rgba(0,0,0,0.6)',
                font='C:/Windows/Fonts/malgun.ttf',
                method='caption',
                size=(image_clip.w * 0.85, None)
            ).set_duration(audio_clip.duration)
            txt_clip = txt_clip.set_position(('center', image_clip.h*0.65))

            # Image에 Audio 입력
            video_clip = CompositeVideoClip([image_clip, txt_clip])
            video_clip = video_clip.set_audio(audio_clip)
            clips.append(video_clip)
        
        except Exception as e:
            print(f"[Scene {scene_num}] Clip 생성 중 오류 발생: {str(e)}")
            continue
    
    # Clip이 없으면 중지
    if not clips:
        raise ValueError("Video Clip이 만들어지지 않아서 취소합니다.")
    
    # 4개의 Clip 순서대로 합치기
    final_video = concatenate_videoclips(clips, method="compose")

    # mp4 File로 렌더링
    final_video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4,
        logger=None
    )

    # Memory 정리
    for clip in clips:
        clip.close()

    final_video.close()

    return output_path