#!/usr/bin/env python3
import argparse
import sys
import os
import signal
import threading
import time
import logging
from pathlib import Path

from log_parser import LogParser
from stats import StatisticsCollector
from reporter import HTMLReporter
from alerter import AlertManager, AlertConfig, AlertThresholds, DingtalkConfig

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

STOP_EVENT = threading.Event()

def load_config(config_path: str = None) -> dict:
    default_config = {
        "alert": {
            "enabled": True,
            "window_seconds": 60,
            "min_requests": 10,
            "thresholds": {
                "error_rate": 5.0,
                "five_hundred_rate": 1.0,
                "four_hundred_rate": 20.0,
                "qps_spike": 2.0
            },
            "cooldown_seconds": 300
        },
        "dingtalk": {
            "webhook": "",
            "secret": "",
            "at_mobiles": [],
            "at_all": False
        },
        "stats": {
            "top_n": 10,
            "history_keep_seconds": 3600
        },
        "logging": {
            "level": "INFO",
            "file": ""
        }
    }
    
    if config_path and os.path.exists(config_path):
        if not HAS_YAML:
            print("警告: PyYAML 未安装，使用默认配置")
            return default_config
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f) or {}
                for key, value in user_config.items():
                    if key in default_config:
                        if isinstance(value, dict) and isinstance(default_config[key], dict):
                            default_config[key].update(value)
                        else:
                            default_config[key] = value
            return default_config
        except Exception as e:
            print(f"警告: 配置文件加载失败，使用默认配置: {e}")
    
    return default_config

def setup_logging(log_config: dict):
    level = getattr(logging, log_config.get("level", "INFO").upper(), logging.INFO)
    log_file = log_config.get("file", "")
    
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def parse_args():
    parser = argparse.ArgumentParser(
        description="Nginx 日志分析工具 - 处理多 GB 级别的 Nginx 日志文件，支持实时监控和报警",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python cli.py access.log
  python cli.py access.log --follow
  python cli.py access.log --follow --from-beginning
  python cli.py access.log --follow --config config.yaml
  python cli.py access.log --format common --output report.html
  python cli.py access.log --top 20 --json
        """
    )
    
    parser.add_argument(
        "log_file",
        help="Nginx 日志文件路径"
    )
    
    parser.add_argument(
        "--follow", "-F",
        action="store_true",
        help="实时 tail 模式 (类似 tail -f)"
    )
    
    parser.add_argument(
        "--from-beginning", "-b",
        action="store_true",
        help="实时模式下从文件开头开始读取 (默认从末尾)"
    )
    
    parser.add_argument(
        "--config", "-c",
        default=None,
        help="配置文件路径 (默认: config.yaml)"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["combined", "common"],
        default="combined",
        help="Nginx 日志格式 (默认: combined)"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="report.html",
        help="HTML 报告输出路径 (默认: report.html)"
    )
    
    parser.add_argument(
        "--top", "-t",
        type=int,
        default=10,
        help="显示前 N 条记录 (默认: 10)"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="同时输出 JSON 格式的统计数据"
    )
    
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="不生成 HTML 报告"
    )
    
    parser.add_argument(
        "--no-alert",
        action="store_true",
        help="禁用报警功能"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细处理信息"
    )
    
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.5,
        help="实时模式轮询间隔秒数 (默认: 0.5)"
    )
    
    parser.add_argument(
        "--stats-interval",
        type=int,
        default=10,
        help="实时模式下打印统计信息的间隔秒数 (默认: 10)"
    )
    
    return parser.parse_args()

def signal_handler(signum, frame):
    print("\n正在停止...")
    STOP_EVENT.set()

def print_progress(current: int, total: int = None):
    if total:
        percent = (current / total) * 100
        sys.stdout.write(f"\r处理中: {current:,} 条记录 ({percent:.1f}%)")
    else:
        sys.stdout.write(f"\r处理中: {current:,} 条记录")
    sys.stdout.flush()

def print_realtime_stats(collector: StatisticsCollector, alert_manager: AlertManager, record_count: int):
    window_stats = collector.get_window_stats()
    qps = collector.get_qps()
    
    print(f"\n{'='*60}")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"总处理记录数: {record_count:,}")
    print(f"当前 QPS: {qps:.2f}")
    print(f"\n滑动窗口统计 ({window_stats.total_requests} 条记录):")
    print(f"  错误率: {window_stats.error_rate():.2f}%")
    print(f"  5xx 率: {window_stats.five_hundred_rate():.2f}%")
    print(f"  4xx 率: {window_stats.four_hundred_rate():.2f}%")
    print(f"  2xx: {window_stats.total_2xx}, 3xx: {window_stats.total_3xx}")
    print(f"  4xx: {window_stats.total_4xx}, 5xx: {window_stats.total_5xx}")
    
    top_ips = collector.get_top_ips(5)
    if top_ips:
        print(f"\nTop 5 IP:")
        for i, (ip, count) in enumerate(top_ips, 1):
            print(f"  {i}. {ip}: {count}")
    
    cooldown = alert_manager.get_cooldown_status()
    if cooldown:
        print(f"\n冷却状态:")
        for alert_type, status in cooldown.items():
            remaining = status['cooldown_remaining_seconds']
            if remaining > 0:
                print(f"  {alert_type}: 冷却中 ({remaining}s)")
    
    print(f"{'='*60}\n")

def run_batch_mode(args, config):
    log_file = args.log_file
    
    if not os.path.exists(log_file):
        print(f"错误: 日志文件不存在: {log_file}")
        sys.exit(1)
    
    print(f"开始分析日志文件: {log_file}")
    print(f"日志格式: {args.format}")
    print("-" * 50)
    
    try:
        parser = LogParser(log_format=args.format)
        collector = StatisticsCollector(
            top_n=args.top,
            window_seconds=config["alert"]["window_seconds"]
        )
        
        record_count = 0
        for record in parser.parse_file(log_file):
            collector._process_record(record)
            record_count += 1
            if args.verbose and record_count % 10000 == 0:
                print_progress(record_count)
        
        if args.verbose:
            print_progress(record_count)
            print()
        
        stats = collector.stats
        
        print("-" * 50)
        print("分析完成!")
        print("-" * 50)
        print(f"总请求数: {stats.total_requests:,}")
        print(f"总带宽: {stats.total_bytes:,} 字节 ({stats.total_bytes / (1024*1024):.2f} MB)")
        print(f"唯一 IP 数: {len(stats.ips):,}")
        
        status_summary = collector.get_status_code_summary()
        print("\n状态码分布:")
        for category, count in status_summary.items():
            if count > 0:
                print(f"  {category}: {count:,}")
        
        print(f"\nTop {args.top} IP 地址:")
        for i, (ip, count) in enumerate(collector.get_top_ips(args.top), 1):
            print(f"  {i}. {ip}: {count:,}")
        
        if args.json:
            import json
            json_path = Path(args.output).with_suffix('.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(stats.to_dict(), f, ensure_ascii=False, indent=2)
            print(f"\nJSON 数据已保存: {json_path}")
        
        if not args.no_html:
            reporter = HTMLReporter(collector, top_n=args.top)
            reporter.generate(args.output)
        
        print("-" * 50)
        print("分析完成!")
        
    except Exception as e:
        print(f"\n错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def run_follow_mode(args, config):
    log_file = args.log_file
    
    if not os.path.exists(log_file):
        print(f"错误: 日志文件不存在: {log_file}")
        sys.exit(1)
    
    alert_config = AlertConfig(
        enabled=config["alert"]["enabled"] and not args.no_alert,
        window_seconds=config["alert"]["window_seconds"],
        min_requests=config["alert"]["min_requests"],
        thresholds=AlertThresholds(
            error_rate=config["alert"]["thresholds"]["error_rate"],
            five_hundred_rate=config["alert"]["thresholds"]["five_hundred_rate"],
            four_hundred_rate=config["alert"]["thresholds"]["four_hundred_rate"],
            qps_spike=config["alert"]["thresholds"]["qps_spike"]
        ),
        cooldown_seconds=config["alert"]["cooldown_seconds"]
    )
    
    dingtalk_config = DingtalkConfig(
        webhook=config["dingtalk"]["webhook"],
        secret=config["dingtalk"]["secret"],
        at_mobiles=config["dingtalk"]["at_mobiles"],
        at_all=config["dingtalk"]["at_all"]
    )
    
    alert_manager = AlertManager(alert_config, dingtalk_config)
    
    print(f"实时监控模式启动: {log_file}")
    print(f"日志格式: {args.format}")
    print(f"从{'开头' if args.from_beginning else '末尾'}开始读取")
    print(f"报警: {'启用' if alert_config.enabled else '禁用'}")
    print(f"滑动窗口: {alert_config.window_seconds} 秒")
    print("按 Ctrl+C 停止...")
    print("-" * 60)
    
    try:
        parser = LogParser(log_format=args.format)
        collector = StatisticsCollector(
            top_n=args.top,
            window_seconds=alert_config.window_seconds
        )
        
        record_count = 0
        last_stats_time = time.time()
        
        def stop_check():
            return STOP_EVENT.is_set()
        
        for record in parser.tail_file(
            log_file,
            from_beginning=args.from_beginning,
            poll_interval=args.poll_interval,
            stop_check=stop_check
        ):
            if STOP_EVENT.is_set():
                break
            
            collector._process_record(record)
            record_count += 1
            
            if alert_config.enabled:
                window_stats = collector.get_window_stats()
                qps = collector.get_qps()
                alerts = alert_manager.check(window_stats, qps)
                
                for alert in alerts:
                    print(f"\n[ALERT] {alert['type']}: {alert}")
            
            current_time = time.time()
            if current_time - last_stats_time >= args.stats_interval:
                print_realtime_stats(collector, alert_manager, record_count)
                last_stats_time = current_time
        
        print(f"\n监控已停止，共处理 {record_count:,} 条记录")
        
        if record_count > 0:
            if args.json:
                import json
                json_path = Path(args.output).with_suffix('.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(collector.stats.to_dict(), f, ensure_ascii=False, indent=2)
                print(f"JSON 数据已保存: {json_path}")
            
            if not args.no_html:
                reporter = HTMLReporter(collector, top_n=args.top)
                reporter.generate(args.output)
        
        alert_history = alert_manager.get_alert_history()
        if alert_history:
            print(f"\n报警历史 ({len(alert_history)} 条):")
            for alert in alert_history:
                print(f"  {alert['time']} - {alert['type']}: {alert['details']}")
        
    except KeyboardInterrupt:
        print("\n监控已停止")
    except Exception as e:
        print(f"\n错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    args = parse_args()
    
    config_path = args.config or os.path.join(os.path.dirname(__file__), "config.yaml")
    config = load_config(config_path)
    
    setup_logging(config.get("logging", {}))
    
    if args.follow:
        run_follow_mode(args, config)
    else:
        run_batch_mode(args, config)

if __name__ == "__main__":
    main()
