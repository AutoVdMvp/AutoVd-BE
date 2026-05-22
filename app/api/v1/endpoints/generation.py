from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies import get_generation_service
from app.generation.generation_service import GenerationService


router = APIRouter()


class CharacterInput(BaseModel):
    name: str
    appearance_prompt: str
    personality_prompt: str


class StyleInput(BaseModel):
    name: str
    style_prompt: str
    negative_prompt: str


class GenerateImagePromptRequest(BaseModel):
    scene_description: str
    character: CharacterInput
    style: StyleInput


class GenerateImagePromptResponse(BaseModel):
    prompt_id: str
    prompt_version: int
    provider: str
    model: str
    raw_result: str


@router.post("/image-prompt", response_model=GenerateImagePromptResponse)
async def generate_image_prompt(
    request: GenerateImagePromptRequest,
    generation_service: GenerationService = Depends(get_generation_service),
) -> GenerateImagePromptResponse:
    try:
        result = await generation_service.generate_image_prompt(
            scene_description=request.scene_description,
            character=request.character,
            style=request.style,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return GenerateImagePromptResponse(**result)

