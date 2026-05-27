"""新功能测试 - 历史版本、合规检查、影响分析."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time

from configdrift.baseline import save_baseline
from configdrift.compliance import (ComplianceReport, ComplianceResult,
                                     RULE_LIBRARY, run_compliance)
from configdrift.history import (diff_versions, list_versions, load_version,
                                 rollback_to_version, save_version)
from configdrift.impact import (ImpactReport, MetricSnapshot,
                                 analyze_impact)
from configdrift.parsers import get_parser, strip_comments


# ---------------------------------------------------------------------------
# 1. 历史版本测试
# ---------------------------------------------------------------------------

def test_history():
    tmp = tempfile.mkdtemp()
    try:
        # 保存多个版本
        v1_data = {"worker_processes": 2, "listen": 80}
        v2_data = {"worker_processes": 4, "listen": 80, "gzip": True}
        v3_data = {"worker_processes": 4, "listen": 8080, "gzip": True}

        m1 = save_version(tmp, "web01", "nginx", v1_data,
                          content_hash="aaa", comment="v1")
        time.sleep(0.1)
        m2 = save_version(tmp, "web01", "nginx", v2_data,
                          content_hash="bbb", comment="v2")
        time.sleep(0.1)
        m3 = save_version(tmp, "web01", "nginx", v3_data,
                          content_hash="ccc", comment="v3",
                          is_baseline=True)

        # 列表
        lst = list_versions(tmp, "web01", "nginx", limit=10)
        assert len(lst) == 3
        assert lst[0]["version"] == m3.version  # 最新在前
        assert lst[0]["is_baseline"] is True
        print(f"✓ history list: {len(lst)} 个版本,最新={lst[0]['version']}")

        # 加载
        vc = load_version(tmp, "web01", "nginx", m2.version)
        assert vc is not None
        assert vc.data["worker_processes"] == 4
        print(f"✓ history load v2 OK")

        # 版本对比
        d = diff_versions(tmp, "web01", "nginx", m1.version, m2.version)
        assert d["total"] == 2  # listen 不变, worker_processes changed, gzip added
        print(f"✓ history diff v1->v2: {d['total']} 项")

        # 回滚
        save_baseline(tmp, "web01", "nginx", v3_data)
        ok = rollback_to_version(tmp, "web01", "nginx", m1.version, tmp)
        assert ok is True
        from configdrift.baseline import load_baseline
        bl = load_baseline(tmp, "web01", "nginx")
        assert bl["worker_processes"] == 2  # 已回滚到 v1
        print(f"✓ history rollback OK, baseline 已回到 v1")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# 2. 合规检查测试
# ---------------------------------------------------------------------------

def test_compliance():
    # Nginx
    good_nginx = {
        "server_tokens": "off",
        "etag": "off",
        "add_header": "Strict-Transport-Security ...",
        "client_max_body_size": "10m",
    }
    r = run_compliance("nginx", good_nginx, server="web01")
    print(f"✓ nginx 合规得分: {r.score}% ({r.passed_count}/{len(r.results)})")
    for rr in r.results:
        status = "✔" if rr.passed else "✗"
        print(f"  {status} {rr.rule_id} [{rr.severity}] {rr.description}")

    # Redis (不安全配置)
    bad_redis = {
        "bind": "0.0.0.0",
        "protected-mode": "no",
        # 无 requirepass
    }
    r = run_compliance("redis", bad_redis, server="cache01")
    print(f"✓ redis 合规得分: {r.score}% (不安全配置预期低分)")
    for rr in r.results:
        if not rr.passed:
            print(f"  ✗ {rr.rule_id} [{rr.severity}] {rr.description}")

    # MySQL
    good_mysql = {
        "mysqld :: local_infile": 0,
        "mysqld :: symbolic-links": 0,
        "mysqld :: max_connections": 500,
        "mysqld :: log_error": "/var/log/mysql/error.log",
        "mysqld :: skip_name_resolve": 1,
    }
    r = run_compliance("mysql", good_mysql, server="db01")
    print(f"✓ mysql 合规得分: {r.score}%")

    # Kafka
    good_kafka = {
        "auto.create.topics.enable": "false",
        "listeners": "SSL://:9093",
        "default.replication.factor": 3,
    }
    r = run_compliance("kafka", good_kafka, server="mq01")
    print(f"✓ kafka 合规得分: {r.score}%")


# ---------------------------------------------------------------------------
# 3. 影响分析测试
# ---------------------------------------------------------------------------

def test_impact():
    before = [
        MetricSnapshot(metric="qps", service="nginx", timestamp=0,
                       avg=100.0, max=150.0, min=50.0),
        MetricSnapshot(metric="latency", service="nginx", timestamp=0,
                       avg=0.1, max=0.2, min=0.05),
    ]
    after = [
        MetricSnapshot(metric="qps", service="nginx", timestamp=0,
                       avg=120.0, max=180.0, min=60.0),
        MetricSnapshot(metric="latency", service="nginx", timestamp=0,
                       avg=0.3, max=0.5, min=0.1),
    ]
    rpt = analyze_impact("nginx", "web01", before, after)
    print(f"✓ impact level={rpt.impact_level} recommendation={rpt.recommendation}")
    for d in rpt.delta:
        print(f"  {d['metric']}: {d['before_avg']} → {d['after_avg']}  "
              f"变化 {d['change_pct']:+.1f}%")
    assert rpt.impact_level in ("low", "medium", "high")


# ---------------------------------------------------------------------------
# 4. CIS 规则库完整性
# ---------------------------------------------------------------------------

def test_rule_library():
    print(f"\n内置 CIS 规则库:")
    for svc, rules in RULE_LIBRARY.items():
        highs = sum(1 for r in rules if r.severity == "high")
        meds = sum(1 for r in rules if r.severity == "medium")
        print(f"  {svc}: {len(rules)} 条 (high={highs}, medium={meds})")
    assert len(RULE_LIBRARY) == 4  # nginx/mysql/redis/kafka


if __name__ == "__main__":
    print("=" * 60)
    print("历史版本测试")
    print("=" * 60)
    test_history()

    print("\n" + "=" * 60)
    print("合规检查测试")
    print("=" * 60)
    test_compliance()
    test_rule_library()

    print("\n" + "=" * 60)
    print("影响分析测试")
    print("=" * 60)
    test_impact()

    print("\n" + "=" * 60)
    print("✅ 所有新功能测试通过!")
    print("=" * 60)
