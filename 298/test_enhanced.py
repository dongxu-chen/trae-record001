import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import TableSchema, ColumnInfo, IndexInfo, QueryInfo
from index_enhanced import (
    IndexUsageAnalyzer,
    VirtualIndexTester,
    IndexHealthChecker,
    EnhancedIndexAdvisor
)


def test_index_usage_analysis():
    print("=" * 70)
    print("Test 1: 索引使用分析 - 命中率统计")
    print("=" * 70)
    
    config = Config()
    
    schemas = {
        'users': TableSchema(
            name='users',
            columns=[
                ColumnInfo(name='id', data_type='int', is_nullable=False, cardinality=10000),
                ColumnInfo(name='status', data_type='tinyint', is_nullable=True, cardinality=5),
                ColumnInfo(name='country', data_type='varchar(50)', is_nullable=True, cardinality=50),
                ColumnInfo(name='created_at', data_type='datetime', is_nullable=False, cardinality=9500),
            ],
            indexes=[
                IndexInfo(name='PRIMARY', columns=['id'], is_primary=True),
                IndexInfo(name='idx_status', columns=['status']),
                IndexInfo(name='idx_country', columns=['country']),
                IndexInfo(name='idx_status_country', columns=['status', 'country']),
                IndexInfo(name='idx_created', columns=['created_at']),
            ],
            row_count=10000
        )
    }
    
    queries = [
        QueryInfo(
            sql="SELECT * FROM users WHERE status = 1",
            execution_time=1.5,
            tables=['users'],
            where_columns=['status']
        ),
        QueryInfo(
            sql="SELECT * FROM users WHERE status = 1 AND country = 'CN'",
            execution_time=2.5,
            tables=['users'],
            where_columns=['status', 'country']
        ),
        QueryInfo(
            sql="SELECT * FROM users WHERE country = 'US'",
            execution_time=0.8,
            tables=['users'],
            where_columns=['country']
        ),
        QueryInfo(
            sql="SELECT * FROM users ORDER BY created_at DESC",
            execution_time=3.0,
            tables=['users'],
            orderby_columns=['created_at']
        ),
    ]
    
    analyzer = IndexUsageAnalyzer(config)
    stats = analyzer.analyze_usage(schemas, queries)
    
    print(f"\n  分析了 {len(stats)} 个索引的使用情况:")
    print(f"  {'索引名':<25} {'列':<25} {'使用次数':>10} {'命中率':>10}")
    print("-" * 75)
    
    for stat in stats:
        cols = ', '.join(stat.columns)
        print(f"  {stat.index_name:<25} {cols:<25} {stat.usage_count:>10} {stat.hit_rate:>9.1%}")
    
    high_usage = [s for s in stats if s.hit_rate >= 0.5]
    low_usage = [s for s in stats if s.hit_rate < 0.1]
    
    print(f"\n  高使用率索引 (>50%): {len(high_usage)}")
    print(f"  低使用率索引 (<10%): {len(low_usage)}")
    
    print("\n  ✓ 索引使用分析测试通过！")
    return stats


def test_virtual_index_testing():
    print("\n" + "=" * 70)
    print("Test 2: 虚拟索引测试 - 模拟评估效果")
    print("=" * 70)
    
    config = Config()
    
    schemas = {
        'orders': TableSchema(
            name='orders',
            columns=[
                ColumnInfo(name='id', data_type='int', is_nullable=False, cardinality=50000),
                ColumnInfo(name='user_id', data_type='int', is_nullable=False, cardinality=8000),
                ColumnInfo(name='product_id', data_type='int', is_nullable=False, cardinality=2000),
                ColumnInfo(name='status', data_type='varchar(20)', is_nullable=False, cardinality=8),
                ColumnInfo(name='created_at', data_type='datetime', is_nullable=False, cardinality=48000),
            ],
            indexes=[
                IndexInfo(name='PRIMARY', columns=['id'], is_primary=True),
            ],
            row_count=50000
        )
    }
    
    queries = [
        QueryInfo(
            sql="SELECT * FROM orders WHERE user_id = ? AND status = 'paid'",
            execution_time=2.0,
            rows_examined=5000,
            tables=['orders'],
            where_columns=['user_id', 'status']
        ),
        QueryInfo(
            sql="SELECT * FROM orders WHERE product_id = ? ORDER BY created_at DESC",
            execution_time=1.5,
            rows_examined=3000,
            tables=['orders'],
            where_columns=['product_id'],
            orderby_columns=['created_at']
        ),
        QueryInfo(
            sql="SELECT COUNT(*) FROM orders WHERE status = 'pending' AND created_at > ?",
            execution_time=1.0,
            rows_examined=2000,
            tables=['orders'],
            where_columns=['status', 'created_at']
        ),
    ]
    
    candidate_indexes = {
        'orders': [
            ['user_id', 'status'],
            ['product_id', 'created_at'],
            ['status', 'created_at'],
            ['user_id'],
            ['status'],
        ]
    }
    
    tester = VirtualIndexTester(config)
    
    print(f"\n  批量测试 {sum(len(v) for v in candidate_indexes.values())} 个候选索引:")
    results = tester.batch_test(candidate_indexes, queries, schemas)
    
    print(f"\n  {'索引列':<35} {'预估收益':>12} {'影响查询':>10} {'大小(MB)':>10} {'建议':<20}")
    print("-" * 95)
    
    for result in sorted(results, key=lambda r: r.estimated_benefit, reverse=True):
        cols = ', '.join(result.index_columns)
        print(f"  {cols:<35} {result.estimated_benefit:>12.2f} {result.affected_queries:>10} "
              f"{result.estimated_size_mb:>9.2f} {result.recommendation:<20}")
    
    print(f"\n  共测试 {len(results)} 个有收益的索引")
    print(f"  强烈建议: {len([r for r in results if '强烈建议' in r.recommendation])}")
    print(f"  建议考虑: {len([r for r in results if '建议考虑' in r.recommendation])}")
    
    print("\n  ✓ 虚拟索引测试通过！")
    return results


def test_index_health_check():
    print("\n" + "=" * 70)
    print("Test 3: 索引健康检查 - 碎片率检测")
    print("=" * 70)
    
    config = Config()
    
    schemas = {
        'users': TableSchema(
            name='users',
            columns=[
                ColumnInfo(name='id', data_type='int', is_nullable=False, cardinality=100000),
                ColumnInfo(name='username', data_type='varchar(50)', is_nullable=False),
                ColumnInfo(name='email', data_type='varchar(100)', is_nullable=False),
                ColumnInfo(name='status', data_type='tinyint', is_nullable=True),
            ],
            indexes=[
                IndexInfo(name='PRIMARY', columns=['id'], is_primary=True, size_bytes=8 * 1024 * 1024),
                IndexInfo(name='idx_username', columns=['username'], size_bytes=5 * 1024 * 1024),
                IndexInfo(name='idx_email', columns=['email'], size_bytes=6 * 1024 * 1024),
                IndexInfo(name='idx_status', columns=['status'], size_bytes=12 * 1024 * 1024),
            ],
            row_count=100000
        ),
        'orders': TableSchema(
            name='orders',
            columns=[
                ColumnInfo(name='id', data_type='int', is_nullable=False, cardinality=500000),
                ColumnInfo(name='user_id', data_type='int', is_nullable=False),
                ColumnInfo(name='amount', data_type='decimal', is_nullable=False),
            ],
            indexes=[
                IndexInfo(name='PRIMARY', columns=['id'], is_primary=True, size_bytes=40 * 1024 * 1024),
                IndexInfo(name='idx_user_id', columns=['user_id'], size_bytes=25 * 1024 * 1024),
            ],
            row_count=500000
        )
    }
    
    checker = IndexHealthChecker(config)
    health_stats = checker.check_health(schemas)
    
    print(f"\n  检查了 {len(health_stats)} 个索引的健康状况:")
    print(f"  {'表名':<15} {'索引名':<20} {'碎片率':>10} {'大小(MB)':>10} {'状态':<15}")
    print("-" * 80)
    
    for stat in sorted(health_stats, key=lambda s: s.fragmentation_ratio, reverse=True):
        status = "需要重建" if stat.needs_rebuild else "正常"
        print(f"  {stat.table_name:<15} {stat.index_name:<20} "
              f"{stat.fragmentation_ratio:>9.1%} {stat.size_mb:>9.2f} {status:<15}")
    
    needs_rebuild = [s for s in health_stats if s.needs_rebuild]
    print(f"\n  需要重建的索引: {len(needs_rebuild)}")
    
    if needs_rebuild:
        print("\n  重建命令建议:")
        commands = checker.generate_rebuild_commands(needs_rebuild)
        for cmd in commands[:3]:
            print(f"    {cmd}")
    
    print("\n  ✓ 索引健康检查测试通过！")
    return health_stats


def test_enhanced_advisor():
    print("\n" + "=" * 70)
    print("Test 4: 增强索引顾问 - 完整分析")
    print("=" * 70)
    
    config = Config()
    
    schemas = {
        'users': TableSchema(
            name='users',
            columns=[
                ColumnInfo(name='id', data_type='int', is_nullable=False, cardinality=50000),
                ColumnInfo(name='status', data_type='tinyint', is_nullable=True, cardinality=5),
                ColumnInfo(name='country', data_type='varchar(50)', is_nullable=True, cardinality=50),
                ColumnInfo(name='created_at', data_type='datetime', is_nullable=False, cardinality=48000),
            ],
            indexes=[
                IndexInfo(name='PRIMARY', columns=['id'], is_primary=True),
                IndexInfo(name='idx_status', columns=['status'], size_bytes=2 * 1024 * 1024),
                IndexInfo(name='idx_country', columns=['country'], size_bytes=3 * 1024 * 1024),
                IndexInfo(name='idx_created', columns=['created_at'], size_bytes=4 * 1024 * 1024),
            ],
            row_count=50000
        ),
        'orders': TableSchema(
            name='orders',
            columns=[
                ColumnInfo(name='id', data_type='int', is_nullable=False, cardinality=200000),
                ColumnInfo(name='user_id', data_type='int', is_nullable=False, cardinality=30000),
                ColumnInfo(name='product_id', data_type='int', is_nullable=False, cardinality=5000),
                ColumnInfo(name='status', data_type='varchar(20)', is_nullable=False, cardinality=8),
            ],
            indexes=[
                IndexInfo(name='PRIMARY', columns=['id'], is_primary=True),
                IndexInfo(name='idx_user_id', columns=['user_id'], size_bytes=8 * 1024 * 1024),
                IndexInfo(name='idx_status', columns=['status'], size_bytes=15 * 1024 * 1024),
            ],
            row_count=200000
        )
    }
    
    queries = [
        QueryInfo(
            sql="SELECT * FROM users WHERE status = 1 AND country = 'CN'",
            execution_time=2.5,
            rows_examined=8000,
            tables=['users'],
            where_columns=['status', 'country']
        ),
        QueryInfo(
            sql="SELECT * FROM orders WHERE user_id = ? AND status = 'paid'",
            execution_time=1.8,
            rows_examined=5000,
            tables=['orders'],
            where_columns=['user_id', 'status']
        ),
        QueryInfo(
            sql="SELECT * FROM users ORDER BY created_at DESC",
            execution_time=1.5,
            rows_examined=3000,
            tables=['users'],
            orderby_columns=['created_at']
        ),
        QueryInfo(
            sql="SELECT o.* FROM orders o JOIN users u ON o.user_id = u.id WHERE u.status = 1",
            execution_time=3.2,
            rows_examined=15000,
            tables=['orders', 'users'],
            where_columns=['status'],
            join_columns=['user_id', 'id']
        ),
    ]
    
    candidate_indexes = {
        'users': [
            ['status', 'country'],
            ['status', 'created_at'],
        ],
        'orders': [
            ['user_id', 'status'],
            ['status', 'user_id'],
        ]
    }
    
    advisor = EnhancedIndexAdvisor(config)
    report = advisor.run_full_analysis(schemas, queries, candidate_indexes)
    
    advisor.print_report(report)
    
    print("  ✓ 增强索引顾问测试通过！")
    return report


def main():
    print("\n" + "#" * 70)
    print("#  增强索引分析模块测试")
    print("#" * 70)
    
    all_passed = True
    
    try:
        test_index_usage_analysis()
    except Exception as e:
        print(f"\n  ✗ 索引使用分析测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        test_virtual_index_testing()
    except Exception as e:
        print(f"\n  ✗ 虚拟索引测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        test_index_health_check()
    except Exception as e:
        print(f"\n  ✗ 索引健康检查测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        test_enhanced_advisor()
    except Exception as e:
        print(f"\n  ✗ 增强索引顾问测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    print("\n" + "#" * 70)
    if all_passed:
        print("#  ✓ 所有增强功能测试通过！")
    else:
        print("#  ✗ 部分测试失败")
    print("#" * 70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
