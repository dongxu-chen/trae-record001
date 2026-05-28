"""ClickHouse 写入模块（可选）。

将巡检结果写入 ClickHouse，用于历史趋势分析。
需要 clickhouse-driver 或 clickhouse-connect 包。
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

CH_SETUP_DDL = """
CREATE DATABASE IF NOT EXISTS {database};

CREATE TABLE IF NOT EXISTS {database}.inspect_snapshots
(
    ts                   DateTime64(3),
    seed                 String,
    cluster_state        String,
    known_nodes          UInt32,
    cluster_size         UInt32,
    slots_assigned       UInt32,
    slots_ok             UInt32,
    slots_fail           UInt32,
    overall_health       String,
    imbalance            UInt8,
    slot_cv              Float64,
    use_perf_weight    UInt8,
    alerts               Array(String)
)
ENGINE = MergeTree()
ORDER BY (ts, seed);

CREATE TABLE IF NOT EXISTS {database}.node_health
(
    ts            DateTime64(3),
    seed          String,
    node_id       String,
    label         String,
    role          String,
    redis_version String,
    reachable     UInt8,
    slot_count    UInt32,
    mem_frag      Float64,
    mem_frag_th   Float64,
    mem_used      UInt64,
    mem_max       UInt64,
    mem_usage_pct Float64,
    cpu_pct       Float64,
    perf_score    Float64,
    repl_lag_sec  Float64,
    repl_lag_max Float64,
    repl_lag_avg Float64,
    repl_lag_p95 Float64,
    clients       UInt32,
    alerts        Array(String)
)
ENGINE = MergeTree()
ORDER BY (ts, seed, node_id);

CREATE TABLE IF NOT EXISTS {database}.command_hotspots
(
    ts             DateTime64(3),
    seed           String,
    command        String,
    calls          UInt64,
    usec_per_call  Float64,
    total_usec     Float64,
    score          Float64
)
ENGINE = MergeTree()
ORDER BY (ts, seed, command);
"""


class ClickHouseWriter:
    """封装 ClickHouse 写入。未安装驱动时会静默降级。"""

    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg.get("clickhouse", {})
        self.enabled = bool(self.cfg.get("enabled", False))
        self.client = None
        if not self.enabled:
            return
        try:
            from clickhouse_driver import Client  # type: ignore

            self.client = Client(
                host=self.cfg.get("host", "127.0.0.1"),
                port=int(self.cfg.get("port", 9000)),
                user=self.cfg.get("user", "default"),
                password=self.cfg.get("password", ""),
                settings={"use_numpy": False},
            )
        except Exception as e:  # pragma: no cover
            log.warning("ClickHouse 驱动不可用，已禁用写入: %s", e)
            self.client = None
            self.enabled = False

    def ensure_schema(self) -> None:
        if not self.enabled or not self.client:
            return
        ddl = CH_SETUP_DDL.format(database=self.cfg.get("database", "redis_inspect"))
        for stmt in ddl.split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            try:
                self.client.execute(stmt)
            except Exception as e:  # pragma: no cover
                log.warning("CH DDL 失败: %s -> %s", stmt[:40], e)

    def write_snapshot(
        self,
        topo: Any,
        slot_report: Any,
        health_report: Any,
    ) -> None:
        if not self.enabled or not self.client:
            return
        db = self.cfg.get("database", "redis_inspect")
        ts_ms = int(topo.ts * 1000)
        self.client.execute(
            f"INSERT INTO {db}.inspect_snapshots VALUES",
            [(
                ts_ms,
                topo.seed,
                topo.cluster_state,
                topo.cluster_known_nodes,
                topo.cluster_size,
                topo.cluster_slots_assigned,
                topo.cluster_slots_ok,
                topo.cluster_slots_fail,
                health_report.overall,
                1 if slot_report.imbalance else 0,
                float(slot_report.cv),
                1 if getattr(slot_report, "use_perf_weight", False) else 0,
                health_report.alerts,
            )],
        )
        rows = []
        for nh in health_report.nodes.values():
            rows.append((
                ts_ms,
                topo.seed,
                nh.node_id,
                nh.label,
                nh.role,
                getattr(nh, "redis_version", ""),
                1 if nh.reachable else 0,
                nh.slot_count,
                float(nh.mem_fragmentation_ratio),
                float(getattr(nh, "mem_fragmentation_threshold", 1.5)),
                int(nh.used_memory),
                int(nh.maxmemory),
                float(nh.mem_usage_percent),
                float(nh.cpu_usage_percent),
                float(getattr(nh, "perf_score", 0.0)),
                float(nh.replication_lag_sec),
                float(getattr(nh, "replication_lag_max_sec", nh.replication_lag_sec)),
                float(getattr(nh, "replication_lag_avg_sec", nh.replication_lag_sec)),
                float(getattr(nh, "replication_lag_p95_sec", nh.replication_lag_sec)),
                int(nh.connected_clients),
                nh.alerts,
            ))
        self.client.execute(f"INSERT INTO {db}.node_health VALUES", rows)

    def write_hotspots(self, topo: Any, perf_report: Any) -> None:
        if not self.enabled or not self.client:
            return
        db = self.cfg.get("database", "redis_inspect")
        ts_ms = int(topo.ts * 1000)
        rows = [
            (
                ts_ms,
                topo.seed,
                h.command,
                int(h.calls),
                float(h.usec_per_call),
                float(h.total_usec),
                float(h.bottleneck_score),
            )
            for h in perf_report.top_commands
        ]
        if rows:
            self.client.execute(f"INSERT INTO {db}.command_hotspots VALUES", rows)
