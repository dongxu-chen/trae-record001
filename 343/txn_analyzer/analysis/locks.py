"""
Lock Conflict Analyzer - 锁冲突分析
分析锁冲突矩阵、锁等待热点、死锁事件、锁继承关系。
"""
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..parsers.base import TxnRecord, LockEvent, DeadlockEvent, LockMode


@dataclass
class LockConflictRecord:
    """锁冲突记录"""
    table_name: str
    lock_mode: str
    total_events: int = 0
    granted_count: int = 0
    wait_count: int = 0
    total_wait_ms: float = 0.0
    max_wait_ms: float = 0.0
    avg_wait_ms: float = 0.0
    txn_count: int = 0
    conflicting_txns: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "table": self.table_name,
            "lock_mode": self.lock_mode,
            "total_events": self.total_events,
            "wait_count": self.wait_count,
            "total_wait_ms": round(self.total_wait_ms, 2),
            "max_wait_ms": round(self.max_wait_ms, 2),
            "avg_wait_ms": round(self.avg_wait_ms, 2),
            "conflict_rate": round(self.wait_count / max(self.total_events, 1), 3),
        }


@dataclass
class LockConflictResult:
    """锁冲突分析结果"""
    conflicts: List[LockConflictRecord] = field(default_factory=list)
    conflict_matrix: List[Dict] = field(default_factory=list)
    deadlock_events: List[Dict] = field(default_factory=list)
    lock_timeline: List[Dict] = field(default_factory=list)


class LockConflictAnalyzer:
    """锁冲突分析器"""

    def __init__(self, lock_wait_threshold_ms: float = 100.0):
        self.lock_wait_threshold = lock_wait_threshold_ms

    def analyze(
        self,
        txns: List[TxnRecord],
        lock_events: Optional[List[LockEvent]] = None,
        deadlock_events: Optional[List[DeadlockEvent]] = None,
    ) -> LockConflictResult:
        """分析锁冲突"""
        result = LockConflictResult()

        # ---- 按表聚合锁事件 ----
        lock_data: Dict[Tuple[str, str], LockConflictRecord] = {}

        # 从锁事件聚合
        all_lock_events: List[LockEvent] = list(lock_events or [])
        for txn in txns:
            all_lock_events.extend(txn.lock_events)

        for evt in all_lock_events:
            key = (evt.object_name, evt.lock_mode.value)
            if key not in lock_data:
                lock_data[key] = LockConflictRecord(
                    table_name=evt.object_name,
                    lock_mode=evt.lock_mode.value,
                )
            rec = lock_data[key]
            rec.total_events += 1
            if evt.granted:
                rec.granted_count += 1
            else:
                rec.wait_count += 1
            if evt.wait_ms > 0:
                rec.total_wait_ms += evt.wait_ms
                rec.max_wait_ms = max(rec.max_wait_ms, evt.wait_ms)
            if evt.xid not in rec.conflicting_txns:
                rec.conflicting_txns.append(evt.xid)
                rec.txn_count += 1

        for rec in lock_data.values():
            rec.avg_wait_ms = rec.total_wait_ms / max(rec.wait_count, 1)

        # 筛选有等待的冲突
        result.conflicts = sorted(
            [r for r in lock_data.values() if r.total_wait_ms > 0],
            key=lambda r: r.total_wait_ms, reverse=True,
        )

        # ---- 冲突矩阵 (table × lock_mode) ----
        matrix_data: Dict[str, Dict[str, float]] = defaultdict(dict)
        for rec in result.conflicts:
            matrix_data[rec.table_name][rec.lock_mode] = rec.total_wait_ms

        result.conflict_matrix = [
            {"table": table, **modes}
            for table, modes in sorted(
                matrix_data.items(),
                key=lambda x: sum(x[1].values()),
                reverse=True,
            )[:20]
        ]

        # ---- 死锁事件 ----
        if deadlock_events:
            result.deadlock_events = [
                {
                    "timestamp": d.timestamp.isoformat(),
                    "txn1_xid": d.txn1_xid,
                    "txn2_xid": d.txn2_xid,
                    "txn1_query": d.txn1_query,
                    "txn2_query": d.txn2_query,
                    "txn1_lock": d.txn1_lock,
                    "txn2_lock": d.txn2_lock,
                    "victim": d.victim,
                    "schema": d.schema or "N/A",
                }
                for d in deadlock_events
            ]

        # ---- 锁时间线 ----
        timeline: List[Dict] = []
        for txn in txns:
            for evt in txn.lock_events:
                if evt.wait_ms >= self.lock_wait_threshold:
                    timeline.append({
                        "timestamp": evt.timestamp.isoformat(),
                        "xid": evt.xid,
                        "table": evt.object_name,
                        "lock_mode": evt.lock_mode.value,
                        "wait_ms": round(evt.wait_ms, 2),
                        "granted": evt.granted,
                    })

        result.lock_timeline = sorted(
            timeline, key=lambda x: x["timestamp"]
        )

        return result


# ------------------------------------------------------------------
#  锁继承关系树
# ------------------------------------------------------------------


@dataclass
class LockHierarchyNode:
    """锁继承树节点"""
    name: str
    lock_mode: str = ""
    event_count: int = 0
    wait_count: int = 0
    total_wait_ms: float = 0.0
    children: List["LockHierarchyNode"] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "lock_mode": self.lock_mode,
            "event_count": self.event_count,
            "wait_count": self.wait_count,
            "total_wait_ms": round(self.total_wait_ms, 2),
            "children": [c.to_dict() for c in self.children],
        }


class LockHierarchyBuilder:
    """
    锁继承关系构建器
    构建层次: Database → Schema → Table → LockMode
    用于显示嵌套锁关系（如意图锁 IS/IX 包含行锁 RS/RX）
    """

    # 锁模式层级：父锁 → 子锁（嵌套关系）
    LOCK_HIERARCHY = {
        LockMode.INTENTION_SHARED: [LockMode.ROW_SHARED, LockMode.SHARE],
        LockMode.INTENTION_EXCLUSIVE: [LockMode.ROW_EXCLUSIVE, LockMode.EXCLUSIVE, LockMode.AUTO_INC],
        LockMode.SHARE: [LockMode.ROW_SHARED],
        LockMode.EXCLUSIVE: [LockMode.ROW_EXCLUSIVE, LockMode.AUTO_INC],
        LockMode.ROW_EXCLUSIVE: [],
        LockMode.ROW_SHARED: [],
    }

    def __init__(self, max_depth: int = 4):
        self.max_depth = max_depth

    def build(
        self,
        txns: List[TxnRecord],
        lock_events: Optional[List[LockEvent]] = None,
    ) -> LockHierarchyNode:
        """从锁事件构建继承树"""
        root = LockHierarchyNode(name="LockTree", lock_mode="ROOT")

        all_events: List[LockEvent] = list(lock_events or [])
        for txn in txns:
            all_events.extend(txn.lock_events)

        # 按 Schema → Table → LockMode 聚合
        tree: Dict[str, Dict[str, Dict[str, dict]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: {
                "event_count": 0, "wait_count": 0, "total_wait_ms": 0.0
            }))
        )

        for evt in all_events:
            schema = evt.schema or "unknown"
            table = evt.object_name
            mode = evt.lock_mode.value
            node = tree[schema][table][mode]
            node["event_count"] += 1
            if not evt.granted:
                node["wait_count"] += 1
            node["total_wait_ms"] += evt.wait_ms

        for schema, tables in tree.items():
            schema_node = LockHierarchyNode(name=schema, lock_mode="SCHEMA")
            for table, modes in tables.items():
                table_node = LockHierarchyNode(name=table, lock_mode="TABLE")
                for mode, stats in modes.items():
                    mode_node = LockHierarchyNode(
                        name=mode,
                        lock_mode=mode,
                        event_count=stats["event_count"],
                        wait_count=stats["wait_count"],
                        total_wait_ms=stats["total_wait_ms"],
                    )
                    table_node.children.append(mode_node)
                    table_node.event_count += stats["event_count"]
                    table_node.wait_count += stats["wait_count"]
                    table_node.total_wait_ms += stats["total_wait_ms"]
                schema_node.children.append(table_node)
                schema_node.event_count += table_node.event_count
                schema_node.wait_count += table_node.wait_count
                schema_node.total_wait_ms += table_node.total_wait_ms
            root.children.append(schema_node)
            root.event_count += schema_node.event_count
            root.wait_count += schema_node.wait_count
            root.total_wait_ms += schema_node.total_wait_ms

        # 按 event_count 降序排序
        root.children.sort(key=lambda c: c.event_count, reverse=True)
        for schema_node in root.children:
            schema_node.children.sort(key=lambda c: c.event_count, reverse=True)
            for table_node in schema_node.children:
                table_node.children.sort(key=lambda c: c.event_count, reverse=True)

        return root

    def build_from_conflicts(
        self, conflicts: List[LockConflictRecord]
    ) -> LockHierarchyNode:
        """从锁冲突记录构建继承树"""
        root = LockHierarchyNode(name="LockTree", lock_mode="ROOT")

        tree: Dict[str, Dict[str, Dict[str, dict]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: {
                "event_count": 0, "wait_count": 0, "total_wait_ms": 0.0
            }))
        )

        for c in conflicts:
            parts = c.table_name.split(".", 1)
            schema = parts[0] if len(parts) > 1 else "unknown"
            table = parts[1] if len(parts) > 1 else c.table_name
            mode = c.lock_mode
            node = tree[schema][table][mode]
            node["event_count"] = c.total_events
            node["wait_count"] = c.wait_count
            node["total_wait_ms"] = c.total_wait_ms

        for schema, tables in tree.items():
            schema_node = LockHierarchyNode(name=schema, lock_mode="SCHEMA")
            for table, modes in tables.items():
                table_node = LockHierarchyNode(name=table, lock_mode="TABLE")
                for mode, stats in modes.items():
                    mode_node = LockHierarchyNode(
                        name=mode,
                        lock_mode=mode,
                        event_count=stats["event_count"],
                        wait_count=stats["wait_count"],
                        total_wait_ms=stats["total_wait_ms"],
                    )
                    table_node.children.append(mode_node)
                    table_node.event_count += stats["event_count"]
                    table_node.wait_count += stats["wait_count"]
                    table_node.total_wait_ms += stats["total_wait_ms"]
                schema_node.children.append(table_node)
                schema_node.event_count += table_node.event_count
                schema_node.wait_count += table_node.wait_count
                schema_node.total_wait_ms += table_node.total_wait_ms
            root.children.append(schema_node)
            root.event_count += schema_node.event_count
            root.wait_count += schema_node.wait_count
            root.total_wait_ms += schema_node.total_wait_ms

        root.children.sort(key=lambda c: c.event_count, reverse=True)
        for schema_node in root.children:
            schema_node.children.sort(key=lambda c: c.event_count, reverse=True)
        return root
