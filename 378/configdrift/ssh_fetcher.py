"""SSH 远程配置采集模块.

封装 paramiko,通过 SSH 登录服务器拉取配置文件内容.
"""
from __future__ import annotations

from typing import Optional

import paramiko

from configdrift.config import ServerConfig
from configdrift.logger import get_logger

logger = get_logger(__name__)


def _connect(server: ServerConfig) -> paramiko.SSHClient:
    """建立 SSH 连接并返回 client."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs = dict(
        hostname=server.host,
        port=server.port,
        username=server.username,
        timeout=15,
        banner_timeout=15,
        auth_timeout=15,
        allow_agent=False,
        look_for_keys=False,
    )
    if server.key_file:
        kwargs["key_filename"] = server.key_file
    elif server.password:
        kwargs["password"] = server.password
    else:
        logger.warning("未提供密码或密钥,尝试使用默认密钥文件")
        kwargs["look_for_keys"] = True
    client.connect(**kwargs)
    return client


def fetch_file(
    server: ServerConfig,
    remote_path: str,
    sudo: bool = False,
    sudo_password: Optional[str] = None,
) -> str:
    """拉取远程文件内容.

    Args:
        server: 目标服务器信息.
        remote_path: 远程文件绝对路径.
        sudo: 是否通过 sudo 读取 (用于需要 root 权限的配置).
        sudo_password: sudo 密码,若为空则复用 server.password.

    Returns:
        原始文件内容字符串.

    Raises:
        RuntimeError: 当命令执行失败或文件不存在时抛出.
    """
    client = _connect(server)
    try:
        if sudo:
            pw = sudo_password or server.password or ""
            cmd = f"sudo -S cat {remote_path}"
            stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
            stdin.write(pw + "\n")
            stdin.flush()
        else:
            cmd = f"cat {remote_path}"
            stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        rc = stdout.channel.recv_exit_status()
        if rc != 0:
            raise RuntimeError(
                f"[{server.name}] 读取 {remote_path} 失败(rc={rc}): {err[:500]}"
            )
        logger.debug("[%s] 拉取 %s (%d bytes)", server.name, remote_path, len(out))
        return out
    finally:
        client.close()


def run_remote(
    server: ServerConfig,
    command: str,
    sudo: bool = False,
    sudo_password: Optional[str] = None,
) -> str:
    """在远程服务器执行任意命令并返回 stdout."""
    client = _connect(server)
    try:
        if sudo:
            pw = sudo_password or server.password or ""
            cmd = f"sudo -S bash -c {shlex_quote(command)}"
            stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
            stdin.write(pw + "\n")
            stdin.flush()
        else:
            stdin, stdout, stderr = client.exec_command(command)
        out = stdout.read().decode("utf-8", errors="replace")
        rc = stdout.channel.recv_exit_status()
        if rc != 0:
            raise RuntimeError(
                f"[{server.name}] 命令失败 ({command}) rc={rc}"
            )
        return out
    finally:
        client.close()


def shlex_quote(s: str) -> str:
    """简易 shell 单引号转义 (shlex.quote 的简单实现),避免额外依赖."""
    return "'" + s.replace("'", "'\\''") + "'"
