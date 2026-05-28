import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-3.5-turbo"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2048

    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"
    CHROMA_COLLECTION_NAME: str = "knowledge_base"

    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100

    TOP_K_RETRIEVAL: int = 4
    MIN_SIMILARITY_THRESHOLD: float = 0.5

    MAX_SESSION_HISTORY: int = 10
    UPLOAD_DIR: str = "./data/uploads"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    return settings
