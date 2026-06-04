import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.database import engine, Base
from app.models import models
from app.api import auth, users
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
    lifespan=lifespan
)

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ], # 실제 배포 시 프론트 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("temp_projects", exist_ok=True)
app.mount("/static", StaticFiles(directory="temp_projects"), name="static")

# API Router 등록
app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Authentication"])

# User Router 등록
app.include_router(users.router, prefix=f"{settings.API_PREFIX}/users", tags=["Users"])

# Project Router 등록
app.include_router(projects.router, prefix=f"{settings.API_PREFIX}/projects", tags=["Projects"])

# Video Router 등록
app.include_router(video.router, prefix=f"{settings.API_PREFIX}/video", tags=["Video Generation"])

# Health Check Endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to AI Video Generator API!",
        "status": "Server is running smoothly."
    }