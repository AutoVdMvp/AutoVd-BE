import os
import requests
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.db.database import get_db
from app.db.redis_client import redis_client
from app.schemas.auth import GoogleLoginRequest, TokenResponse, RefreshTokenRequest
from app.models.models import User
from app.core.security import create_access_token, create_refresh_token
from app.core.config import settings

router = APIRouter()

@router.post("/google", response_model=TokenResponse)
async def google_login(request: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        # Google Token 검증
        idinfo = id_token.verify_oauth2_token(
            request.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10
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
        refresh_token = await create_refresh_token(data={"sub": str(user.id)}, user_id=str(user.id))

        # Test Response
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
    
    except ValueError as e:
        # Token 검증 실패
        print(f"Google Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid Google Token")

@router.get("/kakao/login")
async def kakao_login_redirect():
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize?"
        f"client_id={settings.KAKAO_CLIENT_ID}&redirect_uri={settings.KAKAO_REDIRECT_URI}&response_type=code"
        f"&prompt=consent"
    )
    return RedirectResponse(url=kakao_auth_url)

@router.get("/kakao/callback")
async def kakao_callback(code: str, db: AsyncSession = Depends(get_db)):
    # Kakao Access Token 요청
    token_req_data = {
        "grant_type": "authorization_code",
        "client_id": settings.KAKAO_CLIENT_ID,
        "redirect_uri": settings.KAKAO_REDIRECT_URI,
        "client_secret": settings.KAKAO_CLIENT_SECRET,
        "code": code,
    }
    token_headers = {"Content-type": "application/x-www-form-urlencoded;charset=utf-8"}
    token_res = requests.post("https://kauth.kakao.com/oauth/token", data=token_req_data, headers=token_headers)

    if token_res.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get Kakao access token")
    
    kakao_token = token_res.json().get("access_token")

    # Kakao User Info 조회
    user_info_headers = {
        "Authorization": f"Bearer {kakao_token}",
        "Content-type": "application/x-www-form-urlencoded;charset=utf-8"
    }
    user_info_res = requests.get("https://kapi.kakao.com/v2/user/me", headers=user_info_headers)

    if user_info_res.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get Kakao user info")
    
    user_info = user_info_res.json()
    kakao_id = user_info.get("id")
    kakao_account = user_info.get("kakao_account", {})
    email = kakao_account.get("email")

    # Nickname 가져오기(없으면 '카카오유저'로 대체)
    profile = kakao_account.get("profile", {})
    name = profile.get("nickname", "카카오유저")

    if not email:
        email = f"kakao_{kakao_id}@kakao.dummy.com"
    
    # DB Logic 통합
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        user = User(email=email, nickname=name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    # JWT 발급
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = await create_refresh_token(data={"sub": str(user.id)}, user_id=str(user.id))

    return {
        "message": "Kakao Login Successful",
        "email": email,
        "access_token": access_token,
        "refresh_token": refresh_token
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(request: RefreshTokenRequest):
    try:
        # Refresh Token 검증
        payload = jwt.decode(
            request.refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # Redis 중앙 통제소 확인
        stored_token = await redis_client.get(f"refresh_token:{user_id}")

        # Redis에 토큰이 없거나, 다르면 차단
        if stored_token is None or stored_token != request.refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token is invalid or has been revoked")
        
        # 새로운 Access Token 발급
        new_access_token = create_access_token(data={"sub": user_id})

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=request.refresh_token
        )
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
@router.post("/logout")
async def logout(request: RefreshTokenRequest):
    try:
        # Refresh Token 검증
        payload = jwt.decode(
            request.refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")

        # Redis에서 해당 User의 Refresh Token 삭제
        if user_id:
            await redis_client.delete(f"refresh_token:{user_id}")
    
    except jwt.PyJWTError:
        pass

    return {"message": "Logged Out Successfully"}