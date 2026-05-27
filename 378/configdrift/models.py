"""数据结构定义,避免循环导入."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from configdrift.compliance import ComplianceReport
from configdrift.detector import DriftReport
from configdrift.impact import ImpactReport


@dataclass
class InspectionResult:
    """单次巡检完整结果,包含漂移、合规、影响分析."""

    server: str
    service: str
    timestamp: str
    drift: Optional[DriftReport] = None
    compliance: Optional[ComplianceReport] = None
    impact: Optional[ImpactReport] = None
    before_snapshots: Any = None
    repair_commands: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "server": self.server,
            "service": self.service,
            "timestamp": self.timestamp,
            "drift": self.drift.to_dict() if self.drift else None,
            "compliance": self.compliance.to_dict() if self.compliance else None,
            "impact": self.impact.to_dict() if self.impact else None,
            "repair_commands": self.repair_commands or [],
        }
