import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from pydantic import BaseModel

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.models import User, Project
from app.schemas.projects import ProjectResponse                                       

router = APIRouter()

# 요청 Data 규격
class CreateProjectRequest(BaseModel):
    article_url: str

# Project List 조회 API
@router.get("/", response_model=List[ProjectResponse])
async def get_my_projects(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 현재 로그인한 User의 Project 조회
    result = await db.execute(select(Project).where(Project.user_id == current_user.id))
    return result.scalars().all()

# New Project 생성
@router.post("/create")
async def create_project(request: CreateProjectRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        # URL 유효성 검사
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}

        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.get(request.article_url, headers=headers)
            response.raise_for_status()
    
    except httpx.TimeoutException:
        raise HTTPException(status_code=400, detail="Link is not responding.")
    
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"접근할 수 없는 링크입니다. (Status Code: {e.response.status_code})")
    
    except httpx.RequestError:
        raise HTTPException(status_code=400, detail="잘못된 형식의 링크이거나, 아예 존재하지 않는 도메인입니다.")
    
    # DB에 Project Data Save
    new_project = Project(
        user_id=current_user.id,
        original_url=request.article_url,
        status="pending"
    )
    
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    # DB에서 발급된 UUID 반환
    return {
        "message": "프로젝트가 성공적으로 생성되었습니다.",
        "project_id": str(new_project.id),
        "article_url": new_project.original_url
    }