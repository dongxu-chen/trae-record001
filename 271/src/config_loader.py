import os
import yaml
from typing import Dict, Any
from dotenv import load_dotenv


class ConfigLoader:
    def __init__(self, config_path: str = "config/config.yaml", 
                 rules_path: str = "config/rules/custom_rules.yaml"):
        self.config_path = config_path
        self.rules_path = rules_path
        load_dotenv()
        
    def load_config(self) -> Dict[str, Any]:
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    
    def load_custom_rules(self) -> Dict[str, Any]:
        if os.path.exists(self.rules_path):
            with open(self.rules_path, 'r', encoding='utf-8') as f:
                rules = yaml.safe_load(f)
            return rules
        return {}
    
    def get_env_var(self, key: str, default: str = None) -> str:
        return os.getenv(key, default)
