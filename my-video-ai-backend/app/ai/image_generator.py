import os
import random
import time
import urllib.parse
import httpx

from app.services.artifacts.local_store import LocalStore
from app.schemas.video import GeneratedImage, ImagePromptResult

IMAGE_SIZE = (1080, 1920)

class PollinationsImageClient:
    """Concrete Pollinations client used by ImageGenerator."""

    BASE_URL = "https://image.pollinations.ai/prompt"
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 5
    POST_SUCCESS_DELAY_SECONDS = 3
    TIMEOUT_SECONDS = 120.0
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def render(
        self,
        prompt: str,
        dest: str,
        *,
        size: tuple[int, int] = IMAGE_SIZE,
        negative_prompt: str | None = None,
    ) -> str:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        width, height = size
        image_url = self._image_url(
            prompt,
            width=width,
            height=height,
            negative_prompt=negative_prompt,
        )
        headers = {"User-Agent": self.USER_AGENT}
        last_error: Exception | None = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = httpx.get(
                    image_url,
                    headers=headers,
                    timeout=self.TIMEOUT_SECONDS,
                    follow_redirects=True,
                )
                response.raise_for_status()
                with open(dest, "wb") as image_file:
                    image_file.write(response.content)
                time.sleep(self.POST_SUCCESS_DELAY_SECONDS)
                return dest
            except Exception as exc:
                last_error = exc
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY_SECONDS)

        raise RuntimeError(f"Pollinations 이미지 다운로드 실패: {last_error}")

    def _image_url(
        self,
        prompt: str,
        *,
        width: int,
        height: int,
        negative_prompt: str | None,
    ) -> str:
        full_prompt = prompt
        if negative_prompt:
            full_prompt = f"{prompt}. Avoid: {negative_prompt}"
        safe_prompt = urllib.parse.quote(full_prompt)
        seed = random.randint(1, 100000)
        return (
            f"{self.BASE_URL}/{safe_prompt}"
            f"?width={width}&height={height}&nologo=true&seed={seed}"
        )

class ImageGenerator:
    """ImagePromptResult -> GeneratedImage[]."""

    def __init__(
        self,
        client: PollinationsImageClient | None = None,
        store: LocalStore | None = None,
    ) -> None:
        self.client = client or PollinationsImageClient()
        self.store = store or LocalStore()

    def generate(self, project_id: str, prompt_result: ImagePromptResult) -> list[GeneratedImage]:
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