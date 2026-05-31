"""
Celery 비동기 Task 큐 설정 모듈

Redis를 Message Broker 및 Result Backend로 사용하는
Celery 애플리케이션 인스턴스를 생성하고 설정합니다.

사용 방법:
    from app.core.celery_app import celery_app

Worker 실행 명령어 (프로젝트 루트에서):
    celery -A app.core.celery_app worker --loglevel=info
"""

from celery import Celery

# Celery 앱 인스턴스 생성
# - broker: Task를 보내고 받는 메시지 큐 (Redis)
# - backend: Task 결과를 저장하는 저장소 (Redis)
celery_app = Celery(
    "video_worker",
    broker="redis://localhost:6379/0",    # Redis DB 0번: 작업 큐
    backend="redis://localhost:6379/0",   # Redis DB 0번: 결과 저장
)

celery_app.conf.update(
    task_serializer="json",       # Task 데이터 직렬화 형식
    accept_content=["json"],      # 수신 허용 Content-Type
    result_serializer="json",     # 결과 데이터 직렬화 형식
    timezone="Asia/Seoul",        # Task 스케줄링 기준 시간대
    enable_utc=True,              # 내부 시간은 UTC로 통일 (timezone과 함께 사용)
)

# Worker 실행 시 Task가 정의된 모듈을 자동으로 탐색
# app/services/ 하위의 @celery_app.task 데코레이터를 가진 함수들을 등록
celery_app.autodiscover_tasks(["app.services"])
