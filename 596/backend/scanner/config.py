from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class VulnerabilityStatus(str, Enum):
    NEW = "new"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    FIXED = "fixed"
    VERIFIED = "verified"
    CLOSED = "closed"
    REOPENED = "reopened"


class ExploitResult(BaseModel):
    exploit_type: str
    success: bool
    data_extracted: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: Optional[str] = None
    exploit_time: str = Field(default_factory=lambda: datetime.now().isoformat())


class Comment(BaseModel):
    author: str
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class VulnerabilityRecord(BaseModel):
    vuln_id: str
    vulnerability: Vulnerability
    status: VulnerabilityStatus = VulnerabilityStatus.NEW
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    exploit_result: Optional[ExploitResult] = None
    assignee: Optional[str] = None
    priority: Optional[str] = None
    cvss_score: Optional[float] = None
    fix_commit: Optional[str] = None
    fix_date: Optional[str] = None
    comments: List[Comment] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    history: List[Dict[str, Any]] = Field(default_factory=list)


class RoleConfig(BaseModel):
    name: str
    description: Optional[str] = None
    auth_type: str = "none"
    auth_token: Optional[str] = None
    auth_headers: Optional[Dict[str, str]] = None
    is_admin: bool = False


class ScanConfig(BaseModel):
    target_url: str
    auth_type: str = "none"
    auth_token: Optional[str] = None
    auth_headers: Optional[Dict[str, str]] = None
    roles: Optional[List[RoleConfig]] = None
    concurrency: int = 5
    scan_types: List[str] = ["sql_injection", "xxe", "idor", "privilege_escalation", "business_logic"]
    verify_ssl: bool = False
    timeout: int = 10
    max_retries: int = 3
    false_positive_verification: bool = True
    verification_replay_count: int = 3
    enable_session_isolation: bool = True
    enable_exploit: bool = True
    exploit_depth: str = "medium"


class VerificationResult(BaseModel):
    replay_count: int
    success_count: int
    consistency_score: float
    original_response: Dict[str, Any]
    replay_responses: List[Dict[str, Any]]
    is_consistent: bool


class Vulnerability(BaseModel):
    type: str
    severity: str
    endpoint: str
    method: str
    payload: str
    evidence: str
    description: str
    recommendation: str
    verified: bool = False
    verification_result: Optional[VerificationResult] = None
    role_context: Optional[str] = None
    comparison_evidence: Optional[str] = None
    exploit_result: Optional[ExploitResult] = None


class ScanResult(BaseModel):
    target_url: str
    scan_time: str
    total_requests: int
    vulnerabilities: List[Vulnerability]
    scan_status: str
    roles_scanned: Optional[List[str]] = None
    session_id: Optional[str] = None
    exploited_data: Optional[List[Dict[str, Any]]] = None


class VulnerabilityFilter(BaseModel):
    status: Optional[List[VulnerabilityStatus]] = None
    severity: Optional[List[str]] = None
    vuln_type: Optional[List[str]] = None
    assignee: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    tags: Optional[List[str]] = None


class StatusUpdateRequest(BaseModel):
    status: VulnerabilityStatus
    comment: Optional[str] = None
    author: Optional[str] = None
