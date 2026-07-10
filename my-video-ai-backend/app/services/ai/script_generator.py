import json
from typing import Any
from pydantic import ValidationError

from app.services.ai.gemini_client import GeminiClient
from app.services.ai.prompts.script_prompt import SYSTEM_INSTRUCTION
from app.schemas.video import (
    CrawledSource,
    ScriptResult,
    VideoGenerateRequest,
)

class ScriptGenerator:
    """CrawledSource -> ScriptResult."""

    def __init__(self, client: GeminiClient | None = None) -> None:
        self.client = client or GeminiClient()

    def generate(
        self,
        source: CrawledSource,
        request: VideoGenerateRequest,
    ) -> ScriptResult:
        response_text = self.client.generate_content(
            user_prompt=self._user_prompt(source, request),
            system_instruction=SYSTEM_INSTRUCTION,
        )

        try:
            raw = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Gemini가 올바른 JSON 형식을 반환하지 않았습니다. 원본 응답:\n{response_text}"
            ) from exc

        try:
            result = ScriptResult.model_validate(_normalize_script_payload(raw))
        except ValidationError as exc:
            raise ValueError("Gemini 응답이 ScriptResult 계약을 만족하지 않습니다.") from exc

        _validate_script_result(result)
        return result

    @staticmethod
    def _user_prompt(source: CrawledSource, request: VideoGenerateRequest) -> str:
        title_line = f"제목: {source.title}\n" if source.title else ""
        return (
            f"{title_line}"
            f"목표 길이: {request.target_seconds}초\n"
            f"화면비: {request.aspect_ratio}\n"
            f"스타일: {request.style}\n\n"
            f"본문:\n{source.content}"
        )

def _normalize_script_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Accept v4 payloads and migrate the previous scene_number/image_prompt shape."""
    raw_scenes = raw.get("scenes") or []
    scenes = []
    narrations = []

    for position, raw_scene in enumerate(raw_scenes):
        if not isinstance(raw_scene, dict):
            scenes.append(raw_scene)
            continue

        index = raw_scene.get("index")
        if index is None and raw_scene.get("scene_number") is not None:
            index = int(raw_scene["scene_number"]) - 1
        if index is None:
            index = position

        narration = raw_scene.get("narration", "")
        image_concept = raw_scene.get("image_concept") or raw_scene.get("image_prompt", "")
        narrations.append(str(narration))
        scenes.append(
            {
                "index": index,
                "narration": narration,
                "image_concept": image_concept,
                "estimated_duration_sec": raw_scene.get("estimated_duration_sec"),
                "subtitle": raw_scene.get("subtitle"),
            }
        )

    title = raw.get("title") or "AutoVd Shorts"
    full_script = raw.get("full_script") or " ".join(narrations)
    return {"title": title, "full_script": full_script, "scenes": scenes}

def _validate_script_result(result: ScriptResult) -> None:
    if not result.scenes:
        raise ValueError("영상 기획안에 Scene이 없습니다.")

    seen: set[int] = set()
    for scene in result.scenes:
        if scene.index in seen:
            raise ValueError(f"중복된 Scene index입니다: {scene.index}")
        seen.add(scene.index)
        if not scene.narration.strip():
            raise ValueError(f"[Scene {scene.index}] narration이 비어 있습니다.")
        if not scene.image_concept.strip():
            raise ValueError(f"[Scene {scene.index}] image_concept가 비어 있습니다.")