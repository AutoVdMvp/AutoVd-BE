from fastapi import APIRouter

from app.api.v1.endpoints import generation, prompts


router = APIRouter()

router.include_router(
    generation.router,
    prefix="/generation",
    tags=["generation"],
)
router.include_router(
    prompts.router,
    prefix="/prompts",
    tags=["prompts"],
)

