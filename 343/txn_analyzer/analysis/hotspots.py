"""
Hotspot Analyzer - 事务热点排名
按表/Schema 统计事务操作频率，识别热点表和热点事务。
"""
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..parsers.base import TxnRecord, TxnStatus


@dataclass
class TableHotspot:
    """表热点数据"""
    table_name: str
    total_ops: int = 0
    txn_count: int = 0
    insert_count: int = 0
    update_count: int = 0
    delete_count: int = 0
    total_lock_wait_ms: float = 0.0
    max_lock_wait_ms: float = 0.0
    avg_duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "table": self.table_name,
            "total_ops": self.total_ops,
            "txn_count": self.txn_count,
            "total_lock_wait_ms": round(self.total_lock_wait_ms, 2),
            "max_lock_wait_ms": round(self.max_lock_wait_ms, 2),
            "avg_duration_ms": round(self.avg_duration_ms, 2),
        }


@dataclass
class SchemaHotspot:
    """Schema 级别热点"""
    schema_name: str
    total_ops: int = 0
    txn_count: int = 0
    tables: List[TableHotspot] = field(default_factory=list)


@dataclass
class HotspotResult:
    """热点分析结果"""
    top_tables: List[TableHotspot] = field(default_factory=list)
    top_schemas: List[SchemaHotspot] = field(default_factory=list)
    top_txns: List[Dict] = field(default_factory=list)
    table_heatmap_data: List[Dict] = field(default_factory=list)


class HotspotAnalyzer:
    """热点分析器"""

    def __init__(self, top_n: int = 20):
        self.top_n = top_n

    def analyze(self, txns: List[TxnRecord]) -> HotspotResult:
        """分析热点数据"""
        result = HotspotResult()

        # ---- 按表聚合 ----
        table_data: Dict[str, TableHotspot] = defaultdict(lambda: TableHotspot(""))
        schema_data: Dict[str, SchemaHotspot] = defaultdict(lambda: SchemaHotspot(""))

        for txn in txns:
            for table, ops in txn.table_ops.items():
                if table not in table_data:
                    table_data[table] = TableHotspot(table_name=table)
                td = table_data[table]
                td.total_ops += ops
                td.total_lock_wait_ms += txn.total_lock_wait_ms
                td.max_lock_wait_ms = max(td.max_lock_wait_ms, txn.max_lock_wait_ms)
                td.avg_duration_ms = (
                    (td.avg_duration_ms * td.txn_count + txn.duration_ms)
                    / (td.txn_count + 1)
                )
                td.txn_count += 1

                # Schema 级别
                schema = table.split(".")[0] if "." in table else "default"
                if schema not in schema_data:
                    schema_data[schema] = SchemaHotspot(schema_name=schema)
                sd = schema_data[schema]
                sd.total_ops += ops
                sd.txn_count += 1

        # ---- Top 表 ----
        sorted_tables = sorted(
            table_data.values(), key=lambda t: t.total_ops, reverse=True
        )
        result.top_tables = sorted_tables[: self.top_n]

        # ---- Top Schema ----
        sorted_schemas = sorted(
            schema_data.values(), key=lambda s: s.total_ops, reverse=True
        )
        for sd in sorted_schemas[: self.top_n]:
            sd.tables = sorted(
                [t for t in table_data.values() if t.table_name.startswith(sd.schema_name)],
                key=lambda t: t.total_ops, reverse=True,
            )[:10]
        result.top_schemas = sorted_schemas

        # ---- Top 事务 ----
        top_txns = sorted(
            txns,
            key=lambda t: (t.duration_ms + t.total_lock_wait_ms, t.row_ops_count),
            reverse=True,
        )[: self.top_n]

        result.top_txns = [
            {
                "xid": txn.xid,
                "schema": txn.schema or "N/A",
                "status": txn.status.value,
                "duration_ms": round(txn.duration_ms, 2),
                "row_ops": txn.row_ops_count,
                "total_lock_wait_ms": round(txn.total_lock_wait_ms, 2),
                "tables": list(txn.table_ops.keys())[:5],
                "query": txn.queries[0] if txn.queries else "",
            }
            for txn in top_txns
        ]

        # ---- 热力图数据 (table × schema) ----
        heatmap: Dict[Tuple[str, str], int] = defaultdict(int)
        for table, td in table_data.items():
            schema = table.split(".")[0] if "." in table else "default"
            heatmap[(schema, table)] = td.total_ops

        result.table_heatmap_data = [
            {"schema": s, "table": t, "ops": ops}
            for (s, t), ops in sorted(heatmap.items(), key=lambda x: x[1], reverse=True)
        ][: self.top_n * 2]

        return result
