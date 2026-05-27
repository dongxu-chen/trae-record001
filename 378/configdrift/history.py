"""配置历史版本管理.

功能:
    - 每次采集都保存为一个版本,带时间戳,永不覆盖
    - 支持版本列表查询、版本对比、按版本回滚
    - 版本元数据存于 ``history/{server}.{service}/meta.json``,
      内容存于 ``history/{server}.{service}/{version}.json``
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from configdrift.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VersionMeta:
    """单个版本元数据."""

    version: str
    timestamp: float
    server: str
    service: str
    content_hash: str
    comment: str = ""
    operator: str = "system"
    is_baseline: bool = False
    drift_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VersionedConfig:
    """带元数据的配置快照."""

    meta: VersionMeta
    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {"meta": self.meta.to_dict(), "data": self.data}


def _safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)


def _history_dir(history_dir: str, server: str, service: str) -> str:
    return os.path.join(history_dir, f"{_safe(server)}.{_safe(service)}")


def _meta_path(history_dir: str, server: str, service: str) -> str:
    return os.path.join(_history_dir(history_dir, server, service), "meta.json")


def _version_path(history_dir: str, server: str, service: str, version: str) -> str:
    return os.path.join(_history_dir(history_dir, server, service), f"{version}.json")


def _load_meta(history_dir: str, server: str, service: str) -> List[Dict[str, Any]]:
    path = _meta_path(history_dir, server, service)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_meta(history_dir: str, server: str, service: str,
               meta_list: List[Dict[str, Any]]) -> None:
    os.makedirs(_history_dir(history_dir, server, service), exist_ok=True)
    with open(_meta_path(history_dir, server, service), "w", encoding="utf-8") as f:
        json.dump(meta_list, f, ensure_ascii=False, indent=2)


def save_version(history_dir: str,
                 server: str,
                 service: str,
                 data: Dict[str, Any],
                 content_hash: str = "",
                 comment: str = "",
                 operator: str = "system",
                 is_baseline: bool = False,
                 drift_count: int = 0) -> VersionMeta:
    """保存一个新版本,返回其元数据."""
    version = time.strftime("%Y%m%d_%H%M%S")
    # 避免同一秒内重名
    meta_list = _load_meta(history_dir, server, service)
    while any(m["version"] == version for m in meta_list):
        version += "_" + str(int(time.time() * 1000) % 1000)

    meta = VersionMeta(
        version=version,
        timestamp=time.time(),
        server=server,
        service=service,
        content_hash=content_hash,
        comment=comment,
        operator=operator,
        is_baseline=is_baseline,
        drift_count=drift_count,
    )
    os.makedirs(_history_dir(history_dir, server, service), exist_ok=True)
    with open(_version_path(history_dir, server, service, version),
              "w", encoding="utf-8") as f:
        json.dump(VersionedConfig(meta=meta, data=data).to_dict(),
                  f, ensure_ascii=False, indent=2)

    meta_list.append(meta.to_dict())
    _save_meta(history_dir, server, service, meta_list)
    logger.info("[%s/%s] 保存版本 %s", server, service, version)
    return meta


def list_versions(history_dir: str, server: str, service: str,
                  limit: int = 20) -> List[Dict[str, Any]]:
    """返回版本列表 (最新在前)."""
    meta_list = _load_meta(history_dir, server, service)
    meta_list.sort(key=lambda m: m["timestamp"], reverse=True)
    return meta_list[:limit]


def load_version(history_dir: str, server: str, service: str,
                 version: str) -> Optional[VersionedConfig]:
    """加载指定版本,若不存在返回 None."""
    path = _version_path(history_dir, server, service, version)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return VersionedConfig(
        meta=VersionMeta(**raw["meta"]),
        data=raw["data"],
    )


def latest_version(history_dir: str, server: str, service: str) -> Optional[VersionedConfig]:
    """获取最新版本."""
    meta_list = _load_meta(history_dir, server, service)
    if not meta_list:
        return None
    meta_list.sort(key=lambda m: m["timestamp"], reverse=True)
    return load_version(history_dir, server, service, meta_list[0]["version"])


def diff_versions(history_dir: str, server: str, service: str,
                  v1: str, v2: str) -> Dict[str, Any]:
    """对比两个版本,返回结构化 diff."""
    a = load_version(history_dir, server, service, v1)
    b = load_version(history_dir, server, service, v2)
    if not a or not b:
        return {"error": "version not found"}

    from configdrift.detector import detect_drift
    items = detect_drift(a.data, b.data)
    return {
        "server": server,
        "service": service,
        "from_version": v1,
        "to_version": v2,
        "total": len(items),
        "items": [asdict(it) for it in items],
    }


def rollback_to_version(history_dir: str, server: str, service: str,
                        version: str, baseline_dir: str) -> bool:
    """回滚 baseline 到指定历史版本,返回是否成功."""
    vc = load_version(history_dir, server, service, version)
    if not vc:
        logger.error("版本 %s 不存在", version)
        return False
    from configdrift.baseline import save_baseline
    save_baseline(baseline_dir, server, service, vc.data)
    logger.info("[%s/%s] 已回滚到版本 %s", server, service, version)
    # 再保存一份回滚记录
    save_version(history_dir, server, service, vc.data,
                 content_hash=vc.meta.content_hash,
                 comment=f"rollback to {version}",
                 operator="rollback",
                 is_baseline=True)
    return True
