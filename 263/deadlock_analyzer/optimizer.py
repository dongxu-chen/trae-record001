from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from collections import Counter
import re
from deadlock_parser import Deadlock, Transaction, Lock
from .analyzer import Statistics
from .explain_analyzer import ExplainAnalyzer, IndexRecommendation, ExplainAnalysisResult


@dataclass
class OptimizationSuggestion:
    category: str
    priority: str
    title: str
    description: str
    affected_tables: List[str] = field(default_factory=list)
    affected_sql_patterns: List[str] = field(default_factory=list)
    suggested_action: str = ""
    estimated_impact: str = ""
    index_recommendations: List[IndexRecommendation] = field(default_factory=list)
    explain_analysis: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "affected_tables": self.affected_tables,
            "affected_sql_patterns": self.affected_sql_patterns,
            "suggested_action": self.suggested_action,
            "estimated_impact": self.estimated_impact,
            "index_recommendations": [
                {
                    "table_name": rec.table_name,
                    "index_columns": rec.index_columns,
                    "index_name": rec.index_name,
                    "reason": rec.reason,
                    "estimated_benefit": rec.estimated_benefit,
                    "create_statement": rec.create_statement,
                    "sql_sample": rec.sql_sample
                }
                for rec in self.index_recommendations
            ],
            "explain_analysis": self.explain_analysis
        }


class OptimizationAdvisor:
    def __init__(self, db_type: str = 'mysql'):
        self.suggestions: List[OptimizationSuggestion] = []
        self.explain_analyzer = ExplainAnalyzer(db_type=db_type)
        self.db_type = db_type

    def analyze(self, deadlocks: List[Deadlock], statistics: Statistics,
                explain_outputs: Optional[Dict[str, str]] = None) -> List[OptimizationSuggestion]:
        self.suggestions = []

        all_sqls = self._collect_all_sqls(deadlocks)

        explain_results = []
        if all_sqls:
            explain_results = self.explain_analyzer.analyze_multiple(all_sqls, explain_outputs)

        index_recs = self.explain_analyzer.get_all_recommendations(explain_results)

        self._check_index_issues(deadlocks, statistics, index_recs, explain_results)
        self._check_transaction_order(deadlocks, statistics)
        self._check_lock_mode_issues(deadlocks, statistics)
        self._check_long_transactions(deadlocks, statistics)
        self._check_hotspot_tables(statistics)
        self._check_sql_pattern_issues(deadlocks, statistics, explain_results)

        self.suggestions.sort(key=lambda x: self._priority_score(x.priority), reverse=True)
        return self.suggestions

    def _collect_all_sqls(self, deadlocks: List[Deadlock]) -> List[str]:
        sqls = []
        seen = set()
        for deadlock in deadlocks:
            for txn in deadlock.transactions:
                for sql in txn.sql_statements:
                    normalized = sql.strip()[:200]
                    if normalized and normalized not in seen:
                        seen.add(normalized)
                        sqls.append(sql)
        return sqls

    def _priority_score(self, priority: str) -> int:
        scores = {"high": 3, "medium": 2, "low": 1}
        return scores.get(priority, 0)

    def _check_index_issues(self, deadlocks: List[Deadlock], statistics: Statistics,
                            index_recs: List[IndexRecommendation],
                            explain_results: List[ExplainAnalysisResult]):
        tables_without_index = set()
        tables_with_gap_lock = set()

        for deadlock in deadlocks:
            for txn in deadlock.transactions:
                for lock in txn.holding_locks:
                    if lock.lock_type == 'RECORD' and (not lock.index_name or lock.index_name == 'PRIMARY'):
                        if 'X' in lock.lock_mode or 'gap' in lock.lock_mode.lower():
                            tables_with_gap_lock.add(lock.table_name)
                    if not lock.index_name or lock.index_name == 'GEN_CLUST_INDEX':
                        tables_without_index.add(lock.table_name)
                if txn.waiting_lock:
                    lock = txn.waiting_lock
                    if not lock.index_name or lock.index_name == 'GEN_CLUST_INDEX':
                        tables_without_index.add(lock.table_name)

        explain_analysis_data = []
        for result in explain_results:
            if result.has_full_table_scan or not result.has_index:
                explain_analysis_data.append({
                    "sql": result.sql[:100],
                    "table_name": result.table_name,
                    "has_index": result.has_index,
                    "has_full_table_scan": result.has_full_table_scan,
                    "type": result.type,
                    "warnings": result.warnings
                })

        if tables_without_index or index_recs:
            suggestion = OptimizationSuggestion(
                category="索引优化",
                priority="high",
                title="检测到表缺少有效索引",
                description="以下表在死锁中使用了全表扫描或隐式索引，这会导致锁定过多的行，增加死锁概率。",
                affected_tables=list(tables_without_index),
                suggested_action="为经常用于WHERE条件、JOIN条件的列添加适当的索引。避免使用SELECT *，只查询需要的列。",
                estimated_impact="高 - 可以显著减少锁的范围和数量",
                index_recommendations=index_recs,
                explain_analysis=explain_analysis_data
            )
            self.suggestions.append(suggestion)

        if tables_with_gap_lock:
            self.suggestions.append(OptimizationSuggestion(
                category="索引优化",
                priority="medium",
                title="检测到间隙锁使用",
                description="以下表存在间隙锁(GAP lock)，这可能导致更大范围的锁定。",
                affected_tables=list(tables_with_gap_lock),
                suggested_action="考虑将事务隔离级别从REPEATABLE READ降低到READ COMMITTED，或者使用唯一索引来避免间隙锁。",
                estimated_impact="中 - 可以减少锁冲突范围"
            ))

    def _check_transaction_order(self, deadlocks: List[Deadlock], statistics: Statistics):
        table_access_sequences = []

        for deadlock in deadlocks:
            for txn in deadlock.transactions:
                tables = []
                for lock in txn.holding_locks:
                    if lock.table_name not in tables:
                        tables.append(lock.table_name)
                if txn.waiting_lock and txn.waiting_lock.table_name not in tables:
                    tables.append(txn.waiting_lock.table_name)
                if len(tables) >= 2:
                    table_access_sequences.append(tuple(tables))

        conflicting_orders = []
        for i, seq1 in enumerate(table_access_sequences):
            for seq2 in table_access_sequences[i + 1:]:
                if len(seq1) >= 2 and len(seq2) >= 2:
                    if seq1[0] == seq2[1] and seq1[1] == seq2[0]:
                        conflicting_orders.append((seq1, seq2))

        if conflicting_orders:
            affected_tables = set()
            for seq1, seq2 in conflicting_orders:
                affected_tables.update(seq1)
                affected_tables.update(seq2)

            suggested_order = sorted(affected_tables)

            self.suggestions.append(OptimizationSuggestion(
                category="事务顺序",
                priority="high",
                title="检测到不一致的表访问顺序",
                description=f"不同事务以相反的顺序访问相同的表，这是导致死锁的最常见原因。\n检测到的冲突顺序:\n" +
                            "\n".join([f"  事务1: {' → '.join(s1)}\n  事务2: {' → '.join(s2)}" for s1, s2 in conflicting_orders[:3]]),
                affected_tables=list(affected_tables),
                suggested_action=f"统一所有事务的表访问顺序，例如按以下顺序访问表: {' → '.join(suggested_order)}。\n可以使用死锁回放模拟功能验证修改后的效果。",
                estimated_impact="高 - 可以消除大部分由顺序问题导致的死锁"
            ))

    def _check_lock_mode_issues(self, deadlocks: List[Deadlock], statistics: Statistics):
        exclusive_lock_count = 0
        shared_lock_count = 0
        intention_lock_count = 0

        for mode, count in statistics.lock_mode_stats.items():
            mode_upper = mode.upper()
            if 'X' in mode_upper:
                exclusive_lock_count += count
            elif 'S' in mode_upper and 'X' not in mode_upper:
                shared_lock_count += count
            if 'IX' in mode_upper or 'IS' in mode_upper:
                intention_lock_count += count

        if exclusive_lock_count > 0 and exclusive_lock_count > shared_lock_count * 2:
            self.suggestions.append(OptimizationSuggestion(
                category="锁模式优化",
                priority="medium",
                title="排他锁使用过多",
                description=f"检测到 {exclusive_lock_count} 个排他锁，远多于共享锁 ({shared_lock_count})。",
                suggested_action="1. 考虑使用SELECT ... FOR SKIP LOCKED或NOWAIT来避免等待\n2. 将不需要严格一致性的读操作改为快照读\n3. 避免在事务中执行长时间的计算\n4. 对于MySQL 8.0+可以考虑使用NOWAIT和SKIP LOCKED语法",
                estimated_impact="中 - 可以减少锁冲突"
            ))

    def _check_long_transactions(self, deadlocks: List[Deadlock], statistics: Statistics):
        long_wait_txns = []
        for deadlock in deadlocks:
            for txn in deadlock.transactions:
                if txn.wait_time is not None and txn.wait_time >= 5:
                    long_wait_txns.append(txn)

        if long_wait_txns or statistics.average_wait_time > 3:
            affected_sqls = []
            for txn in long_wait_txns[:5]:
                affected_sqls.extend(txn.sql_statements)

            self.suggestions.append(OptimizationSuggestion(
                category="事务性能",
                priority="high" if statistics.average_wait_time > 5 else "medium",
                title="检测到长事务或长时间锁等待",
                description=f"平均等待时间: {statistics.average_wait_time:.2f}秒，有 {len(long_wait_txns)} 个事务等待时间超过5秒。",
                affected_sql_patterns=list(set(affected_sqls))[:10],
                suggested_action="1. 缩小事务范围，只在必要时才开启事务\n2. 避免在事务中进行外部API调用或耗时计算\n3. 将大事务拆分为多个小事务\n4. 适当调整innodb_lock_wait_timeout参数\n5. 可以使用实时监控功能提前发现长事务",
                estimated_impact="高 - 可以显著减少锁持有时间"
            ))

    def _check_hotspot_tables(self, statistics: Statistics):
        if not statistics.table_stats:
            return

        top_tables = statistics.table_stats.most_common(3)
        total_deadlocks = statistics.total_deadlocks

        hotspot_tables = []
        for table, count in top_tables:
            if total_deadlocks > 0 and count / total_deadlocks > 0.3:
                hotspot_tables.append((table, count))

        if hotspot_tables:
            tables = [t[0] for t in hotspot_tables]
            table_details = "\n".join([f"  {table}: {count}次死锁 ({count/total_deadlocks*100:.1f}%)" for table, count in hotspot_tables])

            self.suggestions.append(OptimizationSuggestion(
                category="热点优化",
                priority="high",
                title="检测到热点表",
                description=f"以下表参与了超过30%的死锁事件，可能是系统中的热点表。\n{table_details}",
                affected_tables=tables,
                suggested_action="1. 考虑对热点表进行水平分库分表\n2. 引入缓存层(Redis)减少数据库访问\n3. 优化针对这些表的SQL语句\n4. 考虑使用队列来串行化对热点表的访问\n5. 使用实时监控功能关注热点表的锁等待情况",
                estimated_impact="中到高 - 取决于具体优化方案"
            ))

    def _check_sql_pattern_issues(self, deadlocks: List[Deadlock], statistics: Statistics,
                                  explain_results: List[ExplainAnalysisResult]):
        problematic_patterns = []

        for pattern, count in statistics.sql_pattern_stats.most_common(10):
            if count >= 2:
                pattern_lower = pattern.lower()

                issues = []
                if 'update' in pattern_lower and 'where' not in pattern_lower:
                    issues.append("UPDATE语句缺少WHERE条件")
                if 'delete' in pattern_lower and 'where' not in pattern_lower:
                    issues.append("DELETE语句缺少WHERE条件")
                if 'select ... for update' in pattern_lower:
                    issues.append("使用了SELECT ... FOR UPDATE，注意锁范围")
                if 'order by' in pattern_lower and 'limit' not in pattern_lower:
                    issues.append("ORDER BY可能导致额外的锁")
                if re.search(r'join\s+\w+', pattern_lower) and not re.search(r'on\s+\w+', pattern_lower):
                    issues.append("JOIN缺少ON条件，可能导致笛卡尔积")

                if issues:
                    problematic_patterns.append({
                        "pattern": pattern,
                        "count": count,
                        "issues": issues
                    })

        sql_without_index = []
        for result in explain_results:
            if not result.has_index and result.has_full_table_scan:
                sql_without_index.append({
                    "sql": result.sql[:100],
                    "table": result.table_name,
                    "warnings": result.warnings
                })

        if problematic_patterns or sql_without_index:
            patterns = [p["pattern"] for p in problematic_patterns[:5]]
            descriptions = []
            for p in problematic_patterns[:5]:
                descriptions.append(f"SQL模式(出现{p['count']}次): {'; '.join(p['issues'])}")

            if sql_without_index:
                descriptions.append(f"\n{len(sql_without_index)}条SQL存在全表扫描:")
                for item in sql_without_index[:3]:
                    descriptions.append(f"  - {item['sql']}")

            self.suggestions.append(OptimizationSuggestion(
                category="SQL优化",
                priority="high",
                title="检测到有问题的SQL模式",
                description="\n".join(descriptions),
                affected_sql_patterns=patterns,
                suggested_action="1. 为所有UPDATE/DELETE添加明确的WHERE条件\n2. 避免不必要的SELECT ... FOR UPDATE\n3. 确保JOIN语句有正确的ON条件\n4. 使用EXPLAIN分析查询计划\n5. 参考EXPLAIN分析模块的具体索引推荐",
                estimated_impact="高 - 可以直接消除由不良SQL导致的死锁"
            ))
