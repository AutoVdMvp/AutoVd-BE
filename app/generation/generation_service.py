from typing import Protocol

from app.ai.ai_service import AIService
from app.prompts.prompt_service import PromptService


class CharacterData(Protocol):
    """Minimum character fields required to render image prompts."""

    name: str
    appearance_prompt: str
    personality_prompt: str


class StyleData(Protocol):
    """Minimum style fields required to render image prompts."""

    name: str
    style_prompt: str
    negative_prompt: str


class GenerationService:
    """Coordinates prompt rendering and AI text generation workflows."""

    def __init__(
        self,
        prompt_service: PromptService,
        ai_service: AIService,
    ):
        self.prompt_service = prompt_service
        self.ai_service = ai_service

    async def generate_image_prompt(
        self,
        scene_description: str,
        character: CharacterData,
        style: StyleData,
    ) -> dict:
        """Generate an image prompt from scene, character, and style inputs."""
        prompt = self.prompt_service.render(
            prompt_id="image.prompt.generate",
            variables={
                "scene_description": scene_description,
                "character_name": character.name,
                "character_appearance": character.appearance_prompt,
                "character_personality": character.personality_prompt,
                "style_name": style.name,
                "style_prompt": style.style_prompt,
                "negative_prompt": style.negative_prompt,
            },
        )

        result = await self.ai_service.generate_text(prompt)

        return {
            "prompt_id": prompt.id,
            "prompt_version": prompt.version,
            "provider": prompt.provider,
            "model": prompt.model,
            "raw_result": result.text,
        }

