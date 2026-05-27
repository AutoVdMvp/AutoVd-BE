import time
from app.core.celery_app import celery_app
from app.services.crawler import extract_article
from app.services.llm import generate_video_plan
from app.services.asset_generator import generate_assets
from app.services.video_editor import merge_video


# Background Worker Process
@celery_app.task(bind=True)
def generate_video_task(self, project_id: str, article_url: str):
    try:
        # 1. 기사 Text Crawling
        print(f"{project_id} 영상 생성 작업 시작...(URL: {article_url})")
        self.update_state(state="PROGRESS", meta={"step": "crawling", "percent": 10})

        # Crawling Extraction
        article_data = extract_article(article_url)
        clean_text = article_data["content"]

        # 2. AI 영상 기획 및 Scene 분할
        print(f"[{project_id}] AI가 텍스트를 분석하여 영상을 기획 중입니다...")
        self.update_state(state="PROGRESS", meta={"step": "ai_planning", "percent": 30})

        # 텍스트를 AI에게 전달
        video_plan = generate_video_plan(clean_text)
        
        # 3. Media Asset 생성(TTS & Image)
        print(
            f"[{project_id}] 목소리와 이미지를 생성하고 다운로드합니다. (약 10 ~ 30초 소요)"
        )
        self.update_state(
            state="PROGRESS", meta={"step": "asset_generation", "percent": 60}
        )

        # Module 실행
        scene_assets = generate_assets(project_id, video_plan)

        # 4. Video 생성
        print(f"[{project_id}] 동영상 생성을 시작합니다. (약 30초 ~ 1분 소요)")
        self.update_state(
            state="PROGRESS", meta={"step": "video_editing", "percent": 80}
        )

        final_video_path = merge_video(project_id, scene_assets)
        print(f"[{project_id}] 최종 영상 생성 완료! 파일 위치: {final_video_path}")

        return {
            "status": "success",
            "message": "Video 생성 완료",
            "final_video_path": final_video_path,
            "project_id": project_id,
        }

    except Exception as e:
        print(f"{project_id} 작업 실패: {str(e)}")
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise e
