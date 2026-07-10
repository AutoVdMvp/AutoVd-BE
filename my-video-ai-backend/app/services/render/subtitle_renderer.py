import os

from moviepy.editor import TextClip

from app.core.config import settings
from app.schemas.video import BuiltSubtitle, SubtitleStyle

def default_font_path() -> str:
    if settings.VIDEO_FONT_PATH:
        return settings.VIDEO_FONT_PATH
    return "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"

def default_subtitle_style() -> SubtitleStyle:
    return SubtitleStyle(font_path=default_font_path())

class SubtitleRenderer:
    """BuiltSubtitle + style + duration -> MoviePy TextClip."""

    def render(
        self,
        subtitle: BuiltSubtitle,
        style: SubtitleStyle,
        *,
        duration_sec: float,
        canvas_size: tuple[int, int],
    ):
        width, height = canvas_size
        x_align, y_ratio = style.position
        
        # TextClip은 내부적으로 ImageMagick을 호출합니다.
        clip = TextClip(
            subtitle.text,
            fontsize=style.font_size,
            color=style.color,
            bg_color=style.bg_color,
            font=style.font_path,
            method="caption",
            size=(int(width * style.max_width_ratio), None),
        ).set_duration(duration_sec)
        
        return clip.set_position((x_align, height * y_ratio))