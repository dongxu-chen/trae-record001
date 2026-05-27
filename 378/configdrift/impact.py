"""配置影响分析 (Impact Analysis).

功能:
    - 在配置变更前后,采集关键监控指标 (Prometheus)
    - 对比变更前后的平均/最大值,量化配置变更的影响
    - 输出影响报告,辅助判断是否需要回滚

设计:
    - 默认禁用,通过 ``impact_enabled: true`` 开启
    - 变更前自动采集 ``metrics_window_minutes`` 的指标作为基线
    - 变更后在设定的时间窗口内再次采集并对比
    - 依赖 Prometheus HTTP API (无需额外库,使用 urllib)
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from configdrift.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MetricQuery:
    """单个指标查询定义."""

    name: str
    service: str
    query: str  # PromQL
    description: str = ""
    unit: str = ""


# 默认关键指标
DEFAULT_METRICS: Dict[str, List[MetricQuery]] = {
    "nginx": [
        MetricQuery("nginx_requests", "nginx", "rate(nginx_http_requests_total[5m])",
                    "请求速率", "qps"),
        MetricQuery("nginx_connections", "nginx", "nginx_connections_active",
                    "活跃连接数", "个"),
        MetricQuery("nginx_response_time", "nginx", "histogram_quantile(0.95, rate(nginx_http_request_duration_seconds_bucket[5m]))",
                    "P95 响应时间", "s"),
    ],
    "mysql": [
        MetricQuery("mysql_qps", "mysql", "rate(mysql_global_status_questions[5m])",
                    "QPS", "qps"),
        MetricQuery("mysql_connections", "mysql", "mysql_global_status_threads_connected",
                    "连接数", "个"),
        MetricQuery("mysql_slow_queries", "mysql", "rate(mysql_global_status_slow_queries[5m])",
                    "慢查询速率", "qps"),
    ],
    "redis": [
        MetricQuery("redis_ops", "redis", "rate(redis_commands_processed_total[5m])",
                    "OPS", "qps"),
        MetricQuery("redis_memory", "redis", "redis_memory_used_bytes",
                    "内存使用", "MB"),
        MetricQuery("redis_connections", "redis", "redis_connected_clients",
                    "连接数", "个"),
    ],
    "kafka": [
        MetricQuery("kafka_messages_in", "kafka", "rate(kafka_server_broker_topic_metrics_messagesin_total[5m])",
                    "消息入站速率", "msg/s"),
        MetricQuery("kafka_under_replicated", "kafka", "kafka_server_replicamanager_underreplicatedpartitions",
                    "未复制分区数", "个"),
        MetricQuery("kafka_latency", "kafka", "kafka_network_requestmetrics_requesttotaltimems{request=\"Produce\"}",
                    "Produce 延迟", "ms"),
    ],
}


@dataclass
class MetricSnapshot:
    """某一时刻的指标快照."""

    metric: str
    service: str
    timestamp: float
    avg: float = 0.0
    max: float = 0.0
    min: float = 0.0
    values: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp_str"] = time.strftime("%Y-%m-%d %H:%M:%S",
                                           time.localtime(self.timestamp))
        return d


@dataclass
class ImpactReport:
    """单个服务的影响分析报告."""

    service: str
    server: str
    before: List[MetricSnapshot] = field(default_factory=list)
    after: List[MetricSnapshot] = field(default_factory=list)
    delta: List[Dict[str, Any]] = field(default_factory=list)
    impact_level: str = "unknown"  # low / medium / high / unknown
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Prometheus 查询
# ---------------------------------------------------------------------------

def _prom_query_range(prom_url: str, query: str,
                      start: float, end: float, step: int = 30) -> List[float]:
    """调用 Prometheus range_query,返回数值列表."""
    if not prom_url:
        return []
    params = (f"?query={urllib.parse.quote(query, safe='')}"
              f"&start={start}&end={end}&step={step}")
    url = prom_url.rstrip("/") + "/api/v1/query_range" + params
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("status") != "success":
            logger.warning("Prometheus 查询失败: %s", data.get("error"))
            return []
        result = data.get("data", {}).get("result", [])
        if not result:
            return []
        return [float(v[1]) for v in result[0].get("values", [])]
    except Exception as e:
        logger.debug("Prometheus 调用异常: %s", e)
        return []


def _snapshot(metric: MetricQuery, prom_url: str,
              start: float, end: float) -> MetricSnapshot:
    values = _prom_query_range(prom_url, metric.query, start, end)
    snap = MetricSnapshot(
        metric=metric.name,
        service=metric.service,
        timestamp=end,
    )
    if values:
        snap.values = values
        snap.avg = sum(values) / len(values)
        snap.max = max(values)
        snap.min = min(values)
    return snap


# ---------------------------------------------------------------------------
# 影响分析入口
# ---------------------------------------------------------------------------

def capture_before(service: str, prom_url: str,
                   window_minutes: int = 30) -> List[MetricSnapshot]:
    """采集变更前的指标快照."""
    end = time.time()
    start = end - window_minutes * 60
    out: List[MetricSnapshot] = []
    for m in DEFAULT_METRICS.get(service, []):
        snap = _snapshot(m, prom_url, start, end)
        out.append(snap)
        logger.debug("[%s] before %s: avg=%.3f", service, m.name, snap.avg)
    return out


def capture_after(service: str, prom_url: str,
                  window_minutes: int = 10) -> List[MetricSnapshot]:
    """采集变更后的指标快照."""
    end = time.time()
    start = end - window_minutes * 60
    out: List[MetricSnapshot] = []
    for m in DEFAULT_METRICS.get(service, []):
        snap = _snapshot(m, prom_url, start, end)
        out.append(snap)
        logger.debug("[%s] after %s: avg=%.3f", service, m.name, snap.avg)
    return out


def analyze_impact(service: str, server: str,
                   before: List[MetricSnapshot],
                   after: List[MetricSnapshot]) -> ImpactReport:
    """对比 before/after 快照,生成影响报告."""
    report = ImpactReport(service=service, server=server,
                          before=before, after=after)
    max_change_pct = 0.0
    deltas: List[Dict[str, Any]] = []

    before_map = {s.metric: s for s in before}
    after_map = {s.metric: s for s in after}

    for name, b_snap in before_map.items():
        a_snap = after_map.get(name)
        if not a_snap:
            continue
        if b_snap.avg == 0 and a_snap.avg == 0:
            change_pct = 0.0
        elif b_snap.avg == 0:
            change_pct = 100.0 if a_snap.avg > 0 else -100.0
        else:
            change_pct = (a_snap.avg - b_snap.avg) / b_snap.avg * 100.0
        max_change_pct = max(max_change_pct, abs(change_pct))
        deltas.append({
            "metric": name,
            "before_avg": round(b_snap.avg, 4),
            "after_avg": round(a_snap.avg, 4),
            "change_pct": round(change_pct, 2),
            "before_max": round(b_snap.max, 4),
            "after_max": round(a_snap.max, 4),
        })
    report.delta = deltas

    if max_change_pct > 50:
        report.impact_level = "high"
        report.recommendation = "指标波动较大,建议回滚并进一步分析"
    elif max_change_pct > 20:
        report.impact_level = "medium"
        report.recommendation = "指标有一定波动,持续观察"
    else:
        report.impact_level = "low"
        report.recommendation = "影响可控,配置变更稳定"
    logger.info("[%s/%s] 影响等级: %s (max_change=%.1f%%)",
                server, service, report.impact_level, max_change_pct)
    return report
