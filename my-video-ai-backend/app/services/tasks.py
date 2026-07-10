import os
import time
import asyncio
import uuid
from celery.exceptions import MaxRetriesExceededError
from sqlalchemy.future import select

from app.core.celery_app import celery_app
from app.db.database import AsyncSessionLocal
from app.models.models import Project
from app.schemas.video import VideoGenerateRequest
from app.services.video_generation import run_pipeline

# Celery Wolker 전용 DB Update
async def update_project_in_db(project_id: str, status: str, vd_url: str = None):
    async with AsyncSessionLocal() as session:
        project_uuid = uuid.UUID(project_id)

        # DB에서 해당 Project 조회
        result = await session.execute(select(Project).where(Project.id == project_uuid))
        project = result.scalar_one_or_none()

        if project:
            project.status = status
            if vd_url:
                project.vd_url = vd_url
            
            await session.commit()
            print(f"[{project_id}] DB 상태 동기화 완료")
        else:
            print(f"[{project_id}] DB에서 프로젝트를 찾을 수 없습니다.")

# 동기 태스크 내에서 간편하게 호출하기 위한 Wrapper 함수
def change_project_status(project_id: str, status: str, vd_url: str = None):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(update_project_in_db(project_id, status, vd_url))
        loop.close()
    except Exception as e:
        print(f"[{project_id}] DB 상태 업데이트 중 에러 발생: {e}")

# Garbage Collection 함수
def cleanup_temp_files(project_id: str):
    project_path = os.path.abspath(os.path.join(os.getcwd(), "temp_projects", str(project_id)))

    if not os.path.exists(project_path):
        return
    
    # jpg, mp3 파일만 지우고 mp4 파일(최종 결과물)은 놔둠
    try:
        deleted_count = 0
        for file_name in os.listdir(project_path):
            if file_name.endswith(".jpg") or file_name.endswith(".mp3"):
                os.remove(os.path.join(project_path, file_name))
                deleted_count += 1
    except Exception as e:
        print(f"[{project_id}] 디스크 청소 실패: {e}")

# Background Worker Process
@celery_app.task(bind=True, max_retries=3)
def generate_video_task(self, project_id: str, article_url: str):
    try:
        print(f"{project_id} 영상 생성 작업 시작...(URL: {article_url})")
        change_project_status(project_id, "processing")

        def report_progress(step: str, percent: int) -> None:
            print(f"[{project_id}] 진행 단계: {step} ({percent}%)")
            self.update_state(state="PROGRESS", meta={"step": step, "percent": percent})

        output = run_pipeline(
            project_id,
            VideoGenerateRequest(url=article_url),
            progress=report_progress,
        )
        final_video_path = output.video_path

        # 성공 시 DB에 completed 보낸 후 경로 저장
        change_project_status(project_id, "completed", vd_url=final_video_path)
        print(f"[{project_id}] 최종 영상 생성 완료! 파일 위치: {final_video_path}")

        # 회원님의 디스크 청소 로직 실행
        cleanup_temp_files(project_id)

        return {
            "status": "success",
            "message": "Video 생성 완료",
            "final_video_path": final_video_path,
            "project_id": project_id
        }
    
    except Exception as e:
        print(f"{project_id} 작업 실패: {str(e)}")

        try:
            # 재시도 횟수
            raise self.retry(exc=e, countdown=10)
        
        except MaxRetriesExceededError:
            # 모두 실패 했을 경우
            print(f"[{project_id}] 재시도 횟수를 초과했습니다.")
            self.update_state(state="FAILURE", meta={"error": "재시도 횟수 초과: " + str(e)})
            change_project_status(project_id, "failed")

            # 실패 시에도 찌꺼기가 남지 않도록 청소
            cleanup_temp_files(project_id)

            raise e