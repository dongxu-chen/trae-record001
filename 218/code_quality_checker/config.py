import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class LinterConfig:
    enabled: bool = True
    config_file: Optional[str] = None
    auto_fix: bool = False
    extensions: List[str] = field(default_factory=list)
    args: List[str] = field(default_factory=list)
    jar_path: Optional[str] = None


@dataclass
class QualityGateRule:
    linter: str
    max_errors: Optional[int] = None
    max_warnings: Optional[int] = None
    min_score: Optional[float] = None
    enabled: bool = True


@dataclass
class QualityGateConfig:
    enabled: bool = True
    rules: List[QualityGateRule] = field(default_factory=list)
    block_merge: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QualityGateConfig":
        rules_data = data.get("rules", [])
        rules = []
        for rule_data in rules_data:
            rules.append(QualityGateRule(**rule_data))
        return cls(
            enabled=data.get("enabled", True),
            rules=rules,
            block_merge=data.get("block_merge", True),
        )


@dataclass
class CustomRuleConfig:
    name: str
    pattern: str
    message: str
    severity: str = "warning"
    extensions: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    case_sensitive: bool = True
    fixable: bool = False


@dataclass
class CustomRulesConfig:
    enabled: bool = False
    rules: List[CustomRuleConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: List[Dict[str, Any]]) -> "CustomRulesConfig":
        if not data:
            return cls(enabled=False)
        rules = []
        for rule_data in data:
            rules.append(CustomRuleConfig(**rule_data))
        return cls(enabled=True, rules=rules)


@dataclass
class HTMLReportConfig:
    enabled: bool = True
    template: Optional[str] = None
    include_charts: bool = True
    include_trend: bool = True
    include_details: bool = True
    theme: str = "default"


@dataclass
class ThresholdConfig:
    error: int = 0
    warning: int = 10
    pylint_score: float = 8.0


@dataclass
class IncrementalConfig:
    enabled: bool = True
    base_branch: str = "main"


@dataclass
class ReportConfig:
    format: str = "table"
    output_dir: str = "quality-reports"
    show_summary: bool = True
    html: HTMLReportConfig = field(default_factory=HTMLReportConfig)


@dataclass
class CIConfig:
    fail_on_threshold: bool = True
    generate_badge: bool = True


@dataclass
class AppConfig:
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    linters: Dict[str, LinterConfig] = field(default_factory=dict)
    incremental: IncrementalConfig = field(default_factory=IncrementalConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    ci: CIConfig = field(default_factory=CIConfig)
    quality_gate: QualityGateConfig = field(default_factory=QualityGateConfig)
    custom_rules: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        thresholds = ThresholdConfig(**data.get("thresholds", {}))

        linters = {}
        for name, linter_data in data.get("linters", {}).items():
            linters[name] = LinterConfig(**linter_data)

        incremental = IncrementalConfig(**data.get("incremental", {}))

        report_data = data.get("report", {})
        html_config = HTMLReportConfig(**report_data.get("html", {}))
        report = ReportConfig(
            format=report_data.get("format", "table"),
            output_dir=report_data.get("output_dir", "quality-reports"),
            show_summary=report_data.get("show_summary", True),
            html=html_config,
        )

        ci = CIConfig(**data.get("ci", {}))
        quality_gate = QualityGateConfig.from_dict(data.get("quality_gate", {}))
        custom_rules = data.get("custom_rules", [])

        return cls(
            thresholds=thresholds,
            linters=linters,
            incremental=incremental,
            report=report,
            ci=ci,
            quality_gate=quality_gate,
            custom_rules=custom_rules,
        )


def load_config(config_path: Optional[str] = None) -> AppConfig:
    if config_path is None:
        config_path = ".code-quality.yml"

    if not os.path.exists(config_path):
        print(f"Config file {config_path} not found, using defaults.")
        return AppConfig()

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return AppConfig.from_dict(data)
