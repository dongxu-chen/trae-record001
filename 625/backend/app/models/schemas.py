from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=50, description="要摘要的原始文本")
    summary_type: Literal["extractive", "abstractive"] = Field(
        default="abstractive",
        description="摘要类型：extractive(抽取式) 或 abstractive(生成式)"
    )
    model: Literal["bart", "t5"] = Field(
        default="bart",
        description="生成式模型：bart 或 t5"
    )
    max_length: int = Field(
        default=150,
        ge=50,
        le=500,
        description="摘要最大长度（强制停止）"
    )
    min_length: int = Field(
        default=50,
        ge=20,
        le=200,
        description="摘要最小长度"
    )
    extractive_sentences: int = Field(
        default=3,
        ge=1,
        le=10,
        description="抽取式摘要的句子数量"
    )
    preserve_keywords: bool = Field(
        default=True,
        description="是否保留关键信息"
    )
    language: Optional[str] = Field(
        default=None,
        description="文本语言，自动检测或手动指定"
    )
    enable_sliding_window: bool = Field(
        default=True,
        description="启用滑动窗口处理长文档"
    )
    enable_fact_check: bool = Field(
        default=True,
        description="启用事实性校验（数字/实体）"
    )
    auto_correct: bool = Field(
        default=True,
        description="自动修正事实性错误"
    )
    enable_topic_segmentation: bool = Field(
        default=False,
        description="启用话题分段输出"
    )
    topic_method: Literal["kmeans", "lda"] = Field(
        default="kmeans",
        description="话题提取方法"
    )
    num_topics: Optional[int] = Field(
        default=None,
        description="话题数量，自动检测或手动指定"
    )


class FactCheckInfo(BaseModel):
    is_consistent: bool
    number_issues: List[dict] = []
    entity_issues: List[dict] = []
    corrections: List[dict] = []


class TopicSummary(BaseModel):
    topic_id: int
    keywords: List[str]
    topic_summary: str
    topic_text: str
    num_sentences: int


class TopicAwareSummary(BaseModel):
    topics: List[TopicSummary]
    num_topics: int
    method: str


class RougeScores(BaseModel):
    rouge1: float
    rouge2: float
    rougel: float
    rouge1_precision: float
    rouge2_precision: float
    rougel_precision: float
    rouge1_recall: float
    rouge2_recall: float
    rougel_recall: float


class QualityEvaluation(BaseModel):
    rouge_scores: RougeScores
    factual_consistency: float
    relevance_score: float
    coverage_score: float
    overall_score: float
    overall_quality: str
    key_points_covered: List[dict] = []
    missing_key_points: List[dict] = []


class SummarizeResponse(BaseModel):
    summary: str
    corrected_summary: Optional[str] = None
    original_length: int
    summary_length: int
    summary_type: str
    model: str
    language: str
    key_phrases: List[str]
    compression_ratio: float
    chunks_processed: int = 1
    fact_check: Optional[FactCheckInfo] = None
    topic_summary: Optional[TopicAwareSummary] = None
    quality_evaluation: Optional[QualityEvaluation] = None


class MultiDocSummarizeRequest(BaseModel):
    documents: List[str] = Field(..., min_items=2, description="文档列表")
    summary_type: Literal["extractive", "abstractive"] = Field(
        default="extractive",
        description="多文档摘要类型"
    )
    model: Literal["bart", "t5"] = Field(
        default="bart",
        description="生成式模型"
    )
    max_length: int = Field(
        default=300,
        ge=100,
        le=800,
        description="综合摘要最大长度"
    )
    num_sentences: int = Field(
        default=8,
        ge=3,
        le=20,
        description="抽取式摘要句子数量"
    )
    enable_quality_eval: bool = Field(
        default=True,
        description="启用质量评估"
    )


class DocContribution(BaseModel):
    doc_id: int
    sentences_used: int
    total_sentences: int


class MultiDocSummarizeResponse(BaseModel):
    summary: str
    summary_type: str
    num_docs: int
    model: Optional[str] = None
    doc_contributions: List[DocContribution] = []
    intermediate_summaries: Optional[List[str]] = None
    quality_evaluation: Optional[QualityEvaluation] = None


class EvaluateRequest(BaseModel):
    summary: str = Field(..., description="待评估的摘要")
    source_text: str = Field(..., description="原始文本")
    reference_summary: Optional[str] = Field(
        default=None,
        description="参考摘要（可选）"
    )


class EvaluateResponse(BaseModel):
    evaluation: QualityEvaluation


class HealthResponse(BaseModel):
    status: str
    models_loaded: List[str]
