import sys
import json
from pprint import pprint


def example_1_check_fragmentation():
    print("="*60)
    print("Example 1: Check Memory Fragmentation")
    print("="*60)
    
    from redis_connection import RedisConnectionManager
    from memory_analyzer import MemoryAnalyzer
    
    connection_manager = RedisConnectionManager()
    analyzer = MemoryAnalyzer(connection_manager)
    
    summary = analyzer.get_cluster_fragmentation_summary()
    pprint(summary)
    print()


def example_2_analyze_single_node():
    print("="*60)
    print("Example 2: Analyze Single Node Memory")
    print("="*60)
    
    from redis_connection import RedisConnectionManager
    from memory_analyzer import MemoryAnalyzer
    
    connection_manager = RedisConnectionManager()
    analyzer = MemoryAnalyzer(connection_manager)
    
    nodes = connection_manager.get_all_nodes()
    if nodes:
        node = nodes[0]
        mem_info = analyzer.get_node_memory_info(node)
        
        print(f"Node: {mem_info.host}:{mem_info.port}")
        print(f"  Used Memory: {mem_info.used_memory_mb:.2f} MB")
        print(f"  RSS Memory: {mem_info.used_memory_rss_mb:.2f} MB")
        print(f"  Fragmentation Ratio: {mem_info.mem_fragmentation_ratio:.2f}")
        print(f"  Fragmentation: {mem_info.fragmentation_mb:.2f} MB")
        print(f"  Is High: {analyzer.is_fragmentation_high(mem_info)}")
    print()


def example_3_defrag_node():
    print("="*60)
    print("Example 3: Defragment a Node")
    print("="*60)
    
    from redis_connection import RedisConnectionManager
    from memory_defrag import MemoryDefragmenter
    
    connection_manager = RedisConnectionManager()
    defragmenter = MemoryDefragmenter(connection_manager)
    
    nodes = connection_manager.get_all_nodes()
    if nodes:
        node = nodes[0]
        result = defragmenter.defrag_node(node['id'])
        print(defragmenter.compare_before_after(result))
    print()


def example_4_defrag_high_fragmentation():
    print("="*60)
    print("Example 4: Defrag High Fragmentation Nodes")
    print("="*60)
    
    from redis_connection import RedisConnectionManager
    from memory_defrag import MemoryDefragmenter
    
    connection_manager = RedisConnectionManager()
    defragmenter = MemoryDefragmenter(connection_manager)
    
    results = defragmenter.defrag_high_fragmentation_nodes(threshold=1.5, min_memory_mb=512)
    summary = defragmenter.get_defrag_summary(results)
    
    print(f"Total nodes: {summary['total_nodes']}")
    print(f"Successful: {summary['successful']}")
    print(f"Total memory saved: {summary['total_memory_saved_mb']:.2f} MB")
    print()


def example_5_store_and_retrieve_stats():
    print("="*60)
    print("Example 5: Store and Retrieve Statistics")
    print("="*60)
    
    from redis_connection import RedisConnectionManager
    from memory_analyzer import MemoryAnalyzer
    from statistics_analyzer import StatisticsAnalyzer
    
    connection_manager = RedisConnectionManager()
    analyzer = MemoryAnalyzer(connection_manager)
    stats_analyzer = StatisticsAnalyzer()
    
    all_memory_info = analyzer.get_all_memory_info()
    
    for mem_info in all_memory_info:
        stats_analyzer.store_memory_snapshot(mem_info)
        print(f"Stored snapshot for {mem_info.host}:{mem_info.port}")
    
    if all_memory_info:
        node_id = all_memory_info[0].node_id
        trend = stats_analyzer.get_memory_history(node_id, hours=1)
        print(f"\nHistory for node {node_id}:")
        print(f"  Data points: {len(trend.fragmentation_ratios)}")
        if trend.fragmentation_ratios:
            print(f"  Current ratio: {trend.fragmentation_ratios[-1]:.2f}")
    print()


def example_6_generate_daily_report():
    print("="*60)
    print("Example 6: Generate Daily Report")
    print("="*60)
    
    from redis_connection import RedisConnectionManager
    from memory_analyzer import MemoryAnalyzer
    from statistics_analyzer import StatisticsAnalyzer
    
    connection_manager = RedisConnectionManager()
    analyzer = MemoryAnalyzer(connection_manager)
    stats_analyzer = StatisticsAnalyzer()
    
    all_memory_info = analyzer.get_all_memory_info()
    node_ids = [m.node_id for m in all_memory_info]
    
    report = stats_analyzer.generate_daily_report(node_ids)
    
    print(f"Report Date: {report['report_date']}")
    print(f"Nodes: {report['cluster_summary'].get('node_count', 0)}")
    print(f"Avg Fragmentation: {report['cluster_summary'].get('avg_cluster_fragmentation', 0):.2f}")
    print(f"High Risk Nodes: {len(report['high_risk_nodes'])}")
    print("\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  - {rec}")
    print()


def example_7_celery_tasks():
    print("="*60)
    print("Example 7: Using Celery Tasks")
    print("="*60)
    print("To use Celery tasks, start the worker first:")
    print("  python main.py worker")
    print()
    print("Then start the scheduler:")
    print("  python main.py beat")
    print()
    print("Or trigger tasks manually:")
    print("  from tasks import check_fragmentation, defrag_high_fragmentation_nodes")
    print("  result = check_fragmentation.delay()")
    print("  print(result.get(timeout=30))")
    print()


def main():
    examples = [
        example_1_check_fragmentation,
        example_2_analyze_single_node,
        example_3_defrag_node,
        example_4_defrag_high_fragmentation,
        example_5_store_and_retrieve_stats,
        example_6_generate_daily_report,
        example_7_celery_tasks
    ]
    
    print("Redis Memory Defrag Tool - Usage Examples")
    print("="*60)
    print()
    
    if len(sys.argv) > 1:
        example_num = int(sys.argv[1])
        if 1 <= example_num <= len(examples):
            examples[example_num - 1]()
            return
    
    for i, example in enumerate(examples, 1):
        print(f"Example {i}: {example.__doc__}")
    
    print()
    print("Run with: python example_usage.py <example_number>")
    print("e.g., python example_usage.py 1")


if __name__ == '__main__':
    main()
