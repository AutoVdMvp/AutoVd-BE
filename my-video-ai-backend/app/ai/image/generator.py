import os

from app.ai.image.client import IMAGE_SIZE, PollinationsImageClient
from app.services.artifacts.local_store import LocalStore
from app.schemas.video import GeneratedImage, ImagePromptResult


class ImageGenerator:
    """ImagePromptResult -> GeneratedImage[]."""

    def __init__(
        self,
        client: PollinationsImageClient | None = None,
        store: LocalStore | None = None,
    ) -> None:
        self.client = client or PollinationsImageClient()
        self.store = store or LocalStore()

    def generate(
        self,
        project_id: str,
        prompt_result: ImagePromptResult,
    ) -> list[GeneratedImage]:
        if not prompt_result.prompts:
            raise ValueError("이미지 프롬프트가 없어서 이미지를 생성할 수 없습니다.")

        images = []
        for prompt in prompt_result.prompts:
            dest = self.store.image_path(project_id, prompt.scene_index)
            try:
                path = self.client.render(
                    prompt.prompt,
                    dest,
                    size=IMAGE_SIZE,
                    negative_prompt=prompt.negative_prompt,
                )
            except Exception as exc:
                raise RuntimeError(
                    f"[Scene {prompt.scene_index}] 이미지 생성 실패: {exc}"
                ) from exc

            if not os.path.exists(path):
                raise FileNotFoundError(f"[Scene {prompt.scene_index}] image 파일 누락: {path}")
            images.append(GeneratedImage(scene_index=prompt.scene_index, path=path))

        return images
