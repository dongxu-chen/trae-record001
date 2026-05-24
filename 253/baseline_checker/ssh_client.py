import paramiko
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class SSHClient:
    def __init__(self, hostname: str, port: int = 22, username: str = "root",
                 password: Optional[str] = None, key_file: Optional[str] = None,
                 timeout: int = 30):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.key_file = key_file
        self.timeout = timeout
        self.client = None
        self.sftp = None

    def connect(self) -> bool:
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if self.key_file:
                self.client.connect(
                    hostname=self.hostname,
                    port=self.port,
                    username=self.username,
                    key_filename=self.key_file,
                    timeout=self.timeout,
                    allow_agent=False,
                    look_for_keys=False
                )
            else:
                self.client.connect(
                    hostname=self.hostname,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=self.timeout,
                    allow_agent=False,
                    look_for_keys=False
                )

            self.sftp = self.client.open_sftp()
            logger.info(f"Successfully connected to {self.hostname}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {self.hostname}:{self.port} - {str(e)}")
            return False

    def execute_command(self, command: str) -> Tuple[int, str, str]:
        if not self.client:
            return -1, "", "Not connected"

        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=60)
            exit_code = stdout.channel.recv_exit_status()
            output = stdout.read().decode("utf-8", errors="ignore").strip()
            error = stderr.read().decode("utf-8", errors="ignore").strip()
            return exit_code, output, error
        except Exception as e:
            logger.error(f"Command execution failed: {str(e)}")
            return -1, "", str(e)

    def read_file(self, file_path: str) -> Optional[str]:
        if not self.sftp:
            return None

        try:
            with self.sftp.file(file_path, "r") as f:
                return f.read().decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {str(e)}")
            return None

    def get_file_stat(self, file_path: str) -> Optional[dict]:
        if not self.sftp:
            return None

        try:
            stat = self.sftp.stat(file_path)
            return {
                "permission": oct(stat.st_mode)[-3:],
                "owner": stat.st_uid,
                "group": stat.st_gid,
                "size": stat.st_size,
                "mtime": stat.st_mtime
            }
        except Exception as e:
            logger.error(f"Failed to stat file {file_path}: {str(e)}")
            return None

    def close(self):
        if self.sftp:
            self.sftp.close()
        if self.client:
            self.client.close()
        logger.info(f"Connection to {self.hostname} closed")
