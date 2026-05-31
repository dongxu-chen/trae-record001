from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "Academic Citation Network Analyzer"
    app_version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    crossref_rate_limit: int = 50
    dblp_rate_limit: int = 100
    request_timeout: int = 30

    cache_ttl_search: int = 3600
    cache_ttl_paper: int = 86400
    cache_ttl_graph: int = 1800

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
