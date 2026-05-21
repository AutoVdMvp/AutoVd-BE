from pathlib import Path

import yaml

from app.prompts.prompt_types import PromptTemplate


class PromptRegistry:
    """Loads YAML prompt templates and exposes them by prompt id."""

    def __init__(self, template_dir: str | Path = "app/prompts/templates"):
        self.template_dir = Path(template_dir)
        self._templates: dict[str, PromptTemplate] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Validate and cache every YAML template in the configured directory."""
        if not self.template_dir.exists():
            raise ValueError(f"Prompt template directory not found: {self.template_dir}")

        for path in sorted(self.template_dir.glob("*.yaml")):
            with path.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file)

            if not isinstance(data, dict):
                raise ValueError(f"Invalid prompt template YAML: {path}")

            template = PromptTemplate(**data)
            self._templates[template.id] = template

    def get(self, prompt_id: str) -> PromptTemplate:
        """Return a single template or fail fast when the id is unknown."""
        template = self._templates.get(prompt_id)

        if template is None:
            raise ValueError(f"Prompt template not found: {prompt_id}")

        return template

    def list(self) -> list[PromptTemplate]:
        """Return all loaded templates for API discovery and prompt tooling."""
        return list(self._templates.values())

