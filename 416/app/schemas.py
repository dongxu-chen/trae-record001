from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    file_type: str
    file_size: int
    upload_time: datetime
    chunk_count: int
    status: str


class SourceReference(BaseModel):
    document_id: str
    filename: str
    chunk_id: str
    content: str
    page: Optional[int] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    similarity_score: float
    content_type: str = "text"


class TableReference(BaseModel):
    table_id: str
    document_id: str
    filename: str
    page: Optional[int] = None
    headers: List[str] = []
    rows: List[List[str]] = []
    summary: str = ""


class ChartReference(BaseModel):
    chart_id: str
    document_id: str
    filename: str
    page: Optional[int] = None
    chart_type: str
    title: str
    data_summary: str


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    query: str
    stream: bool = False
    use_multimodal: bool = True


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    confidence_score: float
    sources: List[SourceReference]
    tables: List[TableReference] = []
    charts: List[ChartReference] = []
    reasoning: Optional[str] = None
    suggestions: List[str] = []
    coverage_status: str = "covered"


class AnswerEvaluationResult(BaseModel):
    accuracy_score: float
    completeness_score: float
    relevance_score: float
    overall_score: float
    feedback: str
    needs_improvement: bool
    suggestions: List[str]


class FeedbackRequest(BaseModel):
    session_id: str
    query: str
    answer: str
    rating: int
    comment: Optional[str] = None


class UncoveredQuery(BaseModel):
    query: str
    timestamp: datetime
    attempted_sources: int
    suggested_documents: List[str]


class ActiveLearningStats(BaseModel):
    total_queries: int
    covered_queries: int
    uncovered_queries: int
    coverage_rate: float
    frequent_uncovered: List[Dict]


class SessionInfo(BaseModel):
    session_id: str
    created_at: datetime
    last_active: datetime
    message_count: int
    document_ids: List[str]


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    message: str


class DeleteDocumentRequest(BaseModel):
    document_id: str


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime
    documents_count: int
    active_learning_stats: Optional[ActiveLearningStats] = None
