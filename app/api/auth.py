"""
Google OAuth2 소셜 로그인 인증 API 모듈

Google ID Token을 검증하고, 최초 로그인 시 사용자를 DB에 등록하며,
내부 서비스 인증에 사용할 JWT Access Token을 발급합니다.

흐름:
    프론트엔드(Google 로그인) → ID Token 전달 → 서버에서 검증 → JWT 발급
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.oauth2 import id_token
from google.auth.transport import requests
from app.db.database import get_db
from app.schemas.auth import GoogleLoginRequest, TokenResponse
from app.models.models import User
from app.core.security import create_access_token

router = APIRouter()

# Google Cloud Console에서 발급받은 OAuth2 Client ID
# 실제 배포 시 .env 파일로 관리하는 것을 권장합니다.
GOOGLE_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"


@router.post("/google", response_model=TokenResponse)
async def google_login(request: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Google OAuth2 소셜 로그인 엔드포인트.

    1. 프론트엔드가 전달한 Google ID Token을 Google 서버에서 검증
    2. 토큰에서 이메일/이름을 추출하여 신규 사용자라면 DB에 등록
    3. 내부 서비스용 JWT Access Token을 생성하여 반환

    Args:
        request: Google ID Token이 담긴 요청 바디
        db: 비동기 DB 세션 (Dependency Injection)

    Returns:
        TokenResponse: Bearer JWT Access Token

    Raises:
        HTTPException 400: 토큰에 이메일 정보가 없는 경우
        HTTPException 401: Google Token 검증 실패 시
    """
    try:
        # Google 공개 키로 ID Token의 서명 및 만료 여부 검증
        idinfo = id_token.verify_oauth2_token(
            request.credential, requests.Request(), GOOGLE_CLIENT_ID
        )

        # 검증된 토큰에서 사용자 정보 추출
        email = idinfo.get("email")
        name = idinfo.get("name")

        if not email:
            raise HTTPException(status_code=400, detail="Email not found in token")

        # DB에서 기존 회원 여부 확인
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()

        # 신규 사용자라면 DB에 등록 (자동 회원가입)
        if not user:
            user = User(email=email, nickname=name)
            db.add(user)
            await db.commit()
            await db.refresh(user)  # DB에서 생성된 id(UUID) 등을 반영

        # 사용자 UUID를 payload로 담아 JWT 발급
        access_token = create_access_token(data={"sub": str(user.id)})

        return TokenResponse(access_token=access_token)

    except ValueError:
        # 서명 불일치, 만료, audience 불일치 등 Token 검증 실패
        raise HTTPException(status_code=401, detail="Invalid Google Token")
