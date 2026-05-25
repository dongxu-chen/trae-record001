import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import numpy as np
import gymnasium as gym
from gymnasium import spaces

from database import DatabaseConnector, TableSchema, QueryInfo, QueryCost
from index_analyzer import IndexAnalyzer
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EnvState:
    current_indexes: Dict[str, List[List[str]]]
    query_costs: List[float]
    total_storage_cost: float
    total_maintenance_cost: float
    step_count: int


class IndexRecommendationEnv(gym.Env):
    metadata = {'render_modes': ['human', 'ansi']}

    def __init__(
        self,
        config: Config,
        db_connector: DatabaseConnector,
        queries: List[QueryInfo],
        schemas: Dict[str, TableSchema],
        candidate_indexes: Dict[str, List[List[str]]],
        render_mode: Optional[str] = None
    ):
        super().__init__()
        
        self.config = config
        self.db_connector = db_connector
        self.queries = queries
        self.schemas = schemas
        self.candidate_indexes = candidate_indexes
        self.index_analyzer = IndexAnalyzer(config.index)
        
        self._build_column_ranking()
        self._setup_action_space()
        self._setup_observation_space()
        
        self.render_mode = render_mode
        self.baseline_costs = {}
        self.current_state: Optional[EnvState] = None
        self.created_indexes: List[Tuple[str, str]] = []
        
        self._compute_baseline()

    def _build_column_ranking(self):
        self.all_columns = {}
        self.column_rank = {}
        
        for table, schema in self.schemas.items():
            column_scores = {}
            
            for query in self.queries:
                if table not in query.tables:
                    continue
                
                weight = max(query.execution_time, 1.0)
                
                for i, col in enumerate(query.where_columns):
                    column_scores[col] = column_scores.get(col, 0) + weight * (2.0 - i * 0.1)
                for col in query.join_columns:
                    column_scores[col] = column_scores.get(col, 0) + weight * 1.5
                for col in query.orderby_columns:
                    column_scores[col] = column_scores.get(col, 0) + weight * 1.2
                for col in query.groupby_columns:
                    column_scores[col] = column_scores.get(col, 0) + weight * 1.2
            
            sorted_cols = sorted(column_scores.items(), key=lambda x: x[1], reverse=True)
            self.all_columns[table] = [col for col, score in sorted_cols]
            self.column_rank[table] = {col: i for i, (col, score) in enumerate(sorted_cols)}
            
            logger.info(f"Table {table}: ranked {len(sorted_cols)} columns by importance")

    def _setup_action_space(self):
        all_candidates = []
        self.candidate_map = {}
        
        idx = 0
        for table, indexes in self.candidate_indexes.items():
            for index_cols in indexes:
                all_candidates.append(index_cols)
                self.candidate_map[idx] = (table, index_cols)
                idx += 1
        
        self.total_candidates = len(all_candidates)
        self.action_space = spaces.Discrete(self.total_candidates + 1)

    def _setup_observation_space(self):
        obs_size = self._get_state_dim()
        
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(obs_size,),
            dtype=np.float32
        )
        
        logger.info(f"Observation space dimension: {obs_size}")

    def _get_state_dim(self) -> int:
        num_queries = len(self.queries)
        num_tables = len(self.schemas)
        max_columns_per_table = max(
            len(self.column_rank.get(t, {})) for t in self.schemas
        ) if self.schemas else 0
        
        return (
            num_queries +
            num_tables * max_columns_per_table +
            num_tables * 2 +
            3
        )

    def _compute_baseline(self):
        logger.info("Computing baseline query costs...")
        for i, query in enumerate(self.queries):
            try:
                cost = self.db_connector.explain_query(query.sql)
                self.baseline_costs[i] = cost.estimated_cost
            except Exception as e:
                logger.warning(f"Failed to get baseline cost for query {i}: {e}")
                self.baseline_costs[i] = 1e9

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None):
        super().reset(seed=seed)
        
        for table, idx_name in self.created_indexes:
            try:
                self.db_connector.drop_index(table, idx_name)
            except:
                pass
        self.created_indexes = []
        
        current_indexes = {table: [] for table in self.schemas.keys()}
        query_costs = [self.baseline_costs.get(i, 1e9) for i in range(len(self.queries))]
        
        self.current_state = EnvState(
            current_indexes=current_indexes,
            query_costs=query_costs,
            total_storage_cost=0.0,
            total_maintenance_cost=0.0,
            step_count=0
        )
        
        observation = self._get_observation()
        info = self._get_info()
        
        return observation, info

    def step(self, action: int):
        if self.current_state is None:
            self.reset()
        
        reward = 0.0
        terminated = False
        truncated = False
        
        if action == self.total_candidates:
            terminated = True
            observation = self._get_observation()
            info = self._get_info()
            return observation, reward, terminated, truncated, info
        
        table, index_cols = self.candidate_map[action]
        
        if self._is_duplicate_index(table, index_cols):
            reward = -0.05
        else:
            index_name = f"idx_rl_{table}_{'_'.join(index_cols)}"
            success = self.db_connector.create_index(table, index_cols, index_name)
            
            if success:
                self.created_indexes.append((table, index_name))
                self.current_state.current_indexes[table].append(index_cols)
                
                storage_cost = self.index_analyzer.estimate_index_size(
                    self.schemas[table], index_cols
                )
                self.current_state.total_storage_cost += storage_cost
                
                maintenance_cost = self._calculate_maintenance_cost(table, index_cols)
                self.current_state.total_maintenance_cost += maintenance_cost
                
                improvement = self._evaluate_query_improvement(table, index_cols)
                
                reward = improvement - (
                    storage_cost * self.config.index.index_storage_cost_weight / 1e6 +
                    maintenance_cost * self.config.index.index_maintenance_cost_weight / 1e3
                )
            else:
                reward = -1.0
        
        self.current_state.step_count += 1
        
        if self.current_state.step_count >= self.config.rl.max_steps_per_episode:
            truncated = True
        
        total_indexes = sum(
            len(indexes) for indexes in self.current_state.current_indexes.values()
        )
        if total_indexes >= self.config.index.max_indexes_per_table * len(self.schemas):
            terminated = True
        
        observation = self._get_observation()
        info = self._get_info()
        
        return observation, reward, terminated, truncated, info

    def _is_duplicate_index(self, table: str, index_cols: List[str]) -> bool:
        existing = self.current_state.current_indexes.get(table, [])
        new_set = set(index_cols)
        
        for existing_cols in existing:
            if set(existing_cols) == new_set:
                return True
            if len(existing_cols) >= len(index_cols):
                if all(c in existing_cols[:len(index_cols)] for i, c in enumerate(index_cols)):
                    return True
        return False

    def _calculate_maintenance_cost(self, table: str, index_cols: List[str]) -> float:
        schema = self.schemas.get(table)
        if not schema:
            return 0.0
        
        row_count = schema.row_count or 1000
        num_cols = len(index_cols)
        
        write_cost = row_count * num_cols * self.config.index.write_operation_cost_factor
        
        column_overhead = sum(
            1.0 / (self.column_rank.get(table, {}).get(col, 100) + 1)
            for col in index_cols
        )
        
        return write_cost * (1.0 + column_overhead * 0.1)

    def _evaluate_query_improvement(self, table: str, index_cols: List[str]) -> float:
        total_improvement = 0.0
        index_set = set(index_cols)
        
        for i, query in enumerate(self.queries):
            if table not in query.tables:
                continue
            
            relevant_cols = (
                set(query.where_columns) |
                set(query.join_columns) |
                set(query.orderby_columns) |
                set(query.groupby_columns)
            )
            
            if not relevant_cols & index_set:
                continue
            
            prefix_match = 0
            for j, col in enumerate(index_cols):
                if col in relevant_cols and j == prefix_match:
                    prefix_match += 1
            
            if prefix_match > 0:
                try:
                    new_cost = self.db_connector.explain_query(query.sql)
                    old_cost = self.current_state.query_costs[i]
                    
                    if old_cost > 0:
                        improvement_ratio = (old_cost - new_cost.estimated_cost) / old_cost
                        improvement_ratio = max(0, min(improvement_ratio, 1.0))
                        
                        query_weight = max(query.execution_time, 1.0)
                        total_improvement += improvement_ratio * query_weight
                        
                        self.current_state.query_costs[i] = new_cost.estimated_cost
                except Exception as e:
                    logger.debug(f"Query evaluation failed: {e}")
        
        return total_improvement

    def _get_observation(self) -> np.ndarray:
        obs_parts = []
        
        normalized_costs = []
        for i in range(len(self.queries)):
            baseline = self.baseline_costs.get(i, 1e9)
            current = self.current_state.query_costs[i]
            if baseline > 0:
                normalized_costs.append(current / baseline)
            else:
                normalized_costs.append(1.0)
        obs_parts.extend(normalized_costs)
        
        for table in self.schemas.keys():
            table_cols = self.all_columns.get(table, [])
            table_indexes = self.current_state.current_indexes.get(table, [])
            
            covered_rank = np.zeros(len(table_cols))
            index_order = np.zeros(len(table_cols))
            
            for idx_cols in table_indexes:
                for i, col in enumerate(idx_cols):
                    if col in self.column_rank.get(table, {}):
                        rank = self.column_rank[table][col]
                        if rank < len(covered_rank):
                            covered_rank[rank] = max(covered_rank[rank], 1.0)
                            index_order[rank] = max(index_order[rank], 1.0 / (i + 1))
            
            obs_parts.extend(covered_rank.tolist())
            obs_parts.extend(index_order.tolist())
            
            obs_parts.append(len(table_indexes) / self.config.index.max_indexes_per_table)
        
        obs_parts.append(self.current_state.step_count / self.config.rl.max_steps_per_episode)
        obs_parts.append(self.current_state.total_storage_cost / 1e9)
        obs_parts.append(self.current_state.total_maintenance_cost / 1e6)
        
        expected_dim = self.observation_space.shape[0]
        current_dim = len(obs_parts)
        if current_dim < expected_dim:
            obs_parts.extend([0.0] * (expected_dim - current_dim))
        elif current_dim > expected_dim:
            obs_parts = obs_parts[:expected_dim]
        
        return np.array(obs_parts, dtype=np.float32)

    def _get_info(self) -> Dict[str, Any]:
        total_indexes = sum(
            len(indexes) for indexes in self.current_state.current_indexes.values()
        )
        
        avg_cost_ratio = np.mean([
            self.current_state.query_costs[i] / max(self.baseline_costs.get(i, 1e9), 1)
            for i in range(len(self.queries))
        ])
        
        return {
            'total_indexes': total_indexes,
            'avg_cost_ratio': avg_cost_ratio,
            'total_storage_cost': self.current_state.total_storage_cost,
            'total_maintenance_cost': self.current_state.total_maintenance_cost,
            'step_count': self.current_state.step_count
        }

    def render(self):
        if self.render_mode == 'human':
            info = self._get_info()
            print(f"\nStep: {info['step_count']}")
            print(f"Total indexes created: {info['total_indexes']}")
            print(f"Average cost ratio: {info['avg_cost_ratio']:.4f}")
            print(f"Storage cost: {info['total_storage_cost'] / 1e6:.2f} MB")
            print(f"Maintenance cost: {info['total_maintenance_cost'] / 1e3:.2f}")
            
            for table, indexes in self.current_state.current_indexes.items():
                if indexes:
                    print(f"  {table}: {indexes}")

    def close(self):
        for table, idx_name in self.created_indexes:
            try:
                self.db_connector.drop_index(table, idx_name)
            except:
                pass
        self.created_indexes = []


class MockIndexRecommendationEnv(gym.Env):
    metadata = {'render_modes': ['human', 'ansi']}

    def __init__(
        self,
        config: Config,
        schemas: Dict[str, TableSchema],
        queries: List[QueryInfo],
        candidate_indexes: Dict[str, List[List[str]]],
        render_mode: Optional[str] = None
    ):
        super().__init__()
        
        self.config = config
        self.schemas = schemas
        self.queries = queries
        self.candidate_indexes = candidate_indexes
        self.index_analyzer = IndexAnalyzer(config.index)
        
        self._build_column_ranking()
        self._setup_action_space()
        self._setup_observation_space()
        
        self.render_mode = render_mode
        self.baseline_costs = {}
        self.current_state: Optional[EnvState] = None
        
        self._compute_mock_baseline()

    def _build_column_ranking(self):
        self.all_columns = {}
        self.column_rank = {}
        
        for table, schema in self.schemas.items():
            column_scores = {}
            
            for query in self.queries:
                if table not in query.tables:
                    continue
                
                weight = max(query.execution_time, 1.0)
                
                for i, col in enumerate(query.where_columns):
                    column_scores[col] = column_scores.get(col, 0) + weight * (2.0 - i * 0.1)
                for col in query.join_columns:
                    column_scores[col] = column_scores.get(col, 0) + weight * 1.5
                for col in query.orderby_columns:
                    column_scores[col] = column_scores.get(col, 0) + weight * 1.2
                for col in query.groupby_columns:
                    column_scores[col] = column_scores.get(col, 0) + weight * 1.2
            
            sorted_cols = sorted(column_scores.items(), key=lambda x: x[1], reverse=True)
            self.all_columns[table] = [col for col, score in sorted_cols]
            self.column_rank[table] = {col: i for i, (col, score) in enumerate(sorted_cols)}
            
            logger.debug(f"Table {table}: ranked {len(sorted_cols)} columns")

    def _setup_action_space(self):
        all_candidates = []
        self.candidate_map = {}
        
        idx = 0
        for table, indexes in self.candidate_indexes.items():
            for index_cols in indexes:
                all_candidates.append(index_cols)
                self.candidate_map[idx] = (table, index_cols)
                idx += 1
        
        self.total_candidates = len(all_candidates)
        self.action_space = spaces.Discrete(self.total_candidates + 1)

    def _setup_observation_space(self):
        obs_size = self._get_state_dim()
        
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(obs_size,),
            dtype=np.float32
        )

    def _get_state_dim(self) -> int:
        num_queries = len(self.queries)
        num_tables = len(self.schemas)
        max_columns_per_table = max(
            len(self.column_rank.get(t, {})) for t in self.schemas
        ) if self.schemas else 0
        
        return (
            num_queries +
            num_tables * max_columns_per_table * 2 +
            num_tables +
            3
        )

    def _get_current_state_dim(self) -> int:
        num_queries = len(self.queries)
        num_tables = len(self.schemas)
        total_cols = 0
        for table in self.schemas:
            total_cols += len(self.column_rank.get(table, {})) * 2
        
        return (
            num_queries +
            total_cols +
            num_tables +
            3
        )

    def _compute_mock_baseline(self):
        for i, query in enumerate(self.queries):
            self.baseline_costs[i] = max(query.rows_examined * 10, 1000)

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None):
        super().reset(seed=seed)
        
        current_indexes = {table: [] for table in self.schemas.keys()}
        query_costs = [self.baseline_costs.get(i, 1000) for i in range(len(self.queries))]
        
        self.current_state = EnvState(
            current_indexes=current_indexes,
            query_costs=query_costs,
            total_storage_cost=0.0,
            total_maintenance_cost=0.0,
            step_count=0
        )
        
        observation = self._get_observation()
        info = self._get_info()
        
        return observation, info

    def step(self, action: int):
        if self.current_state is None:
            self.reset()
        
        reward = 0.0
        terminated = False
        truncated = False
        
        if action == self.total_candidates:
            terminated = True
            observation = self._get_observation()
            info = self._get_info()
            return observation, reward, terminated, truncated, info
        
        table, index_cols = self.candidate_map[action]
        
        if self._is_duplicate_index(table, index_cols):
            reward = -0.05
        else:
            self.current_state.current_indexes[table].append(index_cols)
            
            storage_cost = self.index_analyzer.estimate_index_size(
                self.schemas[table], index_cols
            )
            self.current_state.total_storage_cost += storage_cost
            
            maintenance_cost = self._calculate_maintenance_cost(table, index_cols)
            self.current_state.total_maintenance_cost += maintenance_cost
            
            improvement = self._mock_evaluate_improvement(table, index_cols)
            
            reward = improvement - (
                storage_cost * self.config.index.index_storage_cost_weight / 1e6 +
                maintenance_cost * self.config.index.index_maintenance_cost_weight / 1e3
            )
        
        self.current_state.step_count += 1
        
        if self.current_state.step_count >= self.config.rl.max_steps_per_episode:
            truncated = True
        
        total_indexes = sum(
            len(indexes) for indexes in self.current_state.current_indexes.values()
        )
        if total_indexes >= self.config.index.max_indexes_per_table * len(self.schemas):
            terminated = True
        
        observation = self._get_observation()
        info = self._get_info()
        
        return observation, reward, terminated, truncated, info

    def _is_duplicate_index(self, table: str, index_cols: List[str]) -> bool:
        existing = self.current_state.current_indexes.get(table, [])
        new_set = set(index_cols)
        
        for existing_cols in existing:
            if set(existing_cols) == new_set:
                return True
        return False

    def _calculate_maintenance_cost(self, table: str, index_cols: List[str]) -> float:
        schema = self.schemas.get(table)
        if not schema:
            return 0.0
        
        row_count = schema.row_count or 1000
        num_cols = len(index_cols)
        
        write_cost = row_count * num_cols * self.config.index.write_operation_cost_factor
        
        column_overhead = sum(
            1.0 / (self.column_rank.get(table, {}).get(col, 100) + 1)
            for col in index_cols
        )
        
        return write_cost * (1.0 + column_overhead * 0.1)

    def _mock_evaluate_improvement(self, table: str, index_cols: List[str]) -> float:
        total_improvement = 0.0
        index_set = set(index_cols)
        
        for i, query in enumerate(self.queries):
            if table not in query.tables:
                continue
            
            relevant_cols = (
                set(query.where_columns) |
                set(query.join_columns) |
                set(query.orderby_columns) |
                set(query.groupby_columns)
            )
            
            match_cols = index_set & relevant_cols
            if not match_cols:
                continue
            
            prefix_match = 0
            for j, col in enumerate(index_cols):
                if col in relevant_cols and j == prefix_match:
                    prefix_match += 1
            
            if prefix_match > 0:
                improvement_ratio = prefix_match / max(len(index_cols), len(relevant_cols), 1)
                
                old_cost = self.current_state.query_costs[i]
                new_cost = old_cost * (1 - improvement_ratio * 0.8)
                self.current_state.query_costs[i] = new_cost
                
                query_weight = max(query.execution_time, 1.0)
                total_improvement += improvement_ratio * query_weight
        
        return total_improvement

    def _get_observation(self) -> np.ndarray:
        obs_parts = []
        
        normalized_costs = []
        for i in range(len(self.queries)):
            baseline = self.baseline_costs.get(i, 1000)
            current = self.current_state.query_costs[i]
            if baseline > 0:
                normalized_costs.append(current / baseline)
            else:
                normalized_costs.append(1.0)
        obs_parts.extend(normalized_costs)
        
        for table in self.schemas.keys():
            table_cols = self.all_columns.get(table, [])
            table_indexes = self.current_state.current_indexes.get(table, [])
            
            covered_rank = np.zeros(len(table_cols))
            index_order = np.zeros(len(table_cols))
            
            for idx_cols in table_indexes:
                for i, col in enumerate(idx_cols):
                    if col in self.column_rank.get(table, {}):
                        rank = self.column_rank[table][col]
                        if rank < len(covered_rank):
                            covered_rank[rank] = max(covered_rank[rank], 1.0)
                            index_order[rank] = max(index_order[rank], 1.0 / (i + 1))
            
            obs_parts.extend(covered_rank.tolist())
            obs_parts.extend(index_order.tolist())
            
            obs_parts.append(len(table_indexes) / self.config.index.max_indexes_per_table)
        
        obs_parts.append(self.current_state.step_count / self.config.rl.max_steps_per_episode)
        obs_parts.append(self.current_state.total_storage_cost / 1e9)
        obs_parts.append(self.current_state.total_maintenance_cost / 1e6)
        
        expected_dim = self.observation_space.shape[0]
        current_dim = len(obs_parts)
        if current_dim < expected_dim:
            obs_parts.extend([0.0] * (expected_dim - current_dim))
        elif current_dim > expected_dim:
            obs_parts = obs_parts[:expected_dim]
        
        return np.array(obs_parts, dtype=np.float32)

    def _get_info(self) -> Dict[str, Any]:
        total_indexes = sum(
            len(indexes) for indexes in self.current_state.current_indexes.values()
        )
        
        avg_cost_ratio = np.mean([
            self.current_state.query_costs[i] / max(self.baseline_costs.get(i, 1000), 1)
            for i in range(len(self.queries))
        ])
        
        return {
            'total_indexes': total_indexes,
            'avg_cost_ratio': avg_cost_ratio,
            'total_storage_cost': self.current_state.total_storage_cost,
            'total_maintenance_cost': self.current_state.total_maintenance_cost,
            'step_count': self.current_state.step_count
        }

    def render(self):
        if self.render_mode == 'human':
            info = self._get_info()
            print(f"\nStep: {info['step_count']}")
            print(f"Total indexes created: {info['total_indexes']}")
            print(f"Average cost ratio: {info['avg_cost_ratio']:.4f}")
            print(f"Storage cost: {info['total_storage_cost'] / 1e6:.2f} MB")
            print(f"Maintenance cost: {info['total_maintenance_cost'] / 1e3:.2f}")

    def close(self):
        pass
