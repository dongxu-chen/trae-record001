import yaml
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class GlobalConfig:
    log_level: str = "INFO"
    log_file: str = "backup.log"
    temp_dir: str = "./temp"


@dataclass
class EmailConfig:
    enabled: bool = False
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    use_tls: bool = True
    sender: str = ""
    recipients: List[str] = field(default_factory=list)


@dataclass
class SFTPConfig:
    host: str = ""
    port: int = 22
    username: str = ""
    password: str = ""
    remote_base_dir: str = "/backups"


@dataclass
class BackupTask:
    name: str
    enabled: bool
    source_dir: str
    backup_type: str  # 'full' or 'incremental'
    cron: str
    compression: bool
    retention_days: int
    exclude_patterns: List[str] = field(default_factory=list)


@dataclass
class AppConfig:
    global_config: GlobalConfig
    email: EmailConfig
    sftp: SFTPConfig
    backup_tasks: List[BackupTask]


class ConfigLoader:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = None

    def load(self) -> AppConfig:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        global_data = data.get('global', {})
        global_config = GlobalConfig(
            log_level=global_data.get('log_level', 'INFO'),
            log_file=global_data.get('log_file', 'backup.log'),
            temp_dir=global_data.get('temp_dir', './temp')
        )

        email_data = data.get('email', {})
        email_config = EmailConfig(
            enabled=email_data.get('enabled', False),
            smtp_server=email_data.get('smtp_server', ''),
            smtp_port=email_data.get('smtp_port', 587),
            smtp_username=email_data.get('smtp_username', ''),
            smtp_password=email_data.get('smtp_password', ''),
            use_tls=email_data.get('use_tls', True),
            sender=email_data.get('sender', ''),
            recipients=email_data.get('recipients', [])
        )

        sftp_data = data.get('sftp', {})
        sftp_config = SFTPConfig(
            host=sftp_data.get('host', ''),
            port=sftp_data.get('port', 22),
            username=sftp_data.get('username', ''),
            password=sftp_data.get('password', ''),
            remote_base_dir=sftp_data.get('remote_base_dir', '/backups')
        )

        backup_tasks = []
        tasks_data = data.get('backup_tasks', [])
        for task_data in tasks_data:
            task = BackupTask(
                name=task_data.get('name', ''),
                enabled=task_data.get('enabled', True),
                source_dir=task_data.get('source_dir', ''),
                backup_type=task_data.get('backup_type', 'full'),
                cron=task_data.get('cron', '0 2 * * *'),
                compression=task_data.get('compression', True),
                retention_days=task_data.get('retention_days', 30),
                exclude_patterns=task_data.get('exclude_patterns', [])
            )
            backup_tasks.append(task)

        self.config = AppConfig(
            global_config=global_config,
            email=email_config,
            sftp=sftp_config,
            backup_tasks=backup_tasks
        )

        return self.config

    def get_enabled_tasks(self) -> List[BackupTask]:
        if not self.config:
            self.load()
        return [task for task in self.config.backup_tasks if task.enabled]
