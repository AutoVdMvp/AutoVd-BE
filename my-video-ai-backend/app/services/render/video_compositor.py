import os

from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips,
)

from app.services.artifacts.local_store import LocalStore
from app.services.render.subtitle_renderer import (
    SubtitleRenderer,
    default_subtitle_style,
)

from app.schemas.video import (
    BuiltSubtitle,
    GeneratedAudio,
    GeneratedImage,
    SubtitleStyle,
    TimedScene,
    VideoOutput,
)

class VideoCompositor:
    """Compose timed scenes, images, audios, and subtitles into an mp4."""

    FPS = 24
    CODEC = "libx264"
    AUDIO_CODEC = "aac"
    PRESET = "ultrafast"
    THREADS = 4
    DURATION_TOLERANCE = 0.5

    def __init__(
        self,
        *,
        store: LocalStore | None = None,
        subtitle_renderer: SubtitleRenderer | None = None,
    ) -> None:
        self.store = store or LocalStore()
        self.subtitle_renderer = subtitle_renderer or SubtitleRenderer()

    def compose(
        self,
        project_id: str,
        *,
        title: str,
        timed_scenes: list[TimedScene],
        images: list[GeneratedImage],
        audios: list[GeneratedAudio],
        subtitles: list[BuiltSubtitle],
        style: SubtitleStyle | None = None,
    ) -> VideoOutput:
        if not timed_scenes:
            raise ValueError("TimedScene이 없어서 영상 합성을 시작할 수 없습니다.")

        image_map = {image.scene_index: image for image in images}
        audio_map = {audio.scene_index: audio for audio in audios}
        subtitle_map = {subtitle.scene_index: subtitle for subtitle in subtitles}
        subtitle_style = style or default_subtitle_style()
        output_path = self.store.video_path(project_id)
        clips = []
        final_video = None

        try:
            for scene in timed_scenes:
                clips.append(
                    self.build_scene_clip(
                        scene,
                        image_map[scene.index],
                        audio_map[scene.index],
                        subtitle_map[scene.index],
                        subtitle_style,
                    )
                )

            final_video = concatenate_videoclips(clips, method="compose")
            self._verify_total_duration(final_video.duration, timed_scenes)
            final_video.write_videofile(
                output_path,
                fps=self.FPS,
                codec=self.CODEC,
                audio_codec=self.AUDIO_CODEC,
                preset=self.PRESET,
                threads=self.THREADS,
                logger=None,
            )
            if not os.path.exists(output_path):
                raise FileNotFoundError(f"final video 파일 누락: {output_path}")
            return VideoOutput(title=title, video_path=output_path, duration_sec=final_video.duration)
        finally:
            for clip in clips:
                clip.close()
            if final_video is not None:
                final_video.close()

    def build_scene_clip(
        self,
        scene: TimedScene,
        image: GeneratedImage,
        audio: GeneratedAudio,
        subtitle: BuiltSubtitle,
        style: SubtitleStyle | None = None,
    ):
        self._ensure_file(image.path, scene.index, "image")
        self._ensure_file(audio.path, scene.index, "audio")

        duration = scene.duration_sec
        subtitle_style = style or default_subtitle_style()

        try:
            audio_clip = AudioFileClip(audio.path).set_duration(duration)
            image_clip = ImageClip(image.path).set_duration(duration)
            subtitle_clip = self.subtitle_renderer.render(
                subtitle,
                subtitle_style,
                duration_sec=duration,
                canvas_size=(image_clip.w, image_clip.h),
            )
            video_clip = CompositeVideoClip([image_clip, subtitle_clip]).set_duration(duration)
            return video_clip.set_audio(audio_clip)
        except Exception as exc:
            raise RuntimeError(f"[Scene {scene.index}] Clip 생성 실패: {exc}") from exc

    def _verify_total_duration(
        self,
        actual_duration: float,
        timed_scenes: list[TimedScene],
    ) -> None:
        expected = sum(scene.duration_sec for scene in timed_scenes)
        if abs(actual_duration - expected) > self.DURATION_TOLERANCE:
            raise ValueError(
                "합쳐진 영상 길이가 씬 duration 합과 일치하지 않습니다. "
                f"(기대: {expected:.2f}s, 실제: {actual_duration:.2f}s)"
            )

    @staticmethod
    def _ensure_file(path: str, scene_index: int, label: str) -> None:
        if not os.path.exists(path):
            raise FileNotFoundError(f"[Scene {scene_index}] {label} 파일 누락: {path}")