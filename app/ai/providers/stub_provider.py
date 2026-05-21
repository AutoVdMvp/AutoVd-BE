import json

from app.ai.providers.base import AIProvider, GenerateTextInput, GenerateTextResult


class StubProvider(AIProvider):
    """Deterministic provider used until real external AI APIs are connected."""

    def __init__(self, provider_name: str = "stub"):
        self.provider_name = provider_name

    async def generate_text(
        self,
        input_data: GenerateTextInput,
    ) -> GenerateTextResult:
        # Keep the response JSON-shaped so API consumers can build against it.
        payload = {
            "provider": self.provider_name,
            "model": input_data.model,
            "image_prompt": "stub image prompt generated from rendered user prompt",
            "negative_prompt": "stub negative prompt",
            "camera_angle": "medium shot",
            "mood": "warm",
        }

        return GenerateTextResult(
            text=json.dumps(payload, ensure_ascii=False),
            input_tokens=None,
            output_tokens=None,
        )

