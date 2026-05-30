import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

from es_collector import SlowQuery

logger = logging.getLogger(__name__)


class RateLimitAction(Enum):
    MONITOR = "monitor"
    WARN = "warn"
    THROTTLE = "throttle"
    BLOCK = "block"
    UNBLOCK = "unblock"


class ThrottlingLevel(Enum):
    NONE = "none"
    LIGHT = "light"
    MODERATE = "moderate"
    SEVERE = "severe"


@dataclass
class SourceRateInfo:
    source_id: str
    total_requests: int = 0
    slow_requests: int = 0
    last_request_time: float = 0.0
    window_requests: Deque[Tuple[float, bool]] = field(
        default_factory=lambda: deque(maxlen=1000)
    )
    violations: int = 0
    current_action: RateLimitAction = RateLimitAction.MONITOR
    throttling_level: ThrottlingLevel = ThrottlingLevel.NONE
    throttling_start_time: Optional[float] = None
    throttling_duration_seconds: int = 0
    blocked: bool = False
    blocked_reason: str = ""
    blocked_at: Optional[float] = None
    block_duration_seconds: int = 300

    def record_request(self, response_ms: float, is_slow: bool, slow_threshold_ms: float):
        now = time.time()
        self.total_requests += 1
        self.last_request_time = now
        if is_slow:
            self.slow_requests += 1
        self.window_requests.append((now, is_slow))

    def requests_per_second(self, window_seconds: int) -> float:
        if not self.window_requests:
            return 0.0
        now = time.time()
        cutoff = now - window_seconds
        count = sum(1 for ts, _ in self.window_requests if ts >= cutoff)
        return count / max(window_seconds, 1)

    def slow_ratio(self, window_seconds: int) -> float:
        if not self.window_requests:
            return 0.0
        now = time.time()
        cutoff = now - window_seconds
        recent = [(ts, slow) for ts, slow in self.window_requests if ts >= cutoff]
        if not recent:
            return 0.0
        slow_count = sum(1 for _, slow in recent if slow)
        return slow_count / len(recent)

    def avg_response_ms(self, window_seconds: int) -> float:
        return 0.0

    def should_unblock(self) -> bool:
        if not self.blocked or self.blocked_at is None:
            return False
        return time.time() - self.blocked_at >= self.block_duration_seconds


@dataclass
class RateLimitDecision:
    source_id: str
    action: RateLimitAction
    throttling_level: ThrottlingLevel
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)
    applied: bool = False
    dry_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "action": self.action.value,
            "throttling_level": self.throttling_level.value,
            "reason": self.reason,
            "details": self.details,
            "applied": self.applied,
            "dry_run": self.dry_run,
            "timestamp": time.time(),
        }


@dataclass
class RateLimitRule:
    rule_id: str
    name: str
    max_requests_per_second: float = 100.0
    max_slow_ratio: float = 0.3
    slow_threshold_ms: float = 3000.0
    window_seconds: int = 60
    violation_threshold: int = 3
    action_on_violation: RateLimitAction = RateLimitAction.THROTTLE
    throttling_level_on_violation: ThrottlingLevel = ThrottlingLevel.MODERATE
    block_after_violations: int = 5
    enabled: bool = True


class RateLimiter:
    def __init__(self,
                 slow_threshold_ms: float = 3000.0,
                 dry_run: bool = True,
                 auto_apply: bool = False,
                 default_max_rps: float = 100.0,
                 default_max_slow_ratio: float = 0.3):
        self.slow_threshold_ms = slow_threshold_ms
        self.dry_run = dry_run
        self.auto_apply = auto_apply
        self.default_max_rps = default_max_rps
        self.default_max_slow_ratio = default_max_slow_ratio
        self.rules: Dict[str, RateLimitRule] = {}
        self.source_info: Dict[str, SourceRateInfo] = {}
        self.decision_history: Deque[RateLimitDecision] = deque(maxlen=1000)
        self._load_default_rules()

    def _load_default_rules(self):
        self.rules["DEFAULT"] = RateLimitRule(
            rule_id="DEFAULT",
            name="默认限流规则",
            max_requests_per_second=self.default_max_rps,
            max_slow_ratio=self.default_max_slow_ratio,
            slow_threshold_ms=self.slow_threshold_ms,
            window_seconds=60,
            violation_threshold=3,
            action_on_violation=RateLimitAction.THROTTLE,
            throttling_level_on_violation=ThrottlingLevel.MODERATE,
            block_after_violations=5,
        )

        self.rules["STRICT"] = RateLimitRule(
            rule_id="STRICT",
            name="严格限流规则",
            max_requests_per_second=50.0,
            max_slow_ratio=0.15,
            slow_threshold_ms=self.slow_threshold_ms,
            window_seconds=120,
            violation_threshold=2,
            action_on_violation=RateLimitAction.THROTTLE,
            throttling_level_on_violation=ThrottlingLevel.SEVERE,
            block_after_violations=3,
        )

        self.rules["AGGRESSIVE"] = RateLimitRule(
            rule_id="AGGRESSIVE",
            name="激进限流规则",
            max_requests_per_second=20.0,
            max_slow_ratio=0.1,
            slow_threshold_ms=self.slow_threshold_ms,
            window_seconds=180,
            violation_threshold=1,
            action_on_violation=RateLimitAction.BLOCK,
            throttling_level_on_violation=ThrottlingLevel.SEVERE,
            block_after_violations=2,
        )

    def add_rule(self, rule: RateLimitRule):
        self.rules[rule.rule_id] = rule
        logger.info("Added rate limit rule: %s (%s)", rule.name, rule.rule_id)

    def get_or_create_source(self, source_id: str) -> SourceRateInfo:
        if source_id not in self.source_info:
            self.source_info[source_id] = SourceRateInfo(source_id=source_id)
        return self.source_info[source_id]

    def record_and_evaluate(
        self,
        slow_query: SlowQuery,
        source_id: str = "unknown",
        rule_id: str = "DEFAULT",
    ) -> RateLimitDecision:
        src_info = self.get_or_create_source(source_id)
        is_slow = slow_query.response_time_ms > self.slow_threshold_ms
        src_info.record_request(slow_query.response_time_ms, is_slow, self.slow_threshold_ms)

        if src_info.blocked:
            if src_info.should_unblock():
                return self._unblock_source(src_info, rule_id)
            return RateLimitDecision(
                source_id=source_id,
                action=RateLimitAction.BLOCK,
                throttling_level=ThrottlingLevel.SEVERE,
                reason=f"Source is blocked until {self._format_time(src_info.blocked_at + src_info.block_duration_seconds)}",
                details={"blocked_at": src_info.blocked_at, "block_duration": src_info.block_duration_seconds},
                dry_run=self.dry_run,
                applied=not self.dry_run,
            )

        rule = self.rules.get(rule_id, self.rules["DEFAULT"])
        return self._evaluate_source(src_info, rule, slow_query)

    def _evaluate_source(
        self,
        src_info: SourceRateInfo,
        rule: RateLimitRule,
        slow_query: SlowQuery,
    ) -> RateLimitDecision:
        rps = src_info.requests_per_second(rule.window_seconds)
        slow_ratio = src_info.slow_ratio(rule.window_seconds)

        violations: List[str] = []
        if rps > rule.max_requests_per_second:
            violations.append(
                f"请求速率 {rps:.1f} req/s 超过阈值 {rule.max_requests_per_second} req/s"
            )
        if slow_ratio > rule.max_slow_ratio:
            violations.append(
                f"慢查询比例 {slow_ratio * 100:.1f}% 超过阈值 {rule.max_slow_ratio * 100:.0f}%"
            )

        details = {
            "rule_id": rule.rule_id,
            "requests_per_second": round(rps, 2),
            "slow_ratio": round(slow_ratio * 100, 2),
            "total_requests": src_info.total_requests,
            "slow_requests": src_info.slow_requests,
            "violation_count": src_info.violations,
            "max_rps": rule.max_requests_per_second,
            "max_slow_ratio": rule.max_slow_ratio,
            "window_seconds": rule.window_seconds,
            "query_index": slow_query.index_name,
            "query_response_ms": slow_query.response_time_ms,
        }

        if not violations:
            if src_info.current_action != RateLimitAction.MONITOR:
                src_info.current_action = RateLimitAction.MONITOR
                src_info.throttling_level = ThrottlingLevel.NONE
                src_info.violations = max(0, src_info.violations - 1)
                src_info.throttling_start_time = None
                return RateLimitDecision(
                    source_id=src_info.source_id,
                    action=RateLimitAction.MONITOR,
                    throttling_level=ThrottlingLevel.NONE,
                    reason="查询行为恢复正常，解除限流",
                    details=details,
                    applied=self.auto_apply and not self.dry_run,
                    dry_run=self.dry_run,
                )
            return RateLimitDecision(
                source_id=src_info.source_id,
                action=RateLimitAction.MONITOR,
                throttling_level=ThrottlingLevel.NONE,
                reason="查询速率和慢查询比例均在正常范围内",
                details=details,
                dry_run=self.dry_run,
            )

        src_info.violations += 1
        reason = "; ".join(violations)

        if src_info.violations >= rule.block_after_violations:
            action = RateLimitAction.BLOCK
            level = ThrottlingLevel.SEVERE
            reason += f"；连续 {src_info.violations} 次违规，已触发封禁"
            details["block_duration_seconds"] = src_info.block_duration_seconds
            if self.auto_apply and not self.dry_run:
                src_info.blocked = True
                src_info.blocked_at = time.time()
                src_info.blocked_reason = reason
        elif src_info.violations >= rule.violation_threshold:
            action = rule.action_on_violation
            level = rule.throttling_level_on_violation
            reason += f"；第 {src_info.violations} 次违规，触发限流"
            if self.auto_apply and not self.dry_run:
                src_info.current_action = action
                src_info.throttling_level = level
                if src_info.throttling_start_time is None:
                    src_info.throttling_start_time = time.time()
        else:
            action = RateLimitAction.WARN
            level = ThrottlingLevel.LIGHT
            reason += f"；第 {src_info.violations} 次违规，发出警告"

        decision = RateLimitDecision(
            source_id=src_info.source_id,
            action=action,
            throttling_level=level,
            reason=reason,
            details=details,
            applied=self.auto_apply and not self.dry_run,
            dry_run=self.dry_run,
        )
        self.decision_history.append(decision)

        if decision.applied:
            logger.warning(
                "Rate limit applied: source=%s, action=%s, level=%s, reason=%s",
                src_info.source_id, action.value, level.value, reason,
            )
        else:
            logger.info(
                "Rate limit (dry-run): source=%s, action=%s, level=%s, reason=%s",
                src_info.source_id, action.value, level.value, reason,
            )

        return decision

    def _unblock_source(self, src_info: SourceRateInfo, rule_id: str) -> RateLimitDecision:
        src_info.blocked = False
        src_info.blocked_at = None
        src_info.blocked_reason = ""
        src_info.violations = 0
        src_info.current_action = RateLimitAction.MONITOR
        src_info.throttling_level = ThrottlingLevel.NONE
        logger.info("Source unblocked: %s", src_info.source_id)
        return RateLimitDecision(
            source_id=src_info.source_id,
            action=RateLimitAction.UNBLOCK,
            throttling_level=ThrottlingLevel.NONE,
            reason="封禁期限已到，自动解除封禁",
            details={"rule_id": rule_id},
            applied=True,
            dry_run=self.dry_run,
        )

    def get_throttled_sources(self) -> List[Tuple[str, SourceRateInfo]]:
        return [
            (sid, info) for sid, info in self.source_info.items()
            if info.current_action in (RateLimitAction.THROTTLE, RateLimitAction.BLOCK) or info.blocked
        ]

    def generate_report(self) -> str:
        throttled = self.get_throttled_sources()
        total_sources = len(self.source_info)
        total_requests = sum(info.total_requests for info in self.source_info.values())
        total_slow = sum(info.slow_requests for info in self.source_info.values())

        lines = [
            "=" * 70,
            "🚦 自动限流状态报告",
            "=" * 70,
            f"模式: {'演练模式' if self.dry_run else '生产模式'}",
            f"自动应用: {'开启' if self.auto_apply else '关闭'}",
            f"慢查询阈值: {self.slow_threshold_ms}ms",
            "",
            f"总体统计:",
            f"  监控来源总数: {total_sources}",
            f"  总请求数: {total_requests}",
            f"  慢查询总数: {total_slow}",
            f"  总体慢查询比例: {total_slow / max(total_requests, 1) * 100:.1f}%",
            f"  当前限流/封禁来源: {len(throttled)}",
            "",
        ]

        if throttled:
            lines.append("当前限流/封禁来源:")
            for sid, info in throttled:
                status = "🔴 封禁" if info.blocked else "🟡 限流"
                action_label = info.current_action.value if not info.blocked else "block"
                level_label = info.throttling_level.value if not info.blocked else "severe"
                lines.append(
                    f"  {status} {sid} | action={action_label} | level={level_label}"
                    f" | 违规={info.violations}次"
                )
            lines.append("")

        lines.append("限流规则说明:")
        for rid, rule in self.rules.items():
            lines.append(
                f"  - [{rid}] {rule.name}: "
                f"RPS ≤ {rule.max_requests_per_second}, "
                f"慢查询比例 ≤ {rule.max_slow_ratio * 100:.0f}%, "
                f"窗口 {rule.window_seconds}s, "
                f"违规 {rule.violation_threshold} 次触发 {rule.action_on_violation.value}"
            )
        lines.append("")

        lines.append("限流级别说明:")
        lines.append("  - LIGHT (轻度): 警告，记录日志，不实际限流")
        lines.append("  - MODERATE (中度): 限流，将请求速率限制为原有的 50%")
        lines.append("  - SEVERE (严重): 限流，将请求速率限制为原有的 20% 或直接封禁")
        lines.append("")

        lines.append("操作建议:")
        if self.dry_run:
            lines.append("  ⚠ 当前为演练模式，所有限流措施不会实际生效。")
            lines.append("    如需实际生效，请设置 auto_apply=True 或 --apply 参数。")
        if not self.auto_apply:
            lines.append("  ⚠ 自动应用已关闭，限流决策仅生成报告，需要手动执行。")
        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)

    def get_recent_decisions(
        self,
        source_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[RateLimitDecision]:
        decisions = list(self.decision_history)
        if source_id:
            decisions = [d for d in decisions if d.source_id == source_id]
        return decisions[-limit:]

    @staticmethod
    def _format_time(timestamp: Optional[float]) -> str:
        if timestamp is None:
            return "N/A"
        import datetime
        return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def extract_source_id(
    slow_query: SlowQuery,
    headers: Optional[Dict[str, Any]] = None,
    default_source: str = "unknown",
) -> str:
    parts = []
    if slow_query.index_name:
        parts.append(f"idx:{slow_query.index_name}")
    if headers:
        for h in ["X-Forwarded-For", "X-Real-IP", "Referer", "User-Agent", "X-Client-ID"]:
            if h in headers and headers[h]:
                val = str(headers[h])[:50]
                parts.append(f"ip:{val}")
                break
        if "X-App-Name" in headers:
            parts.append(f"app:{headers['X-App-Name']}")
        if "X-User-ID" in headers:
            parts.append(f"user:{headers['X-User-ID']}")
    if not parts:
        parts.append(default_source)
    return "|".join(parts)
