from typing import Any

from app.prompts.prompt_registry import PromptRegistry
from app.prompts.prompt_renderer import PromptRenderer
from app.prompts.prompt_types import PromptTemplate, RenderedPrompt


class PromptService:
    """Facade for prompt lookup and rendering."""

    def __init__(
        self,
        registry: PromptRegistry,
        renderer: PromptRenderer,
    ):
        self.registry = registry
        self.renderer = renderer

    def render(
        self,
        prompt_id: str,
        variables: dict[str, Any],
    ) -> RenderedPrompt:
        """Load a template by id and render it with the supplied variables."""
        template = self.registry.get(prompt_id)
        return self.renderer.render(template=template, variables=variables)

    def list_templates(self) -> list[PromptTemplate]:
        """Expose prompt metadata to API clients and internal tooling."""
        return self.registry.list()

