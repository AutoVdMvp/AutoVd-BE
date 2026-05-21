from app.ai.providers.base import AIProvider, GenerateTextInput, GenerateTextResult
from app.prompts.prompt_types import RenderedPrompt


class AIService:
    """Routes rendered prompts to the configured AI provider."""

    def __init__(self, providers: dict[str, AIProvider]):
        self.providers = providers

    def get_provider(self, provider_name: str) -> AIProvider:
        """Resolve a provider name from the prompt template configuration."""
        provider = self.providers.get(provider_name)

        if provider is None:
            raise ValueError(f"Unsupported AI provider: {provider_name}")

        return provider

    async def generate_text(
        self,
        prompt: RenderedPrompt,
    ) -> GenerateTextResult:
        """Convert a rendered prompt into the provider input contract."""
        provider = self.get_provider(prompt.provider)

        return await provider.generate_text(
            GenerateTextInput(
                model=prompt.model,
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
            )
        )

