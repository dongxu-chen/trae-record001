import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DatabaseConfig:
    db_type: str = "mysql"
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "test"
    
    def get_connection_string(self) -> str:
        if self.db_type == "mysql":
            return f"mysql+mysqlconnector://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.db_type == "postgresql":
            return f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        return ""


@dataclass
class RLConfig:
    gamma: float = 0.99
    epsilon_start: float = 1.0
    epsilon_end: float = 0.01
    epsilon_decay: float = 0.995
    learning_rate: float = 0.001
    batch_size: int = 64
    target_update_freq: int = 100
    memory_capacity: int = 10000
    num_episodes: int = 500
    max_steps_per_episode: int = 50
    hidden_size: int = 256


@dataclass
class IndexConfig:
    max_indexes_per_table: int = 5
    max_columns_per_index: int = 4
    min_index_benefit_threshold: float = 0.1
    duplicate_index_similarity_threshold: float = 0.8
    index_storage_cost_weight: float = 0.1
    index_maintenance_cost_weight: float = 0.3
    write_operation_cost_factor: float = 0.5
    use_column_order_compatibility: bool = True


@dataclass
class Config:
    db: DatabaseConfig = DatabaseConfig()
    rl: RLConfig = RLConfig()
    index: IndexConfig = IndexConfig()
    slow_query_log_path: Optional[str] = None
    tables_to_analyze: Optional[List[str]] = None
    output_dir: str = "./output"
    
    def __post_init__(self):
        os.makedirs(self.output_dir, exist_ok=True)
