from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    skywalking_base_url: str = "http://localhost:12800"
    skywalking_timeout: int = 30

    host: str = "0.0.0.0"
    port: int = 8000

    default_lookback_hours: int = 168
    alert_frequency_threshold: int = 10
    noise_rule_threshold: float = 0.7

    cors_origins: list = ["*"]


settings = Settings()
