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

    # .env 파일 읽어오기
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# settings 객체를 import하여 사용
settings = Settings()