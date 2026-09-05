from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    RABBITMQ_URL: str = "amqp://meetingos:meetingos_pass@localhost:5672"
    DATABASE_URL: Optional[str] = None
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    ENVIRONMENT: str = "development"
    WORKER_PORT: int = 8001
    DEFAULT_MODEL: str = "gemini-2.0-flash"

    class Config:
        case_sensitive = True

settings = Settings()
