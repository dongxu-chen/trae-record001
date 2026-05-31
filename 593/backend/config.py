import os
import yaml
from typing import Dict, Any
from dotenv import load_dotenv


class Config:
    def __init__(self, config_path: str = None):
        load_dotenv()
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), '..', 'config', 'rules.yaml')
        self.rules = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self.rules
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def get_branch_naming_rules(self) -> Dict:
        return self.rules.get('branch_naming', {})

    def get_merge_direction_rules(self) -> Dict:
        return self.rules.get('merge_direction', {})

    def get_pr_size_rules(self) -> Dict:
        return self.rules.get('pr_size', {})

    def get_commit_frequency_rules(self) -> Dict:
        return self.rules.get('commit_frequency', {})

    def get_auto_fix_rules(self) -> Dict:
        return self.rules.get('auto_fix', {})

    def get_ci_rules(self) -> Dict:
        return self.rules.get('ci', {})

    def get_branch_age_rules(self) -> Dict:
        return self.rules.get('branch_age', {})

    def get_commit_quality_rules(self) -> Dict:
        return self.rules.get('commit_quality', {})

    def get_team_report_rules(self) -> Dict:
        return self.rules.get('team_report', {})
