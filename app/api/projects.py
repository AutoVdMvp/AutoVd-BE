"""
영상 생성 테스트용 API 모듈 (개발/디버깅 전용)

video.py의 정식 API와 달리, 이 모듈은 고정된 mock project ID를 사용하여
영상 생성 파이프라인을 빠르게 테스트하기 위한 임시 엔드포인트를 제공합니다.

Note:
    실제 서비스 엔드포인트는 app/api/video.py 를 사용하세요.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.tasks import generate_video_task
from app.core.celery_app import celery_app

router = APIRouter()


class VideoGenerateRequest(BaseModel):
    """영상 생성 요청 바디 스키마."""
    article_url: str  # 크롤링할 뉴스 기사 URL


@router.post("/generate")
async def start_video_generation(request: VideoGenerateRequest):
    """
    영상 생성을 비동기로 시작하는 테스트용 엔드포인트.

    Celery Task를 백그라운드로 실행하고,
    완료를 기다리지 않고 Task ID를 즉시 반환합니다.
    실제 진행 상황은 GET /tasks/{task_id} 로 폴링하여 확인합니다.

    Args:
        request: 크롤링 대상 기사 URL이 담긴 요청 바디

    Returns:
        task_id, project_id 등 작업 추적에 필요한 정보
    """
    # 테스트용 고정 Project ID (실제 서비스에서는 DB의 UUID 사용)
    mock_project_id = "proj-9999"

    # .delay()로 Celery Worker에 Task 비동기 전달 (즉시 반환)
    task = generate_video_task.delay(mock_project_id, request.article_url)

    # 영상 생성 완료를 기다리지 않고 Task 추적 정보만 즉시 반환
    return {
        "message": "영상 생성이 시작되었습니다.",
        "project_id": mock_project_id,
        "task_id": task.id,  # 폴링에 사용할 Celery Task ID
    }


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    Celery Task의 현재 진행 상태를 조회하는 엔드포인트.

    Args:
        task_id: POST /generate 에서 반환된 Celery Task ID

    Returns:
        status(PENDING/PROGRESS/SUCCESS/FAILURE), result 등 상태 정보
    """
    # Redis Backend에서 Task 상태 조회
    task_result = celery_app.AsyncResult(task_id)

    # 기본 응답 구조 (status에 따라 추가 필드가 채워짐)
    response = {"task_id": task_id, "status": task_result.status, "result": None}

    # 작업이 진행 중인 경우 — step, percent 등 세부 진행 정보 포함
    if task_result.status == "PROGRESS":
        response["progress"] = task_result.info

    # 작업이 성공적으로 완료된 경우 — 최종 결과물 경로 포함
    elif task_result.status == "SUCCESS":
        response["result"] = task_result.result

    # 작업이 실패한 경우 — 에러 메시지 포함
    elif task_result.status == "FAILURE":
        response["result"] = str(task_result.info)

    return response
