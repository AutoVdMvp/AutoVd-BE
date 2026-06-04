import os
import uuid
from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Optional
from celery.result import AsyncResult

from app.core.celery_app import celery_app
from app.schemas.response import CommonResponse
from app.services.tasks import generate_video_task
from app.db.database import get_db
from app.models.models import Project, User
from app.api.deps import get_current_user

router = APIRouter()

# 요청 Schema 정의
class RemakeVideoRequest(BaseModel):
    id: str

class RemakeVideoResponse(BaseModel):
    project_id: str
    task_id: str

class VideoStatusResponse(BaseModel):
    status: str
    step: Optional[str] = None
    percent: Optional[int] = None
    new_vd_link: Optional[str] = None

class VideoListResponse(BaseModel):
    id: str
    vd_url: Optional[str] = None

# [POST] 영상 생성 요청 API
@router.post("/prompt/remake_video", response_model=CommonResponse[RemakeVideoResponse])
async def remake_video(body: RemakeVideoRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 문자열 ID를 UUID 객체로 변환
    try:
        project_uuid = uuid.UUID(body.id)
    except ValueError:
        raise HTTPException(status_code=400, detail="유효하지 않은 Project ID 입니다.")
    
    # DB에 Project가 존재하는지 조회
    result = await db.execute(select(Project).where(Project.id == project_uuid, Project.user_id == current_user.id))
    project = result.scalars().first()

    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
    
    project_id_str = str(project.id)

    # DB에 저장되어 있던 기사 링크를 꺼내서 Celery에 전달
    article_url = project.original_url

    if not article_url:
        raise HTTPException(status_code=400, detail="기사 링크가 존재하지 않습니다.")

    task = generate_video_task.delay(project_id_str, article_url)

    # Project Status를 DB에 'processing'으로 Update
    await db.execute(
        update(Project)
        .where(Project.id == project_uuid)
        .values(status="processing")
    )
    await db.commit() # 변경 사항 확정

    return CommonResponse(
        status=200,
        message="영상 생성을 시작했습니다.",
        data=RemakeVideoResponse(project_id=project_id_str, task_id=task.id)
    )

# [GET] 작업 진행 상태 조회 API
@router.get("/prompt/status", response_model=CommonResponse[VideoStatusResponse])
async def get_video_status(id: str = Query(..., description="Celery Task ID"), db: AsyncSession = Depends(get_db)):
    # Celery에서 현재 Task Status 조회
    task_result = AsyncResult(id, app=celery_app)

    # [PROGRESS] 아직 대기 중
    if task_result.state == "PROGRESS":
        meta = task_result.info or {}
        return CommonResponse(
            status=200,
            message="영상 생성 중입니다.",
            data=VideoStatusResponse(
                status="PROGRESS",
                step=meta.get("step", "processing"),
                percent=meta.get("percent", 0)
            )
        )
    
    # [SUCCESS] 성공적으로 완료했을 때
    elif task_result.state == "SUCCESS":
        result_data = task_result.result

        # 절대 경로에서 File Name만 추출
        file_name = os.path.basename(result_data.get('final_video_path', ''))
        video_url = f"http://localhost:8000/static/{file_name}"

        # DB Update Logic
        project_id = result_data.get('project_id')
        if project_id:
            try:
                proj_uuid = uuid.UUID(project_id)
                result = await db.execute(select(Project).where(Project.id == proj_uuid))
                project = result.scalars().first()
                if project and project.status != "completed":
                    project.status = "completed"
                    project.vd_url = video_url
                    await db.commit()
            except ValueError:
                pass

        return CommonResponse(
            status=200,
            message="영상 생성이 완료되었습니다.",
            data=VideoStatusResponse(
                status="SUCCESS",
                percent=100,
                new_vd_link=video_url
            )
        )
    
    # [FAILURE] 실패했을 때
    elif task_result.state == "FAILURE":
        return CommonResponse(
            status=500,
            message="영상 생성 중 오류가 발생했습니다.",
            data=VideoStatusResponse(status="FAILURE")
        )
    
    # 그 외의 상태
    return CommonResponse(
        status=200,
        message="작업 대기 중입니다.",
        data=VideoStatusResponse(status="PENDING", percent=0)
    )

# [GET] 영상 목록 조회 API
@router.get("/vd/list", response_model=CommonResponse[List[VideoListResponse]])
async def get_video_list(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # DB에서 해당 User의 Project 가져오기
    result = await db.execute(select(Project).where(Project.user_id == current_user.id))
    projects = result.scalars().all()

    # 가져온 Data API 규격에 맞게 조합
    video_list = [
        VideoListResponse(id=str(p.id), vd_url=p.vd_url) for p in projects
    ]

    return CommonResponse(
        status=200,
        message="데이터를 성공적으로 가져왔습니다.",
        data=video_list
    )

# [GET] 영상 Download API
@router.get("/download/{project_id}")
async def download_video(project_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        proj_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="유효하지 않은 Project ID 입니다.")
    
    # 내 Project가 맞는지 DB 확인
    result = await db.execute(select(Project).where(Project.id == proj_uuid, Project.user_id == current_user.id))
    project = result.scalars().first()

    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없거나 권한이 없습니다.")
    
    # 임시 파일 제공
    file_path = "temp_projects/test_video.mp4"

    # 파일 존재 여부 확인
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="영상 파일이 아직 생성되지 않았거나 삭제되었습니다.")
    
    # Download Response
    return FileResponse(
        path=file_path,
        filename=f"aivideo_{project_id}.mp4",
        media_type="video/mp4",
        headers={"Content-Disposition": f"attachment; filename=aivideo_{project_id}.mp4"}
    )