from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "低代码ETL平台"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./etl_platform.db"
    PREFECT_API_URL: str = "http://localhost:4200/api"
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
