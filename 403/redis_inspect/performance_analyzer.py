"""统计分析与性能瓶颈诊断。

基于采集到的 commandstats 和 slowlog，结合 Python 统计分析，识别：
- 热点命令（高调用/高平均耗时）
- 热点节点（CPU/内存/连接数最高）
- 集群级的吞吐与延迟指标
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from .collector import ClusterTopology, NodeInfo


@dataclass
class CommandHotspot:
    command: str
    calls: int
    usec_per_call: float
    total_usec: float
    bottleneck_score: float = 0.0


@dataclass
class PerformanceReport:
    top_commands: List[CommandHotspot] = field(default_factory=list)
    top_cpu_nodes: List[Tuple[str, float]] = field(default_factory=list)
    top_mem_nodes: List[Tuple[str, float]] = field(default_factory=list)
    top_conn_nodes: List[Tuple[str, int]] = field(default_factory=list)
    total_calls: int = 0
    total_usec: float = 0.0
    avg_usec_per_call: float = 0.0
    slow_nodes: List[str] = field(default_factory=list)  # 存在慢查询的节点
    bottleneck_summary: str = ""
    recommendations: List[str] = field(default_factory=list)


def analyze_performance(
    topo: ClusterTopology, slowlog_usec: int = 10000, top_n: int = 10
) -> PerformanceReport:
    rep = PerformanceReport()

    # 1. 聚合 commandstats
    agg: Dict[str, Dict[str, float]] = {}
    for n in topo.nodes.values():
        for cmd, stats in (n.commandstats or {}).items():
            d = agg.setdefault(cmd, {"calls": 0.0, "usec": 0.0, "usec_per_call": 0.0})
            calls = float(stats.get("calls", 0) or 0)
            usec = float(stats.get("usec", 0) or 0)
            d["calls"] += calls
            d["usec"] += usec
            # 用加权平均近似
            total_calls = d["calls"]
            d["usec_per_call"] = d["usec"] / total_calls if total_calls else 0.0

    hotspots: List[CommandHotspot] = []
    total_calls_all = 0
    total_usec_all = 0.0
    for cmd, d in agg.items():
        calls = int(d["calls"])
        usec = d["usec"]
        total_calls_all += calls
        total_usec_all += usec
        # 瓶颈评分 = log(calls+1) * usec_per_call
        score = (calls ** 0.5) * d["usec_per_call"]
        hotspots.append(
            CommandHotspot(
                command=cmd,
                calls=calls,
                usec_per_call=d["usec_per_call"],
                total_usec=usec,
                bottleneck_score=score,
            )
        )
    hotspots.sort(key=lambda h: h.bottleneck_score, reverse=True)
    rep.top_commands = hotspots[:top_n]
    rep.total_calls = total_calls_all
    rep.total_usec = total_usec_all
    rep.avg_usec_per_call = total_usec_all / total_calls_all if total_calls_all else 0.0

    # 2. 节点热点（仅统计 master 节点）
    cpu_rank: List[Tuple[str, float]] = []
    mem_rank: List[Tuple[str, float]] = []
    conn_rank: List[Tuple[str, int]] = []
    for n in topo.nodes.values():
        if not n.reachable or not isinstance(n.info, dict):
            continue
        cpu = float(n.info.get("CPU", {}).get("used_cpu_sys", 0) or 0) + float(n.info.get("CPU", {}).get("used_cpu_user", 0) or 0)
        mem = float(n.info.get("Memory", {}).get("used_memory", 0) or 0)
        conn = int(n.info.get("Clients", {}).get("connected_clients", 0) or 0)
        label = f"{n.host}:{n.port}({n.node_id[:8]})"
        cpu_rank.append((label, cpu))
        mem_rank.append((label, mem))
        conn_rank.append((label, conn))
    cpu_rank.sort(key=lambda x: x[1], reverse=True)
    mem_rank.sort(key=lambda x: x[1], reverse=True)
    conn_rank.sort(key=lambda x: x[1], reverse=True)
    rep.top_cpu_nodes = cpu_rank[:top_n]
    rep.top_mem_nodes = mem_rank[:top_n]
    rep.top_conn_nodes = conn_rank[:top_n]

    # 3. 慢查询聚合
    slow_nodes: List[str] = []
    slow_total = 0
    for n in topo.nodes.values():
        for s in (n.slowlog or []):
            if int(s.get("duration_us", 0)) >= slowlog_usec:
                slow_total += 1
        if any(int(s.get("duration_us", 0)) >= slowlog_usec for s in (n.slowlog or [])):
            slow_nodes.append(f"{n.host}:{n.port}")
    rep.slow_nodes = slow_nodes

    # 4. 生成瓶颈总结
    summary_parts: List[str] = []
    summary_parts.append(
        f"集群累计命令调用 {rep.total_calls} 次，平均 {rep.avg_usec_per_call:.1f} usec/call"
    )
    if rep.top_commands:
        top = rep.top_commands[0]
        summary_parts.append(
            f"最耗命令: {top.command} (calls={top.calls}, usec/call={top.usec_per_call:.1f})"
        )
    if slow_total:
        summary_parts.append(f"共发现 {slow_total} 条慢查询(>={slowlog_usec}us)")
    rep.bottleneck_summary = "; ".join(summary_parts)

    # 5. 建议
    recs: List[str] = []
    if rep.top_commands:
        t = rep.top_commands[0]
        if t.usec_per_call > 1000:
            recs.append(f"命令 `{t.command}` 单次耗时较高，检查是否存在大 key、复杂计算或未使用管道。")
        if t.calls > 100000:
            recs.append(f"命令 `{t.command}` 调用频次高，考虑缓存、批量或本地合并。")
    if slow_total:
        recs.append(f"存在慢查询，建议使用 SLOWLOG LEN 监控并针对性优化。")
    if len(mem_rank) >= 2 and mem_rank[0][1] > 0:
        ratio = mem_rank[0][1] / max(mem_rank[-1][1], 1)
        if ratio > 2:
            recs.append(f"内存分布不均: 最高 {mem_rank[0][0]} 是最低 {mem_rank[-1][0]} 的 {ratio:.1f} 倍，建议数据分布审查。")
    rep.recommendations = recs
    return rep
