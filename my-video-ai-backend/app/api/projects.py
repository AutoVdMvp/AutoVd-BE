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