"""节点健康与性能瓶颈分析。

- 节点状态检测：node flags、link_state、reachable、failover 状态
- 复制延迟：基于 master_repl_offset 与 slave_repl_offset 的差值
- 内存碎片率：mem_fragmentation_ratio
- 性能瓶颈：
    * 慢查询热点（SLOWLOG + COMMANDSTATS 累加）
    * CPU 使用率、内存使用率阈值
    * 客户端连接数 max_clients
    * 网络输入/输出速率异常
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from .collector import ClusterTopology, NodeInfo


@dataclass
class NodeHealth:
    node_id: str
    label: str
    role: str
    reachable: bool
    flags: List[str]
    link_state: str
    master_id: str = ""
    slot_count: int = 0
    redis_version: str = ""
    # 复制
    master_offset: int = 0
    slave_offset: int = 0
    replication_lag_bytes: int = 0
    replication_lag_sec: float = 0.0
    replication_lag_max_sec: float = 0.0   # 连续采样最大值
    replication_lag_avg_sec: float = 0.0
    replication_lag_p95_sec: float = 0.0
    # 内存
    used_memory_human: str = ""
    used_memory: int = 0
    maxmemory: int = 0
    mem_fragmentation_ratio: float = 1.0
    mem_usage_percent: float = 0.0
    mem_fragmentation_threshold: float = 1.5  # 实际使用的阈值（按版本）
    # CPU
    used_cpu_sys: float = 0.0
    used_cpu_user: float = 0.0
    cpu_usage_percent: float = 0.0
    # 性能评分
    perf_score: float = 0.0
    # 网络
    total_net_input_bytes: int = 0
    total_net_output_bytes: int = 0
    # 客户端
    connected_clients: int = 0
    maxclients: int = 0
    blocked_clients: int = 0
    # 持久化
    rdb_last_bgsave_status: str = ""
    aof_enabled: bool = False
    aof_last_bgrewrite_status: str = ""
    # 告警
    alerts: List[str] = field(default_factory=list)


@dataclass
class HealthReport:
    nodes: Dict[str, NodeHealth] = field(default_factory=dict)
    overall: str = "OK"
    alerts: List[str] = field(default_factory=list)


def analyze_health(
    topo: ClusterTopology, threshold: Dict[str, Any]
) -> HealthReport:
    report = HealthReport()

    # 汇总 master 的复制偏移
    master_offset: Dict[str, int] = {}
    for n in topo.nodes.values():
        if n.role == "master" and n.reachable:
            repl = n.info.get("Replication", {}) if isinstance(n.info, dict) else {}
            master_offset[n.node_id] = int(repl.get("master_repl_offset", 0) or 0)

    for n in topo.nodes.values():
        info = n.info if isinstance(n.info, dict) else {}
        mem = info.get("Memory", {}) or {}
        cpu = info.get("CPU", {}) or {}
        net = info.get("Stats", {}) or {}
        clients = info.get("Clients", {}) or {}
        pers = info.get("Persistence", {}) or {}
        repl = info.get("Replication", {}) or {}
        server = info.get("Server", {}) or {}

        nh = NodeHealth(
            node_id=n.node_id,
            label=f"{n.host}:{n.port}",
            role=n.role,
            reachable=n.reachable,
            flags=n.flags,
            link_state=n.link_state,
            master_id=n.master_id or "",
            slot_count=topo.slot_count(n) if n.role == "master" else 0,
            redis_version=str(server.get("redis_version", "")),
            perf_score=n.perf_score,
        )
        nh.used_memory_human = str(mem.get("used_memory_human", ""))
        nh.used_memory = int(mem.get("used_memory", 0) or 0)
        nh.maxmemory = int(mem.get("maxmemory", 0) or 0)
        nh.mem_fragmentation_ratio = float(mem.get("mem_fragmentation_ratio", 1.0) or 1.0)
        if nh.maxmemory > 0:
            nh.mem_usage_percent = nh.used_memory * 100.0 / nh.maxmemory
        nh.used_cpu_sys = float(cpu.get("used_cpu_sys", 0) or 0)
        nh.used_cpu_user = float(cpu.get("used_cpu_user", 0) or 0)
        # 粗略 CPU 占用：基于 uptime 平均分配，用户感知主要是 busy 百分比，这里做近似
        uptime = float(server.get("uptime_in_seconds", 1) or 1)
        nh.cpu_usage_percent = (nh.used_cpu_sys + nh.used_cpu_user) * 100.0 / max(uptime, 1)
        nh.total_net_input_bytes = int(net.get("total_net_input_bytes", 0) or 0)
        nh.total_net_output_bytes = int(net.get("total_net_output_bytes", 0) or 0)
        nh.connected_clients = int(clients.get("connected_clients", 0) or 0)
        nh.maxclients = int(info.get("Maxclients", {}).get("maxclients", 0) or 0)
        nh.blocked_clients = int(clients.get("blocked_clients", 0) or 0)
        nh.rdb_last_bgsave_status = str(pers.get("rdb_last_bgsave_status", ""))
        nh.aof_enabled = bool(pers.get("aof_enabled", False))
        nh.aof_last_bgrewrite_status = str(pers.get("aof_last_bgrewrite_status", ""))

        # 复制延迟：优先使用连续采样的最大值
        if n.role == "slave" and n.master_id:
            # 使用连续采样结果
            if n.replication_lag_max_sec > 0:
                nh.replication_lag_max_sec = n.replication_lag_max_sec
                nh.replication_lag_avg_sec = n.replication_lag_avg_sec
                nh.replication_lag_p95_sec = n.replication_lag_p95_sec
                nh.replication_lag_sec = nh.replication_lag_max_sec  # 取最严的
            else:
                # 回退到单次采样
                slave_off = int(repl.get("slave_repl_offset", 0) or 0)
                master_off = master_offset.get(n.master_id, 0)
                nh.slave_offset = slave_off
                nh.master_offset = master_off
                nh.replication_lag_bytes = max(master_off - slave_off, 0)
                master_repl = topo.nodes.get(n.master_id)
                if master_repl and master_repl.reachable:
                    m_stats = master_repl.info.get("Stats", {}) if isinstance(master_repl.info, dict) else {}
                    m_server = master_repl.info.get("Server", {}) if isinstance(master_repl.info, dict) else {}
                    bytes_per_sec = max(float(m_stats.get("total_net_output_bytes", 0) or 0) / max(float(m_server.get("uptime_in_seconds", 1) or 1), 1.0), 1.0)
                    nh.replication_lag_sec = nh.replication_lag_bytes / bytes_per_sec
                nh.replication_lag_max_sec = nh.replication_lag_sec
                nh.replication_lag_avg_sec = nh.replication_lag_sec
                nh.replication_lag_p95_sec = nh.replication_lag_sec

        # 按版本确定碎片阈值
        nh.mem_fragmentation_threshold = _get_fragmentation_threshold(nh.redis_version, threshold)

        _fill_alerts(nh, n, threshold, master_offset)
        report.nodes[n.node_id] = nh
        report.alerts.extend(f"[{nh.label}] {a}" for a in nh.alerts)

    if any("fail" in (n.flags or []) or not n.reachable for n in topo.nodes.values()):
        report.overall = "CRITICAL"
    elif report.alerts:
        report.overall = "WARNING"
    else:
        report.overall = "OK"
    return report


def _parse_version(v: str) -> Tuple[int, int, int]:
    """解析 Redis 版本号为 (major, minor, patch)。"""
    try:
        parts = str(v).strip().split(".")
        major = int(parts[0]) if parts else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2].split("-")[0]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except Exception:
        return (0, 0, 0)


def _get_fragmentation_threshold(redis_version: str, threshold: Dict[str, Any]) -> float:
    """按 Redis 版本确定碎片阈值。

    新版 Redis（>= 7.0）使用 jemalloc 改进，碎片率容忍度更高。
    规则：
      - >= 7.4: 阈值 2.0
      - 7.0 ~ 7.2: 阈值 1.8
      - 6.x: 阈值 1.5
      - < 6.0: 阈值 1.3
    配置文件中可覆盖这些默认值。
    """
    version_cfg = threshold.get("mem_fragmentation_by_version", {})
    v = _parse_version(redis_version)
    if not redis_version:
        return float(threshold.get("mem_fragmentation_ratio", 1.5))
    if v >= (7, 4, 0):
        return float(version_cfg.get("ge_7_4", 2.0))
    elif v >= (7, 0, 0):
        return float(version_cfg.get("ge_7_0", 1.8))
    elif v >= (6, 0, 0):
        return float(version_cfg.get("ge_6_0", 1.5))
    else:
        return float(version_cfg.get("lt_6_0", 1.3))


def _fill_alerts(
    nh: NodeHealth,
    node: NodeInfo,
    threshold: Dict[str, Any],
    master_offset: Dict[str, int],
) -> None:
    if not nh.reachable:
        nh.alerts.append("节点不可达")
        return
    if "fail" in nh.flags or "fail?" in nh.flags:
        nh.alerts.append("节点处于 FAIL/PFAIL 状态")
    if nh.link_state != "connected":
        nh.alerts.append(f"集群总线链路异常: {nh.link_state}")
    if nh.role == "slave" and nh.master_id not in master_offset:
        nh.alerts.append("对应的 master 不可达")

    # 复制延迟（使用连续采样的最大值）
    lag_th = float(threshold.get("replication_lag_sec", 5.0))
    if nh.role == "slave" and nh.replication_lag_max_sec > lag_th:
        nh.alerts.append(
            f"复制延迟 max={nh.replication_lag_max_sec:.2f}s avg={nh.replication_lag_avg_sec:.2f}s p95={nh.replication_lag_p95_sec:.2f}s 超过阈值 {lag_th}s"
        )

    # 内存碎片率（按版本差异化阈值）
    frag_th = nh.mem_fragmentation_threshold
    if nh.mem_fragmentation_ratio > frag_th:
        version_note = f"(Redis {nh.redis_version})" if nh.redis_version else ""
        nh.alerts.append(
            f"内存碎片率 {nh.mem_fragmentation_ratio:.2f} 超过阈值 {frag_th} {version_note}"
        )

    mem_th = float(threshold.get("mem_usage_percent", 85.0))
    if nh.mem_usage_percent > mem_th:
        nh.alerts.append(
            f"内存使用率 {nh.mem_usage_percent:.1f}% 超过阈值 {mem_th}%"
        )
    cpu_th = float(threshold.get("cpu_usage_percent", 80.0))
    if nh.cpu_usage_percent > cpu_th:
        nh.alerts.append(
            f"CPU 占用 {nh.cpu_usage_percent:.1f}% 超过阈值 {cpu_th}%"
        )
    if nh.rdb_last_bgsave_status and nh.rdb_last_bgsave_status != "ok":
        nh.alerts.append(f"RDB bgsave 状态异常: {nh.rdb_last_bgsave_status}")
    if nh.aof_enabled and nh.aof_last_bgrewrite_status and nh.aof_last_bgrewrite_status != "ok":
        nh.alerts.append(f"AOF bgrewrite 状态异常: {nh.aof_last_bgrewrite_status}")
