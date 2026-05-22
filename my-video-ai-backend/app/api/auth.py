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

# 실제 Google Cloud에서 발급받은 Client ID로 교체
GOOGLE_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"

@router.post("/google", response_model=TokenResponse)
async def google_login(request: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        # Google Token 검증
        idinfo = id_token.verify_oauth2_token(
            request.credential, requests.Request(), GOOGLE_CLIENT_ID
        )

        email = idinfo.get("email")
        name = idinfo.get("name")

        if not email:
            raise HTTPException(status_code=400, detail="Email not found in token")

        # DB에서 User 확인
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()

        # User에 없으면 DB에 저장
        if not user:
            user = User(email=email, nickname=name)
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # JWT 발급
        access_token = create_access_token(data={"sub": str(user.id)})

        # Test Response
        return TokenResponse(access_token=access_token)
    
    except ValueError:
        # Token 검증 실패
        raise HTTPException(status_code=401, detail="Invalid Google Token")