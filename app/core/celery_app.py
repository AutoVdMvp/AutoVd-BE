import os
from celery import Celery

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")

# Redis broker URL
celery_app = Celery(
    "video_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
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
