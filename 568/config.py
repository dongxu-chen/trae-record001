import os
from dataclasses import dataclass, field
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = ""
    db_type: str = "mysql"


@dataclass
class RewriteConfig:
    enable_subquery_unfolding: bool = True
    enable_optimize_joins: bool = True
    enable_push_predicates: bool = True
    enable_remove_redundant: bool = True
    enable_simplify_conditions: bool = True
    enable_use_index_hints: bool = False
    enable_or_to_union: bool = True
    enable_not_exists_to_leftjoin: bool = True
    max_rewrite_attempts: int = 5
    enable_explain_analyze: bool = True


@dataclass
class AppConfig:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    rewrite: RewriteConfig = field(default_factory=RewriteConfig)
    supported_databases: list = field(default_factory=lambda: ["mysql", "postgresql"])
    slow_query_threshold_ms: int = 100

    def get_db_config(self) -> DatabaseConfig:
        return self.database

    def update_db_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.database, key):
                setattr(self.database, key, value)

    def update_rewrite_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.rewrite, key):
                setattr(self.rewrite, key, value)
