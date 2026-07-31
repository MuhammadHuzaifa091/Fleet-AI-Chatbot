from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "AI_Telematics"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    DB_SERVER: str
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_SERVER}:{self.DB_PORT}/{self.DB_NAME}?connect_timeout=5"

    # LLM
    DEEPSEEK_API_KEY: str
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Vector DB
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200
    TRACCAR_URL: str = "http://202.141.246.12:8082"
    PROD_NETWORK_PATH: Optional[str] = None

    # PC12 (MASTER) Traccar REST API â€” used by auto-sync (read-only)
    PC12_API_URL: str = "http://202.141.246.12:8082"
    PC12_API_USER: str = "aima@admin.com"
    PC12_API_PASS: str = "traccar12344321"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
