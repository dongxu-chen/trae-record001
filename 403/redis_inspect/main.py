"""Redis 集群巡检工具主入口。

使用方式：
    python -m redis_inspect.main --config config.yaml
    python -m redis_inspect.main --host 127.0.0.1 --port 6379 --format markdown
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .clickhouse_writer import ClickHouseWriter
from .collector import (
    collect_topology,
    sample_replication_lag,
    compute_performance_scores,
    sample_hot_keys,
    collect_slowlog_entries,
    analyze_slowlog_patterns,
    analyze_memory_types,
)
from .config import load_config
from .health_analyzer import analyze_health
from .performance_analyzer import analyze_performance
from .report import build_payload, render_text, write_report
from .slot_analyzer import analyze_slots


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="redis-inspect", description="Redis 集群巡检工具")
    p.add_argument("--config", "-c", type=str, default=None, help="配置文件路径（默认 ./config.yaml）")
    p.add_argument("--host", type=str, default=None)
    p.add_argument("--port", type=int, default=None)
    p.add_argument("--password", type=str, default=None)
    p.add_argument("--format", "-f", choices=["text", "json", "markdown"], default=None)
    p.add_argument("--output-dir", "-o", type=str, default=None)
    p.add_argument("--stdout", action="store_true", help="同时输出到标准输出")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--skip-ch", action="store_true", help="本次不写入 ClickHouse")
    return p.parse_args(argv)


def _override_cfg(cfg: dict, args: argparse.Namespace) -> dict:
    if args.host:
        cfg["redis"]["host"] = args.host
    if args.port:
        cfg["redis"]["port"] = args.port
    if args.password:
        cfg["redis"]["password"] = args.password
    if args.format:
        cfg["report"]["format"] = args.format
    if args.output_dir:
        cfg["report"]["output_dir"] = args.output_dir
    if args.skip_ch:
        cfg["clickhouse"]["enabled"] = False
    return cfg


def run_inspection(cfg: dict) -> dict:
    log = logging.getLogger("inspect")
    log.info("开始巡检: seed=%s:%s", cfg["redis"]["host"], cfg["redis"]["port"])

    topo = collect_topology(cfg)
    log.info(
        "拓扑采集完成: state=%s nodes=%d masters=%d slots=%d",
        topo.cluster_state,
        len(topo.nodes),
        len(topo.masters),
        topo.cluster_slots_assigned,
    )

    # 连续采样复制延迟
    sample_replication_lag(topo, cfg)
    log.info("复制延迟采样完成")

    # 计算性能评分（供槽位分配使用
    compute_performance_scores(topo, cfg)
    log.info("节点性能评分完成")

    # 热点 key 采样
    hotkey_report = sample_hot_keys(topo, cfg)
    log.info("热点 key 采样完成: 扫描 %d 个 key", hotkey_report.total_scanned)

    # 慢查询模式聚合
    slowlog_entries = collect_slowlog_entries(topo, cfg)
    slowlog_patterns = analyze_slowlog_patterns(slowlog_entries, top_n=cfg["report"].get("top_n_slowlog", 20))
    log.info("慢查询模式聚合完成: %d 条模式", len(slowlog_patterns))

    # 内存类型分析
    memory_type_report = analyze_memory_types(hotkey_report, top_n=cfg["report"].get("top_n_slowlog", 20))
    log.info("内存类型分析完成: %d 种数据类型", len(memory_type_report.by_type))

    slot_report = analyze_slots(
        topo,
        threshold_cv=cfg["redis"]["threshold"]["slot_unbalance_ratio"],
        use_perf_weight=cfg["redis"].get("slot_balance", {}).get("use_performance_weight", True),
    )
    health_report = analyze_health(topo, cfg["redis"]["threshold"])
    perf_report = analyze_performance(
        topo,
        slowlog_usec=cfg["redis"]["threshold"]["slowlog_usec"],
        top_n=cfg["report"].get("top_n_slowlog", 20),
    )

    # ClickHouse 写入
    ch = ClickHouseWriter(cfg)
    if ch.enabled:
        log.info("写入 ClickHouse...")
        ch.ensure_schema()
        ch.write_snapshot(topo, slot_report, health_report)
        ch.write_hotspots(topo, perf_report)

    payload = build_payload(
        topo, slot_report, health_report, perf_report,
        hotkey_report=hotkey_report,
        slowlog_patterns=slowlog_patterns,
        slowlog_entries=slowlog_entries,
        memory_type_report=memory_type_report,
    )
    return payload


def main(argv=None) -> int:
    args = _parse_args(argv)
    _setup_logging(args.verbose)
    log = logging.getLogger("inspect")

    try:
        cfg = load_config(args.config)
    except Exception as e:
        print(f"[ERROR] 无法加载配置: {e}", file=sys.stderr)
        return 2
    cfg = _override_cfg(cfg, args)

    try:
        payload = run_inspection(cfg)
    except Exception as e:
        log.exception("巡检失败: %s", e)
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    fmt = cfg["report"].get("format", "text")
    path = write_report(cfg["report"]["output_dir"], payload, fmt)
    log.info("报告已生成: %s", path)

    if args.stdout or fmt == "text":
        if fmt == "text":
            print(render_text(payload))
        elif fmt == "markdown":
            from .report import render_markdown
            print(render_markdown(payload))
        else:
            import json
            print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))

    # 退出码：告警但不致命 = 0；CRITICAL = 3
    if payload["health"]["overall"] == "CRITICAL":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
