import yaml
import os


class Config:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._load_config()
        return cls._instance

    @classmethod
    def _load_config(cls):
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config.yaml"
        )
        with open(config_path, "r", encoding="utf-8") as f:
            cls._config = yaml.safe_load(f)

    @classmethod
    def get(cls, key, default=None):
        keys = key.split(".")
        value = cls._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
