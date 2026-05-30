import argparse
import json
import sys
import logging
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_fragmentation(args):
    from memory_analyzer import MemoryAnalyzer
    from redis_connection import RedisConnectionManager
    
    logger.info("Checking Redis memory fragmentation...")
    
    try:
        connection_manager = RedisConnectionManager()
        analyzer = MemoryAnalyzer(connection_manager)
        
        all_memory_info = analyzer.get_all_memory_info()
        summary = analyzer.get_cluster_fragmentation_summary()
        
        print("\n" + "="*80)
        print("Redis Memory Fragmentation Summary")
        print("="*80)
        print(f"Total Nodes: {summary.get('node_count', 0)}")
        print(f"Average Fragmentation Ratio: {summary.get('avg_fragmentation_ratio', 0):.2f}")
        print(f"Max Fragmentation Ratio: {summary.get('max_fragmentation_ratio', 0):.2f}")
        print(f"Total Used Memory: {summary.get('total_used_memory_mb', 0):.2f} MB")
        print(f"Total RSS Memory: {summary.get('total_rss_memory_mb', 0):.2f} MB")
        print(f"Total Fragmentation: {summary.get('total_fragmentation_mb', 0):.2f} MB")
        print(f"Nodes with High Fragmentation (>=1.5): {summary.get('high_fragmentation_count', 0)}")
        print("\nNode Details:")
        print("-"*80)
        print(f"{'Node':<25} {'Ratio':>8} {'Status':>8} {'Used(MB)':>10} {'Frag(MB)':>10} {'P99(ms)':>10} {'QPS':>8}")
        print("-"*80)
        
        for mem_info in all_memory_info:
            status = "HIGH" if mem_info.mem_fragmentation_ratio >= 1.5 else "NORMAL"
            print(f"  {mem_info.host}:{mem_info.port:<5} "
                  f"{mem_info.mem_fragmentation_ratio:>8.2f} "
                  f"{status:>8} "
                  f"{mem_info.used_memory_mb:>10.2f} "
                  f"{mem_info.fragmentation_mb:>10.2f} "
                  f"{mem_info.performance_metrics.p99_latency_ms:>10.2f} "
                  f"{mem_info.performance_metrics.qps:>8.0f}")
        
        print("="*80 + "\n")
        
        return 0
    except Exception as e:
        logger.error(f"Failed to check fragmentation: {e}")
        return 1


def check_versions(args):
    from memory_analyzer import MemoryAnalyzer
    from memory_defrag import MemoryDefragmenter
    from redis_connection import RedisConnectionManager
    
    logger.info("Checking Redis versions and defrag methods...")
    
    try:
        connection_manager = RedisConnectionManager()
        analyzer = MemoryAnalyzer(connection_manager)
        defragmenter = MemoryDefragmenter(connection_manager)
        
        nodes = connection_manager.get_all_nodes()
        
        print("\n" + "="*80)
        print("Redis Version & Defrag Method Check")
        print("="*80)
        print(f"{'Node':<25} {'Role':<8} {'Version':<12} {'Allocator':<12} {'Supports Purge':>14} {'Method':>20}")
        print("-"*80)
        
        for node in nodes:
            try:
                node_info = analyzer.get_node_info(node)
                method = defragmenter.determine_defrag_method(node_info)
                supports = "YES" if node_info.supports_memory_purge() else "NO"
                print(f"  {node_info.host}:{node_info.port:<5} "
                      f"{node_info.role:<8} "
                      f"{str(node_info.version):<12} "
                      f"{node_info.mem_allocator:<12} "
                      f"{supports:>14} "
                      f"{method.value:>20}")
            except Exception as e:
                print(f"  {node['host']}:{node['port']:<5} ERROR: {e}")
        
        print("="*80 + "\n")
        print("Defrag Methods:")
        print("  memory_purge          - Redis 4.0+ with jemalloc (recommended)")
        print("  slave_restart         - Restart slave node (requires orchestration)")
        print("  failover_and_restart  - Failover then restart master")
        print("")
        
        return 0
    except Exception as e:
        logger.error(f"Failed to check versions: {e}")
        return 1


def defrag_node(args):
    from memory_defrag import MemoryDefragmenter
    from redis_connection import RedisConnectionManager
    
    logger.info(f"Starting defragmentation for node: {args.node_id}")
    
    try:
        connection_manager = RedisConnectionManager()
        defragmenter = MemoryDefragmenter(connection_manager, parallel=False)
        
        result = defragmenter.defrag_node(args.node_id)
        
        print("\n" + defragmenter.compare_before_after(result))
        print("\n")
        
        return 0 if result.success else 1
    except Exception as e:
        logger.error(f"Failed to defrag node: {e}")
        return 1


def defrag_high(args):
    from memory_defrag import MemoryDefragmenter
    from redis_connection import RedisConnectionManager
    
    logger.info("Starting defragmentation for high fragmentation nodes...")
    
    try:
        connection_manager = RedisConnectionManager()
        parallel = not args.serial
        max_workers = args.workers if args.workers else 4
        
        defragmenter = MemoryDefragmenter(
            connection_manager, 
            parallel=parallel,
            max_workers=max_workers
        )
        
        threshold = args.threshold if args.threshold else None
        min_memory = args.min_memory if args.min_memory else None
        
        results = defragmenter.defrag_high_fragmentation_nodes(threshold, min_memory)
        summary = defragmenter.get_defrag_summary(results)
        
        print("\n" + "="*80)
        print("Defragmentation Summary")
        print("="*80)
        print(f"Execution Mode: {'Parallel' if parallel else 'Serial'}")
        if parallel:
            print(f"Max Workers: {max_workers}")
        print(f"Total Nodes Processed: {summary.get('total_nodes', 0)}")
        print(f"Successful: {summary.get('successful', 0)}")
        print(f"Failed: {summary.get('failed', 0)}")
        print(f"Total Memory Saved: {summary.get('total_memory_saved_mb', 0):.2f} MB")
        print(f"Average Improvement: {summary.get('average_fragmentation_improvement', 0):.2f}")
        print(f"Average P99 Latency Increase: {summary.get('average_p99_latency_increase_ms', 0):.2f} ms")
        print(f"Average QPS Drop: {summary.get('average_qps_drop_percent', 0):.1f}%")
        print(f"Total Duration: {summary.get('total_duration_seconds', 0):.2f} seconds")
        
        method_dist = summary.get('method_distribution', {})
        if method_dist:
            print(f"\nMethod Distribution:")
            for method, count in method_dist.items():
                print(f"  {method}: {count}")
        
        print("="*80 + "\n")
        
        for result in summary.get('results', []):
            if result['success']:
                print(f"  {result['host']}:{result['port']} [{result.get('method','unknown')}] - "
                      f"Saved: {result['memory_saved_mb']:.2f}MB, "
                      f"P99: {result.get('performance_impact',{}).get('p99_latency_increase_ms',0):+.2f}ms")
            else:
                print(f"  {result['host']}:{result['port']} - FAILED: {result['error_message']}")
        
        print()
        return 0
    except Exception as e:
        logger.error(f"Failed to defrag high fragmentation nodes: {e}")
        return 1


def defrag_all(args):
    from memory_defrag import MemoryDefragmenter
    from redis_connection import RedisConnectionManager
    
    logger.info("Starting defragmentation for all nodes...")
    
    try:
        connection_manager = RedisConnectionManager()
        parallel = not args.serial
        max_workers = args.workers if args.workers else 4
        
        defragmenter = MemoryDefragmenter(
            connection_manager, 
            parallel=parallel,
            max_workers=max_workers
        )
        
        results = defragmenter.defrag_all_nodes()
        summary = defragmenter.get_defrag_summary(results)
        
        print("\n" + "="*80)
        print("Defragmentation All Nodes Summary")
        print("="*80)
        print(f"Execution Mode: {'Parallel' if parallel else 'Serial'}")
        print(f"Total Nodes Processed: {summary.get('total_nodes', 0)}")
        print(f"Successful: {summary.get('successful', 0)}")
        print(f"Failed: {summary.get('failed', 0)}")
        print(f"Total Memory Saved: {summary.get('total_memory_saved_mb', 0):.2f} MB")
        print(f"Average Improvement: {summary.get('average_fragmentation_improvement', 0):.2f}")
        print(f"Average P99 Latency Increase: {summary.get('average_p99_latency_increase_ms', 0):.2f} ms")
        print("="*80 + "\n")
        
        return 0
    except Exception as e:
        logger.error(f"Failed to defrag all nodes: {e}")
        return 1


def analyze_fragmentation_causes(args):
    from memory_analyzer import MemoryAnalyzer
    from redis_connection import RedisConnectionManager
    
    logger.info("Analyzing fragmentation causes...")
    
    try:
        connection_manager = RedisConnectionManager()
        analyzer = MemoryAnalyzer(connection_manager)
        
        analyses = analyzer.analyze_all_fragmentation_causes()
        
        print("\n" + "="*90)
        print("Fragmentation Cause Analysis")
        print("="*90)
        print(f"Nodes with Fragmentation (>=1.3): {len(analyses)}")
        print()
        
        for analysis in analyses:
            print("-"*90)
            print(f"Node: {analysis.host}:{analysis.port}")
            print(f"Primary Causes: {', '.join([c.value for c in analysis.primary_causes])}")
            print()
            print("Cause Confidence:")
            for cause, conf in sorted(analysis.cause_confidence.items(), key=lambda x: x[1], reverse=True):
                if conf >= 0.3:
                    bar = "█" * int(conf * 30)
                    print(f"  {cause.value:<25} {conf*100:>6.1f}% {bar}")
            print()
            print("Keyspace Stats:")
            ks = analysis.keyspace_stats
            print(f"  Total Keys: {ks.total_keys:,}, Expires: {ks.expires_keys:,} ({ks.expires_percent:.1f}%)")
            print(f"  Large Keys (>1MB): {ks.large_keys_count}, Avg TTL: {ks.avg_ttl_seconds/3600:.1f}h")
            print()
            print("Command Stats:")
            cs = analysis.command_stats
            print(f"  Delete: {cs.delete_percent:.1f}%, Expire: {cs.expire_percent:.1f}%, Write/Read: {cs.write_to_read_ratio:.2f}")
            print()
            print("Recommendations:")
            for i, rec in enumerate(analysis.recommendations, 1):
                print(f"  {i}. {rec}")
            print()
        
        if not analyses:
            print("No nodes with significant fragmentation found.")
        
        print("="*90 + "\n")
        
        return 0
    except Exception as e:
        logger.error(f"Failed to analyze fragmentation causes: {e}")
        return 1


def predict_fragmentation(args):
    from fragmentation_predictor import FragmentationPredictor
    
    logger.info("Predicting fragmentation...")
    
    try:
        predictor = FragmentationPredictor()
        hours = args.hours if args.hours else 24
        threshold = args.threshold if args.threshold else 1.5
        
        predictions = predictor.predict_all_nodes(hours=hours, threshold=threshold)
        
        print("\n" + "="*100)
        print(f"Fragmentation Prediction (Next {hours} hours)")
        print("="*100)
        print(f"{'Node':<25} {'Current':>10} {'Predicted':>10} {'Trend':>10} {'Will Exceed':>12} {'Hours to':>12} {'Conf':>8}")
        print("-"*100)
        
        nodes_needing_defrag = []
        
        for p in predictions:
            trend_icon = "↑" if p.trend_direction == "increasing" else "↓" if p.trend_direction == "decreasing" else "→"
            will_exceed = "YES" if p.will_exceed_threshold else "NO"
            hours_to = f"{p.hours_to_threshold:.1f}h" if p.hours_to_threshold else "-"
            conf = f"{p.confidence_score*100:.0f}%"
            
            if p.will_exceed_threshold:
                nodes_needing_defrag.append(p)
                highlight = "*"
            else:
                highlight = " "
            
            print(f"{highlight}{p.host}:{p.port:<5} "
                  f"{p.current_fragmentation_ratio:>10.2f} "
                  f"{p.predicted_fragmentation_ratio:>10.2f} "
                  f"{trend_icon:>10} "
                  f"{will_exceed:>12} "
                  f"{hours_to:>12} "
                  f"{conf:>8}")
        
        print("-"*100)
        print(f"* = Node will exceed threshold of {threshold}")
        print()
        
        if nodes_needing_defrag:
            print(f"Nodes needing predictive defragmentation: {len(nodes_needing_defrag)}")
            for p in nodes_needing_defrag:
                print(f"  - {p.host}:{p.port} (predicted {p.predicted_fragmentation_ratio:.2f} in ~{p.hours_to_threshold:.1f}h)")
        else:
            print("No nodes need predictive defragmentation.")
        
        print("="*100 + "\n")
        
        return 0
    except Exception as e:
        logger.error(f"Failed to predict fragmentation: {e}")
        return 1


def analyze_cost_benefit(args):
    from fragmentation_predictor import CostBenefitAnalyzer
    
    logger.info("Analyzing cost/benefit...")
    
    try:
        analyzer = CostBenefitAnalyzer()
        analyses = analyzer.analyze_all_nodes()
        priority_list = analyzer.get_priority_defrag_list()
        
        print("\n" + "="*100)
        print("Cost/Benefit Analysis")
        print("="*100)
        print(f"{'Node':<25} {'Frag(MB)':>10} {'Save(MB)':>10} {'Duration':>10} {'CPU%':>8} {'P99+ms':>8} {'B/C Ratio':>10} {'Priority':>10}")
        print("-"*100)
        
        for a in sorted(analyses, key=lambda x: x.priority_score, reverse=True):
            priority = f"{a.priority_score:>10.1f}" if a.should_defrag else "         -"
            print(f"{a.host}:{a.port:<5} "
                  f"{a.estimated_memory_saved_mb/0.6:>10.1f} "
                  f"{a.estimated_memory_saved_mb:>10.1f} "
                  f"{a.estimated_duration_seconds:>9.1f}s "
                  f"{a.estimated_cpu_usage_percent:>7.1f}% "
                  f"{a.estimated_p99_latency_increase_ms:>7.1f} "
                  f"{a.benefit_cost_ratio:>9.2f} "
                  f"{priority}")
        
        print("-"*100)
        print()
        
        if priority_list:
            print("Recommended Priority Defragmentation Order:")
            for i, a in enumerate(priority_list, 1):
                print(f"  {i}. {a.host}:{a.port} - {a.recommendation} (score: {a.priority_score:.1f})")
        else:
            print("No nodes recommended for defragmentation based on cost/benefit analysis.")
        
        print()
        print("="*100 + "\n")
        
        return 0
    except Exception as e:
        logger.error(f"Failed to analyze cost/benefit: {e}")
        return 1


def predictive_defrag(args):
    from fragmentation_predictor import FragmentationPredictor, CostBenefitAnalyzer
    from memory_defrag import MemoryDefragmenter
    from redis_connection import RedisConnectionManager
    
    logger.info("Starting predictive defragmentation...")
    
    try:
        predictor = FragmentationPredictor()
        cost_analyzer = CostBenefitAnalyzer()
        
        hours = args.hours if args.hours else 24
        threshold = args.threshold if args.threshold else 1.5
        parallel = not args.serial
        max_workers = args.workers if args.workers else 4
        
        predictions = predictor.get_nodes_needing_defrag(hours=hours, threshold=threshold)
        
        if not predictions:
            print("No nodes need predictive defragmentation.")
            return 0
        
        print(f"\nFound {len(predictions)} nodes needing predictive defragmentation:")
        for p in predictions:
            print(f"  {p.host}:{p.port} - {p.predicted_fragmentation_ratio:.2f} in ~{p.hours_to_threshold:.1f}h")
        
        if args.dry_run:
            print("\nDry run mode enabled. No defragmentation will be performed.")
            return 0
        
        connection_manager = RedisConnectionManager()
        defragmenter = MemoryDefragmenter(
            connection_manager,
            parallel=parallel,
            max_workers=max_workers
        )
        
        node_ids = [p.node_id for p in predictions]
        results = defragmenter.defrag_nodes(node_ids)
        summary = defragmenter.get_defrag_summary(results)
        
        print("\n" + "="*80)
        print("Predictive Defragmentation Complete")
        print("="*80)
        print(f"Nodes Processed: {summary.get('total_nodes', 0)}")
        print(f"Successful: {summary.get('successful', 0)}")
        print(f"Failed: {summary.get('failed', 0)}")
        print(f"Total Memory Saved: {summary.get('total_memory_saved_mb', 0):.2f} MB")
        print(f"Mode: {'Parallel' if parallel else 'Serial'}")
        print("="*80 + "\n")
        
        return 0
    except Exception as e:
        logger.error(f"Failed to perform predictive defragmentation: {e}")
        return 1


def show_statistics(args):
    from statistics_analyzer import StatisticsAnalyzer
    from memory_analyzer import MemoryAnalyzer
    from redis_connection import RedisConnectionManager
    
    logger.info("Generating statistics report...")
    
    try:
        connection_manager = RedisConnectionManager()
        analyzer = MemoryAnalyzer(connection_manager)
        stats_analyzer = StatisticsAnalyzer()
        
        all_memory_info = analyzer.get_all_memory_info()
        node_ids = [m.node_id for m in all_memory_info]
        
        hours = args.hours if args.hours else 24
        
        stats = stats_analyzer.get_cluster_statistics(node_ids, hours)
        effectiveness = stats_analyzer.get_defrag_effectiveness(limit=20)
        
        print("\n" + "="*60)
        print(f"Cluster Statistics (Last {hours} hours)")
        print("="*60)
        print(f"Nodes Analyzed: {stats.get('node_count', 0)}")
        print(f"Average Fragmentation: {stats.get('avg_cluster_fragmentation', 0):.2f}")
        print(f"Max Fragmentation: {stats.get('max_cluster_fragmentation', 0):.2f}")
        print(f"Nodes Above Threshold (>=1.5): {stats.get('nodes_above_threshold', 0)}")
        print(f"Nodes with Increasing Trend: {stats.get('nodes_with_increasing_trend', 0)}")
        
        print("\nDefrag Effectiveness:")
        print(f"  Total Defrags: {effectiveness.get('total_defrags', 0)}")
        print(f"  Success Rate: {effectiveness.get('success_rate', 0)*100:.1f}%")
        print(f"  Avg Memory Saved: {effectiveness.get('average_memory_saved_mb', 0):.2f} MB")
        print(f"  Total Memory Saved: {effectiveness.get('total_memory_saved_mb', 0):.2f} MB")
        
        print("\nNode Statistics:")
        print("-"*60)
        for node_stat in stats.get('node_statistics', []):
            trend = node_stat.get('trend_direction', 'unknown')
            trend_icon = {
                'increasing': '↑',
                'decreasing': '↓',
                'stable': '→',
                'insufficient_data': '?'
            }.get(trend, '?')
            
            print(f"  {node_stat.get('node_id', 'unknown')[:8]}... - "
                  f"Avg: {node_stat.get('avg_fragmentation', 0):.2f}, "
                  f"Current: {node_stat.get('current_fragmentation', 0):.2f} "
                  f"{trend_icon}")
        
        print("="*60 + "\n")
        
        return 0
    except Exception as e:
        logger.error(f"Failed to generate statistics: {e}")
        return 1


def run_worker(args):
    import subprocess
    import sys
    
    cmd = [sys.executable, '-m', 'celery', '-A', 'celery_config', 'worker', '--loglevel=info']
    
    if args.concurrency:
        cmd.extend(['--concurrency', str(args.concurrency)])
    
    logger.info(f"Starting Celery worker: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        return 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Celery worker failed: {e}")
        return 1


def run_beat(args):
    import subprocess
    import sys
    
    cmd = [sys.executable, '-m', 'celery', '-A', 'celery_config', 'beat', '--loglevel=info']
    
    logger.info(f"Starting Celery beat scheduler: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        return 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Celery beat failed: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Redis Memory Fragmentation Management Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py check
  python main.py check-versions
  python main.py analyze-causes
  python main.py predict --hours 24
  python main.py analyze-cost
  python main.py predictive-defrag --hours 24
  python main.py defrag-high --workers 4
  python main.py defrag-high --serial
  python main.py defrag-node --node-id standalone
  python main.py defrag-all
  python main.py stats --hours 24
  python main.py worker
  python main.py beat
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    check_parser = subparsers.add_parser('check', help='Check memory fragmentation')
    check_parser.set_defaults(func=check_fragmentation)
    
    versions_parser = subparsers.add_parser('check-versions', help='Check Redis versions and defrag methods')
    versions_parser.set_defaults(func=check_versions)
    
    analyze_causes_parser = subparsers.add_parser('analyze-causes', help='Analyze fragmentation causes')
    analyze_causes_parser.set_defaults(func=analyze_fragmentation_causes)
    
    predict_parser = subparsers.add_parser('predict', help='Predict fragmentation trends')
    predict_parser.add_argument('--hours', type=int, default=24, help='Hours to predict ahead')
    predict_parser.add_argument('--threshold', type=float, default=1.5, help='Fragmentation threshold')
    predict_parser.set_defaults(func=predict_fragmentation)
    
    analyze_cost_parser = subparsers.add_parser('analyze-cost', help='Analyze cost/benefit of defragmentation')
    analyze_cost_parser.set_defaults(func=analyze_cost_benefit)
    
    predictive_defrag_parser = subparsers.add_parser('predictive-defrag', help='Predictive defragmentation')
    predictive_defrag_parser.add_argument('--hours', type=int, default=24, help='Hours to predict ahead')
    predictive_defrag_parser.add_argument('--threshold', type=float, default=1.5, help='Fragmentation threshold')
    predictive_defrag_parser.add_argument('--serial', action='store_true', help='Run in serial mode')
    predictive_defrag_parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    predictive_defrag_parser.add_argument('--dry-run', action='store_true', help='Show nodes without defragging')
    predictive_defrag_parser.set_defaults(func=predictive_defrag)
    
    defrag_high_parser = subparsers.add_parser('defrag-high', help='Defrag high fragmentation nodes')
    defrag_high_parser.add_argument('--threshold', type=float, help='Fragmentation threshold')
    defrag_high_parser.add_argument('--min-memory', type=float, help='Minimum memory in MB to consider')
    defrag_high_parser.add_argument('--serial', action='store_true', help='Run in serial mode (default: parallel)')
    defrag_high_parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    defrag_high_parser.set_defaults(func=defrag_high)
    
    defrag_node_parser = subparsers.add_parser('defrag-node', help='Defrag a specific node')
    defrag_node_parser.add_argument('--node-id', required=True, help='Node ID')
    defrag_node_parser.set_defaults(func=defrag_node)
    
    defrag_all_parser = subparsers.add_parser('defrag-all', help='Defrag all nodes')
    defrag_all_parser.add_argument('--serial', action='store_true', help='Run in serial mode (default: parallel)')
    defrag_all_parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    defrag_all_parser.set_defaults(func=defrag_all)
    
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    stats_parser.add_argument('--hours', type=int, default=24, help='Hours of history to analyze')
    stats_parser.set_defaults(func=show_statistics)
    
    worker_parser = subparsers.add_parser('worker', help='Start Celery worker')
    worker_parser.add_argument('--concurrency', type=int, help='Number of worker processes')
    worker_parser.set_defaults(func=run_worker)
    
    beat_parser = subparsers.add_parser('beat', help='Start Celery beat scheduler')
    beat_parser.set_defaults(func=run_beat)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
