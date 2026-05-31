"""
인증(Authentication) 관련 Pydantic 스키마 모듈

Google OAuth2 로그인 요청/응답에 사용되는 데이터 유효성 검증 스키마를 정의합니다.
"""

from pydantic import BaseModel, EmailStr


class GoogleLoginRequest(BaseModel):
    """
    Google OAuth2 로그인 요청 스키마.

    프론트엔드가 Google Identity Services SDK를 통해 받은
    ID Token을 그대로 전달합니다.
    """
    credential: str  # Google에서 발급한 ID Token (JWT 형식)


class TokenResponse(BaseModel):
    """
    로그인 성공 후 반환되는 JWT 토큰 응답 스키마.

    프론트엔드는 이 Access Token을 저장하고,
    이후 API 요청의 Authorization 헤더에 "Bearer <token>" 형식으로 포함합니다.
    """
    access_token: str           # 서버에서 발급한 JWT Access Token
    token_type: str = "bearer"  # 토큰 타입 (OAuth2 표준: "bearer")
