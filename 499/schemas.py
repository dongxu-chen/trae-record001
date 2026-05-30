from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
from pydantic import BaseModel, Field


class PurchaseVerificationStatus(str, Enum):
    VERIFIED_PURCHASE = "verified_purchase"
    UNVERIFIED_PURCHASE = "unverified_purchase"
    NO_PURCHASE_RECORD = "no_purchase_record"


class ReputationEventType(str, Enum):
    REVIEW_REMOVED = "review_removed"
    FAKE_REVIEW_DETECTED = "fake_review_detected"
    BRUSH_ORDER_REPORTED = "brush_order_reported"
    MALICIOUS_REVIEW_REPORTED = "malicious_review_reported"
    PURCHASE_VERIFIED = "purchase_verified"
    HELPFUL_VOTE_RECEIVED = "helpful_vote_received"
    REVIEW_RESTORED = "review_restored"
    APPEAL_APPROVED = "appeal_approved"
    GANG_MEMBER_DETECTED = "gang_member_detected"


class PurchaseBehavior(BaseModel):
    has_purchased: bool = False
    purchase_verified: bool = False
    purchase_time: Optional[datetime] = None
    review_after_purchase: bool = False
    days_between_purchase_and_review: Optional[float] = None
    purchase_amount: Optional[float] = None
    return_requested: bool = False
    return_completed: bool = False


class ReputationEvent(BaseModel):
    event_type: ReputationEventType
    event_time: datetime
    severity: float = Field(default=1.0, ge=0.0, le=5.0)
    description: str = ""
    related_review_id: Optional[str] = None


class UserProfile(BaseModel):
    user_id: str
    account_age_days: int = Field(..., ge=0)
    total_reviews: int = Field(..., ge=0)
    verified_purchases: int = Field(..., ge=0)
    helpful_votes_received: int = Field(..., ge=0)
    review_removal_count: int = Field(..., ge=0)
    average_rating: float = Field(..., ge=1.0, le=5.0)
    registration_date: Optional[datetime] = None
    reputation_events: List[ReputationEvent] = Field(default_factory=list)
    current_reputation_score: Optional[float] = None


class VoteRecord(BaseModel):
    voter_id: str
    target_user_id: str
    target_review_id: str
    vote_time: datetime
    vote_type: str = "helpful"


class MerchantReply(BaseModel):
    reply_id: str = ""
    reply_content: str
    reply_time: datetime
    is_official: bool = True
    mentions_solution: bool = False
    mentions_compensation: bool = False
    is_apologetic: bool = False


class ReviewInteraction(BaseModel):
    review_id: str
    view_count: int = 0
    helpful_votes: int = 0
    unhelpful_votes: int = 0
    share_count: int = 0
    collect_count: int = 0
    comment_count: int = 0
    purchase_after_view_count: int = 0
    add_to_cart_after_view_count: int = 0
    vote_records: List[VoteRecord] = Field(default_factory=list)


class ReviewItem(BaseModel):
    review_id: str
    user_id: str
    product_id: str
    content: str
    rating: int = Field(..., ge=1, le=5)
    helpful_votes: int = Field(default=0, ge=0)
    create_time: datetime
    is_verified_purchase: bool = False
    has_images: bool = False
    has_videos: bool = False
    user_profile: Optional[UserProfile] = None
    purchase_behavior: Optional[PurchaseBehavior] = None
    merchant_reply: Optional[MerchantReply] = None
    interaction: Optional[ReviewInteraction] = None


class BatchReviewRequest(BaseModel):
    reviews: List[ReviewItem]
    interactions: Optional[List[ReviewInteraction]] = None
    vote_records: Optional[List[VoteRecord]] = None


class DimensionScores(BaseModel):
    authenticity: float = Field(..., ge=0.0, le=100.0)
    usefulness: float = Field(..., ge=0.0, le=100.0)
    completeness: float = Field(..., ge=0.0, le=100.0)
    user_reputation: float = Field(..., ge=0.0, le=100.0)


class PurchaseVerificationDetail(BaseModel):
    verification_status: PurchaseVerificationStatus
    purchase_score: float = Field(..., ge=0.0, le=100.0)
    penalty_applied: float = 0.0
    warnings: List[str] = Field(default_factory=list)


class GangDetectionResult(BaseModel):
    gang_id: str
    member_count: int
    mutual_vote_count: int
    suspicious_score: float = Field(..., ge=0.0, le=100.0)
    members: List[str]
    mutual_votes: List[Dict]
    is_suspicious: bool
    warnings: List[str] = Field(default_factory=list)


class AdoptionAnalysisResult(BaseModel):
    review_id: str
    adoption_score: float = Field(..., ge=0.0, le=100.0)
    purchase_influence: float = Field(..., ge=0.0, le=100.0)
    engagement_quality: float = Field(..., ge=0.0, le=100.0)
    decision_helpfulness: float = Field(..., ge=0.0, le=100.0)
    adoption_rank: Optional[int] = None
    warnings: List[str] = Field(default_factory=list)


class MerchantReplyImpact(BaseModel):
    reply_id: str = ""
    review_id: str
    quality_delta: float = 0.0
    trust_boost: float = 0.0
    satisfaction_improvement: float = 0.0
    adjusted_overall_score: Optional[float] = None
    impact_level: str = "none"
    warnings: List[str] = Field(default_factory=list)


class ReviewQualityResult(BaseModel):
    review_id: str
    overall_score: float = Field(..., ge=0.0, le=100.0)
    dimension_scores: DimensionScores
    purchase_verification: Optional[PurchaseVerificationDetail] = None
    should_collapse: bool
    is_low_quality: bool
    sort_score: float
    time_factor: Optional[float] = None
    gang_detection: Optional[GangDetectionResult] = None
    adoption_analysis: Optional[AdoptionAnalysisResult] = None
    merchant_reply_impact: Optional[MerchantReplyImpact] = None
    warnings: List[str] = Field(default_factory=list)
    processed_at: datetime


class BatchReviewResponse(BaseModel):
    results: List[ReviewQualityResult]
    total_processed: int
    low_quality_count: int
    collapsed_count: int
    gang_detections: List[GangDetectionResult] = Field(default_factory=list)
    top_adopted_reviews: List[AdoptionAnalysisResult] = Field(default_factory=list)


class ReputationEventRequest(BaseModel):
    user_id: str
    event: ReputationEvent


class GangDetectionRequest(BaseModel):
    reviews: List[ReviewItem]
    vote_records: List[VoteRecord]
