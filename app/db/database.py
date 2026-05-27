from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Asyncd DB Engine 생성
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # 개발 중에는 True, 배포 시에는 False
    pool_size=10,  # 평소 유지할 DB 연결 개수
    max_overflow=20,  # 트래픽이 몰릴 때 추가로 허용할 연결 개수
)

# Session Factory 생성
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

# 모든 모델의 Parent 클래스
Base = declarative_base()


# API 호출 시 DB Session을 제공하는 Dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # 에러 없이 끝나면 DB에 저장
        except Exception:
            await session.rollback()  # 중간에 에러가 나면 데이터 복구
            raise
