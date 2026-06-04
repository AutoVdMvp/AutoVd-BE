import redis.asyncio as redis
from app.core.config import settings

# 비동기 Redis Client
redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)