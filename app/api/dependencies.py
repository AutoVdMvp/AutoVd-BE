from functools import lru_cache

from app.ai.ai_service import AIService
from app.ai.providers.base import AIProvider
from app.ai.providers.stub_provider import StubProvider
from app.generation.generation_service import GenerationService
from app.prompts.prompt_registry import PromptRegistry
from app.prompts.prompt_renderer import PromptRenderer
from app.prompts.prompt_service import PromptService


@lru_cache
def get_prompt_service() -> PromptService:
    """Build the prompt service once and reuse it across requests."""
    registry = PromptRegistry()
    renderer = PromptRenderer()
    return PromptService(registry=registry, renderer=renderer)


@lru_cache
def get_ai_service() -> AIService:
    """Register available AI providers for the current MVP runtime."""
    providers: dict[str, AIProvider] = {
        # Gemini is mapped to the stub until the real provider is implemented.
        "stub": StubProvider(),
        "gemini": StubProvider(provider_name="gemini"),
    }
    return AIService(providers=providers)


@lru_cache
def get_generation_service() -> GenerationService:
    """Compose the high-level generation workflow from prompt and AI services."""
    return GenerationService(
        prompt_service=get_prompt_service(),
        ai_service=get_ai_service(),
    )

