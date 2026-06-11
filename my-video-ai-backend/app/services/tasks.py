import time
import asyncio
import uuid
from celery.exceptions import MaxRetriesExceededError
from sqlalchemy.future import select

from app.core.celery_app import celery_app
from app.services.crawler import extract_article
from app.services.llm import generate_video_plan
from app.services.asset_generator import generate_assets
from app.services.video_editor import merge_video
from app.db.database import AsyncSessionLocal
from app.models.models import Project

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
        asyncio.run(update_project_in_db(project_id, status, vd_url))
    except Exception as e:
        print(f"[{project_id}] DB 상태 업데이트 중 에러 발생: {e}")

# Background Worker Process
@celery_app.task(bind=True, max_retries=3)
def generate_video_task(self, project_id: str, article_url: str):
    try:
        # 1. 기사 Text Crawling
        print(f"{project_id} 영상 생성 작업 시작...(URL: {article_url})")
        self.update_state(state="PROGRESS", meta={"step": "crawling", "percent": 10})

        # 대기 중인 프로젝트를 작업 상태로 DB 전환
        change_project_status(project_id, "processing")

        # Crawling Extraction
        article_data = extract_article(article_url)
        clean_text = article_data['content']

        # 2. AI 영상 기획 및 Scene 분할
        print(f"[{project_id}] AI가 텍스트를 분석하여 영상을 기획 중입니다...")
        self.update_state(state="PROGRESS", meta={"step": "ai_planning", "percent": 30})

        # 텍스트를 AI에게 전달
        video_plan = generate_video_plan(clean_text)

        # 3. Media Asset 생성(TTS & Image)
        print(f"[{project_id}] 목소리와 이미지를 생성하고 다운로드합니다. (약 10 ~ 30초 소요)")
        self.update_state(state="PROGRESS", meta={"step": "asset_generation", "percent": 60})
        
        # Module 실행
        scene_assets = generate_assets(project_id, video_plan)

        # 4. Video 생성
        print(f"[{project_id}] 동영상 생성을 시작합니다. (약 30초 ~ 1분 소요)")
        self.update_state(state="PROGRESS", meta={"step": "video_editing", "percent": 80})
        final_video_path = merge_video(project_id, scene_assets)

        # 성공 시 DB에 completed 보낸 후 경로 저장
        change_project_status(project_id, "completed", vd_url=final_video_path)
        print(f"[{project_id}] 최종 영상 생성 완료! 파일 위치: {final_video_path}")

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
            print(f"[{project_id}] 10초 후 작업을 재시작합니다... (현재 재시도: {self.request.retries}/3)")
            raise self.retry(exc=e, countdown=10)
        
        except MaxRetriesExceededError:
            # 모두 실패 했을 경우
            print(f"[{project_id}] 재시도 횟수를 초과했습니다.")
            self.update_state(state="FAILURE", meta={"error": "재시도 횟수 초과: " + str(e)})
            change_project_status(project_id, "failed")

            raise e