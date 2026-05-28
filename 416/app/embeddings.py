from typing import List
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from app.config import get_settings


class EmbeddingManager:
    _instance = None
    _embeddings: Embeddings = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        settings = get_settings()
        cls._embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL,
        )

    @property
    def embeddings(self) -> Embeddings:
        return self._embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._embeddings.embed_query(text)


def get_embeddings() -> Embeddings:
    return EmbeddingManager().embeddings
