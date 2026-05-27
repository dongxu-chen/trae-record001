"""配置合规检查模块.

基于 CIS Benchmark 等业界基准,对各服务配置进行安全合规性检测.
规则均以数据驱动的方式定义,方便扩展.

当前内置:
    - Nginx CIS 基线 (精简版)
    - MySQL CIS 基线 (精简版)
    - Redis CIS 基线 (精简版)
    - Kafka CIS 基线 (精简版)

每条规则:
    id, severity, description, check(data) -> (bool, detail)
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional

from configdrift.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ComplianceRule:
    """合规规则定义."""

    id: str
    service: str
    severity: str  # high / medium / low
    description: str
    rationale: str = ""
    remediation: str = ""
    check: Callable[[Dict[str, Any]], tuple] = None  # (passed, detail)

    def run(self, data: Dict[str, Any]) -> "ComplianceResult":
        try:
            passed, detail = self.check(data) if self.check else (True, "")
        except Exception as e:
            passed, detail = False, f"check error: {e}"
        return ComplianceResult(
            rule_id=self.id,
            service=self.service,
            severity=self.severity,
            description=self.description,
            passed=passed,
            detail=detail,
            remediation=self.remediation,
            rationale=self.rationale,
        )


@dataclass
class ComplianceResult:
    rule_id: str
    service: str
    severity: str
    description: str
    passed: bool
    detail: str = ""
    remediation: str = ""
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ComplianceReport:
    server: str
    service: str
    profile: str
    results: List[ComplianceResult] = field(default_factory=list)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        return len(self.results) - self.passed_count

    @property
    def score(self) -> float:
        if not self.results:
            return 0.0
        return round(self.passed_count / len(self.results) * 100, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "server": self.server,
            "service": self.service,
            "profile": self.profile,
            "total": len(self.results),
            "passed": self.passed_count,
            "failed": self.failed_count,
            "score": self.score,
            "results": [r.to_dict() for r in self.results],
        }


# ---------------------------------------------------------------------------
# 辅助函数: 从字典获取值 (支持 nginx block 风格 "http > server :: listen")
# ---------------------------------------------------------------------------

def _get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """带 section 支持的键查找."""
    if key in data:
        return data[key]
    # 尝试 section 前缀模糊匹配
    for k, v in data.items():
        if k.endswith(" :: " + key) or k.endswith("." + key):
            return v
    return default


def _bool(v: Any) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        if v.lower() in ("on", "yes", "true", "1"):
            return True
        if v.lower() in ("off", "no", "false", "0"):
            return False
    return None


# ---------------------------------------------------------------------------
# 规则库
# ---------------------------------------------------------------------------

# Nginx: https://www.cisecurity.org/benchmark/nginx
_NGINX_RULES: List[ComplianceRule] = [
    ComplianceRule(
        id="NGINX-001",
        service="nginx",
        severity="high",
        description="禁用 server_tokens 隐藏版本号",
        rationale="避免暴露 Nginx 版本,降低针对性攻击风险",
        remediation="http 块内添加 server_tokens off;",
        check=lambda d: (_get(d, "server_tokens") in ("off", "0", False, "no"),
                         f"当前值: {_get(d, 'server_tokens')}"),
    ),
    ComplianceRule(
        id="NGINX-002",
        service="nginx",
        severity="high",
        description="禁用 ETag (减少信息泄露)",
        rationale="ETag 可能泄露 inode 等系统信息",
        remediation="etag off;",
        check=lambda d: (_get(d, "etag") in ("off", "0", False, "no"),
                         f"当前值: {_get(d, 'etag')}"),
    ),
    ComplianceRule(
        id="NGINX-003",
        service="nginx",
        severity="high",
        description="启用 HSTS (Strict-Transport-Security)",
        rationale="防止 SSL 剥离攻击",
        remediation="add_header Strict-Transport-Security 'max-age=31536000; includeSubDomains' always;",
        check=lambda d: ("Strict-Transport-Security" in str(_get(d, "add_header", "")),
                         f"当前值: {_get(d, 'add_header')}"),
    ),
    ComplianceRule(
        id="NGINX-004",
        service="nginx",
        severity="medium",
        description="禁用不必要的 HTTP 方法 (TRACE/TRACK)",
        rationale="TRACE 可被用于 XST 攻击",
        remediation="if ($request_method ~ ^(TRACE|TRACK)$) { return 405; }",
        check=lambda d: (True, "手动核查"),
    ),
    ComplianceRule(
        id="NGINX-005",
        service="nginx",
        severity="medium",
        description="限制请求体大小 client_max_body_size",
        rationale="防止 DoS 攻击",
        remediation="client_max_body_size 10m;",
        check=lambda d: (_get(d, "client_max_body_size") is not None,
                         f"当前值: {_get(d, 'client_max_body_size')}"),
    ),
]

# MySQL: https://www.cisecurity.org/benchmark/mysql
_MYSQL_RULES: List[ComplianceRule] = [
    ComplianceRule(
        id="MYSQL-001",
        service="mysql",
        severity="high",
        description="禁用 local_infile (防止任意文件读取)",
        rationale="local_infile 可被利用读取服务器敏感文件",
        remediation="[mysqld] 下 local_infile = 0",
        check=lambda d: (_get(d, "mysqld :: local_infile") in (0, "0", False, "OFF", "off"),
                         f"当前值: {_get(d, 'mysqld :: local_infile')}"),
    ),
    ComplianceRule(
        id="MYSQL-002",
        service="mysql",
        severity="high",
        description="禁用 symbolic-links",
        rationale="符号链接可能导致越权访问数据文件",
        remediation="symbolic-links = 0",
        check=lambda d: (_get(d, "mysqld :: symbolic-links") in (0, "0", False, "OFF"),
                         f"当前值: {_get(d, 'mysqld :: symbolic-links')}"),
    ),
    ComplianceRule(
        id="MYSQL-003",
        service="mysql",
        severity="medium",
        description="设置 max_connections 合理值",
        rationale="防止资源耗尽",
        remediation="max_connections = 500",
        check=lambda d: (
            isinstance(_get(d, "mysqld :: max_connections"), int)
            and _get(d, "mysqld :: max_connections") > 0,
            f"当前值: {_get(d, 'mysqld :: max_connections')}",
        ),
    ),
    ComplianceRule(
        id="MYSQL-004",
        service="mysql",
        severity="medium",
        description="开启 log_error",
        rationale="错误日志是审计与故障排查的基础",
        remediation="log_error = /var/log/mysql/error.log",
        check=lambda d: (_get(d, "mysqld :: log_error") is not None,
                         f"当前值: {_get(d, 'mysqld :: log_error')}"),
    ),
    ComplianceRule(
        id="MYSQL-005",
        service="mysql",
        severity="high",
        description="启用 skip_name_resolve (禁用 DNS 反查)",
        rationale="避免 DNS 劫持,提升连接性能",
        remediation="skip_name_resolve = 1",
        check=lambda d: (_get(d, "mysqld :: skip_name_resolve") in (1, "1", True, "ON"),
                         f"当前值: {_get(d, 'mysqld :: skip_name_resolve')}"),
    ),
]

# Redis
_REDIS_RULES: List[ComplianceRule] = [
    ComplianceRule(
        id="REDIS-001",
        service="redis",
        severity="high",
        description="必须设置 requirepass",
        rationale="Redis 默认无密码,暴露即被入侵",
        remediation="requirepass <strong_password>",
        check=lambda d: (
            _get(d, "requirepass") is not None and _get(d, "requirepass") != "",
            f"当前值: {_get(d, 'requirepass')}",
        ),
    ),
    ComplianceRule(
        id="REDIS-002",
        service="redis",
        severity="high",
        description="禁用 CONFIG 等危险命令",
        rationale="CONFIG/FLUSHALL 等命令可能被恶意利用",
        remediation="rename-command CONFIG \"\"",
        check=lambda d: (
            any("CONFIG" in str(v).upper() for v in d.values()),
            "建议 rename-command CONFIG",
        ),
    ),
    ComplianceRule(
        id="REDIS-003",
        service="redis",
        severity="high",
        description="绑定特定网卡,不绑定 0.0.0.0",
        rationale="避免 Redis 暴露到公网",
        remediation="bind 127.0.0.1 <内网IP>",
        check=lambda d: (
            "0.0.0.0" not in str(_get(d, "bind", "")),
            f"当前 bind: {_get(d, 'bind')}",
        ),
    ),
    ComplianceRule(
        id="REDIS-004",
        service="redis",
        severity="medium",
        description="禁用 protected-mode 需配合密码",
        rationale="protected-mode no 且无密码 = 严重风险",
        check=lambda d: (
            not (_get(d, "protected-mode") == "no"
                 and _get(d, "requirepass") in (None, "")),
            f"protected-mode={_get(d, 'protected-mode')} requirepass={_get(d, 'requirepass')}",
        ),
    ),
]

# Kafka
_KAFKA_RULES: List[ComplianceRule] = [
    ComplianceRule(
        id="KAFKA-001",
        service="kafka",
        severity="high",
        description="禁用 Topic 自动创建 auto.create.topics.enable",
        rationale="防止误操作或恶意创建 Topic",
        remediation="auto.create.topics.enable=false",
        check=lambda d: (_get(d, "auto.create.topics.enable") in ("false", "0", False, "no"),
                         f"当前值: {_get(d, 'auto.create.topics.enable')}"),
    ),
    ComplianceRule(
        id="KAFKA-002",
        service="kafka",
        severity="high",
        description="开启 SSL 认证",
        rationale="Kafka 明文传输易被嗅探",
        remediation="listeners=SSL://:9093",
        check=lambda d: ("SSL" in str(_get(d, "listeners", "")).upper(),
                         f"当前 listeners: {_get(d, 'listeners')}"),
    ),
    ComplianceRule(
        id="KAFKA-003",
        service="kafka",
        severity="medium",
        description="设置合理的 replication.factor >= 2",
        rationale="保证高可用",
        check=lambda d: (
            isinstance(_get(d, "default.replication.factor"), int)
            and _get(d, "default.replication.factor") >= 2,
            f"当前值: {_get(d, 'default.replication.factor')}",
        ),
    ),
]


RULE_LIBRARY: Dict[str, List[ComplianceRule]] = {
    "nginx": _NGINX_RULES,
    "mysql": _MYSQL_RULES,
    "redis": _REDIS_RULES,
    "kafka": _KAFKA_RULES,
}


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def run_compliance(service: str,
                   data: Dict[str, Any],
                   profile: str = "level1",
                   server: str = "") -> ComplianceReport:
    """对某服务配置运行合规检查."""
    rules = RULE_LIBRARY.get(service, [])
    report = ComplianceReport(server=server, service=service, profile=profile)
    for r in rules:
        result = r.run(data)
        report.results.append(result)
        if not result.passed:
            logger.debug("[%s] FAIL %s: %s", service, r.id, result.detail)
    logger.info("[%s/%s] 合规得分: %.1f%% (%d/%d)",
                server, service, report.score,
                report.passed_count, len(report.results))
    return report
