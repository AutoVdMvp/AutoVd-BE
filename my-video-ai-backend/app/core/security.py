import jwt
from datetime import datetime, timedelta
from app.core.config import Settings

# Token 만료 시간
ACCESS_TOKEN_EXPIRE_DAYS = 7

def create_access_token(data: dict):
    to_encode = data.copy()

    # 만료 시간 Setting
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})

    # JWT Token 생성
    encoded_jwt = jwt.encode(
        to_encode,
        Settings.JWT_SECRET_KEY,
        algorithm=Settings.JWT_ALGORITHM
    )

    return encoded_jwt