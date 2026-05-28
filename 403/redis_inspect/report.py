"""巡检报告生成。

支持 text / json / markdown 三种输出格式。
"""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .collector import (
    ClusterTopology,
    HotKeyReport,
    SlowlogPattern,
    SlowlogEntry,
    MemoryTypeReport,
)
from .health_analyzer import HealthReport
from .performance_analyzer import PerformanceReport
from .slot_analyzer import SlotReport


def _as_dict(obj: Any) -> Any:
    if is_dataclass(obj):
        return {k: _as_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _as_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_as_dict(v) for v in obj]
    return obj


def _format_size(n: int) -> str:
    if n < 1024:
        return f"{n}B"
    elif n < 1024 * 1024:
        return f"{n / 1024:.1f}KB"
    elif n < 1024 * 1024 * 1024:
        return f"{n / 1024 / 1024:.1f}MB"
    else:
        return f"{n / 1024 / 1024 / 1024:.2f}GB"


def _ascii_bar(pct: float, width: int = 20) -> str:
    filled = int(pct * width / 100)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def build_payload(
    topo: ClusterTopology,
    slot_report: SlotReport,
    health_report: HealthReport,
    perf_report: PerformanceReport,
    hotkey_report: HotKeyReport | None = None,
    slowlog_patterns: List[SlowlogPattern] | None = None,
    slowlog_entries: List[SlowlogEntry] | None = None,
    memory_type_report: MemoryTypeReport | None = None,
) -> Dict[str, Any]:
    return {
        "timestamp": datetime.utcfromtimestamp(topo.ts).isoformat() + "Z",
        "seed": topo.seed,
        "cluster": {
            "state": topo.cluster_state,
            "known_nodes": topo.cluster_known_nodes,
            "size": topo.cluster_size,
            "slots_assigned": topo.cluster_slots_assigned,
            "slots_ok": topo.cluster_slots_ok,
            "slots_fail": topo.cluster_slots_fail,
        },
        "slots": _as_dict(slot_report),
        "health": _as_dict(health_report),
        "performance": _as_dict(perf_report),
        "hotkeys": _as_dict(hotkey_report) if hotkey_report else None,
        "slowlog_patterns": _as_dict(slowlog_patterns) if slowlog_patterns else None,
        "slowlog_entries": _as_dict(slowlog_entries) if slowlog_entries else None,
        "memory_types": _as_dict(memory_type_report) if memory_type_report else None,
    }


def render_text(payload: Dict[str, Any]) -> str:
    lines: list[str] = []
    sep = "=" * 72
    lines.append(sep)
    lines.append("Redis 集群巡检报告")
    lines.append(f"时间: {payload['timestamp']}    种子节点: {payload['seed']}")
    lines.append(sep)
    c = payload["cluster"]
    lines.append(
        f"集群状态: {c['state']}    已知节点: {c['known_nodes']}    "
        f"主节点: {c['size']}    已分配槽位: {c['slots_assigned']}/16384    "
        f"异常槽位: {c['slots_fail']}"
    )
    lines.append("")

    s = payload["slots"]
    lines.append("-- 槽位分配 --")
    lines.append(f"不均衡度 CV={s['cv']:.3f}; 均值={s['mean']:.1f}; 标准差={s['stddev']:.1f}")
    lines.append(f"最多={s['max_count']}@{s['max_master'][:8]}…; 最少={s['min_count']}@{s['min_master'][:8]}…")
    if s.get("unassigned_slots"):
        lines.append(f"未分配槽位: {s['unassigned_slots']}")
    if s.get("use_perf_weight") and s.get("perf_weights"):
        lines.append("按性能权重分配目标槽位：")
        for nid in sorted(s["perf_weights"], key=lambda k: -s["perf_weights"][k]):
            w = s["perf_weights"][nid]
            target = s.get("weighted_targets", {}).get(nid, 0)
            current = s.get("slot_counts", {}).get(nid, 0)
            diff = target - current
            lines.append(
                f"  {nid[:8]}… : 权重={w*100:.1f}% 目标={target} 实际={current} "
                f"{'+' + str(diff) if diff >= 0 else str(diff)}"
            )
    lines.append("槽位 -> 节点:")
    for nid, cnt in (s.get("slot_counts") or {}).items():
        lines.append(f"  {nid[:8]}… : {cnt}")
    if s.get("move_plan"):
        lines.append("重平衡建议:")
        for row in s["move_plan"]:
            lines.append(f"  {row[0][:8]}… -> {row[1][:8]}… 迁移 {row[2]} 个槽位")
    lines.append("")

    h = payload["health"]
    lines.append(f"-- 节点健康 (总体: {h['overall']}) --")
    for nid, nh in h["nodes"].items():
        version = nh.get("redis_version", "")
        version_suffix = f" v{version}" if version else ""
        frag_th = nh.get("mem_fragmentation_threshold", 1.5)
        perf = nh.get("perf_score", 0.0)
        lines.append(
            f"[{nh['role']}] {nh['label']} ({nid[:8]}…){version_suffix} reachable={nh['reachable']} "
            f"mem_frag={nh['mem_fragmentation_ratio']:.2f}(阈值={frag_th:.2f}) "
            f"mem_usage={nh['mem_usage_percent']:.1f}% cpu={nh['cpu_usage_percent']:.1f}% "
            f"perf_score={perf:.1f} "
            f"repl_lag_max={nh.get('replication_lag_max_sec', nh['replication_lag_sec']):.3f}s "
            f"clients={nh['connected_clients']}"
        )
        if nh.get("alerts"):
            for a in nh["alerts"]:
                lines.append(f"    ! {a}")
    lines.append("")

    # 热点 Key
    hk = payload.get("hotkeys")
    if hk and hk.get("samples"):
        lines.append(f"-- 热点 Key (采样 {hk['total_scanned']} 个, 策略={hk.get('maxmemory_policy', 'unknown')}) --")
        if hk.get("by_freq"):
            lines.append("按访问频率 Top-10:")
            for ks in hk["by_freq"][:10]:
                lines.append(
                    f"  freq={ks['freq']:>5}  size={_format_size(ks['size_bytes']):>10}  "
                    f"type={ks['type']:<10}  key={ks['key'][:60]}"
                )
        if hk.get("by_size"):
            lines.append("按内存大小 Top-10:")
            for ks in hk["by_size"][:10]:
                lines.append(
                    f"  freq={ks['freq']:>5}  size={_format_size(ks['size_bytes']):>10}  "
                    f"type={ks['type']:<10}  key={ks['key'][:60]}"
                )
        lines.append("")

    # 内存类型分析
    mt = payload.get("memory_types")
    if mt and mt.get("by_type"):
        lines.append(f"-- 内存类型占比 (采样 {mt['total_sampled_keys']} 个 key, 共 {_format_size(mt['total_sampled_size'])}) --")
        for t, info in sorted(mt["by_type"].items(), key=lambda x: -x[1]["total_size"]):
            pct = info["total_size"] / max(mt["total_sampled_size"], 1) * 100
            bar = _ascii_bar(pct, 25)
            lines.append(
                f"  {t:<12} {bar} {pct:>5.1f}%  "
                f"count={info['count']:>6}  total={_format_size(info['total_size']):>10}  "
                f"avg={_format_size(int(info['avg_size']))}"
            )
        if mt.get("top_large_keys"):
            lines.append("Top-10 大 Key:")
            for ks in mt["top_large_keys"][:10]:
                lines.append(
                    f"  size={_format_size(ks['size_bytes']):>10}  type={ks['type']:<10}  "
                    f"encoding={ks.get('encoding', ''):<12}  key={ks['key'][:50]}"
                )
        lines.append("")

    # 慢查询模式
    sp = payload.get("slowlog_patterns")
    if sp:
        lines.append(f"-- 慢查询模式聚合 (共 {len(sp)} 种模式) --")
        for p in sp:
            lines.append(
                f"  [{p['pattern']}] count={p['count']}  "
                f"total={p['total_duration_us']/1000:.1f}ms  "
                f"max={p['max_duration_us']/1000:.1f}ms  "
                f"avg={p['avg_duration_us']/1000:.1f}ms"
            )
            if p.get("sample_commands"):
                for sc in p["sample_commands"][:2]:
                    lines.append(f"    示例: {sc[:120]}")
        lines.append("")

    p = payload["performance"]
    lines.append("-- 性能热点 --")
    lines.append(p.get("bottleneck_summary", ""))
    lines.append("Top 命令:")
    for cmd in p.get("top_commands", [])[:10]:
        lines.append(
            f"  {cmd['command']:<16} calls={cmd['calls']:<8} "
            f"usec/call={cmd['usec_per_call']:<8.1f} score={cmd['bottleneck_score']:.1f}"
        )
    if p.get("recommendations"):
        lines.append("优化建议:")
        for r in p["recommendations"]:
            lines.append(f"  * {r}")
    lines.append(sep)
    return "\n".join(lines)


def render_markdown(payload: Dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Redis 集群巡检报告 ({payload['timestamp']})")
    c = payload["cluster"]
    lines.append("")
    lines.append("## 集群概况")
    lines.append("")
    lines.append("| 项 | 值 |")
    lines.append("|---|---|")
    lines.append(f"| 种子节点 | {payload['seed']} |")
    lines.append(f"| 集群状态 | {c['state']} |")
    lines.append(f"| 已知节点 | {c['known_nodes']} |")
    lines.append(f"| 主节点数 | {c['size']} |")
    lines.append(f"| 已分配槽位 | {c['slots_assigned']}/16384 |")
    lines.append(f"| 异常槽位 | {c['slots_fail']} |")

    s = payload["slots"]
    lines.append("")
    lines.append("## 槽位分配")
    lines.append("")
    lines.append(f"- 不均衡度 CV = **{s['cv']:.3f}**")
    lines.append(f"- 均值 = {s['mean']:.1f}, 标准差 = {s['stddev']:.1f}")
    lines.append(f"- 最多={s['max_count']}@{s['max_master'][:8]}…; 最少={s['min_count']}@{s['min_master'][:8]}…")
    if s.get("unassigned_slots"):
        lines.append(f"- 未分配槽位: **{s['unassigned_slots']}**")
    if s.get("use_perf_weight") and s.get("perf_weights"):
        lines.append("")
        lines.append("### 按性能权重分配目标槽位")
        lines.append("")
        lines.append("| 节点 | 权重(%) | 目标槽位 | 实际槽位 | 差值 |")
        lines.append("|---|---:|---:|---:|---:|")
        for nid in sorted(s["perf_weights"], key=lambda k: -s["perf_weights"][k]):
            w = s["perf_weights"][nid]
            target = s.get("weighted_targets", {}).get(nid, 0)
            current = s.get("slot_counts", {}).get(nid, 0)
            diff = target - current
            lines.append(f"| {nid[:8]}… | {w*100:.1f} | {target} | {current} | {'+' + str(diff) if diff >= 0 else str(diff)} |")
    if s.get("move_plan"):
        lines.append("")
        lines.append("### 重平衡建议")
        for row in s["move_plan"]:
            lines.append(f"- 从 `{row[0][:8]}…` -> `{row[1][:8]}…` 迁移 {row[2]} 个槽位")

    h = payload["health"]
    lines.append("")
    lines.append(f"## 节点健康 (总体: {h['overall']})")
    lines.append("")
    lines.append("| 节点 | 版本 | 角色 | 可达 | 槽位 | mem_frag(阈值) | mem% | cpu% | perf | repl_max(s) | 客户端 | 告警 |")
    lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for nid, nh in h["nodes"].items():
        alerts = "<br>".join(nh.get("alerts") or []) or "-"
        version = nh.get("redis_version", "")
        frag_th = nh.get("mem_fragmentation_threshold", 1.5)
        frag_str = f"{nh['mem_fragmentation_ratio']:.2f}({frag_th:.2f})"
        repl_max = nh.get("replication_lag_max_sec", nh.get("replication_lag_sec", 0))
        perf = nh.get("perf_score", 0.0)
        lines.append(
            f"| {nh['label']} ({nid[:8]}…) | {version} | {nh['role']} | {'Y' if nh['reachable'] else 'N'} | "
            f"{nh['slot_count']} | {frag_str} | "
            f"{nh['mem_usage_percent']:.1f} | {nh['cpu_usage_percent']:.1f} | {perf:.1f} | "
            f"{repl_max:.3f} | {nh['connected_clients']} | {alerts} |"
        )

    p = payload["performance"]
    lines.append("")
    lines.append("## 性能热点")
    lines.append("")
    lines.append(f"{p.get('bottleneck_summary', '')}")
    lines.append("")
    lines.append("| 命令 | 调用次数 | usec/call | 总耗时(us) | 瓶颈分 |")
    lines.append("|---|---:|---:|---:|---:|")
    for cmd in p.get("top_commands", [])[:10]:
        lines.append(
            f"| {cmd['command']} | {cmd['calls']} | {cmd['usec_per_call']:.1f} | "
            f"{cmd['total_usec']:.0f} | {cmd['bottleneck_score']:.1f} |"
        )
    if p.get("recommendations"):
        lines.append("")
        lines.append("## 优化建议")
        for r in p["recommendations"]:
            lines.append(f"- {r}")

    # 热点 Key
    hk = payload.get("hotkeys")
    if hk and hk.get("samples"):
        lines.append("")
        lines.append(f"## 热点 Key (采样 {hk['total_scanned']} 个)")
        lines.append("")
        lines.append(f"- 淘汰策略: **{hk.get('maxmemory_policy', 'unknown')}**")
        if hk.get("by_freq"):
            lines.append("")
            lines.append("### 按访问频率 Top-10")
            lines.append("")
            lines.append("| Key | 类型 | 大小 | 频率 |")
            lines.append("|---|---|---:|---:|")
            for ks in hk["by_freq"][:10]:
                lines.append(
                    f"| `{ks['key'][:60]}` | {ks['type']} | "
                    f"{_format_size(ks['size_bytes'])} | {ks['freq']} |"
                )
        if hk.get("by_size"):
            lines.append("")
            lines.append("### 按内存大小 Top-10")
            lines.append("")
            lines.append("| Key | 类型 | 大小 | 编码 |")
            lines.append("|---|---|---:|---|")
            for ks in hk["by_size"][:10]:
                lines.append(
                    f"| `{ks['key'][:60]}` | {ks['type']} | "
                    f"{_format_size(ks['size_bytes'])} | {ks.get('encoding', '')} |"
                )

    # 内存类型分析
    mt = payload.get("memory_types")
    if mt and mt.get("by_type"):
        lines.append("")
        lines.append(
            f"## 内存类型占比 (采样 {mt['total_sampled_keys']} 个 key, "
            f"共 {_format_size(mt['total_sampled_size'])})"
        )
        lines.append("")
        lines.append("| 类型 | Key 数量 | 总大小 | 平均大小 | 占比 |")
        lines.append("|---|---:|---:|---:|---:|")
        for t, info in sorted(mt["by_type"].items(), key=lambda x: -x[1]["total_size"]):
            pct = info["total_size"] / max(mt["total_sampled_size"], 1) * 100
            lines.append(
                f"| {t} | {info['count']} | {_format_size(info['total_size'])} | "
                f"{_format_size(int(info['avg_size']))} | {pct:.1f}% |"
            )
        if mt.get("top_large_keys"):
            lines.append("")
            lines.append("### Top-10 大 Key")
            lines.append("")
            lines.append("| Key | 类型 | 大小 | 编码 |")
            lines.append("|---|---|---:|---|")
            for ks in mt["top_large_keys"][:10]:
                lines.append(
                    f"| `{ks['key'][:50]}` | {ks['type']} | "
                    f"{_format_size(ks['size_bytes'])} | {ks.get('encoding', '')} |"
                )

    # 慢查询模式
    sp = payload.get("slowlog_patterns")
    if sp:
        lines.append("")
        lines.append(f"## 慢查询模式聚合 (共 {len(sp)} 种模式)")
        lines.append("")
        lines.append("| 模式 | 次数 | 总耗时(ms) | 最大(ms) | 平均(ms) | 示例 |")
        lines.append("|---|---:|---:|---:|---:|---|")
        for p in sp:
            sample = p.get("sample_commands", [""])[0][:80] if p.get("sample_commands") else ""
            lines.append(
                f"| `{p['pattern']}` | {p['count']} | "
                f"{p['total_duration_us']/1000:.1f} | {p['max_duration_us']/1000:.1f} | "
                f"{p['avg_duration_us']/1000:.1f} | `{sample}` |"
            )

    return "\n".join(lines)


def write_report(
    output_dir: str,
    payload: Dict[str, Any],
    fmt: str = "text",
) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ts = payload["timestamp"].replace(":", "").replace("-", "").replace("Z", "")
    if fmt == "json":
        content = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        path = out / f"report_{ts}.json"
    elif fmt == "markdown":
        content = render_markdown(payload)
        path = out / f"report_{ts}.md"
    else:
        content = render_text(payload)
        path = out / f"report_{ts}.txt"
    path.write_text(content, encoding="utf-8")
    return path
