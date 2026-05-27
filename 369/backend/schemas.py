from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class DocumentBase(BaseModel):
    doc_id: str
    title: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class DocumentCreate(DocumentBase):
    pass


class Document(DocumentBase):
    created_at: datetime

    class Config:
        from_attributes = True


class QueryBase(BaseModel):
    query_id: str
    query_text: str
    description: Optional[str] = None
    query_type: Optional[str] = Field(default="information", description="查询类型: navigational, informational, transactional, exploratory")


class QueryCreate(QueryBase):
    pass


class Query(QueryBase):
    created_at: datetime

    class Config:
        from_attributes = True


class AnnotationBase(BaseModel):
    query_id: str
    doc_id: str
    relevance: int = Field(ge=0, le=3, description="0: 不相关, 1: 一般相关, 2: 相关, 3: 高度相关")
    annotator: Optional[str] = "system"
    request_id: Optional[str] = Field(default=None, description="关联的搜索请求ID，用于串联标注和搜索")


class AnnotationCreate(AnnotationBase):
    pass


class Annotation(AnnotationBase):
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    doc_id: str
    score: float
    rank: int
    title: Optional[str] = None
    content: Optional[str] = None
    relevant: Optional[bool] = None


class SearchRequest(BaseModel):
    query_text: str
    model_name: str = "default"
    k: int = 10
    index: str = "documents"
    request_id: Optional[str] = Field(default=None, description="请求唯一标识，用于串联搜索和标注")
    query_type: Optional[str] = Field(default=None, description="查询类型筛选")


class SearchResponse(BaseModel):
    query_id: str
    query_text: str
    model_name: str
    k: int
    results: List[SearchResult]
    total: int
    took: float
    request_id: str
    query_type: Optional[str] = None


class EvaluationMetrics(BaseModel):
    recall_at_k: float
    precision_at_k: float
    f1_at_k: float
    hit_rate: float
    mrr: float
    ndcg_at_k: float
    map_at_k: float
    average_precision: float


class EvaluationResult(BaseModel):
    evaluation_id: str
    model_name: str
    query_id: str
    query_text: str
    k: int
    results: List[SearchResult]
    metrics: EvaluationMetrics
    created_at: datetime


class ConfusionMatrix(BaseModel):
    tp: int
    fp: int
    fn: int
    tn: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    specificity: float


class ModelComparison(BaseModel):
    model_name: str
    k_values: List[int]
    recall_scores: List[float]
    precision_scores: List[float]
    f1_scores: List[float]
    hit_rates: List[float]
    ndcg_scores: List[float]


class FailureCase(BaseModel):
    query_id: str
    query_text: str
    expected_docs: List[str]
    returned_docs: List[Dict[str, Any]]
    missing_docs: List[Dict[str, Any]]
    irrelevant_docs: List[Dict[str, Any]]
    metrics: EvaluationMetrics
    query_type: Optional[str] = None
    failure_reason: Optional[str] = None
    failure_severity: Optional[str] = None


class FailureCaseStratifiedSample(BaseModel):
    total_cases: int
    sampled_cases: int
    strata: List[Dict[str, Any]]
    cases: List[FailureCase]


class ModelComparisonDrillDown(BaseModel):
    query_type: str
    query_count: int
    comparisons: List[ModelComparison]


class BatchAnnotationRequest(BaseModel):
    query_id: str
    annotations: List[AnnotationCreate]
    request_id: Optional[str] = Field(default=None, description="关联的搜索请求ID")


class ModelInfo(BaseModel):
    model_name: str
    description: Optional[str] = None
    endpoint: Optional[str] = None
    is_active: bool = True


class QueryTypeStats(BaseModel):
    query_type: str
    count: int
    avg_recall: float
    avg_precision: float
    avg_f1: float
    avg_ndcg: float


class ClickEventBase(BaseModel):
    request_id: str
    query_id: str
    doc_id: str
    rank: int
    click_position: int
    dwell_time: float = Field(default=0, description="停留时间(秒)")
    click_type: str = Field(default="normal", description="点击类型: normal, quick_view, deep_view, copy")
    session_id: Optional[str] = None


class ClickEventCreate(ClickEventBase):
    pass


class ClickEvent(ClickEventBase):
    created_at: datetime


class AutoAnnotationRequest(BaseModel):
    request_id: str
    query_id: str
    min_dwell_time: float = Field(default=3, description="最小停留时间(秒)")
    max_annotations: int = Field(default=10, description="最大自动标注数量")


class AutoAnnotationResult(BaseModel):
    request_id: str
    query_id: str
    auto_generated: bool
    annotations_count: int
    annotations: List[Dict[str, Any]]
    message: str


class ABTestConfigBase(BaseModel):
    test_name: str
    control_model: str
    treatment_model: str
    traffic_split: float = Field(default=0.5, description="实验组流量比例", ge=0.1, le=0.9)
    status: str = Field(default="draft", description="状态: draft, running, paused, completed")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class ABTestConfigCreate(ABTestConfigBase):
    pass


class ABTestConfig(ABTestConfigBase):
    test_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class ABTestAssignment(BaseModel):
    test_id: str
    session_id: str
    group: str
    model_name: str
    assigned_at: datetime


class ABTestMetrics(BaseModel):
    test_id: str
    test_name: str
    control_model: str
    treatment_model: str
    control: Dict[str, Any]
    treatment: Dict[str, Any]
    lift: Dict[str, Any]
    confidence: Dict[str, Any]
    sample_size: Dict[str, int]


class FeedbackLearningRequest(BaseModel):
    model_name: str
    feedback_type: str = Field(default="relevance", description="反馈类型: relevance, click, implicit")
    min_confidence: float = Field(default=0.7, description="最小置信度")
    training_data_format: str = Field(default="jsonl", description="训练数据格式")


class TrainingSample(BaseModel):
    query_id: str
    query_text: str
    doc_id: str
    doc_title: Optional[str] = None
    relevance: int
    source: str
    confidence: float
    created_at: datetime


class FeedbackLearningResult(BaseModel):
    model_name: str
    total_samples: int
    high_confidence_samples: int
    training_samples: List[TrainingSample]
    export_path: Optional[str] = None
    message: str


class ModelRetrainingConfig(BaseModel):
    model_name: str
    base_model: Optional[str] = None
    training_data_source: str = Field(default="annotations", description="数据来源: annotations, feedback, mixed")
    test_ratio: float = Field(default=0.2, description="测试集比例")
    hyperparameters: Optional[Dict[str, Any]] = None


class RetrainingResult(BaseModel):
    model_name: str
    new_version: str
    training_samples: int
    validation_samples: int
    training_metrics: Dict[str, Any]
    validation_metrics: Dict[str, Any]
    status: str
    message: str
