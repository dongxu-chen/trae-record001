import os
import io
import time
import logging
import hashlib
import paramiko
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Callable
from datetime import datetime, timedelta


class SFTPUploader:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        remote_base_dir: str,
        logger: Optional[logging.Logger] = None
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.remote_base_dir = remote_base_dir
        self.logger = logger or logging.getLogger(__name__)
        self.ssh_client = None
        self.sftp = None

    def connect(self) -> None:
        self.logger.info(f"连接SFTP服务器: {self.host}:{self.port}")
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            timeout=30
        )
        self.sftp = self.ssh_client.open_sftp()
        self.logger.info("SFTP连接成功")

    def disconnect(self) -> None:
        if self.sftp:
            self.sftp.close()
        if self.ssh_client:
            self.ssh_client.close()
        self.logger.info("SFTP连接已关闭")

    def ensure_remote_dir(self, remote_path: str) -> None:
        dirs = remote_path.split('/')
        current_path = ''
        for dir_part in dirs:
            if dir_part:
                current_path += '/' + dir_part
                try:
                    self.sftp.stat(current_path)
                except FileNotFoundError:
                    self.sftp.mkdir(current_path)
                    self.logger.debug(f"创建远程目录: {current_path}")

    def get_remote_file_list(self, task_name: str) -> Dict[str, dict]:
        if not self.sftp:
            self.connect()

        remote_dir = f"{self.remote_base_dir}/{task_name}"
        file_info_map = {}

        try:
            files = self.sftp.listdir_attr(remote_dir)
            for file_attr in files:
                if file_attr.filename.endswith('.tar.gz'):
                    file_info_map[file_attr.filename] = {
                        'filename': file_attr.filename,
                        'size': file_attr.st_size,
                        'mtime': file_attr.st_mtime
                    }
        except FileNotFoundError:
            self.logger.warning(f"远程目录不存在: {remote_dir}")

        return file_info_map

    def get_latest_backup_time(self, task_name: str) -> float:
        remote_files = self.get_remote_file_list(task_name)
        if not remote_files:
            return 0
        return max(info['mtime'] for info in remote_files.values())

    def upload_file(self, local_file_path: str, task_name: str) -> str:
        if not self.sftp:
            self.connect()

        remote_dir = f"{self.remote_base_dir}/{task_name}"
        self.ensure_remote_dir(remote_dir)

        file_name = os.path.basename(local_file_path)
        remote_path = f"{remote_dir}/{file_name}"

        self.logger.info(f"上传文件: {local_file_path} -> {remote_path}")
        
        file_size = os.path.getsize(local_file_path)
        uploaded_size = [0]
        
        def progress_callback(transferred, total):
            uploaded_size[0] = transferred
            percent = (transferred / total) * 100
            if transferred % (10 * 1024 * 1024) == 0:
                self.logger.debug(f"上传进度: {percent:.1f}% ({transferred / (1024*1024):.1f} MB / {total / (1024*1024):.1f} MB)")

        self.sftp.put(local_file_path, remote_path, callback=progress_callback)
        
        self.logger.info(f"文件上传完成: {remote_path}")
        return remote_path

    def stream_upload(self, file_obj, remote_path: str, total_size: int) -> None:
        if not self.sftp:
            self.connect()

        self.logger.info(f"开始流式上传: {remote_path}")
        uploaded = 0

        with self.sftp.open(remote_path, 'wb', bufsize=1024*1024) as remote_file:
            while True:
                chunk = file_obj.read(1024 * 1024)
                if not chunk:
                    break
                remote_file.write(chunk)
                uploaded += len(chunk)
                percent = (uploaded / total_size) * 100 if total_size > 0 else 0
                if uploaded % (10 * 1024 * 1024) == 0:
                    self.logger.debug(f"流式上传进度: {percent:.1f}% ({uploaded / (1024*1024):.1f} MB)")

        self.logger.info(f"流式上传完成: {remote_path}")

    def list_backups(self, task_name: str) -> List[dict]:
        if not self.sftp:
            self.connect()

        remote_dir = f"{self.remote_base_dir}/{task_name}"
        backups = []

        try:
            files = self.sftp.listdir_attr(remote_dir)
            for file_attr in files:
                if file_attr.filename.endswith('.tar.gz'):
                    file_info = {
                        'filename': file_attr.filename,
                        'size': file_attr.st_size,
                        'mtime': file_attr.st_mtime,
                        'path': f"{remote_dir}/{file_attr.filename}"
                    }
                    backups.append(file_info)
        except FileNotFoundError:
            self.logger.warning(f"远程目录不存在: {remote_dir}")

        return sorted(backups, key=lambda x: x['mtime'], reverse=True)

    def delete_backup(self, remote_path: str) -> None:
        if not self.sftp:
            self.connect()

        try:
            self.sftp.remove(remote_path)
            self.logger.info(f"删除远程备份: {remote_path}")
        except FileNotFoundError:
            self.logger.warning(f"远程文件不存在: {remote_path}")
        except Exception as e:
            self.logger.error(f"删除远程备份失败 {remote_path}: {e}")

    def cleanup_old_backups(self, task_name: str, retention_days: int) -> Tuple[int, int]:
        backups = self.list_backups(task_name)
        cutoff_time = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
        
        deleted_count = 0
        total_freed_space = 0
        
        for backup in backups:
            if backup['mtime'] < cutoff_time:
                total_freed_space += backup['size']
                self.delete_backup(backup['path'])
                deleted_count += 1
        
        if deleted_count > 0:
            freed_mb = total_freed_space / (1024 * 1024)
            self.logger.info(f"清理了 {deleted_count} 个超过 {retention_days} 天的备份文件，释放空间: {freed_mb:.2f} MB")
        else:
            self.logger.info(f"没有需要清理的备份文件 (保留最近 {retention_days} 天)")
        
        return deleted_count, total_freed_space

    def __enter__(self):
        self.connect()
        return self

    def calculate_remote_md5(self, remote_path: str) -> str:
        if not self.sftp:
            self.connect()

        self.logger.debug(f"计算远程文件MD5: {remote_path}")
        md5_hash = hashlib.md5()
        
        with self.sftp.open(remote_path, 'rb') as remote_file:
            while True:
                chunk = remote_file.read(8192)
                if not chunk:
                    break
                md5_hash.update(chunk)
        
        md5_hex = md5_hash.hexdigest()
        self.logger.debug(f"远程文件MD5: {md5_hex}")
        return md5_hex

    def stream_upload_with_verification(
        self,
        data_stream: io.BytesIO,
        remote_path: str,
        expected_md5: str,
        max_retries: int = 3,
        retry_delay: int = 5
    ) -> bool:
        data_size = data_stream.getbuffer().nbytes
        original_position = data_stream.tell()
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    self.logger.info(f"重试上传 ({attempt}/{max_retries})...")
                    time.sleep(retry_delay)
                
                data_stream.seek(original_position)
                self.stream_upload(data_stream, remote_path, data_size)
                
                remote_md5 = self.calculate_remote_md5(remote_path)
                
                if remote_md5.lower() == expected_md5.lower():
                    self.logger.info(f"MD5校验通过: {expected_md5}")
                    return True
                else:
                    self.logger.warning(f"MD5校验失败 (尝试 {attempt + 1}/{max_retries})")
                    self.logger.warning(f"  期望: {expected_md5}")
                    self.logger.warning(f"  实际: {remote_md5}")
                    
                    try:
                        self.sftp.remove(remote_path)
                    except:
                        pass
                    
            except Exception as e:
                self.logger.error(f"上传失败 (尝试 {attempt + 1}/{max_retries}): {e}")
        
        self.logger.error(f"上传失败，已重试 {max_retries} 次")
        return False

    def upload_with_verification(
        self,
        local_file_path: str,
        task_name: str,
        max_retries: int = 3,
        retry_delay: int = 5
    ) -> Tuple[str, str]:
        from encryption import Encryptor
        encryptor = Encryptor(logger=self.logger)
        
        local_md5 = encryptor.calculate_md5(local_file_path)
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    self.logger.info(f"重试上传 ({attempt}/{max_retries})...")
                    time.sleep(retry_delay)
                
                remote_path = self.upload_file(local_file_path, task_name)
                remote_md5 = self.calculate_remote_md5(remote_path)
                
                if remote_md5.lower() == local_md5.lower():
                    self.logger.info(f"MD5校验通过: {local_md5}")
                    return remote_path, local_md5
                else:
                    self.logger.warning(f"MD5校验失败 (尝试 {attempt + 1}/{max_retries})")
                    try:
                        self.sftp.remove(remote_path)
                    except:
                        pass
                    
            except Exception as e:
                self.logger.error(f"上传失败 (尝试 {attempt + 1}/{max_retries}): {e}")
        
        raise RuntimeError(f"上传失败，已重试 {max_retries} 次")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
