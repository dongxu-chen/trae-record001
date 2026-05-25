import os
import yaml
from typing import Dict, Any, Optional


class ConfigLoader:
    DEFAULT_CONFIG_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "default_config.yaml"
    )

    def __init__(self, custom_config_path: Optional[str] = None):
        self.custom_config_path = custom_config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        with open(self.DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if self.custom_config_path and os.path.exists(self.custom_config_path):
            with open(self.custom_config_path, "r", encoding="utf-8") as f:
                custom_config = yaml.safe_load(f)
                config = self._deep_merge(config, custom_config or {})
        else:
            project_config = self._find_project_config()
            if project_config:
                with open(project_config, "r", encoding="utf-8") as f:
                    custom_config = yaml.safe_load(f)
                    config = self._deep_merge(config, custom_config or {})

        return config

    def _find_project_config(self) -> Optional[str]:
        possible_names = [
            ".commit-checker.yaml",
            ".commit-checker.yml",
            "commit-checker.yaml",
            "commit-checker.yml",
            ".gcc.yaml",
            ".gcc.yml",
        ]
        cwd = os.getcwd()
        for name in possible_names:
            path = os.path.join(cwd, name)
            if os.path.exists(path):
                return path
        return None

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        result = base.copy()
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def __getitem__(self, key: str) -> Any:
        return self.config[key]

    def __contains__(self, key: str) -> bool:
        return key in self.config
