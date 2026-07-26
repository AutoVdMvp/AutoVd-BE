from app.schemas.video import ImagePrompt, ImagePromptResult, Scene

_STYLE_SUFFIX = (
    "cinematic vertical composition, realistic editorial style, high detail, "
    "natural lighting, 9:16 shorts frame, no text, no watermark"
)
_NEGATIVE_PROMPT = "text, watermark, logo, distorted faces, blurry, low quality"


class ImagePromptGenerator:
    """Scene[] -> ImagePromptResult without another LLM call."""

    def generate(
        self,
        scenes: list[Scene],
        *,
        aspect_ratio: str = "9:16",
    ) -> ImagePromptResult:
        if not scenes:
            raise ValueError("Scene이 없어서 이미지 프롬프트를 생성할 수 없습니다.")

        prompts = []
        seen: set[int] = set()
        for scene in scenes:
            if scene.index in seen:
                raise ValueError(f"중복된 Scene index입니다: {scene.index}")
            seen.add(scene.index)
            concept = scene.image_concept.strip()
            if not concept:
                raise ValueError(
                    f"[Scene {scene.index}] image_concept가 비어 있습니다."
                )

            prompts.append(
                ImagePrompt(
                    scene_index=scene.index,
                    image_concept=concept,
                    # 고정된 스타일과 aspect ratio를 결합하여 최종 프롬프트 생성
                    prompt=f"{concept}, {_STYLE_SUFFIX}, aspect ratio {aspect_ratio}",
                    negative_prompt=_NEGATIVE_PROMPT,
                )
            )

        return ImagePromptResult(prompts=prompts)
