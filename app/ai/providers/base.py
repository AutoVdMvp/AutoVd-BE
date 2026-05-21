from abc import ABC, abstractmethod

from pydantic import BaseModel


class GenerateTextInput(BaseModel):
    """Provider-agnostic text generation input."""

    model: str
    system_prompt: str
    user_prompt: str


class GenerateTextResult(BaseModel):
    """Normalized text generation result returned by every provider."""

    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class AIProvider(ABC):
    """Common interface for Gemini, OpenAI, OpenRouter, and test providers."""

    @abstractmethod
    async def generate_text(
        self,
        input_data: GenerateTextInput,
    ) -> GenerateTextResult:
        raise NotImplementedError

