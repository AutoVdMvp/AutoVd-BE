from collections.abc import Iterable
from pydantic import BaseModel

from app.schemas.video import (
    BuiltSubtitle,
    GeneratedAudio,
    GeneratedImage,
    Scene,
    TimedScene,
)

class DurationAligner:
    """Pure join and validation gate for image/audio/subtitle scene sets."""

    def align(
        self,
        scenes: list[Scene],
        images: list[GeneratedImage],
        audios: list[GeneratedAudio],
        subtitles: list[BuiltSubtitle],
    ) -> list[TimedScene]:
        if not scenes:
            raise ValueError("Scene이 없어서 duration을 정렬할 수 없습니다.")

        scene_indexes = _indexes(scenes, "Scene")
        image_map = _by_index(images, "image")
        audio_map = _by_index(audios, "audio")
        subtitle_map = _by_index(subtitles, "subtitle")

        for label, items in (
            ("image", image_map),
            ("audio", audio_map),
            ("subtitle", subtitle_map),
        ):
            missing = scene_indexes - set(items)
            extra = set(items) - scene_indexes
            if missing or extra:
                raise ValueError(
                    f"{label} scene_index 정합이 맞지 않습니다. "
                    f"missing={sorted(missing)}, extra={sorted(extra)}"
                )

        timed_scenes = []
        for scene in scenes:
            audio = audio_map[scene.index]
            if audio.duration_sec <= 0:
                raise ValueError(f"[Scene {scene.index}] audio duration_sec는 0보다 커야 합니다.")
            timed_scenes.append(
                TimedScene(**scene.model_dump(), duration_sec=audio.duration_sec)
            )

        return timed_scenes

def _indexes(items: Iterable[BaseModel], label: str) -> set[int]:
    indexes: set[int] = set()
    for item in items:
        index = getattr(item, "index", None)
        if index is None:
            index = getattr(item, "scene_index")
        if index in indexes:
            raise ValueError(f"중복된 {label} index입니다: {index}")
        indexes.add(index)
    return indexes

def _by_index(items: Iterable[BaseModel], label: str) -> dict[int, BaseModel]:
    mapped = {}
    for item in items:
        index = getattr(item, "scene_index")
        if index in mapped:
            raise ValueError(f"중복된 {label} scene_index입니다: {index}")
        mapped[index] = item
    return mapped