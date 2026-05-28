"""Redis 集群巡检工具 - 配置加载"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


DEFAULT_CONFIG: Dict[str, Any] = {
    "redis": {
        "host": "127.0.0.1",
        "port": 6379,
        "password": "",
        "socket_timeout": 2.0,
        "socket_connect_timeout": 2.0,
        "retry_on_timeout": True,
        "replication_lag_sample": {
            "duration_sec": 1.0,
            "interval_sec": 0.1,
        },
        "slot_balance": {
            "use_performance_weight": True,
        },
        "hotkey_sample": {
            "max_keys_per_node": 500,
            "scan_count": 500,
        },
        "threshold": {
            "replication_lag_sec": 5.0,
            "mem_fragmentation_ratio": 1.5,
            "mem_fragmentation_by_version": {
                "ge_7_4": 2.0,
                "ge_7_0": 1.8,
                "ge_6_0": 1.5,
                "lt_6_0": 1.3,
            },
            "slot_unbalance_ratio": 0.1,
            "slowlog_usec": 10000,
            "cpu_usage_percent": 80.0,
            "mem_usage_percent": 85.0,
        },
    },
    "clickhouse": {
        "host": "127.0.0.1",
        "port": 9000,
        "user": "default",
        "password": "",
        "database": "redis_inspect",
        "enabled": False,
    },
    "report": {
        "output_dir": "./reports",
        "format": "text",
        "top_n_slowlog": 20,
    },
}


def _deep_merge(base: Dict[str, Any], other: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in other.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | os.PathLike[str] | None = None) -> Dict[str, Any]:
    """加载并合并配置文件与默认值。"""
    if path is None:
        path = Path(__file__).resolve().parent / "config.yaml"
    else:
        path = Path(path)

    cfg: Dict[str, Any] = dict(DEFAULT_CONFIG)
    if path.exists():
        if yaml is None:
            raise RuntimeError("需要 PyYAML 才能读取 config.yaml: pip install pyyaml")
        with path.open("r", encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
        cfg = _deep_merge(cfg, user_cfg)
    return cfg
