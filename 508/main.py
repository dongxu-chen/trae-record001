import argparse
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from alerter import (
    Alerter,
    ConsoleAlertChannel,
    EmailAlertChannel,
    FileAlertChannel,
    WebhookAlertChannel,
)
from cache_optimizer import CacheOptimizer
from dry_run import DryRunEngine
from es_collector import ESCollector, SlowQuery
from query_analyzer import QueryAnalyzer
from rate_limiter import RateLimiter, RateLimitAction, extract_source_id
from rule_engine import RuleEngine
from trend_predictor import TrendPredictor

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> Dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        logger.error("Config file not found: %s", config_path)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logging(cfg: Dict[str, Any]):
    log_cfg = cfg.get("logging", {})
    level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
    fmt = log_cfg.get("format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logging.basicConfig(level=level, format=fmt)


def create_collector(cfg: Dict[str, Any]) -> ESCollector:
    es_cfg = cfg.get("elasticsearch", {})
    return ESCollector(
        hosts=es_cfg.get("hosts", ["http://localhost:9200"]),
        username=es_cfg.get("username", ""),
        password=es_cfg.get("password", ""),
        timeout=es_cfg.get("timeout", 30),
        verify_certs=es_cfg.get("verify_certs", False),
    )


def create_alerter(cfg: Dict[str, Any]) -> Alerter:
    alert_cfg = cfg.get("alerts", {})
    channels = []

    for name, ch_cfg in alert_cfg.get("channels", {}).items():
        if not ch_cfg.get("enabled", False):
            continue
        if name == "console":
            channels.append(ConsoleAlertChannel())
        elif name == "file":
            channels.append(FileAlertChannel(file_path=ch_cfg.get("path", "slow_query_alerts.jsonl")))
        elif name == "email":
            channels.append(EmailAlertChannel(
                smtp_host=ch_cfg.get("smtp_host", ""),
                smtp_port=ch_cfg.get("smtp_port", 587),
                username=ch_cfg.get("username", ""),
                password=ch_cfg.get("password", ""),
                from_addr=ch_cfg.get("from", ""),
                to_addrs=ch_cfg.get("to", []),
                use_tls=ch_cfg.get("use_tls", True),
            ))
        elif name == "webhook":
            channels.append(WebhookAlertChannel(
                webhook_url=ch_cfg.get("url", ""),
                headers=ch_cfg.get("headers"),
            ))

    if not channels:
        channels.append(ConsoleAlertChannel())

    return Alerter(channels=channels, min_severity=alert_cfg.get("min_severity", "medium"))


class SlowQueryMonitor:
    def __init__(self, collector: ESCollector, analyzer: QueryAnalyzer,
                 rule_engine: RuleEngine, alerter: Alerter,
                 config: Dict[str, Any],
                 dry_run_engine: Optional[DryRunEngine] = None,
                 trend_predictor: Optional[TrendPredictor] = None,
                 rate_limiter: Optional[RateLimiter] = None,
                 cache_optimizer: Optional[CacheOptimizer] = None):
        self.collector = collector
        self.analyzer = analyzer
        self.rule_engine = rule_engine
        self.alerter = alerter
        self.config = config
        self.dry_run_engine = dry_run_engine
        self.trend_predictor = trend_predictor
        self.rate_limiter = rate_limiter
        self.cache_optimizer = cache_optimizer
        self._running = False
        self.threshold_ms = config.get("monitor", {}).get("threshold_ms", 3000)
        self.interval = config.get("monitor", {}).get("interval_seconds", 60)
        self.index_patterns = config.get("monitor", {}).get("index_patterns", ["*"])
        self.slow_log_index = config.get("monitor", {}).get("slow_log_index", ".slowlog-*")
        self.enable_profiling = config.get("monitor", {}).get("enable_profiling", True)
        self.enable_trend_prediction = config.get("features", {}).get("trend_prediction", True)
        self.enable_rate_limiting = config.get("features", {}).get("rate_limiting", True)
        self.enable_cache_optimization = config.get("features", {}).get("cache_optimization", True)

    def run_once(self):
        logger.info("Starting slow query collection cycle")
        slow_queries = self._collect_slow_queries()
        if not slow_queries:
            logger.info("No slow queries detected")
            self._run_periodic_analyses()
            return

        logger.info("Detected %d slow queries", len(slow_queries))
        for sq in slow_queries:
            diagnosis = self.analyzer.analyze(sq)
            rule_matches = self.rule_engine.evaluate(sq, diagnosis)

            if rule_matches:
                logger.info("Rule engine matched %d rules for query %s",
                            len(rule_matches), sq.query_id)

            self.alerter.alert(diagnosis)

            if self.trend_predictor:
                self.trend_predictor.record_query(sq)

            if self.rate_limiter:
                source_id = extract_source_id(sq)
                decision = self.rate_limiter.record_and_evaluate(sq, source_id=source_id)
                if decision.action in (RateLimitAction.THROTTLE, RateLimitAction.BLOCK):
                    logger.warning(
                        "Rate limit decision: %s for source %s, level: %s, reason: %s",
                        decision.action.value, decision.source_id,
                        decision.throttling_level.value, decision.reason,
                    )

            if self.cache_optimizer:
                self.cache_optimizer.record_query(sq)

            if self.dry_run_engine:
                dry_results = self.dry_run_engine.evaluate(diagnosis)
                report = self.dry_run_engine.generate_report(dry_results)
                print(report)

        self._run_periodic_analyses()

    def _run_periodic_analyses(self):
        if self.enable_trend_prediction and self.trend_predictor:
            try:
                prediction = self.trend_predictor.predict()
                report = self.trend_predictor.generate_trend_report()
                print(f"\n{report}\n")
            except Exception as e:
                logger.error("Trend prediction failed: %s", e, exc_info=True)

        if self.enable_rate_limiting and self.rate_limiter:
            try:
                report = self.rate_limiter.generate_report()
                print(f"\n{report}\n")
            except Exception as e:
                logger.error("Rate limiting report failed: %s", e, exc_info=True)

        if self.enable_cache_optimization and self.cache_optimizer:
            try:
                self._sync_cache_stats_from_es()
                analysis = self.cache_optimizer.analyze()
                print(f"\n{analysis.to_text()}\n")
            except Exception as e:
                logger.error("Cache optimization analysis failed: %s", e, exc_info=True)

    def _sync_cache_stats_from_es(self):
        if not self.cache_optimizer:
            return
        try:
            for pattern in self.index_patterns:
                try:
                    es_stats = self.collector.get_detailed_index_stats(pattern)
                    if es_stats:
                        self.cache_optimizer.update_from_es_stats(pattern, es_stats)
                except Exception as e:
                    logger.debug("Failed to sync cache stats for %s: %s", pattern, e)
        except Exception as e:
            logger.warning("Failed to sync ES cache stats: %s", e)

    def run_loop(self):
        self._running = True

        def _signal_handler(signum, frame):
            logger.info("Received signal %s, shutting down...", signum)
            self._running = False

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        logger.info("Starting slow query monitor (interval=%ds, threshold=%dms)",
                    self.interval, self.threshold_ms)
        while self._running:
            try:
                self.run_once()
            except Exception as e:
                logger.error("Monitor cycle failed: %s", e, exc_info=True)

            for _ in range(self.interval):
                if not self._running:
                    break
                time.sleep(1)

        logger.info("Slow query monitor stopped")

    def _collect_slow_queries(self) -> List[SlowQuery]:
        queries = self.collector.collect_slow_logs(
            log_index=self.slow_log_index,
        )

        if not queries:
            logger.debug("No slow log entries found, checking active queries via profiling")
            queries = self._profile_active_queries()

        return queries

    def _profile_active_queries(self) -> List[SlowQuery]:
        results = []
        for pattern in self.index_patterns:
            try:
                test_queries = self._get_sample_queries(pattern)
                for q in test_queries:
                    sq = self.collector.execute_and_collect(
                        index_name=pattern,
                        query_body=q,
                        threshold_ms=self.threshold_ms,
                    )
                    if sq:
                        results.append(sq)
            except Exception as e:
                logger.debug("No sample queries for %s: %s", pattern, e)
        return results

    @staticmethod
    def _get_sample_queries(index_pattern: str) -> List[Dict[str, Any]]:
        return [
            {"query": {"match_all": {}}, "size": 10},
        ]


def demo():
    config = {
        "monitor": {"threshold_ms": 3000, "interval_seconds": 60,
                     "index_patterns": ["*"], "slow_log_index": ".slowlog-*",
                     "enable_profiling": True},
        "features": {"trend_prediction": True, "rate_limiting": True, "cache_optimization": True},
    }

    sq_dfs = SlowQuery(
        query_id="demo-dfs-001",
        index_name="orders",
        query_body={
            "query": {
                "bool": {
                    "must": [
                        {"prefix": {"status_code": "ERR"}},
                        {"fuzzy": {"description": {"value": "paymnt", "fuzziness": "AUTO"}}},
                        {"wildcard": {"trace_id": "*-timeout-*"}},
                    ]
                }
            },
            "from": 12000,
            "size": 100,
            "sort": [{"created_at": {"order": "desc"}}],
        },
        response_time_ms=28500.0,
        timestamp=time.time(),
        search_type="dfs_query_then_fetch",
        total_shards=120,
        successful_shards=120,
        profile_data=None,
        cache_hit=False,
        hits_total=800000,
        from_offset=12000,
        size=100,
    )

    sq_prefix = SlowQuery(
        query_id="demo-prefix-001",
        index_name="logs",
        query_body={
            "query": {
                "bool": {
                    "must": [
                        {"prefix": {"host": "web-server-"}},
                        {"prefix": {"path": "/api/v2/"}},
                    ],
                    "filter": [
                        {"range": {"timestamp": {"gte": "now-1h"}}},
                    ]
                }
            },
            "size": 50,
        },
        response_time_ms=8500.0,
        timestamp=time.time(),
        search_type="query_then_fetch",
        total_shards=30,
        successful_shards=30,
        profile_data=None,
        cache_hit=None,
        hits_total=2000000,
        from_offset=0,
        size=50,
    )

    sq_normal1 = SlowQuery(
        query_id="demo-slow-001",
        index_name="products",
        query_body={
            "query": {"match": {"title": "elasticsearch tutorial"}},
            "from": 0,
            "size": 10,
        },
        response_time_ms=4200.0,
        timestamp=time.time(),
        search_type="query_then_fetch",
        total_shards=5,
        successful_shards=5,
        profile_data=None,
        cache_hit=False,
        hits_total=12000,
        from_offset=0,
        size=10,
    )

    analyzer = QueryAnalyzer()
    rule_engine = RuleEngine()
    alerter = Alerter(channels=[ConsoleAlertChannel(), FileAlertChannel("slow_query_alerts.jsonl")],
                      min_severity="medium")
    dry_run = DryRunEngine()
    trend_predictor = TrendPredictor(slow_threshold_ms=3000)
    rate_limiter = RateLimiter(slow_threshold_ms=3000, dry_run=True, auto_apply=False)
    cache_optimizer = CacheOptimizer()

    print(f"\n{'#' * 70}")
    print("# 📊 阶段 1: 基础分析和告警")
    print(f"{'#' * 70}")

    for sq in [sq_dfs, sq_prefix, sq_normal1, sq_normal1]:
        print(f"\n{'-' * 70}")
        print(f"分析查询: {sq.query_id} (search_type={sq.search_type})")
        print(f"{'-' * 70}")

        diagnosis = analyzer.analyze(sq)
        rule_matches = rule_engine.evaluate(sq, diagnosis)

        print(f"规则引擎匹配: {len(rule_matches)} 条规则")
        for rm in rule_matches:
            print(f"  - [{rm.rule.rule_id}] {rm.rule.name}")

        alerter.alert(diagnosis)

    print(f"\n{'#' * 70}")
    print("# 📈 阶段 2: 趋势预测")
    print(f"{'#' * 70}")

    for sq in [sq_dfs, sq_prefix, sq_normal1, sq_normal1, sq_normal1]:
        trend_predictor.record_query(sq)
        source_id = f"client:{sq.query_id}"
        if sq.index_name == "orders":
            source_id = "app:web-api"
        elif sq.index_name == "logs":
            source_id = "app:log-collector"
        else:
            source_id = "app:search-service"
        trend_predictor.record_query(sq, source_id=source_id)

    trend_report = trend_predictor.generate_trend_report()
    print(trend_report)

    print(f"\n{'#' * 70}")
    print("# 🚦 阶段 3: 自动限流分析")
    print(f"{'#' * 70}")

    for sq in [sq_dfs, sq_prefix, sq_normal1, sq_normal1]:
        source_id = f"app:web-api" if sq.index_name == "orders" else "app:search-service"
        decision = rate_limiter.record_and_evaluate(sq, source_id=source_id)
        print(f"\n来源 {source_id}: action={decision.action.value}, "
              f"level={decision.throttling_level.value}, "
              f"applied={decision.applied}")
        print(f"  原因: {decision.reason}")

    print(f"\n{rate_limiter.generate_report()}")

    print(f"\n{'#' * 70}")
    print("# 💾 阶段 4: 缓存分析")
    print(f"{'#' * 70}")

    for sq in [sq_dfs, sq_prefix, sq_normal1, sq_normal1]:
        cache_optimizer.record_query(sq)

    cache_report = cache_optimizer.analyze()
    print(cache_report.to_text())

    print(f"\n{'#' * 70}")
    print("# 🧪 阶段 5: 演练模式 (索引调整评估)")
    print(f"{'#' * 70}")

    for sq in [sq_dfs, sq_prefix]:
        diagnosis = analyzer.analyze(sq)
        dry_results = dry_run.evaluate(diagnosis)
        dry_report = dry_run.generate_report(dry_results)
        print(dry_report)

    return diagnosis


def main():
    parser = argparse.ArgumentParser(description="Elasticsearch Slow Query Alert Tool")
    parser.add_argument("-c", "--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--once", action="store_true", help="只运行一次采集周期")
    parser.add_argument("--demo", action="store_true", help="使用演示数据运行")
    parser.add_argument("--dry-run", action="store_true",
                        help="演练模式: 分析慢查询并评估索引调整影响，不执行实际修改")
    parser.add_argument("--threshold", type=float, help="覆盖慢查询阈值(ms)")
    parser.add_argument("--no-trend", action="store_true", help="禁用趋势预测")
    parser.add_argument("--no-rate-limit", action="store_true", help="禁用自动限流")
    parser.add_argument("--no-cache-opt", action="store_true", help="禁用缓存优化分析")
    parser.add_argument("--apply-rate-limit", action="store_true",
                        help="限流模式下实际执行限流操作（默认只报告不执行）")
    parser.add_argument("--rate-limit-rule", default="DEFAULT",
                        help="限流规则: DEFAULT, STRICT, AGGRESSIVE")
    args = parser.parse_args()

    if args.demo:
        setup_logging({"logging": {"level": "INFO"}})
        demo()
        return

    config = load_config(args.config)
    setup_logging(config)

    if args.threshold:
        config.setdefault("monitor", {})["threshold_ms"] = args.threshold

    features_cfg = config.setdefault("features", {})
    features_cfg["trend_prediction"] = not args.no_trend and features_cfg.get("trend_prediction", True)
    features_cfg["rate_limiting"] = not args.no_rate_limit and features_cfg.get("rate_limiting", True)
    features_cfg["cache_optimization"] = not args.no_cache_opt and features_cfg.get("cache_optimization", True)

    collector = create_collector(config)
    analyzer = QueryAnalyzer()
    rule_engine = RuleEngine()
    alerter = create_alerter(config)
    dry_run_engine = DryRunEngine()

    trend_predictor = None
    if features_cfg["trend_prediction"]:
        threshold = config.get("monitor", {}).get("threshold_ms", 3000)
        trend_predictor = TrendPredictor(slow_threshold_ms=threshold)

    rate_limiter = None
    if features_cfg["rate_limiting"]:
        threshold = config.get("monitor", {}).get("threshold_ms", 3000)
        rate_cfg = config.get("rate_limiting", {})
        rate_limiter = RateLimiter(
            slow_threshold_ms=threshold,
            dry_run=not args.apply_rate_limit,
            auto_apply=rate_cfg.get("auto_apply", False),
            default_max_rps=rate_cfg.get("max_requests_per_second", 100.0),
            default_max_slow_ratio=rate_cfg.get("max_slow_ratio", 0.3),
        )

    cache_optimizer = None
    if features_cfg["cache_optimization"]:
        cache_cfg = config.get("cache", {})
        cache_optimizer = CacheOptimizer(
            min_queries_for_analysis=cache_cfg.get("min_queries", 5),
            min_savings_for_recommendation_ms=cache_cfg.get("min_savings_ms", 100.0),
        )

    monitor = SlowQueryMonitor(
        collector=collector,
        analyzer=analyzer,
        rule_engine=rule_engine,
        alerter=alerter,
        config=config,
        dry_run_engine=dry_run_engine if args.dry_run else None,
        trend_predictor=trend_predictor,
        rate_limiter=rate_limiter,
        cache_optimizer=cache_optimizer,
    )

    if args.once or args.dry_run:
        monitor.run_once()
    else:
        monitor.run_loop()


if __name__ == "__main__":
    main()
