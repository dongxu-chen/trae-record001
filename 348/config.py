import yaml
import os
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    db_type: str
    host: str
    port: int
    database: str
    username: str
    password: str
    charset: str = "utf8mb4"
    schema: Optional[str] = None
    extra_params: Dict = field(default_factory=dict)


@dataclass
class BackupConfig:
    backup_file_path: str
    backup_type: str = "full"
    encryption_key: Optional[str] = None
    encryption_algorithm: str = "AES-256-CBC"
    compression: Optional[str] = None


@dataclass
class ValidationConfig:
    row_count_check: bool = True
    row_count_tolerance: float = 0.0
    sample_check: bool = True
    sample_percentage: float = 5.0
    sample_min_rows: int = 100
    sample_max_rows: int = 10000
    business_logic_check: bool = True
    rules_file: Optional[str] = None
    tables_to_validate: Optional[List[str]] = None
    exclude_tables: List[str] = field(default_factory=list)


@dataclass
class ReportConfig:
    output_dir: str = "./output"
    report_format: str = "html"
    template_path: Optional[str] = None
    include_detailed_log: bool = True


@dataclass
class AppConfig:
    source_db: DatabaseConfig
    verification_db: DatabaseConfig
    backup: BackupConfig
    validation: ValidationConfig
    report: ReportConfig


class ConfigLoader:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config_data = None

    def load(self) -> AppConfig:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config_data = yaml.safe_load(f)

        return self._parse_config()

    def _parse_config(self) -> AppConfig:
        source_db_data = self.config_data.get('source_database', {})
        verify_db_data = self.config_data.get('verification_database', {})
        backup_data = self.config_data.get('backup', {})
        validation_data = self.config_data.get('validation', {})
        report_data = self.config_data.get('report', {})

        source_db = DatabaseConfig(
            db_type=source_db_data.get('type', 'mysql'),
            host=source_db_data.get('host', 'localhost'),
            port=source_db_data.get('port', 3306),
            database=source_db_data.get('database', ''),
            username=source_db_data.get('username', ''),
            password=source_db_data.get('password', ''),
            charset=source_db_data.get('charset', 'utf8mb4'),
            schema=source_db_data.get('schema'),
            extra_params=source_db_data.get('extra_params', {})
        )

        verify_db = DatabaseConfig(
            db_type=verify_db_data.get('type', source_db.db_type),
            host=verify_db_data.get('host', 'localhost'),
            port=verify_db_data.get('port', 3306),
            database=verify_db_data.get('database', ''),
            username=verify_db_data.get('username', ''),
            password=verify_db_data.get('password', ''),
            charset=verify_db_data.get('charset', 'utf8mb4'),
            schema=verify_db_data.get('schema'),
            extra_params=verify_db_data.get('extra_params', {})
        )

        backup = BackupConfig(
            backup_file_path=backup_data.get('file_path', ''),
            backup_type=backup_data.get('type', 'full'),
            encryption_key=backup_data.get('encryption_key'),
            encryption_algorithm=backup_data.get('encryption_algorithm', 'AES-256-CBC'),
            compression=backup_data.get('compression')
        )

        validation = ValidationConfig(
            row_count_check=validation_data.get('row_count_check', True),
            row_count_tolerance=validation_data.get('row_count_tolerance', 0.0),
            sample_check=validation_data.get('sample_check', True),
            sample_percentage=validation_data.get('sample_percentage', 5.0),
            sample_min_rows=validation_data.get('sample_min_rows', 100),
            sample_max_rows=validation_data.get('sample_max_rows', 10000),
            business_logic_check=validation_data.get('business_logic_check', True),
            rules_file=validation_data.get('rules_file'),
            tables_to_validate=validation_data.get('tables'),
            exclude_tables=validation_data.get('exclude_tables', [])
        )

        report = ReportConfig(
            output_dir=report_data.get('output_dir', './output'),
            report_format=report_data.get('format', 'html'),
            template_path=report_data.get('template_path'),
            include_detailed_log=report_data.get('include_detailed_log', True)
        )

        return AppConfig(
            source_db=source_db,
            verification_db=verify_db,
            backup=backup,
            validation=validation,
            report=report
        )


def load_config(config_path: str) -> AppConfig:
    loader = ConfigLoader(config_path)
    return loader.load()
