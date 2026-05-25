from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import date
import warnings
warnings.filterwarnings('ignore')


class CompetitionEnvironment(BaseModel):
    same_period_movies: int = Field(..., description="同期上映电影数量", ge=0)
    average_competitor_budget: float = Field(..., description="竞争对手平均宣发预算（万元）", ge=0)
    genre_overlap_ratio: float = Field(..., description="类型重叠率", ge=0, le=1)
    competitor_ratings: Optional[List[float]] = Field(None, description="竞争对手评分")


class PreSalesData(BaseModel):
    total_amount: float = Field(..., description="预售总金额（万元）", ge=0)
    daily_sales: List[float] = Field(..., description="每日预售数据序列，按上映前倒序对齐（万元）")
    presale_days: int = Field(..., description="预售天数", ge=0)
    wish_count: Optional[int] = Field(0, description="想看人数", ge=0)


class PromotionTimeSeries(BaseModel):
    daily_spend: List[float] = Field(..., description="每日宣发投入序列，与预售序列对齐（万元）")
    spend_pattern: Optional[str] = Field(None, description="宣发投入模式：front_loaded/back_loaded/uniform/pulsed")
    total_spend: Optional[float] = Field(None, description="累计宣发总投入（万元）", ge=0)


class PointScreenData(BaseModel):
    screen_count: int = Field(0, description="点映场次数量", ge=0)
    total_viewers: int = Field(0, description="点映观众总人数", ge=0)
    average_occupancy: float = Field(0.0, description="点映平均上座率", ge=0, le=1)
    point_screen_days: int = Field(0, description="点映天数", ge=0)
    average_score: float = Field(0.0, description="点映观众平均评分（0-10分）", ge=0, le=10)
    positive_review_ratio: float = Field(0.0, description="正面评论占比", ge=0, le=1)
    social_media_mentions: int = Field(0, description="社交媒体提及次数", ge=0)
    want_to_watch_increase: int = Field(0, description="点映后想看人数增长", ge=0)
    viewer_comments: Optional[List[str]] = Field(None, description="观众评论摘要")


class WOMScoring(BaseModel):
    douban_score: Optional[float] = Field(None, description="豆瓣评分（0-10）", ge=0, le=10)
    maoyan_score: Optional[float] = Field(None, description="猫眼评分（0-10）", ge=0, le=10)
    taopiaopiao_score: Optional[float] = Field(None, description="淘票票评分（0-10）", ge=0, le=10)
    imdb_score: Optional[float] = Field(None, description="IMDb评分（0-10）", ge=0, le=10)
    rotten_tomatoes: Optional[float] = Field(None, description="烂番茄新鲜度（0-100）", ge=0, le=100)
    metacritic: Optional[float] = Field(None, description="Metacritic评分（0-100）", ge=0, le=100)


class MovieFeatures(BaseModel):
    title: str = Field(..., description="电影名称")
    genres: List[str] = Field(..., description="电影类型列表", min_length=1)
    director: str = Field(..., description="导演姓名")
    main_actor: str = Field(..., description="主演姓名")
    release_date: str = Field(..., description="上映日期（YYYY-MM-DD）")
    promotion_budget: float = Field(..., description="宣发总费用（万元）", ge=0)
    promotion_timeseries: Optional[PromotionTimeSeries] = Field(None, description="宣发费用时间序列")
    runtime: int = Field(120, description="片长（分钟）", ge=1, le=300)
    production_budget: Optional[float] = Field(None, description="制作成本（万元）", ge=0)
    competition_environment: CompetitionEnvironment
    pre_sales_data: PreSalesData
    point_screen_data: Optional[PointScreenData] = Field(None, description="点映数据")
    wom_scoring: Optional[WOMScoring] = Field(None, description="口碑评分数据")

    @field_validator('release_date')
    @classmethod
    def validate_release_date(cls, v):
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError('上映日期格式必须为 YYYY-MM-DD')
        return v

    @field_validator('genres')
    @classmethod
    def validate_genres(cls, v):
        if not v or len(v) == 0:
            raise ValueError('至少指定一个电影类型')
        return v


class PredictionInterval(BaseModel):
    lower: float
    upper: float
    point: float
    confidence: float
    quantiles: Dict[str, float]


class FeatureImportance(BaseModel):
    feature: str
    importance: float
    importance_percent: float


class FeatureGroupImportance(BaseModel):
    rank: int
    group_name: str
    importance_percent: float


class LocalFeatureContribution(BaseModel):
    feature: str
    value: float
    shap_value: float
    impact: str


class ModelContribution(BaseModel):
    target: str
    xgb_weight: float
    lstm_weight: float
    intercept: float


class WeeklyForecast(BaseModel):
    week: int
    week_box_office: float
    cumulative_box_office: float
    wom_multiplier: float
    share_of_total: float


class WOMAnalysis(BaseModel):
    weekly_forecast: List[WeeklyForecast]
    adjusted_first_week: float
    adjusted_total: float
    legs_ratio: float
    word_of_mouth_score: float
    word_of_mouth_impact: float
    point_screen_correction: float
    peak_week: int
    forecast_weeks: int
    wom_recommendation: str


class SegmentPrice(BaseModel):
    optimal_price: float
    expected_revenue: float
    expected_occupancy: float
    expected_demand: float
    price_range: List[float]
    demand_elasticity: float


class SegmentPricing(BaseModel):
    weekday: SegmentPrice
    weekend: SegmentPrice


class PricingStrategy(BaseModel):
    average_ticket_price: float
    min_suggested_price: float
    max_suggested_price: float
    price_sensitivity_index: float
    segment_pricing: Dict[str, SegmentPricing]
    wom_adjustment: float
    recommendation: str


class PredictionResponse(BaseModel):
    movie_title: str
    first_week_box_office: PredictionInterval
    total_box_office: PredictionInterval
    model_contributions: List[ModelContribution]
    feature_importance: List[FeatureImportance]
    feature_group_importance: List[FeatureGroupImportance]
    local_explanation: Dict[str, Any]
    prediction_confidence: float
    wom_analysis: Optional[WOMAnalysis] = None
    pricing_strategy: Optional[PricingStrategy] = None
    point_screen_applied: bool = False
    point_screen_correction_factor: float = 1.0


class HealthResponse(BaseModel):
    status: str
    model_ready: bool
    version: str


class BatchPredictionRequest(BaseModel):
    movies: List[MovieFeatures]
    confidence: float = Field(0.9, description="预测置信度", ge=0.5, le=0.99)
