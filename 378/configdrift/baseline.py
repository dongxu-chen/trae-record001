"""基准配置的持久化与加载."""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict

from configdrift.logger import get_logger

logger = get_logger(__name__)


def _safe(name: str) -> str:
    """替换文件名中不安全的字符."""
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)


def baseline_path(baseline_dir: str, server: str, service: str) -> str:
    return os.path.join(baseline_dir, f"{_safe(server)}.{_safe(service)}.json")


def save_baseline(baseline_dir: str, server: str, service: str,
                  data: Dict[str, Any]) -> str:
    os.makedirs(baseline_dir, exist_ok=True)
    path = baseline_path(baseline_dir, server, service)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
    logger.info("基准已保存: %s", path)
    return path


def load_baseline(baseline_dir: str, server: str, service: str) -> Dict[str, Any]:
    path = baseline_path(baseline_dir, server, service)
    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到基准: {path},请先运行 baselines 子命令.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
