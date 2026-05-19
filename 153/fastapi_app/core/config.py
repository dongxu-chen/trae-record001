from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "校园心理健康预约系统"
    DEBUG: bool = True
    
    SECRET_KEY: str = "mental-health-app-secret-key-2024-change-in-production"
    ENCRYPTION_SALT: bytes = b"mental_health_app_salt_2024"
    
    DATABASE_URL: str = "sqlite+aiosqlite:///./mental_health.db"
    
    CORS_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"


settings = Settings()
