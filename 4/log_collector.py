#!/usr/bin/env python3
"""
Docker 容器日志采集脚本
功能：从 Docker 容器采集日志并保存到本地文件
"""

import os
import sys
import json
import signal
import logging
import argparse
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Set, Dict

try:
    import yaml
    import docker
    from docker.errors import DockerException, NotFound
except ImportError as e:
    print(f"缺少依赖库: {e.name}")
    print("请运行: pip install pyyaml docker paramiko")
    sys.exit(1)

from remote_utils import (
    SSHConnectionPool,
    RemoteDockerClient,
    HostConfig,
)


class LogCollector:
    """Docker 日志采集器（支持多主机）"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.running = False
        self._local_docker_client = None
        self._remote_docker_clients: Dict[str, RemoteDockerClient] = {}
        self._ssh_pool: Optional[SSHConnectionPool] = None

        self._active_targets: Set[str] = set()
        self._target_threads: Dict[str, threading.Thread] = {}
        self._target_stop_flags: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()

        self._setup_logging()
        self._init_hosts()

    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"配置文件不存在: {config_path}")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"配置文件解析错误: {e}")
            sys.exit(1)

    def _setup_logging(self):
        """设置脚本自身的日志"""
        sys_cfg = self.config.get("system_log", {})
        log_dir = Path(sys_cfg.get("directory", "./system_logs"))
        log_dir.mkdir(parents=True, exist_ok=True)

        collector_cfg = self.config["log_collector"]
        log_level = collector_cfg.get("log_level", "INFO")
        log_file = log_dir / "log_collector.log"

        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format=sys_cfg.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger("LogCollector")

    def _init_hosts(self):
        """初始化所有主机连接"""
        hosts_cfg = self.config.get("hosts", [])

        if not hosts_cfg:
            self.logger.info("未配置 hosts，使用默认本地 Docker")
            hosts_cfg = [{"name": "local", "type": "local"}]

        pool_cfg = self.config.get("connection_pool", {})
        self._ssh_pool = SSHConnectionPool(
            max_idle_time=pool_cfg.get("max_idle_time", 300),
            cleanup_interval=pool_cfg.get("cleanup_interval", 60),
        )
        self._ssh_pool.start_cleanup()

        local_connected = False
        for host_cfg in hosts_cfg:
            host_name = host_cfg.get("name")
            host_type = host_cfg.get("type", "local")

            if host_type == "local":
                if self._connect_local_docker():
                    local_connected = True
                    self.logger.info(f"已配置本地主机: {host_name}")
            elif host_type == "remote":
                try:
                    remote_cfg = HostConfig.from_dict(host_cfg)
                    remote_client = RemoteDockerClient(remote_cfg, self._ssh_pool)

                    if remote_client.ping():
                        self._remote_docker_clients[host_name] = remote_client
                        self.logger.info(f"已连接远程主机: {host_name} ({remote_cfg.host}:{remote_cfg.port})")
                    else:
                        self.logger.warning(f"远程主机 Docker 不可用: {host_name}")
                except Exception as e:
                    self.logger.error(f"初始化远程主机失败 {host_name}: {e}")
            else:
                self.logger.warning(f"未知的主机类型: {host_type} (主机: {host_name})")

        if not local_connected and not self._remote_docker_clients:
            self.logger.error("没有可用的 Docker 连接")
            sys.exit(1)

        self.logger.info(f"共配置 {len(self._remote_docker_clients) + (1 if local_connected else 0)} 台主机")

    def _connect_local_docker(self) -> bool:
        """连接本地 Docker 客户端"""
        docker_cfg = self.config.get("docker", {})
        try:
            self._local_docker_client = docker.DockerClient(
                base_url=docker_cfg.get("base_url", "unix:///var/run/docker.sock"),
                tls=docker_cfg.get("tls_verify", False),
                timeout=docker_cfg.get("timeout", 10)
            )
            self._local_docker_client.ping()
            self.logger.info("成功连接到本地 Docker 守护进程")
            return True
        except DockerException as e:
            self.logger.warning(f"连接本地 Docker 失败: {e}")
            self._local_docker_client = None
            return False

    def _get_all_targets(self) -> List[str]:
        """获取所有主机上的目标容器（格式: {host}__{container}）"""
        collector_cfg = self.config["log_collector"]
        target_names = collector_cfg.get("target_containers", [])
        exclude_names = collector_cfg.get("exclude_containers", [])

        all_targets = []

        if self._local_docker_client:
            try:
                containers = self._local_docker_client.containers.list(all=False)
                for container in containers:
                    name = container.name
                    if exclude_names and name in exclude_names:
                        continue
                    if target_names and name not in target_names:
                        continue
                    all_targets.append(f"local__{name}")
            except Exception as e:
                self.logger.error(f"获取本地容器列表失败: {e}")

        for host_name, remote_client in self._remote_docker_clients.items():
            try:
                containers = remote_client.list_containers()
                for name in containers:
                    if exclude_names and name in exclude_names:
                        continue
                    if target_names and name not in target_names:
                        continue
                    all_targets.append(f"{host_name}__{name}")
            except Exception as e:
                self.logger.error(f"获取远程主机 {host_name} 容器列表失败: {e}")

        self.logger.info(f"共找到 {len(all_targets)} 个目标容器（来自所有主机）")
        return all_targets

    def _parse_target(self, target: str) -> tuple:
        """解析目标标识 (host__container)"""
        if "__" in target:
            parts = target.split("__", 1)
            return parts[0], parts[1]
        return "local", target

    def _parse_since(self, since: str) -> int:
        """解析 since 参数为 Unix 时间戳"""
        if not since or since.lower() == "all":
            return 0

        unit = since[-1].lower()
        try:
            value = int(since[:-1])
        except ValueError:
            return 0

        now = datetime.now()
        if unit == "h":
            delta = timedelta(hours=value)
        elif unit == "d":
            delta = timedelta(days=value)
        elif unit == "m":
            delta = timedelta(minutes=value)
        elif unit == "s":
            delta = timedelta(seconds=value)
        else:
            return 0

        return int((now - delta).timestamp())

    def _format_log_line(
        self,
        host_name: str,
        container_name: str,
        log_entry: bytes,
        fmt: str
    ) -> str:
        """格式化日志行"""
        try:
            line = log_entry.decode("utf-8", errors="replace").strip()
        except Exception:
            line = str(log_entry)

        if fmt == "json":
            return json.dumps({
                "timestamp": datetime.now().isoformat(),
                "host": host_name,
                "container": container_name,
                "message": line
            }, ensure_ascii=False)
        else:
            return f"[{datetime.now().isoformat()}] [{host_name}] [{container_name}] {line}"

    def _get_container_status(self, host_name: str, container_name: str) -> Optional[str]:
        """获取容器状态"""
        if host_name == "local":
            if not self._local_docker_client:
                return None
            try:
                container = self._local_docker_client.containers.get(container_name)
                return container.status
            except NotFound:
                return None
            except Exception:
                return None
        else:
            remote_client = self._remote_docker_clients.get(host_name)
            if not remote_client:
                return None
            return remote_client.get_container_status(container_name)

    def _collect_local_logs(
        self,
        host_name: str,
        container_name: str,
        log_file: Path,
        stop_event: threading.Event,
        collector_cfg: dict,
    ):
        """采集本地 Docker 容器日志"""
        kwargs = {
            "stream": True,
            "follow": collector_cfg.get("follow", True),
            "since": self._parse_since(collector_cfg.get("since", "24h")),
        }

        tail = collector_cfg.get("tail", "all")
        if tail != "all":
            try:
                kwargs["tail"] = int(tail)
            except ValueError:
                kwargs["tail"] = "all"

        container = self._local_docker_client.containers.get(container_name)

        with open(log_file, "a", encoding="utf-8") as f:
            for line in container.logs(**kwargs):
                if stop_event.is_set():
                    break
                if line:
                    formatted = self._format_log_line(
                        host_name, container_name, line,
                        collector_cfg.get("output_format", "json")
                    )
                    f.write(formatted + "\n")
                    f.flush()

    def _collect_remote_logs(
        self,
        host_name: str,
        container_name: str,
        log_file: Path,
        stop_event: threading.Event,
        collector_cfg: dict,
    ):
        """采集远程 Docker 容器日志（通过 SSH）"""
        remote_client = self._remote_docker_clients.get(host_name)
        if not remote_client:
            raise RuntimeError(f"未找到远程主机: {host_name}")

        log_stream = remote_client.stream_logs(
            container_name=container_name,
            follow=collector_cfg.get("follow", True),
            since=collector_cfg.get("since", "24h"),
            tail=collector_cfg.get("tail", "all"),
        )

        with open(log_file, "a", encoding="utf-8") as f:
            for line in log_stream:
                if stop_event.is_set():
                    break
                if line:
                    formatted = self._format_log_line(
                        host_name, container_name, line,
                        collector_cfg.get("output_format", "json")
                    )
                    f.write(formatted + "\n")
                    f.flush()

    def collect_container_logs(self, target: str):
        """采集单个容器的日志（带重连机制，支持多主机）

        Args:
            target: 目标标识，格式: {host}__{container}
        """
        host_name, container_name = self._parse_target(target)
        collector_cfg = self.config["log_collector"]

        output_base_dir = Path(collector_cfg.get("output_dir", "./logs"))
        output_dir = output_base_dir / host_name
        output_dir.mkdir(parents=True, exist_ok=True)

        log_file = output_dir / f"{container_name}.log"
        self.logger.info(f"开始采集容器日志: {host_name}/{container_name}")

        stop_event = self._target_stop_flags.get(target)
        if stop_event is None:
            return

        retry_count = 0
        max_retries = collector_cfg.get("max_retries", 10)
        base_retry_delay = collector_cfg.get("retry_delay", 2)

        while not stop_event.is_set():
            try:
                status = self._get_container_status(host_name, container_name)

                if status is None:
                    self.logger.warning(
                        f"容器不存在: {host_name}/{container_name}，等待 5 秒后重试..."
                    )
                    time.sleep(5)
                    continue

                if status != "running":
                    self.logger.info(
                        f"容器 {host_name}/{container_name} 状态为 {status}，等待 5 秒后重试..."
                    )
                    time.sleep(5)
                    continue

                retry_count = 0
                self.logger.info(
                    f"成功连接到容器 {host_name}/{container_name}，开始接收日志流"
                )

                if host_name == "local":
                    self._collect_local_logs(
                        host_name, container_name, log_file, stop_event, collector_cfg
                    )
                else:
                    self._collect_remote_logs(
                        host_name, container_name, log_file, stop_event, collector_cfg
                    )

                self.logger.info(f"容器日志流结束: {host_name}/{container_name}")

            except Exception as e:
                if stop_event.is_set():
                    break

                retry_count += 1
                if max_retries > 0 and retry_count > max_retries:
                    self.logger.error(
                        f"采集容器 {host_name}/{container_name} 日志超过最大重试次数 {max_retries}，停止采集"
                    )
                    break

                delay = min(base_retry_delay * (2 ** (retry_count - 1)), 30)
                self.logger.warning(
                    f"采集容器 {host_name}/{container_name} 日志出错: {e}，"
                    f"第 {retry_count} 次重试，等待 {delay} 秒"
                )
                time.sleep(delay)

        self.logger.info(f"停止采集容器日志: {host_name}/{container_name}")

    def _start_target_collector(self, target: str):
        """启动单个目标的采集线程"""
        with self._lock:
            if target in self._active_targets:
                return

            stop_event = threading.Event()
            self._target_stop_flags[target] = stop_event
            self._active_targets.add(target)

            t = threading.Thread(
                target=self.collect_container_logs,
                args=(target,),
                daemon=True
            )
            self._target_threads[target] = t
            t.start()

            host_name, container_name = self._parse_target(target)
            self.logger.info(f"已启动采集线程: {host_name}/{container_name}")

    def _stop_target_collector(self, target: str):
        """停止单个目标的采集线程"""
        with self._lock:
            if target not in self._active_targets:
                return

            stop_event = self._target_stop_flags.pop(target, None)
            if stop_event:
                stop_event.set()

            thread = self._target_threads.pop(target, None)
            self._active_targets.discard(target)

            host_name, container_name = self._parse_target(target)
            self.logger.info(f"已停止采集线程: {host_name}/{container_name}")

    def _monitor_targets(self):
        """监控所有主机上的容器变化（新增/消失/重启）"""
        monitor_interval = self.config["log_collector"].get("monitor_interval", 10)
        self.logger.info("启动多主机容器状态监控")

        while self.running:
            try:
                current_targets = set(self._get_all_targets())

                with self._lock:
                    to_add = current_targets - self._active_targets
                    to_remove = self._active_targets - current_targets

                for target in to_add:
                    host_name, container_name = self._parse_target(target)
                    self.logger.info(f"发现新容器: {host_name}/{container_name}")
                    self._start_target_collector(target)

                for target in to_remove:
                    host_name, container_name = self._parse_target(target)
                    self.logger.info(f"容器已消失: {host_name}/{container_name}")
                    self._stop_target_collector(target)

            except Exception as e:
                self.logger.error(f"监控容器状态出错: {e}")

            time.sleep(monitor_interval)

    def start(self):
        """启动采集器"""
        self.running = True

        def handle_signal(signum, frame):
            self.logger.info("收到停止信号，正在优雅退出...")
            self.running = False

            with self._lock:
                for stop_event in self._target_stop_flags.values():
                    stop_event.set()

            if self._ssh_pool:
                self._ssh_pool.close_all()

            sys.exit(0)

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        targets = self._get_all_targets()
        if not targets:
            self.logger.warning("没有找到任何可采集的容器，等待容器出现...")

        for target in targets:
            self._start_target_collector(target)

        self._monitor_targets()

    def stop(self):
        """停止采集器"""
        self.running = False
        with self._lock:
            for stop_event in self._target_stop_flags.values():
                stop_event.set()

        if self._ssh_pool:
            self._ssh_pool.close_all()


def main():
    parser = argparse.ArgumentParser(description="Docker 容器日志采集工具")
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="配置文件路径（默认: config.yaml）"
    )
    parser.add_argument(
        "-d", "--daemon",
        action="store_true",
        help="以守护进程方式运行"
    )
    args = parser.parse_args()

    collector = LogCollector(config_path=args.config)
    collector.start()


if __name__ == "__main__":
    main()
