from google import genai
from google.genai import types

from app.core.config import settings

class GeminiClient:
    """Thin concrete Gemini client. No Protocol seam until a second adapter exists."""

    MODEL_NAME = "gemini-2.0-flash"  # 최신 모델명으로 업데이트 제안 (기존 gemini-flash-latest도 가능)
    TEMPERATURE = 0.7

    def __init__(self) -> None:
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def generate_content(self, *, user_prompt: str, system_instruction: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=self.TEMPERATURE,
                    response_mime_type="application/json",
                ),
            )
            return response.text
        except Exception as exc:
            raise RuntimeError(f"Gemini 영상 기획 호출 중 오류가 발생했습니다: {exc}") from exc