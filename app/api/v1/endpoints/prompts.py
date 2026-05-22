from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies import get_prompt_service
from app.prompts.prompt_service import PromptService
from app.prompts.prompt_types import PromptTemplate, RenderedPrompt


router = APIRouter()


class RenderPromptRequest(BaseModel):
    prompt_id: str
    variables: dict[str, Any]


@router.get("", response_model=list[PromptTemplate])
def list_prompts(
    prompt_service: PromptService = Depends(get_prompt_service),
) -> list[PromptTemplate]:
    return prompt_service.list_templates()


@router.post("/render", response_model=RenderedPrompt)
def render_prompt(
    request: RenderPromptRequest,
    prompt_service: PromptService = Depends(get_prompt_service),
) -> RenderedPrompt:
    try:
        return prompt_service.render(
            prompt_id=request.prompt_id,
            variables=request.variables,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

