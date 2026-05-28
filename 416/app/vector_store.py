import uuid
import re
import math
from typing import List, Optional, Tuple
from dataclasses import dataclass
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from app.config import get_settings
from app.embeddings import get_embeddings
from app.schemas import SourceReference


@dataclass
class QueryComplexity:
    score: float
    word_count: int
    entity_count: int
    question_type: str
    is_compound: bool


class QueryComplexityAnalyzer:
    QUESTION_WORDS = {
        "what", "什么", "what's", "是什么",
        "why", "为什么", "原因",
        "how", "如何", "怎么", "怎样",
        "when", "何时", "什么时候",
        "where", "哪里", "什么地方",
        "who", "谁", "什么人",
        "which", "哪个", "哪一个",
        "how much", "多少",
        "how many", "多少",
        "explain", "解释", "说明",
        "compare", "比较", "对比",
        "define", "定义",
        "list", "列出", "列举",
    }

    ENTITY_PATTERNS = [
        r'\d+',
        r'[A-Z][a-z]+',
        r'[\u4e00-\u9fa5]+',
    ]

    @classmethod
    def analyze(cls, query: str) -> QueryComplexity:
        words = cls._tokenize(query)
        word_count = len(words)
        entity_count = cls._count_entities(query)
        question_type = cls._detect_question_type(query)
        is_compound = cls._is_compound_query(query)

        score = cls._calculate_complexity_score(
            word_count=word_count,
            entity_count=entity_count,
            is_compound=is_compound,
            question_type=question_type,
        )

        return QueryComplexity(
            score=score,
            word_count=word_count,
            entity_count=entity_count,
            question_type=question_type,
            is_compound=is_compound,
        )

    @classmethod
    def _tokenize(cls, text: str) -> List[str]:
        text = text.lower()
        words = re.findall(r'\b\w+\b|[\u4e00-\u9fa5]+', text)
        return [w for w in words if len(w) > 0]

    @classmethod
    def _count_entities(cls, text: str) -> int:
        entities = set()
        for pattern in cls.ENTITY_PATTERNS:
            matches = re.findall(pattern, text)
            entities.update(matches)
        return len(entities)

    @classmethod
    def _detect_question_type(cls, query: str) -> str:
        query_lower = query.lower()
        for q_word in cls.QUESTION_WORDS:
            if q_word in query_lower:
                return q_word
        return "statement"

    @classmethod
    def _is_compound_query(cls, query: str) -> bool:
        conjunctions = [" and ", " or ", "同时", "并且", "而且", "还有", "另外"]
        query_lower = query.lower()
        return any(conj in query_lower for conj in conjunctions)

    @classmethod
    def _calculate_complexity_score(
        cls,
        word_count: int,
        entity_count: int,
        is_compound: bool,
        question_type: str,
    ) -> float:
        score = 0.0

        score += min(word_count / 20.0, 1.0) * 0.4

        score += min(entity_count / 5.0, 1.0) * 0.3

        if is_compound:
            score += 0.2

        complex_types = {"explain", "compare", "define", "解释", "比较", "对比", "定义"}
        if question_type in complex_types:
            score += 0.1

        return min(score, 1.0)


class DynamicThresholdCalculator:
    @staticmethod
    def calculate(
        base_threshold: float,
        complexity: QueryComplexity,
    ) -> float:
        complexity_factor = complexity.score

        adjustment = (1.0 - complexity_factor) * 0.2

        dynamic_threshold = base_threshold - adjustment

        dynamic_threshold = max(0.2, min(0.8, dynamic_threshold))

        return dynamic_threshold

    @staticmethod
    def adjust_k(
        base_k: int,
        complexity: QueryComplexity,
    ) -> int:
        complexity_factor = complexity.score

        if complexity_factor > 0.7:
            return base_k + 2
        elif complexity_factor > 0.4:
            return base_k + 1
        else:
            return base_k


class VectorStore:
    _instance = None
    _db: Chroma = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        settings = get_settings()
        cls._db = Chroma(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=get_embeddings(),
            persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
        )
        cls._complexity_analyzer = QueryComplexityAnalyzer()
        cls._threshold_calculator = DynamicThresholdCalculator()

    @property
    def db(self) -> Chroma:
        return self._db

    def add_documents(self, documents: List[Document]) -> List[str]:
        return self._db.add_documents(documents)

    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        return self._db.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[dict] = None,
    ) -> List[Document]:
        return self._db.similarity_search(query=query, k=k, filter=filter)

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: Optional[dict] = None,
    ) -> List[Tuple[Document, float]]:
        return self._db.similarity_search_with_score(
            query=query, k=k, filter=filter
        )

    def search_with_references(
        self,
        query: str,
        k: Optional[int] = None,
        document_ids: Optional[List[str]] = None,
        min_score: Optional[float] = None,
    ) -> List[SourceReference]:
        settings = get_settings()
        base_k = k or settings.TOP_K_RETRIEVAL
        base_threshold = min_score or settings.MIN_SIMILARITY_THRESHOLD

        complexity = self._complexity_analyzer.analyze(query)
        dynamic_k = self._threshold_calculator.adjust_k(base_k, complexity)
        dynamic_threshold = self._threshold_calculator.calculate(
            base_threshold, complexity
        )

        filter_dict = {}
        if document_ids:
            filter_dict["document_id"] = {"$in": document_ids}

        results = self.similarity_search_with_score(
            query=query, k=dynamic_k, filter=filter_dict if filter_dict else None
        )

        references = []
        for doc, score in results:
            normalized_score = self._normalize_score(score)
            if normalized_score >= dynamic_threshold:
                references.append(
                    SourceReference(
                        document_id=doc.metadata.get("document_id", ""),
                        filename=doc.metadata.get("filename", ""),
                        chunk_id=doc.metadata.get("chunk_id", ""),
                        content=doc.page_content,
                        page=doc.metadata.get("page"),
                        start_line=doc.metadata.get("start_line"),
                        end_line=doc.metadata.get("end_line"),
                        similarity_score=normalized_score,
                    )
                )

        references.sort(key=lambda x: x.similarity_score, reverse=True)
        return references

    def analyze_query_complexity(self, query: str) -> QueryComplexity:
        return self._complexity_analyzer.analyze(query)

    def _normalize_score(self, score: float) -> float:
        if score > 1.0:
            return 1.0
        if score < 0.0:
            return 0.0
        return score

    def delete_by_document_id(self, document_id: str):
        self._db.delete(where={"document_id": document_id})

    def delete_by_ids(self, ids: List[str]):
        self._db.delete(ids=ids)

    def get_document_count(self) -> int:
        collection = self._db.get()
        return len(collection["ids"])

    def get_all_documents(self) -> List[Document]:
        collection = self._db.get(include=["documents", "metadatas"])
        documents = []
        for doc_id, content, metadata in zip(
            collection["ids"],
            collection["documents"],
            collection["metadatas"],
        ):
            documents.append(
                Document(page_content=content, metadata=metadata if metadata else {})
            )
        return documents

    def persist(self):
        self._db.persist()


def get_vector_store() -> VectorStore:
    return VectorStore()
