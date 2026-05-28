from typing import List, Optional, Union, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class ResumeData(BaseModel):
    candidate_name: Optional[str] = Field(default=None, description="候选人姓名")
    phone: Optional[str] = Field(default=None, description="电话")
    email: Optional[str] = Field(default=None, description="邮箱")
    skills: List[str] = Field(default_factory=list, description="技能列表")
    work_experience: List[dict] = Field(default_factory=list, description="工作经验")
    education: List[dict] = Field(default_factory=list, description="教育经历")
    projects: List[dict] = Field(default_factory=list, description="项目经验")
    certifications: List[str] = Field(default_factory=list, description="证书")
    languages: List[str] = Field(default_factory=list, description="语言")
    raw_text: str = Field(default="", description="简历原始文本")
    full_text: str = Field(default="", description="简历完整文本")


class JobDescription(BaseModel):
    title: str = Field(..., description="岗位名称")
    description: str = Field(..., description="岗位描述")
    required_skills: List[str] = Field(default_factory=list, description="要求技能")
    min_education: str = Field(default="本科", description="最低学历要求")
    min_experience_years: Union[int, str] = Field(default=0, description="工作年限要求，支持表达式如\"3年以上\"、\"3-5年\"等")


class MatchReason(BaseModel):
    category: str = Field(..., description="匹配类别")
    detail: str = Field(..., description="匹配详情")
    score: float = Field(..., description="该类别得分")
    weight: float = Field(..., description="该类别权重")


class InterviewQuestion(BaseModel):
    question: str = Field(..., description="面试问题")
    category: str = Field(..., description="问题类别")
    reason: str = Field(..., description="推荐理由")


class MatchResult(BaseModel):
    candidate_name: str = Field(..., description="候选人姓名")
    overall_score: float = Field(..., description="综合匹配得分")
    skill_score: float = Field(..., description="技能匹配得分")
    experience_score: float = Field(..., description="经验匹配得分")
    education_score: float = Field(..., description="学历匹配得分")
    project_score: float = Field(..., description="项目匹配得分")
    match_reasons: List[MatchReason] = Field(default_factory=list, description="匹配理由列表")
    interview_questions: List[InterviewQuestion] = Field(default_factory=list, description="面试问题推荐")


class ScreeningResponse(BaseModel):
    job_title: str = Field(..., description="岗位名称")
    total_candidates: int = Field(..., description="候选人数")
    ranked_results: List[MatchResult] = Field(default_factory=list, description="排名结果")


class TalentPoolRecord(BaseModel):
    record_id: str = Field(..., description="人才库记录ID")
    candidate_name: str = Field(..., description="候选人姓名")
    phone: Optional[str] = Field(default=None, description="电话")
    email: Optional[str] = Field(default=None, description="邮箱")
    resume: ResumeData = Field(..., description="简历数据")
    fingerprint: str = Field(..., description="简历指纹（用于去重）")
    source: Optional[str] = Field(default=None, description="简历来源")
    added_time: datetime = Field(default_factory=datetime.now, description="入库时间")
    last_updated: datetime = Field(default_factory=datetime.now, description="最后更新时间")
    tags: List[str] = Field(default_factory=list, description="标签")
    status: str = Field(default="active", description="状态: active/archived/blacklisted")
    match_history: List[dict] = Field(default_factory=list, description="匹配历史")


class DedupResult(BaseModel):
    is_duplicate: bool = Field(..., description="是否重复")
    confidence: float = Field(..., description="重复置信度")
    duplicate_with: Optional[str] = Field(default=None, description="重复的记录ID")
    duplicate_candidate: Optional[str] = Field(default=None, description="重复的候选人姓名")
    matched_fields: List[str] = Field(default_factory=list, description="匹配的字段")
    suggestion: str = Field(..., description="处理建议")


class TalentPoolResponse(BaseModel):
    total_records: int = Field(..., description="人才库总记录数")
    active_records: int = Field(..., description="活跃记录数")
    recent_additions: int = Field(..., description="近期新增数")
    records: List[TalentPoolRecord] = Field(default_factory=list, description="记录列表")


class FunnelStage(BaseModel):
    stage_name: str = Field(..., description="阶段名称")
    stage_code: str = Field(..., description="阶段代码")
    candidate_count: int = Field(..., description="该阶段人数")
    conversion_rate: Optional[float] = Field(default=None, description="从上一阶段转化率")
    overall_rate: Optional[float] = Field(default=None, description="从简历投递的整体转化率")
    avg_days: Optional[float] = Field(default=None, description="该阶段平均停留天数")
    stage_detail: Optional[str] = Field(default=None, description="阶段说明")


class FunnelAnalysisResponse(BaseModel):
    job_title: str = Field(..., description="岗位名称")
    total_applicants: int = Field(..., description="总申请人数")
    stages: List[FunnelStage] = Field(default_factory=list, description="漏斗各阶段数据")
    overall_conversion: float = Field(..., description="整体转化率（录取率）")
    avg_hiring_days: Optional[float] = Field(default=None, description="平均招聘周期")
    bottlenecks: List[str] = Field(default_factory=list, description="瓶颈环节")
    suggestions: List[str] = Field(default_factory=list, description="优化建议")


class CompetitorAnalysis(BaseModel):
    company_name: str = Field(..., description="竞对公司名称")
    candidate_count: int = Field(..., description="来自该公司的候选人数")
    avg_match_score: float = Field(..., description="平均匹配得分")
    common_positions: List[str] = Field(default_factory=list, description="常见岗位")
    common_skills: List[str] = Field(default_factory=list, description="常见技能")
    outflow_direction: List[dict] = Field(default_factory=list, description="人才流向")
    talent_flow_score: float = Field(..., description="人才流动指数")


class TalentFlowRecord(BaseModel):
    from_company: str = Field(..., description="原公司")
    to_company: str = Field(..., description="目标公司")
    candidate_count: int = Field(..., description="流动人数")
    common_skills: List[str] = Field(default_factory=list, description="共性技能")
    avg_duration: Optional[float] = Field(default=None, description="平均任职时长")


class CompetitorResponse(BaseModel):
    total_companies: int = Field(..., description="涉及竞对公司数量")
    competitor_analysis: List[CompetitorAnalysis] = Field(default_factory=list, description="竞对分析列表")
    talent_flow: List[TalentFlowRecord] = Field(default_factory=list, description="人才流动记录")
    top_sources: List[str] = Field(default_factory=list, description="Top人才来源")
    market_insights: List[str] = Field(default_factory=list, description="市场洞察")