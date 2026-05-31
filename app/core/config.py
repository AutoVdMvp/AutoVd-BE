"""
애플리케이션 설정(환경 변수) 관리 모듈

pydantic-settings를 사용하여 .env 파일의 환경 변수를 읽고
타입 검증된 설정 객체(settings)로 제공합니다.

사용 방법:
    from app.core.config import settings
    print(settings.DATABASE_URL)

필요한 환경 변수는 프로젝트 루트의 .env.example 파일을 참고하세요.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 전역 설정 클래스."""

    # 서버 기본 정보
    PROJECT_NAME: str   # Swagger UI에 표시될 API 이름
    VERSION: str        # API 버전 (예: "1.0.0")
    API_PREFIX: str     # 모든 API 경로의 공통 prefix (예: "/api/v1")

    # 데이터베이스 연결 URL
    # 형식: postgresql+asyncpg://user:password@host:port/dbname
    DATABASE_URL: str

    # JWT 인증 설정
    JWT_SECRET_KEY: str     # JWT 서명에 사용할 비밀 키 (절대 외부 노출 금지)
    JWT_ALGORITHM: str      # JWT 서명 알고리즘 (예: "HS256")

    # 외부 AI 서비스 API Key
    LLM_API_KEY: str        # LLM 서비스 API Key (현재 미사용, 향후 확장용)
    GEMINI_API_KEY: str     # Google Gemini AI API Key (영상 기획 생성에 사용)

    # 프로젝트 루트의 .env 파일을 자동으로 읽어옴
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# 모듈 전역에서 공유할 싱글톤 설정 인스턴스
# 다른 모듈에서는 이 객체를 import하여 사용합니다.
settings = Settings()
