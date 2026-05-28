"""槽位分配分析与重平衡建议。

- 统计每个 master 的槽位数量
- 计算分布的 stddev、不均衡度（cv = stddev/mean）
- 判断是否需要重平衡
- 生成可直接用于 redis-cli --cluster rebalance 的参数建议
  （或给出手动迁移槽位的建议清单）
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .collector import ClusterTopology, NodeInfo, TOTAL_SLOTS


@dataclass
class SlotReport:
    slot_counts: Dict[str, int] = field(default_factory=dict)   # node_id -> count
    perf_weights: Dict[str, float] = field(default_factory=dict)  # node_id -> 权重 (0~1)
    weighted_targets: Dict[str, int] = field(default_factory=dict)  # node_id -> 按权重应分配的目标槽位数
    unassigned_slots: int = 0
    balanced_perfect: bool = False
    mean: float = 0.0
    stddev: float = 0.0
    cv: float = 0.0
    min_master: str = ""
    max_master: str = ""
    min_count: int = 0
    max_count: int = 0
    imbalance: bool = False
    use_perf_weight: bool = False
    recommendation: str = ""
    move_plan: List[Tuple[str, str, int]] = field(default_factory=list)   # (from_id, to_id, count)


def analyze_slots(
    topo: ClusterTopology,
    threshold_cv: float = 0.1,
    use_perf_weight: bool = True,
) -> SlotReport:
    report = SlotReport()
    report.use_perf_weight = use_perf_weight
    masters = topo.masters
    if not masters:
        report.recommendation = "未发现 master 节点，集群不可用"
        return report

    slot_counts: Dict[str, int] = {}
    assigned = 0
    for m in masters:
        c = topo.slot_count(m)
        slot_counts[m.node_id] = c
        assigned += c

    report.slot_counts = slot_counts
    report.unassigned_slots = max(TOTAL_SLOTS - assigned, 0)

    # 性能权重：归一化所有 master 的 perf_score
    perf_weights: Dict[str, float] = {}
    if use_perf_weight:
        scores = {m.node_id: max(m.perf_score, 1.0) for m in masters if m.reachable}
        total_score = sum(scores.values()) if scores else 0
        if total_score > 0:
            for m in masters:
                perf_weights[m.node_id] = scores.get(m.node_id, 0.0) / total_score
    # 如果不使用权重或评分全为 0，则均分
    if not perf_weights:
        n = len(masters)
        for m in masters:
            perf_weights[m.node_id] = 1.0 / n if n > 0 else 0.0
    report.perf_weights = perf_weights

    # 按权重计算目标槽位数
    total_slots = TOTAL_SLOTS
    targets: Dict[str, int] = {}
    remaining = total_slots
    sorted_nodes = sorted(perf_weights.items(), key=lambda x: x[1], reverse=True)
    for i, (nid, w) in enumerate(sorted_nodes):
        if i == len(sorted_nodes) - 1:
            targets[nid] = remaining
        else:
            t = int(round(total_slots * w))
            targets[nid] = min(t, remaining)
            remaining -= t
    report.weighted_targets = targets

    # 检查是否均衡（按权重目标）
    diffs = [abs(slot_counts.get(nid, 0) - targets[nid]) for nid in targets]
    report.balanced_perfect = report.unassigned_slots == 0 and all(d == 0 for d in diffs)

    counts = list(slot_counts.values())
    report.mean = statistics.mean(counts) if counts else 0
    report.stddev = statistics.pstdev(counts) if len(counts) > 1 else 0.0
    report.cv = report.stddev / report.mean if report.mean else 0.0

    # min/max
    min_id = min(slot_counts, key=lambda k: slot_counts[k])
    max_id = max(slot_counts, key=lambda k: slot_counts[k])
    report.min_master = min_id
    report.max_master = max_id
    report.min_count = slot_counts[min_id]
    report.max_count = slot_counts[max_id]

    report.imbalance = (not report.balanced_perfect) and (report.cv > threshold_cv or report.unassigned_slots > 0)

    report.move_plan = _build_move_plan(topo, slot_counts, targets)
    report.recommendation = _render_recommendation(topo, report)
    return report


def _build_move_plan(
    topo: ClusterTopology,
    slot_counts: Dict[str, int],
    targets: Dict[str, int],
) -> List[Tuple[str, str, int]]:
    """生成一个近似的槽位迁移计划（支持按权重目标分配）。
    """
    if not slot_counts or not targets:
        return []
    plan: List[Tuple[str, str, int]] = []
    remaining = dict(slot_counts)

    # 计算过剩与短缺
    excess: List[Tuple[str, int]] = []
    deficit: List[Tuple[str, int]] = []
    for nid, cnt in remaining.items():
        diff = cnt - targets.get(nid, cnt)
        if diff > 0:
            excess.append((nid, diff))
        elif diff < 0:
            deficit.append((nid, -diff))

    # 贪心配对
    excess.sort(key=lambda x: -x[1])
    deficit.sort(key=lambda x: -x[1])
    i = j = 0
    while i < len(excess) and j < len(deficit):
        nid_e, amt_e = excess[i]
        nid_d, amt_d = deficit[j]
        move = min(amt_e, amt_d)
        if move > 0:
            plan.append((nid_e, nid_d, move))
            amt_e -= move
            amt_d -= move
            excess[i] = (nid_e, amt_e)
            deficit[j] = (nid_d, amt_d)
        if amt_e <= 0:
            i += 1
        if amt_d <= 0:
            j += 1
    return plan


def _render_recommendation(topo: ClusterTopology, report: SlotReport) -> str:
    lines: List[str] = []
    if report.balanced_perfect:
        lines.append("槽位分配均衡，无需操作。")
        return "\n".join(lines)

    if report.use_perf_weight and report.perf_weights:
        lines.append("已按节点性能权重分配目标槽位：")
        for nid in sorted(report.perf_weights, key=lambda k: -report.perf_weights[k]):
            w = report.perf_weights[nid]
            target = report.weighted_targets.get(nid, 0)
            current = report.slot_counts.get(nid, 0)
            n = topo.nodes.get(nid)
            label = f"{n.host}:{n.port}" if n else nid[:8]
            lines.append(
                f"  {label}: 权重={w*100:.1f}% 目标={target} 实际={current} "
                f"{'(+%d)' % (target - current) if target > current else '(%d)' % (target - current)}"
            )

    lines.append(
        f"不均衡度 CV={report.cv:.3f}，阈值={_default_threshold()}; "
        f"最多={report.max_count}@{report.max_master[:8]}…, "
        f"最少={report.min_count}@{report.min_master[:8]}…"
    )
    if report.unassigned_slots:
        lines.append(f"存在 {report.unassigned_slots} 个未分配槽位，应尽快分配。")

    if report.move_plan:
        lines.append("建议迁移计划（可用于 --cluster reshard）:")
        for from_id, to_id, count in report.move_plan:
            lines.append(
                f"  从 {_node_label(topo, from_id)} -> {_node_label(topo, to_id)} 迁移 {count} 个槽位"
            )
    return "\n".join(lines)


def _node_label(topo: ClusterTopology, node_id: str) -> str:
    n = topo.nodes.get(node_id)
    if not n:
        return node_id
    return f"{n.host}:{n.port}({node_id[:8]})"


def _default_threshold() -> str:
    return "0.1"
