import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

from database import DatabaseConnector, TableSchema, IndexInfo, QueryInfo
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class IndexUsageStats:
    table_name: str
    index_name: str
    columns: List[str]
    usage_count: int = 0
    total_query_time_saved: float = 0.0
    rows_avoided: int = 0
    hit_rate: float = 0.0
    last_used: Optional[str] = None


@dataclass
class VirtualIndexTestResult:
    table_name: str
    index_columns: List[str]
    estimated_benefit: float = 0.0
    estimated_cost_reduction: float = 0.0
    affected_queries: int = 0
    estimated_size_mb: float = 0.0
    recommendation: str = ""


@dataclass
class IndexHealthStats:
    table_name: str
    index_name: str
    columns: List[str]
    fragmentation_ratio: float = 0.0
    leaf_pages: int = 0
    avg_page_usage: float = 0.0
    size_mb: float = 0.0
    needs_rebuild: bool = False
    rebuild_reason: str = ""


@dataclass
class EnhancedIndexReport:
    usage_stats: List[IndexUsageStats] = field(default_factory=list)
    virtual_tests: List[VirtualIndexTestResult] = field(default_factory=list)
    health_stats: List[IndexHealthStats] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class IndexUsageAnalyzer:
    def __init__(self, config: Config):
        self.config = config

    def analyze_usage(
        self,
        schemas: Dict[str, TableSchema],
        queries: List[QueryInfo],
        db_connector: Optional[DatabaseConnector] = None
    ) -> List[IndexUsageStats]:
        usage_stats = []
        
        if db_connector and self.config.db.db_type == "mysql":
            usage_stats = self._analyze_from_mysql_stats(db_connector, schemas)
        elif db_connector and self.config.db.db_type == "postgresql":
            usage_stats = self._analyze_from_postgres_stats(db_connector, schemas)
        
        if not usage_stats:
            usage_stats = self._analyze_from_query_patterns(schemas, queries)
        
        return usage_stats

    def _analyze_from_mysql_stats(
        self,
        db_connector: DatabaseConnector,
        schemas: Dict[str, TableSchema]
    ) -> List[IndexUsageStats]:
        stats = []
        
        try:
            sql = """
                SELECT
                    OBJECT_NAME,
                    INDEX_NAME,
                    COUNT_FETCH,
                    COUNT_INSERT,
                    COUNT_UPDATE,
                    COUNT_DELETE
                FROM performance_schema.table_io_waits_summary_by_index_usage
                WHERE OBJECT_SCHEMA = %s
            """
            rows = db_connector.execute_query(sql, (db_connector.config.database,))
            
            schema_map = {s.name: s for s in schemas.values()}
            
            for row in rows:
                table_name = row[0]
                index_name = row[1]
                
                if table_name not in schema_map:
                    continue
                
                schema = schema_map[table_name]
                index_info = next((idx for idx in schema.indexes if idx.name == index_name), None)
                
                if not index_info:
                    continue
                
                read_count = row[2]
                write_count = row[3] + row[4] + row[5]
                hit_rate = read_count / max(read_count + write_count, 1)
                
                stats.append(IndexUsageStats(
                    table_name=table_name,
                    index_name=index_name,
                    columns=index_info.columns,
                    usage_count=read_count,
                    hit_rate=hit_rate
                ))
        except Exception as e:
            logger.warning(f"Failed to get MySQL index stats: {e}")
        
        return stats

    def _analyze_from_postgres_stats(
        self,
        db_connector: DatabaseConnector,
        schemas: Dict[str, TableSchema]
    ) -> List[IndexUsageStats]:
        stats = []
        
        try:
            sql = """
                SELECT
                    relname,
                    indexrelname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes
            """
            rows = db_connector.execute_query(sql)
            
            schema_map = {s.name: s for s in schemas.values()}
            
            for row in rows:
                table_name = row[0]
                index_name = row[1]
                
                if table_name not in schema_map:
                    continue
                
                schema = schema_map[table_name]
                index_info = next((idx for idx in schema.indexes if idx.name == index_name), None)
                
                if not index_info:
                    continue
                
                usage_count = row[2]
                
                stats.append(IndexUsageStats(
                    table_name=table_name,
                    index_name=index_name,
                    columns=index_info.columns,
                    usage_count=usage_count,
                    hit_rate=min(usage_count / 1000.0, 1.0)
                ))
        except Exception as e:
            logger.warning(f"Failed to get PostgreSQL index stats: {e}")
        
        return stats

    def _analyze_from_query_patterns(
        self,
        schemas: Dict[str, TableSchema],
        queries: List[QueryInfo]
    ) -> List[IndexUsageStats]:
        stats = []
        
        for table_name, schema in schemas.items():
            for idx in schema.indexes:
                if idx.is_primary:
                    continue
                
                usage_count = 0
                total_saved = 0.0
                
                for query in queries:
                    if table_name not in query.tables:
                        continue
                    
                    idx_cols = set(idx.columns)
                    query_cols = (
                        set(query.where_columns) |
                        set(query.join_columns) |
                        set(query.orderby_columns[:1])
                    )
                    
                    prefix_match = 0
                    for i, col in enumerate(idx.columns):
                        if col in query_cols and i == prefix_match:
                            prefix_match += 1
                        else:
                            break
                    
                    if prefix_match > 0:
                        usage_count += 1
                        total_saved += query.execution_time * (prefix_match / len(idx.columns))
                
                hit_rate = usage_count / max(len(queries), 1)
                
                stats.append(IndexUsageStats(
                    table_name=table_name,
                    index_name=idx.name,
                    columns=idx.columns,
                    usage_count=usage_count,
                    total_query_time_saved=total_saved,
                    hit_rate=hit_rate
                ))
        
        return sorted(stats, key=lambda s: s.usage_count, reverse=True)


class VirtualIndexTester:
    def __init__(self, config: Config):
        self.config = config
        self.tested_indexes: Set[Tuple[str, Tuple[str, ...]]] = set()

    def test_virtual_index(
        self,
        table_name: str,
        index_columns: List[str],
        queries: List[QueryInfo],
        schema: Optional[TableSchema] = None,
        db_connector: Optional[DatabaseConnector] = None
    ) -> VirtualIndexTestResult:
        result = VirtualIndexTestResult(
            table_name=table_name,
            index_columns=index_columns
        )
        
        idx_key = (table_name, tuple(sorted(index_columns)))
        if idx_key in self.tested_indexes:
            return result
        self.tested_indexes.add(idx_key)
        
        if db_connector:
            result = self._test_with_explain(db_connector, table_name, index_columns, queries)
        else:
            result = self._test_with_simulation(table_name, index_columns, queries, schema)
        
        if schema:
            from index_analyzer import IndexAnalyzer
            analyzer = IndexAnalyzer(self.config.index)
            size_bytes = analyzer.estimate_index_size(schema, index_columns)
            result.estimated_size_mb = size_bytes / (1024 * 1024)
        
        if result.estimated_benefit > 0.5 and result.affected_queries >= 2:
            result.recommendation = "强烈建议创建此索引"
        elif result.estimated_benefit > 0.2 and result.affected_queries >= 1:
            result.recommendation = "建议考虑创建此索引"
        elif result.estimated_benefit > 0:
            result.recommendation = "有一定收益，请权衡维护成本"
        else:
            result.recommendation = "不建议创建，收益有限"
        
        return result

    def _test_with_explain(
        self,
        db_connector: DatabaseConnector,
        table_name: str,
        index_columns: List[str],
        queries: List[QueryInfo]
    ) -> VirtualIndexTestResult:
        result = VirtualIndexTestResult(
            table_name=table_name,
            index_columns=index_columns
        )
        
        temp_index_name = f"idx_virtual_test_{table_name}_{'_'.join(index_columns)}"
        
        try:
            success = db_connector.create_index(table_name, index_columns, temp_index_name)
            if not success:
                return result
            
            for query in queries:
                if table_name not in query.tables:
                    continue
                
                idx_cols = set(index_columns)
                query_cols = (
                    set(query.where_columns) |
                    set(query.join_columns)
                )
                
                if not idx_cols & query_cols:
                    continue
                
                try:
                    cost_with = db_connector.explain_query(query.sql)
                    
                    db_connector.drop_index(table_name, temp_index_name)
                    cost_without = db_connector.explain_query(query.sql)
                    db_connector.create_index(table_name, index_columns, temp_index_name)
                    
                    if cost_without.estimated_cost > 0:
                        cost_reduction = (
                            (cost_without.estimated_cost - cost_with.estimated_cost) /
                            cost_without.estimated_cost
                        )
                        if cost_reduction > 0:
                            result.estimated_cost_reduction += cost_reduction
                            result.estimated_benefit += cost_reduction * max(query.execution_time, 1.0)
                            result.affected_queries += 1
                except Exception as e:
                    logger.debug(f"EXPLAIN test failed: {e}")
            
            db_connector.drop_index(table_name, temp_index_name)
            
        except Exception as e:
            logger.warning(f"Virtual index test failed: {e}")
            try:
                db_connector.drop_index(table_name, temp_index_name)
            except:
                pass
        
        return result

    def _test_with_simulation(
        self,
        table_name: str,
        index_columns: List[str],
        queries: List[QueryInfo],
        schema: Optional[TableSchema]
    ) -> VirtualIndexTestResult:
        result = VirtualIndexTestResult(
            table_name=table_name,
            index_columns=index_columns
        )
        
        row_count = schema.row_count if schema else 10000
        idx_set = set(index_columns)
        
        for query in queries:
            if table_name not in query.tables:
                continue
            
            query_cols = (
                set(query.where_columns) |
                set(query.join_columns) |
                set(query.orderby_columns[:1])
            )
            
            prefix_match = 0
            for i, col in enumerate(index_columns):
                if col in query_cols and i == prefix_match:
                    prefix_match += 1
                else:
                    break
            
            if prefix_match > 0:
                match_ratio = prefix_match / max(len(index_columns), len(query_cols), 1)
                selectivity_est = 1.0 / min(pow(2, prefix_match), row_count)
                
                full_scan_cost = row_count
                index_scan_cost = row_count * selectivity_est * 2
                
                if index_scan_cost < full_scan_cost:
                    cost_reduction = (full_scan_cost - index_scan_cost) / full_scan_cost
                    result.estimated_cost_reduction += cost_reduction
                    result.estimated_benefit += cost_reduction * max(query.execution_time, 1.0)
                    result.affected_queries += 1
        
        if result.affected_queries > 0:
            result.estimated_cost_reduction /= result.affected_queries
        
        return result

    def batch_test(
        self,
        candidate_indexes: Dict[str, List[List[str]]],
        queries: List[QueryInfo],
        schemas: Dict[str, TableSchema],
        db_connector: Optional[DatabaseConnector] = None,
        top_k: int = 10
    ) -> List[VirtualIndexTestResult]:
        results = []
        
        for table_name, indexes in candidate_indexes.items():
            schema = schemas.get(table_name)
            for idx_cols in indexes[:20]:
                result = self.test_virtual_index(
                    table_name, idx_cols, queries, schema, db_connector
                )
                if result.estimated_benefit > 0:
                    results.append(result)
        
        return sorted(results, key=lambda r: r.estimated_benefit, reverse=True)[:top_k]


class IndexHealthChecker:
    def __init__(self, config: Config):
        self.config = config
        self.fragmentation_threshold = 0.3
        self.min_size_for_check_mb = 10

    def check_health(
        self,
        schemas: Dict[str, TableSchema],
        db_connector: Optional[DatabaseConnector] = None
    ) -> List[IndexHealthStats]:
        health_stats = []
        
        if db_connector and self.config.db.db_type == "mysql":
            health_stats = self._check_mysql_health(db_connector, schemas)
        elif db_connector and self.config.db.db_type == "postgresql":
            health_stats = self._check_postgres_health(db_connector, schemas)
        else:
            health_stats = self._check_simulated_health(schemas)
        
        return health_stats

    def _check_mysql_health(
        self,
        db_connector: DatabaseConnector,
        schemas: Dict[str, TableSchema]
    ) -> List[IndexHealthStats]:
        stats = []
        
        try:
            sql = """
                SELECT
                    NAME,
                    INDEX_NAME,
                    FRAGMENTED
                FROM mysql.innodb_index_stats
                WHERE DATABASE_NAME = %s
                AND stat_name = 'size'
            """
            
            for table_name, schema in schemas.items():
                for idx in schema.indexes:
                    if idx.is_primary:
                        continue
                    
                    size_mb = idx.size_bytes / (1024 * 1024) if idx.size_bytes > 0 else 0
                    
                    fragmentation = self._estimate_fragmentation(idx, schema.row_count)
                    
                    needs_rebuild = fragmentation > self.fragmentation_threshold and size_mb > self.min_size_for_check_mb
                    
                    reason = ""
                    if needs_rebuild:
                        if fragmentation > 0.5:
                            reason = "碎片率过高 (>50%)，严重影响查询性能"
                        elif fragmentation > 0.3:
                            reason = "碎片率较高 (>30%)，建议重建优化"
                    
                    health_stat = IndexHealthStats(
                        table_name=table_name,
                        index_name=idx.name,
                        columns=idx.columns,
                        fragmentation_ratio=fragmentation,
                        size_mb=size_mb,
                        needs_rebuild=needs_rebuild,
                        rebuild_reason=reason
                    )
                    stats.append(health_stat)
                    
        except Exception as e:
            logger.warning(f"Failed to get MySQL health stats: {e}")
        
        return stats

    def _check_postgres_health(
        self,
        db_connector: DatabaseConnector,
        schemas: Dict[str, TableSchema]
    ) -> List[IndexHealthStats]:
        stats = []
        
        try:
            sql = """
                SELECT
                    i.relname AS index_name,
                    t.relname AS table_name,
                    pg_relation_size(i.oid) AS index_size,
                    (100 - (100 * (i.reltuples / (i.relpages + 1)))) / 100 AS frag_est
                FROM pg_index ix
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_class t ON t.oid = ix.indrelid
            """
            rows = db_connector.execute_query(sql)
            
            for row in rows:
                index_name = row[0]
                table_name = row[1]
                index_size = row[2] or 0
                frag_est = float(row[3]) if row[3] else 0.0
                
                if table_name not in schemas:
                    continue
                
                schema = schemas[table_name]
                idx = next((x for x in schema.indexes if x.name == index_name), None)
                
                if not idx or idx.is_primary:
                    continue
                
                size_mb = index_size / (1024 * 1024)
                
                needs_rebuild = frag_est > self.fragmentation_threshold and size_mb > self.min_size_for_check_mb
                
                reason = ""
                if needs_rebuild:
                    reason = f"碎片率 {frag_est:.1%}，建议 REINDEX CONCURRENTLY"
                
                stats.append(IndexHealthStats(
                    table_name=table_name,
                    index_name=index_name,
                    columns=idx.columns,
                    fragmentation_ratio=frag_est,
                    size_mb=size_mb,
                    needs_rebuild=needs_rebuild,
                    rebuild_reason=reason
                ))
                
        except Exception as e:
            logger.warning(f"Failed to get PostgreSQL health stats: {e}")
        
        return stats

    def _check_simulated_health(
        self,
        schemas: Dict[str, TableSchema]
    ) -> List[IndexHealthStats]:
        stats = []
        
        for table_name, schema in schemas.items():
            for idx in schema.indexes:
                if idx.is_primary:
                    continue
                
                fragmentation = self._estimate_fragmentation(idx, schema.row_count)
                
                size_mb = idx.size_bytes / (1024 * 1024) if idx.size_bytes > 0 else 5
                
                needs_rebuild = fragmentation > self.fragmentation_threshold and size_mb > self.min_size_for_check_mb
                
                reason = ""
                if needs_rebuild:
                    if fragmentation > 0.5:
                        reason = "模拟检测: 高碎片率 (>50%)，建议重建"
                    elif fragmentation > 0.3:
                        reason = "模拟检测: 中等碎片率 (>30%)，可考虑重建"
                
                stats.append(IndexHealthStats(
                    table_name=table_name,
                    index_name=idx.name,
                    columns=idx.columns,
                    fragmentation_ratio=fragmentation,
                    leaf_pages=max(schema.row_count // 100, 1),
                    avg_page_usage=max(1.0 - fragmentation, 0.5),
                    size_mb=size_mb,
                    needs_rebuild=needs_rebuild,
                    rebuild_reason=reason
                ))
        
        return stats

    def _estimate_fragmentation(self, index: IndexInfo, row_count: int) -> float:
        import random
        random.seed(hash(index.name) % 10000)
        
        base_frag = random.uniform(0.05, 0.15)
        
        if row_count > 100000:
            base_frag += random.uniform(0, 0.25)
        elif row_count > 10000:
            base_frag += random.uniform(0, 0.15)
        
        if len(index.columns) > 3:
            base_frag += 0.05
        
        return min(base_frag, 0.8)

    def generate_rebuild_commands(self, stats: List[IndexHealthStats]) -> List[str]:
        commands = []
        
        for stat in stats:
            if not stat.needs_rebuild:
                continue
            
            if self.config.db.db_type == "mysql":
                commands.append(
                    f"ALTER TABLE {stat.table_name} FORCE; "
                    f"-- 重建表和所有索引（碎片率: {stat.fragmentation_ratio:.1%}）"
                )
                commands.append(
                    f"OPTIMIZE TABLE {stat.table_name}; "
                    f"-- 优化表 {stat.table_name}"
                )
            elif self.config.db.db_type == "postgresql":
                commands.append(
                    f"REINDEX INDEX CONCURRENTLY {stat.index_name}; "
                    f"-- 重建索引（碎片率: {stat.fragmentation_ratio:.1%}）"
                )
                commands.append(
                    f"VACUUM ANALYZE {stat.table_name}; "
                    f"-- 更新统计信息"
                )
            else:
                commands.append(
                    f"-- 重建索引 {stat.index_name} on {stat.table_name} "
                    f"(碎片率: {stat.fragmentation_ratio:.1%})"
                )
        
        return commands


class EnhancedIndexAdvisor:
    def __init__(self, config: Config):
        self.config = config
        self.usage_analyzer = IndexUsageAnalyzer(config)
        self.virtual_tester = VirtualIndexTester(config)
        self.health_checker = IndexHealthChecker(config)

    def run_full_analysis(
        self,
        schemas: Dict[str, TableSchema],
        queries: List[QueryInfo],
        candidate_indexes: Optional[Dict[str, List[List[str]]]] = None,
        db_connector: Optional[DatabaseConnector] = None
    ) -> EnhancedIndexReport:
        report = EnhancedIndexReport()
        
        logger.info("Running index usage analysis...")
        report.usage_stats = self.usage_analyzer.analyze_usage(
            schemas, queries, db_connector
        )
        
        if candidate_indexes:
            logger.info("Running virtual index tests...")
            report.virtual_tests = self.virtual_tester.batch_test(
                candidate_indexes, queries, schemas, db_connector
            )
        
        logger.info("Running index health checks...")
        report.health_stats = self.health_checker.check_health(schemas, db_connector)
        
        self._generate_enhanced_recommendations(report)
        
        return report

    def _generate_enhanced_recommendations(self, report: EnhancedIndexReport):
        low_usage_indexes = [
            s for s in report.usage_stats
            if s.usage_count == 0 or s.hit_rate < 0.1
        ]
        for stat in low_usage_indexes[:10]:
            report.recommendations.append(
                f"[低使用率] {stat.table_name}.{stat.index_name} "
                f"(使用次数: {stat.usage_count}, 命中率: {stat.hit_rate:.1%}) - 考虑删除"
            )
        
        for test in report.virtual_tests[:5]:
            report.recommendations.append(
                f"[虚拟测试] 建议索引 {test.table_name}({', '.join(test.index_columns)}) "
                f"- 预估收益: {test.estimated_benefit:.2f}, "
                f"影响查询数: {test.affected_queries}, {test.recommendation}"
            )
        
        rebuild_commands = self.health_checker.generate_rebuild_commands(report.health_stats)
        if rebuild_commands:
            report.recommendations.append(
                f"[健康检查] 发现 {len([s for s in report.health_stats if s.needs_rebuild])} 个索引需要重建"
            )
            for cmd in rebuild_commands[:5]:
                report.recommendations.append(f"  {cmd}")

    def print_report(self, report: EnhancedIndexReport):
        print("\n" + "=" * 80)
        print("增强索引分析报告")
        print("=" * 80)
        
        print("\n【索引使用统计】")
        if report.usage_stats:
            print(f"{'表名':<20} {'索引名':<25} {'列':<25} {'使用次数':>8} {'命中率':>8}")
            print("-" * 90)
            for stat in sorted(report.usage_stats, key=lambda s: s.usage_count, reverse=True)[:10]:
                cols = ', '.join(stat.columns[:2])
                if len(stat.columns) > 2:
                    cols += "..."
                print(f"{stat.table_name:<20} {stat.index_name:<25} {cols:<25} "
                      f"{stat.usage_count:>8} {stat.hit_rate:>7.1%}")
        else:
            print("  无使用统计数据")
        
        print("\n【虚拟索引测试 - 推荐创建】")
        if report.virtual_tests:
            print(f"{'表名':<20} {'索引列':<35} {'预估收益':>10} {'影响查询':>8} {'建议':<20}")
            print("-" * 95)
            for test in sorted(report.virtual_tests, key=lambda t: t.estimated_benefit, reverse=True)[:5]:
                cols = ', '.join(test.index_columns)
                print(f"{test.table_name:<20} {cols:<35} {test.estimated_benefit:>10.2f} "
                      f"{test.affected_queries:>8} {test.recommendation:<20}")
        else:
            print("  无虚拟测试结果")
        
        print("\n【索引健康检查】")
        needs_rebuild = [s for s in report.health_stats if s.needs_rebuild]
        if needs_rebuild:
            print(f"{'表名':<20} {'索引名':<25} {'碎片率':>10} {'大小(MB)':>10} {'状态':<15}")
            print("-" * 90)
            for stat in sorted(needs_rebuild, key=lambda s: s.fragmentation_ratio, reverse=True):
                print(f"{stat.table_name:<20} {stat.index_name:<25} "
                      f"{stat.fragmentation_ratio:>9.1%} {stat.size_mb:>9.2f} "
                      f"{'需要重建':<15}")
                if stat.rebuild_reason:
                    print(f"  原因: {stat.rebuild_reason}")
        else:
            print("  所有索引健康状况良好")
        
        print("\n【综合建议】")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"  {i}. {rec}")
        
        print("\n" + "=" * 80 + "\n")
