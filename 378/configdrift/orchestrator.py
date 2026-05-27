"""巡检业务编排 (orchestrator).

端到端的单次巡检流程:
    采集 → 清洗注释 → 版本化存档 → 漂移检测 → 合规检查 → 影响分析
    → 生成报告 + 修复命令

同时提供基于 Redis 的分布式锁 ``inspection_lock``,防止定时任务重叠执行。
"""
from __future__ import annotations

import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

import redis

from configdrift.baseline import content_hash, load_baseline, save_baseline
from configdrift.compliance import run_compliance
from configdrift.config import settings
from configdrift.detector import (DriftReport, build_repair_commands,
                                   detect_drift, summarize)
from configdrift.history import (diff_versions, list_versions, rollback_to_version,
                                 save_version)
from configdrift.impact import (analyze_impact, capture_after, capture_before)
from configdrift.logger import get_logger
from configdrift.models import InspectionResult
from configdrift.parsers import get_parser, strip_comments
from configdrift.reporter import render
from configdrift.ssh_fetcher import fetch_file

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 分布式锁 (Redis)
# ---------------------------------------------------------------------------

_redis_client: Optional[redis.Redis] = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        url = settings.celery_broker
        _redis_client = redis.Redis.from_url(url, decode_responses=True)
    return _redis_client


@contextmanager
def inspection_lock(lock_key: str = "inspection:running",
                    timeout: int = 3600) -> Iterator[bool]:
    r = _get_redis()
    holder = uuid.uuid4().hex
    acquired = r.set(lock_key, holder, ex=timeout, nx=True)
    try:
        yield bool(acquired)
    finally:
        if acquired:
            if r.get(lock_key) == holder:
                r.delete(lock_key)


def enqueue_task(task_key: str) -> int:
    r = _get_redis()
    return r.lpush(task_key, f"{time.time()}:{uuid.uuid4().hex}")


def dequeue_task(task_key: str) -> Optional[str]:
    r = _get_redis()
    return r.rpop(task_key)


# ---------------------------------------------------------------------------
# 核心流程
# ---------------------------------------------------------------------------

def collect_baselines(only_server: Optional[str] = None,
                      only_service: Optional[str] = None) -> List[str]:
    """采集并保存基准配置,同时写入历史版本."""
    saved: List[str] = []
    for srv in settings.servers:
        if only_server and srv.name != only_server:
            continue
        for svc_name in srv.services:
            if only_service and svc_name != only_service:
                continue
            spec = settings.services.get(svc_name)
            if not spec:
                logger.warning("未定义服务 %s,跳过", svc_name)
                continue
            try:
                raw = fetch_file(srv, spec.config_path, sudo=spec.sudo)
                cleaned = strip_comments(raw)
                parser = get_parser(spec.parser)
                data = parser.parse(cleaned)
                h = content_hash(cleaned)
                data["__hash__"] = h
                path = save_baseline(settings.baseline_dir, srv.name, svc_name, data)
                saved.append(path)
                save_version(settings.history_dir, srv.name, svc_name,
                             data, content_hash=h,
                             comment="baseline采集",
                             operator="baseline",
                             is_baseline=True)
            except Exception as e:
                logger.error("[%s] 采集 %s 失败: %s", srv.name, svc_name, e)
    return saved


def run_inspection(only_server: Optional[str] = None,
                   only_service: Optional[str] = None,
                   auto_apply: bool = False) -> List[InspectionResult]:
    """执行一次完整的巡检."""
    results: List[InspectionResult] = []
    all_repair_scripts: Dict[str, List[str]] = {}

    for srv in settings.servers:
        if only_server and srv.name != only_server:
            continue
        for svc_name in srv.services:
            if only_service and svc_name != only_service:
                continue
            spec = settings.services.get(svc_name)
            if not spec:
                continue
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result = InspectionResult(server=srv.name, service=svc_name,
                                      timestamp=timestamp)

            # 采集当前配置
            try:
                current_raw = fetch_file(srv, spec.config_path, sudo=spec.sudo)
            except Exception as e:
                logger.error("[%s] 读取 %s 失败: %s", srv.name, svc_name, e)
                result.drift = DriftReport(
                    server=srv.name, service=svc_name,
                    timestamp=timestamp, summary={"error": str(e)})
                results.append(result)
                continue

            cleaned = strip_comments(current_raw)
            parser = get_parser(spec.parser)
            current_data = parser.parse(cleaned)
            current_hash = content_hash(cleaned)

            # 加载 baseline
            try:
                baseline_data = load_baseline(settings.baseline_dir,
                                              srv.name, svc_name)
                baseline_data.pop("__hash__", None)
            except FileNotFoundError as e:
                logger.warning("%s", e)
                result.drift = DriftReport(
                    server=srv.name, service=svc_name,
                    timestamp=timestamp, summary={"error": str(e)})
                results.append(result)
                continue

            # 保存历史版本
            save_version(settings.history_dir, srv.name, svc_name,
                         current_data, content_hash=current_hash,
                         comment="巡检采集",
                         operator="inspection")

            # 漂移检测
            baseline_text = parser.serialize(baseline_data)
            current_text = parser.serialize(current_data)
            items = detect_drift(
                baseline_data, current_data,
                baseline_text=baseline_text,
                current_text=current_text,
                auto_strip_comments=True,
            )
            drift = DriftReport(
                server=srv.name, service=svc_name,
                timestamp=timestamp,
                drift_items=items,
                summary=summarize(items),
            )
            result.drift = drift

            if items:
                repair_cmds = build_repair_commands(svc_name, spec.config_path, items)
                all_repair_scripts[f"{srv.name}.{svc_name}"] = repair_cmds
                result.repair_commands = repair_cmds
                logger.info("[%s] %s 检测到 %d 项漂移",
                            srv.name, svc_name, len(items))

            # 合规检查
            if settings.compliance_enabled:
                result.compliance = run_compliance(
                    svc_name, current_data,
                    profile=settings.cis_profile,
                    server=srv.name,
                )

            # 影响分析 - 变更前
            if settings.impact_enabled and settings.metrics_endpoint:
                try:
                    before = capture_before(
                        svc_name, settings.metrics_endpoint,
                        window_minutes=settings.metrics_window_minutes,
                    )
                    result.before_snapshots = before
                except Exception as e:
                    logger.warning("[%s/%s] 影响前指标采集失败: %s",
                                   srv.name, svc_name, e)

            results.append(result)

    # 影响分析 - 变更后 (等待窗口 + 对比)
    if settings.impact_enabled and settings.metrics_endpoint:
        _run_impact_analysis(results)

    # 生成报告
    drift_reports = [r.drift for r in results if r.drift]
    paths = render(drift_reports, settings.report_dir)
    logger.info("报告已生成: %s", paths)

    # 生成综合报告 (含合规 + 影响)
    _write_full_report(results, paths)

    # 生成修复脚本
    if all_repair_scripts:
        repair_path = _write_repair_script(all_repair_scripts)
        logger.info("修复脚本已生成: %s", repair_path)

    return results


def _run_impact_analysis(results: List[InspectionResult]) -> None:
    drifted = [r for r in results if r.drift and r.drift.has_drift]
    if not drifted:
        return
    wait_sec = 10
    logger.info("等待 %d 秒后采集变更后指标...", wait_sec)
    time.sleep(wait_sec)
    for r in drifted:
        try:
            after = capture_after(
                r.service, settings.metrics_endpoint,
                window_minutes=10,
            )
            before = r.before_snapshots or []
            r.impact = analyze_impact(r.service, r.server, before, after)
            logger.info("[%s/%s] 影响分析: level=%s recommendation=%s",
                        r.server, r.service, r.impact.impact_level,
                        r.impact.recommendation)
        except Exception as e:
            logger.warning("[%s/%s] 影响分析失败: %s", r.server, r.service, e)


def _write_full_report(results: List[InspectionResult],
                       paths: Dict[str, str]) -> str:
    """将综合结果 (漂移+合规+影响) 写成 JSON 报告."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(settings.report_dir, exist_ok=True)
    path = os.path.join(settings.report_dir, f"full_report_{ts}.json")
    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": [r.to_dict() for r in results],
        "summary": {
            "total_services": len(results),
            "drift_total": sum(
                (r.drift.summary.get("total", 0) if r.drift else 0)
                for r in results
            ),
            "compliance_avg_score": round(
                sum(r.compliance.score for r in results if r.compliance)
                / max(1, sum(1 for r in results if r.compliance)),
                2,
            ),
        },
    }
    with open(path, "w", encoding="utf-8") as f:
        import json
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    logger.info("综合报告已生成: %s", path)
    return path


def _write_repair_script(all_scripts: Dict[str, List[str]]) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(settings.report_dir, exist_ok=True)
    path = os.path.join(settings.report_dir, f"repair_{ts}.sh")
    lines = ["#!/bin/bash", "set -e",
             "# 配置漂移自动修复脚本",
             "# 请在确认无误后执行: bash " + path, ""]
    for key, cmds in all_scripts.items():
        lines.append(f"echo '=== 修复 {key} ==='")
        lines.extend(cmds)
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    try:
        os.chmod(path, 0o755)
    except OSError:
        pass
    return path


# ---------------------------------------------------------------------------
# 历史版本便捷入口
# ---------------------------------------------------------------------------

def history_list(server: str, service: str,
                 limit: int = 20) -> List[Dict[str, Any]]:
    return list_versions(settings.history_dir, server, service, limit=limit)


def history_diff(server: str, service: str, v1: str, v2: str) -> Dict[str, Any]:
    return diff_versions(settings.history_dir, server, service, v1, v2)


def history_rollback(server: str, service: str, version: str) -> bool:
    return rollback_to_version(
        settings.history_dir, server, service,
        version, settings.baseline_dir,
    )
