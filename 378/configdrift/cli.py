"""命令行入口 (CLI).

使用示例::

    # 采集基准配置 (同时写入历史版本)
    python -m configdrift.cli baseline

    # 立即执行一次巡检 (含合规检查)
    python -m configdrift.cli scan

    # 只扫描某台服务器的某个服务
    python -m configdrift.cli scan --server web01 --service nginx

    # 查看历史版本列表
    python -m configdrift.cli history list --server web01 --service nginx

    # 对比两个历史版本
    python -m configdrift.cli history diff --server web01 --service nginx --v1 20260101_000000 --v2 20260101_010000

    # 回滚到指定历史版本
    python -m configdrift.cli history rollback --server web01 --service nginx --version 20260101_000000

    # 启动 Celery worker / beat
    python -m configdrift.cli worker
    python -m configdrift.cli beat
"""
from __future__ import annotations

import argparse
import sys

from configdrift import __version__
from configdrift.logger import get_logger

logger = get_logger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="configdrift",
        description="配置漂移检测工具 (Python + SSH + Jinja2 + Celery)",
    )
    parser.add_argument("-v", "--version", action="version",
                        version=f"%(prog)s {__version__}")
    parser.add_argument("-c", "--config", default="configdrift.yaml",
                        help="配置文件路径")
    parser.add_argument("--log-level", default="INFO",
                        help="日志级别 (DEBUG/INFO/WARN/ERROR)")

    sub = parser.add_subparsers(dest="command", required=True)

    # baseline
    p_base = sub.add_parser("baseline", help="采集基准配置 (含历史版本)")
    p_base.add_argument("--server", help="只采集指定服务器")
    p_base.add_argument("--service", help="只采集指定服务")

    # scan
    p_scan = sub.add_parser("scan", help="执行一次巡检 (漂移 + 合规 + 影响)")
    p_scan.add_argument("--server", help="只扫描指定服务器")
    p_scan.add_argument("--service", help="只扫描指定服务")
    p_scan.add_argument("--no-compliance", action="store_true",
                        help="跳过高管检查")

    # history
    p_hist = sub.add_parser("history", help="历史版本管理")
    h_sub = p_hist.add_subparsers(dest="history_cmd", required=True)
    p_list = h_sub.add_parser("list", help="列出历史版本")
    p_list.add_argument("--server", required=True)
    p_list.add_argument("--service", required=True)
    p_list.add_argument("--limit", type=int, default=20)

    p_diff = h_sub.add_parser("diff", help="对比两个版本")
    p_diff.add_argument("--server", required=True)
    p_diff.add_argument("--service", required=True)
    p_diff.add_argument("--v1", required=True, help="较早版本")
    p_diff.add_argument("--v2", required=True, help="较新版本")

    p_rollback = h_sub.add_parser("rollback", help="回滚到指定版本")
    p_rollback.add_argument("--server", required=True)
    p_rollback.add_argument("--service", required=True)
    p_rollback.add_argument("--version", required=True)

    # worker / beat / queue
    sub.add_parser("worker", help="启动 Celery worker")
    sub.add_parser("beat", help="启动 Celery beat 定时调度")
    sub.add_parser("queue", help="查看巡检队列状态")

    args = parser.parse_args()

    from configdrift import config as _config
    _config.settings = _config.load_settings(args.config)

    import logging
    logging.getLogger("configdrift").setLevel(
        getattr(logging, args.log_level.upper(), logging.INFO)
    )

    # ---- baseline ----
    if args.command == "baseline":
        from configdrift.orchestrator import collect_baselines
        saved = collect_baselines(only_server=args.server,
                                  only_service=args.service)
        print(f"已采集 {len(saved)} 份基准配置 + 历史版本")
        for p in saved:
            print(f"  - {p}")
        return 0

    # ---- scan ----
    if args.command == "scan":
        if args.no_compliance:
            _config.settings.compliance_enabled = False
        from configdrift.orchestrator import run_inspection
        results = run_inspection(only_server=args.server,
                                 only_service=args.service)
        drift_count = 0
        for r in results:
            if r.drift:
                drift_count += r.drift.summary.get("total", 0)
                status = "⚠ 漂移" if r.drift.has_drift else "✔ 正常"
                info = f"  [{status}] {r.server}/{r.service} - {r.drift.summary}"
                if r.compliance:
                    info += f"  合规得分: {r.compliance.score}%"
                if r.impact:
                    info += f"  影响: {r.impact.impact_level}"
                print(info)
        print(f"\n巡检完成,共 {len(results)} 个服务,漂移 {drift_count} 项")
        return 0 if drift_count == 0 else 1

    # ---- history ----
    if args.command == "history":
        from configdrift.orchestrator import (history_diff, history_list,
                                               history_rollback)
        if args.history_cmd == "list":
            items = history_list(args.server, args.service, limit=args.limit)
            print(f"[{args.server}/{args.service}] 共 {len(items)} 个版本:")
            for it in items:
                import time as _t
                ts = _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime(it["timestamp"]))
                flag = "★" if it.get("is_baseline") else " "
                print(f"  {flag} {it['version']}  {ts}  operator={it['operator']}  "
                      f"drift={it.get('drift_count', 0)}  {it.get('comment', '')}")
            return 0

        if args.history_cmd == "diff":
            diff = history_diff(args.server, args.service, args.v1, args.v2)
            print(f"对比 {args.v1} → {args.v2},共 {diff.get('total', 0)} 项差异:")
            for it in diff.get("items", []):
                print(f"  {it['drift_type']:7s} {it['key']}: "
                      f"{it.get('baseline_text', '')} → {it.get('current_text', '')}")
            return 0

        if args.history_cmd == "rollback":
            ok = history_rollback(args.server, args.service, args.version)
            if ok:
                print(f"✓ 已回滚 {args.server}/{args.service} 到版本 {args.version}")
                return 0
            else:
                print(f"✗ 回滚失败,请检查版本号是否存在")
                return 1

    # ---- worker ----
    if args.command == "worker":
        from configdrift.celery_app import app as celery_app
        celery_app.worker_main(["worker", "--loglevel=INFO", "-Q", "inspection"])
        return 0

    # ---- beat ----
    if args.command == "beat":
        from configdrift.celery_app import app as celery_app
        celery_app.Beat(["beat", "--loglevel=INFO",
                         "--scheduler", "celery.beat.PersistentScheduler"]).run()
        return 0

    # ---- queue ----
    if args.command == "queue":
        from configdrift.orchestrator import _get_redis
        r = _get_redis()
        lock_holder = r.get("inspection:running")
        queue_len = r.llen("inspection:queue")
        print(f"当前执行锁: {'持有中 (' + str(lock_holder)[:8] + '...)' if lock_holder else '空闲'}")
        print(f"排队任务数: {queue_len}")
        if queue_len > 0:
            items = r.lrange("inspection:queue", 0, -1)
            for i, it in enumerate(items, 1):
                print(f"  {i}. {it}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
