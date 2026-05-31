"""
데이터베이스 연결 및 세션 관리 모듈

SQLAlchemy 비동기 엔진(AsyncEngine)과 세션 팩토리(async_sessionmaker)를 생성하고,
FastAPI Dependency로 사용할 DB 세션 제공 함수(get_db)를 정의합니다.

아키텍처 흐름:
    FastAPI 요청 → Depends(get_db) → AsyncSession 생성 → API 핸들러 사용
                                                        → 정상 종료 시 commit
                                                        → 에러 발생 시 rollback
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings


# 비동기 DB Engine 생성
# - echo=True: SQL 쿼리를 콘솔에 출력 (개발 중에는 True, 배포 시에는 False로 변경)
# - pool_size: 평소에 유지할 DB 연결 개수 (연결 재사용으로 성능 향상)
# - max_overflow: 트래픽 급증 시 추가로 허용할 임시 연결 개수
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    pool_size=10,
    max_overflow=20,
)

# 비동기 세션 팩토리 생성
# - expire_on_commit=False: commit 이후에도 객체 속성 접근 가능
#   (비동기 환경에서는 commit 후 lazy load가 불가능하므로 False 설정 필수)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

# 모든 ORM 모델이 상속받는 선언적 Base 클래스
# models.py에서 이 Base를 상속하여 테이블 스키마를 정의합니다.
Base = declarative_base()


async def get_db():
    """
    FastAPI Dependency로 사용되는 비동기 DB 세션 제공 함수.

    각 API 요청마다 새로운 AsyncSession을 생성하고,
    요청 처리 완료 후 자동으로 commit 또는 rollback합니다.

    Usage:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...

    Yields:
        AsyncSession: 사용 가능한 비동기 DB 세션
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session                   # API 핸들러에 세션 제공
            await session.commit()          # 에러 없이 완료되면 DB에 변경사항 저장
        except Exception:
            await session.rollback()        # 에러 발생 시 모든 변경사항 롤백
            raise
