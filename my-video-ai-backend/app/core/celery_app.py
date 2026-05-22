from celery import Celery

# Redis broker URL
celery_app = Celery(
    "video_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
)

# Worker가 실행될 때 자동으로 Task를 찾는 경로 지정
celery_app.autodiscover_tasks(["app.services"])