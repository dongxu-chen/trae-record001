"""全局配置与常量定义。

使用方式::

    from configdrift.config import settings

配置加载优先级:
    1. 命令行参数
    2. 环境变量
    3. YAML 配置文件 (默认 ``configdrift.yaml``
    4. 代码内默认值

"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class ServerConfig:
    """单个被监控服务器配置."""

    name: str
    host: str
    port: int = 22
    username: str = "root"
    password: Optional[str] = None
    key_file: Optional[str] = None
    services: List[str] = field(default_factory=lambda: ["nginx", "mysql", "redis", "kafka"])


@dataclass
class ServiceSpec:
    """单个服务的监控规则定义."""

    name: str
    config_path: str
    parser: str = "auto"
    sudo: bool = False
    # 修复命令模板: Optional[str] = None


@dataclass
class Settings:
    """程序设置容器."""

    servers: List[ServerConfig] = field(default_factory=list)
    services: Dict[str, ServiceSpec] = field(default_factory=dict)
    baseline_dir: str = "baselines"
    history_dir: str = "history"
    report_dir: str = "reports"
    log_level: str = "INFO"
    celery_broker: str = "redis://localhost:6379/0"
    celery_backend: str = "redis://localhost:6379/1"
    schedule_minutes: int = 60
    email_on_drift: bool = False
    smtp: Dict[str, Any] = field(default_factory=dict)
    # 合规检查
    compliance_enabled: bool = True
    cis_profile: str = "level1"  # level1 / level2
    # 影响分析
    impact_enabled: bool = False
    metrics_endpoint: str = ""  # Prometheus URL, e.g. http://prom:9090
    metrics_window_minutes: int = 30


def _build_default_services() -> Dict[str, ServiceSpec]:
    """默认服务监控规则."""
    return {
        "nginx": ServiceSpec(
            name="nginx",
            config_path="/etc/nginx/nginx.conf",
            parser="kvshell",
            sudo=True,
        ),
        "mysql": ServiceSpec(
            name="mysql",
            config_path="/etc/mysql/my.cnf",
            parser="ini",
            sudo=True,
        ),
        "redis": ServiceSpec(
            name="redis",
            config_path="/etc/redis/redis.conf",
            parser="kvshell",
        ),
        "kafka": ServiceSpec(
            name="kafka",
            config_path="/opt/kafka/config/server.properties",
            parser="kvshell",
        ),
    }


def load_settings(path: str = "configdrift.yaml") -> Settings:
    """从 YAML 文件加载设置 (如果不存在则使用默认值)."""
    s = Settings(services=_build_default_services())
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        for k, v in (data.get("services") or {}).items():
            s.services[k] = ServiceSpec(name=k, **v)

        servers = data.get("servers", [])
        s.servers = [ServerConfig(**sv) for sv in servers]

        for key in ("baseline_dir", "history_dir", "report_dir", "log_level",
                   "celery_broker", "celery_backend",
                   "schedule_minutes", "email_on_drift", "smtp",
                   "compliance_enabled", "cis_profile",
                   "impact_enabled", "metrics_endpoint",
                   "metrics_window_minutes"):
            if key in data:
                setattr(s, key, data[key])
    return s


settings = load_settings()
