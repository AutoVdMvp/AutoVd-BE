"""
영상 생성 핵심 API 모듈

뉴스 기사를 기반으로 AI 영상을 생성하는 서비스의 주요 엔드포인트를 제공합니다.

엔드포인트 목록:
    - POST /prompt/remake_video : 특정 프로젝트의 영상 (재)생성 요청
    - GET  /prompt/status       : Celery Task 진행 상태 폴링
    - GET  /vd/list             : 특정 사용자의 완성된 영상 목록 조회
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Optional
from celery.result import AsyncResult

from app.core.celery_app import celery_app
from app.schemas.response import CommonResponse
from app.services.tasks import generate_video_task
from app.db.database import get_db
from app.models.models import Project


router = APIRouter()


# ─── 요청 / 응답 Schema 정의 ────────────────────────────────────────────────

class RemakeVideoRequest(BaseModel):
    """영상 (재)생성 요청 바디."""
    id: str  # 영상을 생성할 Project UUID


class RemakeVideoResponse(BaseModel):
    """영상 생성 시작 응답 바디."""
    project_id: str  # 요청한 Project UUID
    task_id: str     # Celery Task ID (상태 폴링에 사용)


class VideoStatusResponse(BaseModel):
    """Celery Task 진행 상태 응답 바디."""
    status: str                   # PENDING / PROGRESS / SUCCESS / FAILURE
    step: Optional[str] = None    # 현재 진행 단계 (crawling, ai_planning 등)
    percent: Optional[int] = None # 진행률 (0~100)
    new_vd_link: Optional[str] = None  # 완성된 영상 접근 URL (SUCCESS 시)


class VideoListResponse(BaseModel):
    """영상 목록 단일 항목 응답 바디."""
    id: str                       # Project UUID
    vd_url: Optional[str] = None  # 완성된 영상 접근 URL (미완성이면 None)


# ─── 엔드포인트 정의 ─────────────────────────────────────────────────────────

# [POST] 영상 (재)생성 요청 API
@router.post("/prompt/remake_video", response_model=CommonResponse[RemakeVideoResponse])
async def remake_video(body: RemakeVideoRequest, db: AsyncSession = Depends(get_db)):
    """
    특정 프로젝트의 영상을 (재)생성 요청하는 엔드포인트.

    DB에 저장된 기사 URL을 꺼내 Celery Task로 비동기 실행합니다.
    Task ID를 반환하며, 진행 상황은 GET /prompt/status 로 폴링합니다.

    Args:
        body: 생성할 Project의 UUID
        db: 비동기 DB 세션 (Dependency Injection)

    Returns:
        CommonResponse: project_id와 task_id 포함

    Raises:
        HTTPException 404: 해당 Project가 DB에 없을 때
        HTTPException 400: 프로젝트에 기사 URL이 없을 때
    """
    # DB에 Project가 존재하는지 확인
    result = await db.execute(select(Project).where(Project.id == body.id))
    project = result.scalars().first()

    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")

    project_id_str = str(project.id)

    # DB에 저장된 기사 링크를 꺼내 Celery Task에 전달
    article_url = project.original_url

    if not article_url:
        raise HTTPException(status_code=400, detail="기사 링크가 존재하지 않습니다.")

    # 영상 생성 Celery Task를 백그라운드로 비동기 실행
    task = generate_video_task.delay(project_id_str, article_url)

    # 작업이 시작되었음을 DB에 기록 (상태: processing)
    project.status = "processing"
    await db.commit()  # 변경 사항 영구 저장

    return CommonResponse(
        status=200,
        message="영상 생성을 시작했습니다.",
        data=RemakeVideoResponse(project_id=project_id_str, task_id=task.id),
    )


# [GET] 작업 진행 상태 조회 API
@router.get("/prompt/status", response_model=CommonResponse[VideoStatusResponse])
def get_video_status(id: str = Query(..., description="Celery Task ID")):
    """
    Celery Task의 현재 진행 상태를 폴링하는 엔드포인트.

    프론트엔드는 이 엔드포인트를 주기적으로 호출하여
    영상 생성 진행률 및 완료 여부를 확인합니다.

    Args:
        id: POST /prompt/remake_video 에서 반환된 Celery Task ID

    Returns:
        CommonResponse: 현재 상태(PENDING/PROGRESS/SUCCESS/FAILURE)와 세부 정보
    """
    # Redis Backend에서 현재 Task 상태 조회
    task_result = AsyncResult(id, app=celery_app)

    # [PROGRESS] 영상 생성이 진행 중인 경우 — 단계(step)와 진행률(percent) 반환
    if task_result.state == "PROGRESS":
        meta = task_result.info or {}
        return CommonResponse(
            status=200,
            message="영상 생성 중입니다.",
            data=VideoStatusResponse(
                status="PROGRESS",
                step=meta.get("step", "processing"),   # 현재 진행 단계
                percent=meta.get("percent", 0),        # 현재 진행률
            ),
        )

    # [SUCCESS] 영상 생성이 성공적으로 완료된 경우 — 완성 영상 URL 반환
    elif task_result.state == "SUCCESS":
        result_data = task_result.result
        return CommonResponse(
            status=200,
            message="영상 생성이 완료되었습니다.",
            data=VideoStatusResponse(
                status="SUCCESS",
                percent=100,
                # 완성된 영상 파일의 정적 접근 URL 조합
                new_vd_link=f"http://localhost:8000/static/{result_data.get('final_video_path')}",
            ),
        )

    # [FAILURE] 영상 생성 중 오류가 발생한 경우
    elif task_result.state == "FAILURE":
        return CommonResponse(
            status=500,
            message="영상 생성 중 오류가 발생했습니다.",
            data=VideoStatusResponse(status="FAILURE"),
        )

    # [PENDING / 기타] 아직 대기열에서 실행을 기다리는 경우
    return CommonResponse(
        status=200,
        message="작업 대기 중입니다.",
        data=VideoStatusResponse(status="PENDING", percent=0),
    )


# [GET] 영상 목록 조회 API
@router.get("/vd/list", response_model=CommonResponse[List[VideoListResponse]])
async def get_video_list(
    userId: str = Query(..., description="유저 UUID"),
    db: AsyncSession = Depends(get_db),
):
    """
    특정 사용자의 영상(프로젝트) 목록을 조회하는 엔드포인트.

    Args:
        userId: 조회할 사용자의 UUID
        db: 비동기 DB 세션 (Dependency Injection)

    Returns:
        CommonResponse: 해당 사용자의 Project ID와 영상 URL 목록
    """
    # DB에서 해당 User ID와 연결된 Project 전체 조회
    result = await db.execute(select(Project).where(Project.user_id == userId))
    projects = result.scalars().all()

    # DB 결과를 API 응답 스키마(VideoListResponse)로 변환
    video_list = [VideoListResponse(id=str(p.id), vd_url=p.vd_url) for p in projects]

    return CommonResponse(
        status=200, message="데이터를 성공적으로 가져왔습니다.", data=video_list
    )
