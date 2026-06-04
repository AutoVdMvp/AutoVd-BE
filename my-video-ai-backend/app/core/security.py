import jwt
from datetime import datetime, timedelta

from app.core.config import settings
from app.db.redis_client import redis_client

# Token 만료 시간
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_access_token(data: dict):
    to_encode = data.copy()

    # 만료 시간 Setting
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    # JWT Token 생성
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt

async def create_refresh_token(data: dict, user_id: str):
    to_encode = data.copy()

    # 만료 시간 Setting
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})

    # JWT Token 생성
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    # Redis에 Refresh Token 저장
    ttl_seconds = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    await redis_client.setex(
        name=f"refresh_token:{user_id}",
        time=ttl_seconds,
        value=encoded_jwt
    )

    return encoded_jwt