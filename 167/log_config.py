from pydantic_settings import BaseSettings
from typing import Optional


class LogRotationSettings(BaseSettings):
    max_logs_per_task: int = 100
    max_log_age_days: Optional[int] = 30
    max_total_logs: int = 10000
    enable_rotation: bool = True

    class Config:
        env_prefix = "LOG_"


log_settings = LogRotationSettings()