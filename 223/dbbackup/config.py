import yaml
import os
from pathlib import Path


class Config:
    def __init__(self, config_path='config.yaml'):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def get_database_config(self, db_type):
        return self.config.get('databases', {}).get(db_type, {})

    def get_backup_config(self):
        return self.config.get('backup', {})

    def get_storage_config(self):
        return self.config.get('storage', {})

    def get_encryption_config(self):
        return self.config.get('encryption', {})

    def get_compression_config(self):
        return self.config.get('compression', {})

    def get_logging_config(self):
        return self.config.get('logging', {})

    def get_verification_config(self):
        return self.get_backup_config().get('verification', {})
