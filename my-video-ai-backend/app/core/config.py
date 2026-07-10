from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str
    VERSION: str
    API_PREFIX: str
    DATABASE_URL: str

    # JWT Settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str

    # AI Model API Key
    LLM_API_KEY: str
    GEMINI_API_KEY: str

    # Google OAuth
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None

    # Kakao OAuth
    KAKAO_CLIENT_ID: str | None = None
    KAKAO_CLIENT_SECRET: str | None = None
    KAKAO_REDIRECT_URI_BACKEND: str | None = None
    KAKAO_REDIRECT_URI_FRONTEND: str | None = None

    # Redis Settings
    REDIS_URL: str = "redis://redis:6479/0"

    # Celery Settings
    CELERY_BROKER_URL: str = "redis://redis:6479/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6479/0"

    # Video Generation Settings
    WORKSPACE_DIR: str = "temp_projects"
    VIDEO_FONT_PATH: str = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"

    # .env 파일 읽어오기
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# settings 객체를 import하여 사용
settings = Settings()