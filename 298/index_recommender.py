import os
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
import numpy as np

from config import Config
from database import DatabaseConnector, TableSchema, QueryInfo
from query_parser import SlowQueryLogParser
from index_analyzer import IndexAnalyzer, IndexAnalysisResult
from index_env import IndexRecommendationEnv, MockIndexRecommendationEnv
from dqn_agent import DQNAgent, DQNTrainer, IndexRecommender

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RecommendationReport:
    rl_recommendations: List[dict] = field(default_factory=list)
    static_analysis: IndexAnalysisResult = field(default_factory=IndexAnalysisResult)
    query_summary: dict = field(default_factory=dict)
    training_metrics: dict = field(default_factory=dict)
    overall_summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'rl_recommendations': self.rl_recommendations,
            'static_analysis': {
                'duplicate_indexes': [
                    {
                        'table': dup.table_name,
                        'redundant_index': dup.redundant_index.name,
                        'redundant_columns': dup.redundant_index.columns,
                        'dominant_index': dup.dominant_index.name,
                        'dominant_columns': dup.dominant_index.columns,
                        'similarity': dup.similarity,
                        'reason': dup.reason
                    }
                    for dup in self.static_analysis.duplicate_indexes
                ],
                'merge_suggestions': [
                    {
                        'table': merge.table_name,
                        'indexes_to_merge': [idx.name for idx in merge.indexes_to_merge],
                        'suggested_columns': merge.suggested_index,
                        'benefit_score': merge.benefit_score,
                        'reason': merge.reason
                    }
                    for merge in self.static_analysis.merge_suggestions
                ],
                'unused_indexes': [
                    {
                        'table': table,
                        'index_name': idx.name,
                        'columns': idx.columns
                    }
                    for table, idx in self.static_analysis.unused_indexes
                ],
                'recommendations': self.static_analysis.recommendations
            },
            'query_summary': self.query_summary,
            'training_metrics': self.training_metrics,
            'overall_summary': self.overall_summary
        }

    def save(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Report saved to {path}")


class DatabaseIndexAdvisor:
    def __init__(self, config: Config, use_mock_env: bool = True):
        self.config = config
        self.use_mock_env = use_mock_env
        
        self.db_connector: Optional[DatabaseConnector] = None
        self.parser = SlowQueryLogParser()
        self.index_analyzer = IndexAnalyzer(config.index)
        
        self.schemas: Dict[str, TableSchema] = {}
        self.queries: List[QueryInfo] = []
        self.candidate_indexes: Dict[str, List[List[str]]] = {}
        
        self.env = None
        self.agent: Optional[DQNAgent] = None
        self.trainer: Optional[DQNTrainer] = None

    def connect_database(self):
        if not self.use_mock_env:
            self.db_connector = DatabaseConnector(self.config.db)
            logger.info("Database connection established")
        else:
            logger.info("Running in mock mode (no database connection)")

    def load_schemas(self, tables: Optional[List[str]] = None):
        if self.db_connector:
            self.schemas = self.db_connector.get_all_schemas(tables)
            logger.info(f"Loaded schemas for {len(self.schemas)} tables")
        else:
            logger.warning("No database connection. Using mock schemas.")

    def load_slow_queries(self, log_path: str, log_type: str = 'mysql') -> List[QueryInfo]:
        if log_type == 'mysql':
            self.queries = self.parser.parse_mysql_slow_log(log_path)
        elif log_type == 'postgresql':
            self.queries = self.parser.parse_postgres_log(log_path)
        
        logger.info(f"Loaded {len(self.queries)} slow queries")
        
        top_queries = self.parser.get_top_queries(self.queries, top_n=20)
        logger.info(f"Selected top {len(top_queries)} queries for analysis")
        
        return top_queries

    def analyze_existing_indexes(self) -> IndexAnalysisResult:
        used_columns = {}
        for table in self.schemas.keys():
            cols = set()
            for query in self.queries:
                if table in query.tables:
                    cols.update(query.where_columns)
                    cols.update(query.join_columns)
                    cols.update(query.orderby_columns)
                    cols.update(query.groupby_columns)
            used_columns[table] = cols
        
        result = self.index_analyzer.analyze_indexes(self.schemas, used_columns)
        logger.info(f"Found {len(result.duplicate_indexes)} duplicate indexes")
        logger.info(f"Found {len(result.merge_suggestions)} merge suggestions")
        
        return result

    def generate_candidate_indexes(self):
        candidate_columns = self.parser.get_candidate_columns(
            self.queries, list(self.schemas.keys())
        )
        
        self.candidate_indexes = {}
        for table, columns in candidate_columns.items():
            if table in self.schemas:
                schema = self.schemas[table]
                candidates = self.index_analyzer.generate_candidate_indexes(
                    schema, columns, schema.indexes
                )
                self.candidate_indexes[table] = candidates
                logger.info(f"Generated {len(candidates)} candidate indexes for table {table}")

    def setup_environment(self):
        if self.use_mock_env:
            self.env = MockIndexRecommendationEnv(
                config=self.config,
                schemas=self.schemas,
                queries=self.queries,
                candidate_indexes=self.candidate_indexes
            )
        else:
            self.env = IndexRecommendationEnv(
                config=self.config,
                db_connector=self.db_connector,
                queries=self.queries,
                schemas=self.schemas,
                candidate_indexes=self.candidate_indexes
            )
        
        logger.info(f"Environment setup complete. Action space: {self.env.action_space.n}")
        return self.env

    def setup_agent(self):
        state_dim = self.env.observation_space.shape[0]
        action_dim = self.env.action_space.n
        
        self.agent = DQNAgent(state_dim, action_dim, self.config.rl)
        self.trainer = DQNTrainer(self.agent, self.env, self.config.rl)
        
        logger.info(f"Agent setup complete. State dim: {state_dim}, Action dim: {action_dim}")
        return self.agent

    def train(self, num_episodes: Optional[int] = None):
        if not self.trainer:
            raise ValueError("Agent not initialized. Call setup_agent first.")
        
        logger.info("Starting DQN training...")
        metrics = self.trainer.train(num_episodes)
        return metrics

    def evaluate(self, num_episodes: int = 5) -> dict:
        if not self.trainer:
            raise ValueError("Agent not initialized. Call setup_agent first.")
        
        return self.trainer.evaluate(num_episodes)

    def get_recommendations(self, top_k: int = 10) -> List[dict]:
        if not self.agent:
            raise ValueError("Agent not initialized. Call setup_agent first.")
        
        candidate_map = getattr(self.env, 'candidate_map', {})
        recommender = IndexRecommender(self.agent, candidate_map)
        
        recommendations = recommender.recommend_from_env(self.env, top_k)
        
        for rec in recommendations:
            table = rec['table']
            columns = rec['columns']
            if table in self.schemas:
                rec['estimated_size_mb'] = (
                    self.index_analyzer.estimate_index_size(
                        self.schemas[table], columns
                    ) / (1024 * 1024)
                )
                rec['sql'] = (
                    f"CREATE INDEX idx_{table}_{'_'.join(columns)} "
                    f"ON {table} ({', '.join(columns)});"
                )
        
        return recommendations

    def run_full_analysis(
        self,
        slow_log_path: Optional[str] = None,
        log_type: str = 'mysql',
        custom_queries: Optional[List[QueryInfo]] = None,
        custom_schemas: Optional[Dict[str, TableSchema]] = None,
        num_episodes: Optional[int] = None
    ) -> RecommendationReport:
        report = RecommendationReport()
        
        logger.info("=" * 60)
        logger.info("Starting Database Index Advisor Analysis")
        logger.info("=" * 60)
        
        if custom_schemas:
            self.schemas = custom_schemas
            logger.info(f"Using {len(self.schemas)} custom schemas")
        else:
            self.connect_database()
            self.load_schemas(self.config.tables_to_analyze)
        
        if custom_queries:
            self.queries = custom_queries
            logger.info(f"Using {len(self.queries)} custom queries")
        elif slow_log_path:
            self.queries = self.load_slow_queries(slow_log_path, log_type)
        else:
            logger.warning("No queries provided. Using empty query list.")
        
        report.query_summary = {
            'total_queries': len(self.queries),
            'tables_used': list({t for q in self.queries for t in q.tables}),
            'total_execution_time': sum(q.execution_time for q in self.queries),
            'avg_execution_time': np.mean([q.execution_time for q in self.queries]) if self.queries else 0
        }
        
        logger.info("\n" + "-" * 60)
        logger.info("Running Static Index Analysis")
        logger.info("-" * 60)
        report.static_analysis = self.analyze_existing_indexes()
        
        logger.info("\n" + "-" * 60)
        logger.info("Generating Candidate Indexes")
        logger.info("-" * 60)
        self.generate_candidate_indexes()
        
        total_candidates = sum(len(v) for v in self.candidate_indexes.values())
        logger.info(f"Total candidate indexes: {total_candidates}")
        
        logger.info("\n" + "-" * 60)
        logger.info("Setting up RL Environment")
        logger.info("-" * 60)
        self.setup_environment()
        self.setup_agent()
        
        logger.info("\n" + "-" * 60)
        logger.info("Training DQN Agent")
        logger.info("-" * 60)
        training_metrics = self.train(num_episodes)
        report.training_metrics = {
            'best_reward': training_metrics.get('best_reward', 0),
            'final_avg_reward': float(np.mean(training_metrics.get('rewards', [])[-10:])),
            'num_episodes': len(training_metrics.get('rewards', []))
        }
        
        logger.info("\n" + "-" * 60)
        logger.info("Generating Recommendations")
        logger.info("-" * 60)
        report.rl_recommendations = self.get_recommendations(top_k=10)
        
        report.overall_summary = self._generate_summary(report)
        
        logger.info("\n" + "=" * 60)
        logger.info("Analysis Complete!")
        logger.info("=" * 60)
        
        return report

    def _generate_summary(self, report: RecommendationReport) -> dict:
        summary = {
            'total_recommendations': len(report.rl_recommendations),
            'duplicate_indexes_found': len(report.static_analysis.duplicate_indexes),
            'merge_suggestions': len(report.static_analysis.merge_suggestions),
            'estimated_storage_savings_mb': 0,
            'estimated_performance_improvement': 0
        }
        
        for dup in report.static_analysis.duplicate_indexes:
            if dup.redundant_index.size_bytes > 0:
                summary['estimated_storage_savings_mb'] += (
                    dup.redundant_index.size_bytes / (1024 * 1024)
                )
        
        if report.rl_recommendations:
            avg_q = np.mean([r['q_value'] for r in report.rl_recommendations])
            summary['estimated_performance_improvement'] = max(0, min(avg_q, 1.0))
        
        return summary

    def print_report(self, report: RecommendationReport):
        print("\n" + "=" * 80)
        print("DATABASE INDEX ADVISOR - ANALYSIS REPORT")
        print("=" * 80)
        
        print("\n【查询概要】")
        print(f"  总查询数: {report.query_summary.get('total_queries', 0)}")
        print(f"  涉及表: {', '.join(report.query_summary.get('tables_used', []))}")
        print(f"  总执行时间: {report.query_summary.get('total_execution_time', 0):.2f}s")
        print(f"  平均执行时间: {report.query_summary.get('avg_execution_time', 0):.4f}s")
        
        print("\n【静态分析 - 冗余索引】")
        if report.static_analysis.duplicate_indexes:
            for dup in report.static_analysis.duplicate_indexes:
                print(f"  - {dup.redundant_index.name} ({', '.join(dup.redundant_index.columns)})")
                print(f"    被 {dup.dominant_index.name} 覆盖, 相似度: {dup.similarity:.2f}")
        else:
            print("  未发现冗余索引")
        
        print("\n【静态分析 - 合并建议】")
        if report.static_analysis.merge_suggestions:
            for merge in report.static_analysis.merge_suggestions:
                idx_names = ', '.join(idx.name for idx in merge.indexes_to_merge)
                print(f"  - 合并 [{idx_names}] -> ({', '.join(merge.suggested_index)})")
                print(f"    收益分数: {merge.benefit_score:.2f}, 原因: {merge.reason}")
        else:
            print("  无合并建议")
        
        print("\n【RL 推荐索引】")
        for i, rec in enumerate(report.rl_recommendations, 1):
            print(f"  {i}. {rec['table']} ({', '.join(rec['columns'])})")
            print(f"     Q值: {rec['q_value']:.4f}, 预估大小: {rec.get('estimated_size_mb', 0):.2f} MB")
            print(f"     SQL: {rec.get('sql', '')}")
        
        print("\n" + "=" * 80 + "\n")

    def close(self):
        if self.env:
            self.env.close()
        if self.db_connector:
            self.db_connector.close()
        logger.info("Advisor closed")


def create_mock_data() -> tuple:
    from database import TableSchema, ColumnInfo, IndexInfo, QueryInfo
    
    schemas = {
        'users': TableSchema(
            name='users',
            columns=[
                ColumnInfo(name='id', data_type='int', is_nullable=False, cardinality=10000),
                ColumnInfo(name='username', data_type='varchar(50)', is_nullable=False, cardinality=10000),
                ColumnInfo(name='email', data_type='varchar(100)', is_nullable=False, cardinality=10000),
                ColumnInfo(name='status', data_type='tinyint', is_nullable=True, cardinality=5),
                ColumnInfo(name='created_at', data_type='datetime', is_nullable=False, cardinality=9500),
                ColumnInfo(name='country', data_type='varchar(50)', is_nullable=True, cardinality=50),
            ],
            indexes=[
                IndexInfo(name='PRIMARY', columns=['id'], is_primary=True),
                IndexInfo(name='idx_username', columns=['username'], is_unique=True),
            ],
            row_count=10000,
            size_bytes=1024 * 1024 * 5
        ),
        'orders': TableSchema(
            name='orders',
            columns=[
                ColumnInfo(name='id', data_type='int', is_nullable=False, cardinality=50000),
                ColumnInfo(name='user_id', data_type='int', is_nullable=False, cardinality=8000),
                ColumnInfo(name='product_id', data_type='int', is_nullable=False, cardinality=2000),
                ColumnInfo(name='amount', data_type='decimal', is_nullable=False, cardinality=15000),
                ColumnInfo(name='status', data_type='varchar(20)', is_nullable=False, cardinality=8),
                ColumnInfo(name='created_at', data_type='datetime', is_nullable=False, cardinality=48000),
            ],
            indexes=[
                IndexInfo(name='PRIMARY', columns=['id'], is_primary=True),
                IndexInfo(name='idx_user_id', columns=['user_id']),
            ],
            row_count=50000,
            size_bytes=1024 * 1024 * 20
        )
    }
    
    queries = [
        QueryInfo(
            sql="SELECT * FROM users WHERE status = 1 AND country = 'CN' ORDER BY created_at DESC",
            execution_time=2.5,
            rows_examined=8000,
            rows_sent=500,
            tables=['users'],
            where_columns=['status', 'country'],
            orderby_columns=['created_at']
        ),
        QueryInfo(
            sql="SELECT * FROM orders WHERE user_id = ? AND status = 'paid' ORDER BY created_at DESC",
            execution_time=1.8,
            rows_examined=5000,
            rows_sent=100,
            tables=['orders'],
            where_columns=['user_id', 'status'],
            orderby_columns=['created_at']
        ),
        QueryInfo(
            sql="SELECT u.*, o.* FROM users u JOIN orders o ON u.id = o.user_id WHERE u.status = 1 AND o.created_at > '2024-01-01'",
            execution_time=5.2,
            rows_examined=20000,
            rows_sent=2000,
            tables=['users', 'orders'],
            where_columns=['status', 'created_at'],
            join_columns=['id', 'user_id']
        ),
        QueryInfo(
            sql="SELECT COUNT(*) FROM orders WHERE product_id = ? AND created_at BETWEEN ? AND ?",
            execution_time=0.9,
            rows_examined=3000,
            rows_sent=1,
            tables=['orders'],
            where_columns=['product_id', 'created_at']
        ),
        QueryInfo(
            sql="SELECT country, COUNT(*) FROM users WHERE status = 1 GROUP BY country ORDER BY COUNT(*) DESC",
            execution_time=1.5,
            rows_examined=6000,
            rows_sent=50,
            tables=['users'],
            where_columns=['status'],
            groupby_columns=['country'],
            orderby_columns=['count(*)']
        ),
    ]
    
    return schemas, queries


def run_mock_demo():
    config = Config()
    config.rl.num_episodes = 100
    config.rl.max_steps_per_episode = 20
    
    advisor = DatabaseIndexAdvisor(config, use_mock_env=True)
    
    schemas, queries = create_mock_data()
    
    report = advisor.run_full_analysis(
        custom_schemas=schemas,
        custom_queries=queries,
        num_episodes=100
    )
    
    advisor.print_report(report)
    
    report_path = os.path.join(config.output_dir, 'index_recommendation_report.json')
    report.save(report_path)
    
    advisor.close()
    
    return report


if __name__ == '__main__':
    run_mock_demo()
