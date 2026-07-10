"""Orchestrate the v4 video generation pipeline."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from app.services.video_generation.ai.image_generator import ImageGenerator
from app.services.video_generation.ai.image_prompt_generator import ImagePromptGenerator
from app.services.video_generation.ai.script_generator import ScriptGenerator
from app.services.video_generation.ai.tts_generator import TTSGenerator
from app.services.video_generation.artifacts.local_store import LocalStore
from app.services.video_generation.crawling.crawler import Crawler
from app.services.video_generation.render.video_compositor import VideoCompositor
from app.services.video_generation.subtitle.subtitle_builder import SubtitleBuilder
from app.services.video_generation.timeline.duration_aligner import DurationAligner
from app.schemas.video import VideoGenerateRequest, VideoOutput

ProgressCallback = Callable[[str, int], None]


def run_pipeline(
    project_id: str,
    request: VideoGenerateRequest,
    *,
    progress: ProgressCallback | None = None,
) -> VideoOutput:
    """Run URL/text input through planning, asset generation, alignment, and render."""
    store = LocalStore()

    _report(progress, "crawling", 10)
    source = Crawler().fetch(request)

    _report(progress, "ai_planning", 30)
    script = ScriptGenerator().generate(source, request)
    image_prompts = ImagePromptGenerator().generate(
        script.scenes,
        aspect_ratio=request.aspect_ratio,
    )

    _report(progress, "asset_generation", 60)
    image_generator = ImageGenerator(store=store)
    tts_generator = TTSGenerator(store=store)
    
    # 이미지 생성과 오디오 생성을 동시에 실행 (병렬 처리로 속도 향상)
    with ThreadPoolExecutor(max_workers=2) as executor:
        image_future = executor.submit(image_generator.generate, project_id, image_prompts)
        audio_future = executor.submit(tts_generator.generate, project_id, script.scenes)
        images = image_future.result()
        audios = audio_future.result()

    subtitles = SubtitleBuilder().build(script.scenes)
    timed_scenes = DurationAligner().align(script.scenes, images, audios, subtitles)

    _report(progress, "video_editing", 80)
    return VideoCompositor(store=store).compose(
        project_id,
        title=script.title,
        timed_scenes=timed_scenes,
        images=images,
        audios=audios,
        subtitles=subtitles,
    )


def _report(progress: ProgressCallback | None, step: str, percent: int) -> None:
    if progress:
        progress(step, percent)