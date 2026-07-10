from pydantic import BaseModel, HttpUrl, model_validator
from app.core.config import settings


class VideoGenerateRequest(BaseModel):
    url: HttpUrl | None = None
    text: str | None = None
    target_seconds: int = 30
    aspect_ratio: str = "9:16"
    style: str = "shorts"

    @model_validator(mode="after")
    def require_url_or_text(self):
        if not self.url and not (self.text and self.text.strip()):
            raise ValueError("url 또는 text 중 하나는 필요합니다.")
        return self


class CrawledSource(BaseModel):
    url: str | None = None
    title: str | None = None
    content: str


class Scene(BaseModel):
    index: int
    narration: str
    image_concept: str
    estimated_duration_sec: float | None = None
    subtitle: str | None = None


class ScriptResult(BaseModel):
    title: str
    full_script: str
    scenes: list[Scene]


class ImagePrompt(BaseModel):
    scene_index: int
    prompt: str
    image_concept: str
    negative_prompt: str | None = None


class ImagePromptResult(BaseModel):
    prompts: list[ImagePrompt]


class GeneratedImage(BaseModel):
    scene_index: int
    path: str


class GeneratedAudio(BaseModel):
    scene_index: int
    path: str
    duration_sec: float


class BuiltSubtitle(BaseModel):
    scene_index: int
    text: str


class TimedScene(Scene):
    duration_sec: float


class SubtitleStyle(BaseModel):
    font_path: str = settings.VIDEO_FONT_PATH
    font_size: int = 32
    color: str = "white"
    bg_color: str = "rgba(0,0,0,0.6)"
    position: tuple[str, float] = ("center", 0.65)
    max_width_ratio: float = 0.85


class VideoOutput(BaseModel):
    title: str
    video_path: str
    duration_sec: float
