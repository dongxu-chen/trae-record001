from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    elasticsearch_host: str = "http://localhost:9200"
    elasticsearch_user: str = "elastic"
    elasticsearch_password: str = "changeme"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    documents_index: str = "documents"
    queries_index: str = "queries"
    annotations_index: str = "annotations"
    evaluations_index: str = "evaluations"
    models_index: str = "models"
    click_events_index: str = "click_events"
    ab_tests_index: str = "ab_tests"
    ab_assignments_index: str = "ab_assignments"
    feedback_data_index: str = "feedback_data"

    class Config:
        env_file = ".env"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
