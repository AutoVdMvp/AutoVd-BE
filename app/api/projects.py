from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from app.db.database import get_db
from app.models.models import User, Project

# from app.services.tasks import generate_video_task
# from app.core.celery_app import celery_app

router = APIRouter()

# 요청 Data 규격
class CreateProjectRequest(BaseModel):
    email: str = "test@test.com"
    article_url: str

@router.post("/create")
async def create_project(request: CreateProjectRequest, db: AsyncSession = Depends(get_db)):
    # User 조회(없으면 생성)
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalars().first()

    if not user:
        user = User(email=request.email, nickname="Test User")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    # DB에 Project Data Save
    new_project = Project(
        user_id=user.id,
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

# class VideoGenerateRequest(BaseModel):
#     article_url: str

# @router.post("/generate")
# async def start_video_generation(request: VideoGenerateRequest):
#     # 임시 Project ID 생성
#     mock_project_id = "proj-9999"

#     # .delay()를 사용하여 실행
#     task = generate_video_task.delay(mock_project_id, request.article_url)

#     # 영상이 완성되는 것을 기다리지 않고 즉시 반환
#     return {
#         "message": "영상 생성이 시작되었습니다.",
#         "project_id": mock_project_id,
#         "task_id": task.id
#     }

# @router.get("/tasks/{task_id}")
# async def get_task_status(task_id: str):
#     # task_id Status 조회
#     task_result = celery_app.AsyncResult(task_id)

#     # 기본 응답 구조
#     response = {
#         "task_id": task_id,
#         "status": task_result.status,
#         "result": None
#     }

#     # 작업이 진행 중인 경우
#     if task_result.status == "PROGRESS":
#         response["progress"] = task_result.info
    
#     # 작업이 완료되었을 때
#     elif task_result.status == "SUCCESS":
#         response["result"] = task_result.result
    
#     # 작업이 실패했을 때
#     elif task_result.status == "FAILURE":
#         response["result"] = str(task_result.info)
    
#     return response
