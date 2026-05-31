"""
JWT(JSON Web Token) 보안 유틸리티 모듈

사용자 인증에 사용되는 JWT Access Token을 생성합니다.
토큰 검증(decode) 로직은 인증이 필요한 엔드포인트의 Dependency로 추가 구현될 수 있습니다.
"""

import jwt
from datetime import datetime, timedelta
from app.core.config import Settings

# JWT Access Token의 유효 기간 (일 단위)
# 7일 후 만료되면 사용자가 재로그인해야 합니다.
ACCESS_TOKEN_EXPIRE_DAYS = 7


def create_access_token(data: dict) -> str:
    """
    주어진 데이터를 payload로 담아 JWT Access Token을 생성합니다.

    Args:
        data: JWT payload에 포함할 데이터 딕셔너리.
              일반적으로 {"sub": "<user_uuid>"} 형태로 사용자 식별자를 담습니다.

    Returns:
        str: 서명된 JWT Token 문자열

    Example:
        token = create_access_token(data={"sub": "123e4567-e89b-12d3-..."})
    """
    to_encode = data.copy()  # 원본 data 변형 방지를 위해 복사

    # 현재 UTC 시간 기준으로 만료 시간(exp) 계산
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})  # payload에 만료 시간 추가

    # 비밀 키와 알고리즘으로 JWT 서명 및 인코딩
    encoded_jwt = jwt.encode(
        to_encode, Settings.JWT_SECRET_KEY, algorithm=Settings.JWT_ALGORITHM
    )

    return encoded_jwt
