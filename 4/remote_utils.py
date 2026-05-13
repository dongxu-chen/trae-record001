#!/usr/bin/env python3
"""
远程主机连接工具库
功能：SSH 连接池管理、远程 Docker 操作封装
"""

import sys
import time
import logging
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from queue import Queue, Empty

try:
    import paramiko
    from paramiko.ssh_exception import SSHException, NoValidConnectionsError, AuthenticationException
except ImportError:
    print("缺少依赖库: paramiko")
    print("请运行: pip install paramiko")
    sys.exit(1)


logger = logging.getLogger("RemoteUtils")


@dataclass
class HostConfig:
    """主机配置"""
    name: str
    host: str
    port: int = 22
    user: str = "root"
    password: Optional[str] = None
    key_file: Optional[str] = None
    key_passphrase: Optional[str] = None
    timeout: int = 10
    connect_timeout: int = 15
    keepalive_interval: int = 30

    @classmethod
    def from_dict(cls, data: dict) -> "HostConfig":
        return cls(
            name=data.get("name", data.get("host", "unknown")),
            host=data["host"],
            port=data.get("port", 22),
            user=data.get("user", "root"),
            password=data.get("password"),
            key_file=data.get("key_file"),
            key_passphrase=data.get("key_passphrase"),
            timeout=data.get("timeout", 10),
            connect_timeout=data.get("connect_timeout", 15),
            keepalive_interval=data.get("keepalive_interval", 30),
        )


class SSHConnection:
    """SSH 连接封装"""

    def __init__(self, host_config: HostConfig):
        self.host_config = host_config
        self._client: Optional[paramiko.SSHClient] = None
        self._lock = threading.Lock()
        self._last_used: float = 0
        self._connected: bool = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._client is not None

    def connect(self) -> bool:
        """建立 SSH 连接"""
        with self._lock:
            if self._connected:
                return True

            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                connect_kwargs = {
                    "hostname": self.host_config.host,
                    "port": self.host_config.port,
                    "username": self.host_config.user,
                    "timeout": self.host_config.connect_timeout,
                    "allow_agent": True,
                    "look_for_keys": True,
                }

                if self.host_config.password:
                    connect_kwargs["password"] = self.host_config.password

                if self.host_config.key_file:
                    connect_kwargs["key_filename"] = self.host_config.key_file
                    if self.host_config.key_passphrase:
                        connect_kwargs["passphrase"] = self.host_config.key_passphrase

                client.connect(**connect_kwargs)

                transport = client.get_transport()
                if transport:
                    transport.set_keepalive(self.host_config.keepalive_interval)

                self._client = client
                self._connected = True
                self._last_used = time.time()

                logger.info(
                    f"SSH 连接成功: {self.host_config.user}@{self.host_config.host}:{self.host_config.port}"
                )
                return True

            except AuthenticationException as e:
                logger.error(f"SSH 认证失败 {self.host_config.name}: {e}")
            except NoValidConnectionsError as e:
                logger.error(f"无法连接到主机 {self.host_config.name}: {e}")
            except SSHException as e:
                logger.error(f"SSH 连接异常 {self.host_config.name}: {e}")
            except Exception as e:
                logger.error(f"SSH 连接失败 {self.host_config.name}: {e}")

            return False

    def disconnect(self):
        """断开 SSH 连接"""
        with self._lock:
            if self._client:
                try:
                    self._client.close()
                except Exception:
                    pass
                self._client = None
            self._connected = False
            logger.info(f"SSH 连接已断开: {self.host_config.name}")

    def execute_command(
        self,
        command: str,
        timeout: Optional[int] = None,
        stream: bool = False,
    ) -> Any:
        """执行远程命令

        Args:
            command: 要执行的命令
            timeout: 超时时间
            stream: 是否以流方式返回输出

        Returns:
            如果 stream=True，返回 (stdin, stdout, stderr) channel
            否则返回 (exit_code, stdout_text, stderr_text)
        """
        if not self._connected:
            if not self.connect():
                raise RuntimeError(f"无法连接到主机 {self.host_config.name}")

        with self._lock:
            try:
                self._last_used = time.time()
                stdin, stdout, stderr = self._client.exec_command(
                    command,
                    timeout=timeout or self.host_config.timeout,
                    get_pty=False,
                )

                if stream:
                    return stdin, stdout, stderr

                stdout_text = stdout.read().decode("utf-8", errors="replace")
                stderr_text = stderr.read().decode("utf-8", errors="replace")
                exit_code = stdout.channel.recv_exit_status()

                return exit_code, stdout_text, stderr_text

            except SSHException as e:
                logger.warning(f"SSH 会话异常，尝试重连: {e}")
                self.disconnect()
                if self.connect():
                    return self.execute_command(command, timeout, stream)
                raise
            except Exception as e:
                logger.error(f"执行远程命令失败 {self.host_config.name}: {e}")
                raise

    def health_check(self) -> bool:
        """检查连接是否健康"""
        if not self._connected:
            return False

        try:
            exit_code, _, _ = self.execute_command("echo ok", timeout=5)
            return exit_code == 0
        except Exception:
            return False


class SSHConnectionPool:
    """SSH 连接池（按主机名管理）"""

    def __init__(self, max_idle_time: int = 300, cleanup_interval: int = 60):
        self._connections: Dict[str, SSHConnection] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()
        self._max_idle_time = max_idle_time
        self._cleanup_interval = cleanup_interval
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False

    def get_connection(self, host_config: HostConfig) -> SSHConnection:
        """获取或创建一个 SSH 连接"""
        host_name = host_config.name

        with self._global_lock:
            if host_name not in self._connections:
                self._connections[host_name] = SSHConnection(host_config)
                self._locks[host_name] = threading.Lock()
            conn = self._connections[host_name]

        if not conn.is_connected:
            with self._locks[host_name]:
                if not conn.is_connected:
                    conn.connect()

        return conn

    def release_connection(self, host_name: str):
        """释放连接（标记为可复用）"""
        pass

    def remove_connection(self, host_name: str):
        """移除并断开连接"""
        with self._global_lock:
            if host_name in self._connections:
                self._connections[host_name].disconnect()
                del self._connections[host_name]
                del self._locks[host_name]

    def _cleanup_idle_connections(self):
        """清理空闲连接"""
        while self._running:
            try:
                now = time.time()
                to_remove = []

                with self._global_lock:
                    for name, conn in self._connections.items():
                        if now - conn._last_used > self._max_idle_time:
                            if conn.is_connected and not conn.health_check():
                                to_remove.append(name)

                    for name in to_remove:
                        self._connections[name].disconnect()
                        del self._connections[name]
                        del self._locks[name]

                if to_remove:
                    logger.info(f"清理了 {len(to_remove)} 个空闲连接")

            except Exception as e:
                logger.error(f"清理连接出错: {e}")

            time.sleep(self._cleanup_interval)

    def start_cleanup(self):
        """启动空闲连接清理线程"""
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            return

        self._running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_idle_connections,
            daemon=True,
        )
        self._cleanup_thread.start()

    def stop_cleanup(self):
        """停止清理线程"""
        self._running = False

    def close_all(self):
        """关闭所有连接"""
        self.stop_cleanup()

        with self._global_lock:
            for conn in self._connections.values():
                try:
                    conn.disconnect()
                except Exception:
                    pass
            self._connections.clear()
            self._locks.clear()


class RemoteDockerClient:
    """远程 Docker 客户端（通过 SSH 执行 docker 命令）"""

    def __init__(
        self,
        host_config: HostConfig,
        connection_pool: SSHConnectionPool,
    ):
        self.host_config = host_config
        self.host_name = host_config.name
        self._pool = connection_pool
        self._docker_path = "docker"

    def _exec(self, command: str, timeout: int = 10) -> tuple:
        """执行 docker 命令"""
        conn = self._pool.get_connection(self.host_config)
        return conn.execute_command(f"{self._docker_path} {command}", timeout=timeout)

    def ping(self) -> bool:
        """检查 Docker 是否可用"""
        try:
            exit_code, _, _ = self._exec("info --format '{{.ServerVersion}}'", timeout=15)
            return exit_code == 0
        except Exception:
            return False

    def list_containers(self, all: bool = False) -> List[str]:
        """列出运行中的容器名称"""
        filter_opt = "" if all else "--filter status=running"
        exit_code, stdout, _ = self._exec(
            f"ps {filter_opt} --format '{{{{.Names}}}}'"
        )
        if exit_code != 0:
            return []
        return [line.strip() for line in stdout.strip().split("\n") if line.strip()]

    def get_container_status(self, container_name: str) -> Optional[str]:
        """获取容器状态"""
        exit_code, stdout, _ = self._exec(
            f"inspect --format '{{{{.State.Status}}}}' {container_name}"
        )
        if exit_code != 0:
            return None
        return stdout.strip()

    def stream_logs(
        self,
        container_name: str,
        follow: bool = True,
        since: str = None,
        tail: str = "all",
    ):
        """流式获取容器日志

        Returns: 一个生成器，逐行产出日志字节
        """
        cmd_parts = ["logs"]
        if follow:
            cmd_parts.append("-f")
        if tail and tail != "all":
            cmd_parts.append(f"--tail {tail}")
        if since:
            cmd_parts.append(f"--since {since}")
        cmd_parts.append(container_name)

        command = f"{self._docker_path} {' '.join(cmd_parts)}"

        conn = self._pool.get_connection(self.host_config)

        try:
            _, stdout, _ = conn.execute_command(command, stream=True)

            channel = stdout.channel
            channel.settimeout(None)

            buffer = b""
            while not channel.exit_status_ready():
                if channel.recv_ready():
                    chunk = channel.recv(4096)
                    if not chunk:
                        break

                    buffer += chunk
                    lines = buffer.split(b"\n")
                    buffer = lines.pop(-1)

                    for line in lines:
                        if line:
                            yield line + b"\n"

            if buffer:
                yield buffer

        except Exception as e:
            logger.error(f"获取远程日志失败 {self.host_name}/{container_name}: {e}")
            raise

    def container_exists(self, container_name: str) -> bool:
        """检查容器是否存在"""
        exit_code, _, _ = self._exec(f"inspect {container_name} > /dev/null 2>&1; echo $?")
        return exit_code == 0
