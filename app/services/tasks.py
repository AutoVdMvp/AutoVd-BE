"""
Celery 영상 생성 Task 모듈

뉴스 기사 URL을 입력받아 최종 영상 파일을 생성하는
비동기 Celery Task를 정의합니다.

영상 생성 파이프라인 (4단계):
    1. 기사 크롤링 (Selenium)        → 10%
    2. AI 영상 기획 (Gemini)         → 30%
    3. 미디어 에셋 생성 (TTS + 이미지) → 60%
    4. 영상 합성 (MoviePy)           → 80% → 완료
"""

import time
from app.core.celery_app import celery_app
from app.services.crawler import extract_article
from app.services.llm import generate_video_plan
from app.services.asset_generator import generate_assets
from app.services.video_editor import merge_video


# bind=True: Task 인스턴스(self)를 통해 상태 업데이트(update_state) 가능
@celery_app.task(bind=True)
def generate_video_task(self, project_id: str, article_url: str):
    """
    뉴스 기사 URL로부터 AI 쇼츠 영상을 생성하는 Celery Task.

    각 단계마다 self.update_state()로 진행률을 Redis에 업데이트하며,
    프론트엔드는 GET /prompt/status API로 폴링하여 진행 상황을 확인합니다.

    Args:
        project_id (str): 작업 대상 Project UUID (로깅 및 파일 저장 경로에 사용)
        article_url (str): 크롤링할 뉴스 기사 URL

    Returns:
        dict: 작업 완료 정보
            - status: "success"
            - message: 완료 메시지
            - final_video_path: 생성된 영상 파일 경로
            - project_id: 입력받은 Project ID

    Raises:
        Exception: 각 단계에서 발생한 예외를 그대로 re-raise
                   (Celery가 FAILURE 상태로 기록)
    """
    try:
        # ── 1단계: 기사 크롤링 ─────────────────────────────────────────────
        print(f"[{project_id}] 영상 생성 작업 시작... (URL: {article_url})")
        self.update_state(state="PROGRESS", meta={"step": "crawling", "percent": 10})

        # Selenium으로 기사 본문과 제목을 추출
        article_data = extract_article(article_url)
        clean_text = article_data["content"]

        # ── 2단계: AI 영상 기획 ────────────────────────────────────────────
        print(f"[{project_id}] AI가 텍스트를 분석하여 영상을 기획 중입니다...")
        self.update_state(state="PROGRESS", meta={"step": "ai_planning", "percent": 30})

        # Gemini에게 기사 본문을 전달하여 씬별 나레이션 + 이미지 프롬프트 생성
        video_plan = generate_video_plan(clean_text)

        # ── 3단계: 미디어 에셋 생성 (TTS + 이미지) ─────────────────────────
        print(
            f"[{project_id}] 목소리와 이미지를 생성하고 다운로드합니다. (약 10 ~ 30초 소요)"
        )
        self.update_state(
            state="PROGRESS", meta={"step": "asset_generation", "percent": 60}
        )

        # Edge TTS로 나레이션 음성 생성, Pollinations AI로 이미지 다운로드
        scene_assets = generate_assets(project_id, video_plan)

        # ── 4단계: 영상 합성 ───────────────────────────────────────────────
        print(f"[{project_id}] 동영상 생성을 시작합니다. (약 30초 ~ 1분 소요)")
        self.update_state(
            state="PROGRESS", meta={"step": "video_editing", "percent": 80}
        )

        # MoviePy로 각 씬의 이미지 + 음성 + 자막을 합쳐 최종 mp4 파일 생성
        final_video_path = merge_video(project_id, scene_assets)
        print(f"[{project_id}] 최종 영상 생성 완료! 파일 위치: {final_video_path}")

        return {
            "status": "success",
            "message": "Video 생성 완료",
            "final_video_path": final_video_path,
            "project_id": project_id,
        }

    except Exception as e:
        # 에러 정보를 Redis에 기록하고 예외를 다시 던짐
        # → Celery가 이 Task를 FAILURE 상태로 마킹
        print(f"[{project_id}] 작업 실패: {str(e)}")
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise e
