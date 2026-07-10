import re

from app.schemas.video import BuiltSubtitle, Scene

class SubtitleBuilder:
    """Scene[] -> BuiltSubtitle[] without external calls."""

    def __init__(self, *, max_chars_per_line: int = 18, max_lines: int = 2) -> None:
        self.max_chars_per_line = max_chars_per_line
        self.max_lines = max_lines

    def build(self, scenes: list[Scene]) -> list[BuiltSubtitle]:
        if not scenes:
            raise ValueError("Scene이 없어서 자막을 생성할 수 없습니다.")

        subtitles = []
        for scene in scenes:
            source_text = scene.subtitle or scene.narration
            text = _normalize_spaces(source_text)
            if not text:
                raise ValueError(f"[Scene {scene.index}] subtitle text가 비어 있습니다.")

            subtitles.append(
                BuiltSubtitle(
                    scene_index=scene.index,
                    text=self._wrap(text),
                )
            )
        return subtitles

    def _wrap(self, text: str) -> str:
        words = text.split(" ")
        lines: list[str] = []
        current = ""

        for word in words:
            candidate = word if not current else f"{current} {word}"
            if len(candidate) <= self.max_chars_per_line:
                current = candidate
                continue

            if current:
                lines.append(current)
            if len(word) > self.max_chars_per_line:
                lines.extend(_chunks(word, self.max_chars_per_line))
                current = ""
            else:
                current = word

        if current:
            lines.append(current)

        if len(lines) <= self.max_lines:
            return "\n".join(lines)

        kept = lines[: self.max_lines]
        kept[-1] = kept[-1].rstrip(".") + "..."
        return "\n".join(kept)

def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def _chunks(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]