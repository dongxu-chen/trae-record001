from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True

    TRIVY_PATH: str = "trivy"
    TRIVY_CACHE_DIR: str = "/tmp/trivy-cache"
    TRIVY_TIMEOUT: int = 300
    
    TRIVY_DB_AUTO_UPDATE: bool = True
    TRIVY_DB_UPDATE_INTERVAL_HOURS: int = 24
    TRIVY_DB_DIR: str = "/tmp/trivy-cache/db"
    TRIVY_OFFLINE_DB_PATH: str = ""

    MAX_CONCURRENT_SCANS: int = 3
    SCAN_TIMEOUT: int = 600

    SENSITIVE_PATTERNS_FILE: str = "backend/config/sensitive_patterns.yaml"
    RULES_CONFIG_FILE: str = "backend/config/rules.yaml"
    
    SENSITIVE_SCAN_KEYWORDS: bool = True
    SENSITIVE_SCAN_FILES: bool = True
    SENSITIVE_SCAN_MAX_FILE_SIZE_MB: int = 50

    REPORTS_DIR: str = "reports"
    LOG_LEVEL: str = "INFO"
    
    DEFAULT_REPORT_FORMAT: str = "json"
    JUNIT_REPORT_FAIL_ON_SEVERITY: str = "MEDIUM"

    DOCKER_SOCKET: str = "unix://var/run/docker.sock"

    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

os.makedirs(settings.REPORTS_DIR, exist_ok=True)
os.makedirs(settings.TRIVY_CACHE_DIR, exist_ok=True)
os.makedirs(settings.TRIVY_DB_DIR, exist_ok=True)
