"""
Configuration module - 全局配置
"""
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MySQLConfig:
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root"
    password: str = ""
    server_id: int = 100
    binlog_file: Optional[str] = None
    binlog_pos: int = 4
    only_schemas: Optional[list] = None
    only_tables: Optional[list] = None


@dataclass
class PGConfig:
    host: str = "127.0.0.1"
    port: int = 5432
    user: str = "postgres"
    password: str = ""
    dbname: str = "postgres"
    wal_file: Optional[str] = None
    pg_waldump_path: str = "pg_waldump"


@dataclass
class AnalysisConfig:
    large_txn_threshold_bytes: int = 10 * 1024 * 1024
    large_txn_threshold_rows: int = 1000
    lock_wait_threshold_ms: int = 100
    long_txn_duration_threshold_ms: int = 5000
    dual_threshold_enabled: bool = True
    deadlock_check_enabled: bool = True
    hotspot_top_n: int = 20
    report_output_dir: str = "./reports"
    enable_visualization: bool = True


@dataclass
class AppConfig:
    mysql: MySQLConfig = field(default_factory=MySQLConfig)
    pg: PGConfig = field(default_factory=PGConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    log_level: str = "INFO"
    log_file: Optional[str] = None

    def ensure_dirs(self):
        os.makedirs(self.analysis.report_output_dir, exist_ok=True)
        if self.log_file:
            log_dir = os.path.dirname(self.log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
