from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.db.database import engine, Base
from app.models import models
from app.api import auth
from app.api import projects
from app.api import video


# 서버 시작 시 실행 로직
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # DB에 Table이 없으면 생성
        await conn.run_sync(Base.metadata.create_all)
    yield

    # 서버 종료 시 실행 로직
    await engine.dispose()


# FastAPI Instance 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    # Swagger UI 주소
    docs_url="/docs",
    lifespan=lifespan,
)

# API Router 등록
app.include_router(
    auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Authentication"]
)

# Project Router 등록
app.include_router(
    projects.router, prefix=f"{settings.API_PREFIX}/projects", tags=["Projects"]
)

# Video Router 등록
app.include_router(video.router, prefix=settings.API_PREFIX, tags=["Video Generation"])


# Health Check Endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to AI Video Generator API!",
        "status": "Server is running smoothly.",
    }
