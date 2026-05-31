"""
AutoVd-BE 메인 애플리케이션 모듈

FastAPI 인스턴스를 생성하고, 라우터를 등록하며,
서버 시작/종료 시 실행되는 lifecycle 이벤트를 관리합니다.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.db.database import engine, Base
from app.models import models
from app.api import auth
from app.api import projects
from app.api import video


# 서버 시작 / 종료 시 실행되는 Lifecycle 관리자
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    서버 시작 및 종료 시 실행되는 Lifecycle 이벤트 핸들러.

    - 시작 시: DB 테이블이 없으면 자동 생성
    - 종료 시: DB 연결 풀 해제
    """
    async with engine.begin() as conn:
        # DB에 Table이 없으면 생성 (개발 편의를 위한 자동 마이그레이션)
        await conn.run_sync(Base.metadata.create_all)
    yield  # 서버가 실행 중인 동안 대기

    # 서버 종료 시 DB 연결 풀 정리
    await engine.dispose()


# FastAPI Instance 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",       # Swagger UI 접근 경로
    lifespan=lifespan,      # 위에서 정의한 Lifecycle 핸들러 등록
)

# 인증(Authentication) API Router 등록
# 엔드포인트 예시: POST /api/v1/auth/google
app.include_router(
    auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Authentication"]
)

# 프로젝트(Projects) API Router 등록
# 엔드포인트 예시: GET /api/v1/projects/vd/list
app.include_router(
    projects.router, prefix=f"{settings.API_PREFIX}/projects", tags=["Projects"]
)

# 영상 생성(Video Generation) API Router 등록
# 엔드포인트 예시: POST /api/v1/prompt/remake_video
app.include_router(video.router, prefix=settings.API_PREFIX, tags=["Video Generation"])


# Health Check Endpoint — 서버가 정상적으로 실행 중인지 확인
@app.get("/")
async def root():
    """서버 상태를 반환하는 헬스 체크 엔드포인트."""
    return {
        "message": "Welcome to AI Video Generator API!",
        "status": "Server is running smoothly.",
    }
