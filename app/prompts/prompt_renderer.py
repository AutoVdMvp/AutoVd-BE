from typing import Any

from jinja2 import Template

from app.prompts.prompt_types import PromptTemplate, RenderedPrompt


class PromptRenderer:
    """Renders validated prompt templates with runtime variables."""

    def render(
        self,
        template: PromptTemplate,
        variables: dict[str, Any],
    ) -> RenderedPrompt:
        # Fail before rendering so prompt mistakes are visible to API callers.
        missing = [key for key in template.input_variables if key not in variables]

        if missing:
            raise ValueError(f"Missing prompt variables: {missing}")

        system_prompt = Template(template.system_prompt).render(**variables)
        user_prompt = Template(template.user_prompt).render(**variables)

        return RenderedPrompt(
            id=template.id,
            version=template.version,
            provider=template.provider,
            model=template.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_format=template.output_format,
            variables=variables,
        )

