from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class BusinessInfo(BaseModel):
    company_id: str
    company_name: str
    registered_capital: float
    paid_in_capital: float
    established_date: str
    operating_status: str
    industry: str
    business_scope: str
    number_of_employees: int
    registered_address: str


class ShareholderInfo(BaseModel):
    company_id: str
    shareholder_name: str
    share_ratio: float
    shareholder_type: str


class ExecutiveInfo(BaseModel):
    company_id: str
    name: str
    position: str
    tenure_years: float


class JudicialRisk(BaseModel):
    company_id: str
    lawsuit_count: int = 0
    executed_person_count: int = 0
    total_executed_amount: float = 0.0
    administrative_penalty_count: int = 0
    total_penalty_amount: float = 0.0
    contract_breach_count: int = 0
    abnormal_operation_records: int = 0
    dishonest_records: int = 0


class IntellectualProperty(BaseModel):
    company_id: str
    patent_count: int = 0
    invention_patent_count: int = 0
    utility_model_count: int = 0
    trademark_count: int = 0
    copyright_count: int = 0
    patent_invalidation_count: int = 0


class TaxRecord(BaseModel):
    company_id: str
    tax_arrears_count: int = 0
    total_arrears_amount: float = 0.0
    tax_credit_rating: str = "B"
    continuous_tax_years: int = 0
    annual_tax_amount: float = 0.0


class FinancialInfo(BaseModel):
    company_id: str
    revenue: float = 0.0
    net_profit: float = 0.0
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    current_ratio: float = 0.0
    debt_to_equity_ratio: float = 0.0
    roe: float = 0.0


class LoanRecord(BaseModel):
    company_id: str
    loan_id: str
    principal_amount: float
    outstanding_amount: float
    issue_date: str
    maturity_date: str
    interest_rate: float
    repayment_status: str
    overdue_days: int = 0


class CompanyInput(BaseModel):
    business_info: BusinessInfo
    shareholders: List[ShareholderInfo] = []
    executives: List[ExecutiveInfo] = []
    judicial_risk: JudicialRisk
    ip: IntellectualProperty
    tax_record: TaxRecord
    financial_info: FinancialInfo
    loan_records: List[LoanRecord] = []


class CreditScoreResponse(BaseModel):
    company_id: str
    credit_score: float
    rating: str
    risk_level: str
    risk_factors: List[Dict[str, Any]]
    key_strengths: List[str]
    recommendation: str
    feature_contributions: List[Dict[str, Any]]


class MonitoringAlert(BaseModel):
    alert_id: str
    company_id: str
    alert_type: str
    alert_level: str
    description: str
    event_date: str
    impact_score: float
    recommended_action: str


class PostLoanMonitoringResponse(BaseModel):
    company_id: str
    current_score: float
    baseline_score: float
    score_change: float
    alert_count: int
    alerts: List[MonitoringAlert]
    risk_assessment: str
    monitoring_status: str


class RiskFactor(BaseModel):
    factor: str
    description: str
    impact: float
    direction: str
    category: str
