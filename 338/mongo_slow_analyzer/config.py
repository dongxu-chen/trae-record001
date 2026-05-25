import yaml
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(path: Path | str | None = None) -> dict:
    """加载YAML配置文件"""
    target = Path(path) if path else _CONFIG_PATH
    with open(target, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg
