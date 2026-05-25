import paramiko
import io
import hashlib
import time
from typing import Optional, Tuple, Dict, Any
from config import SSH_TIMEOUT, SSH_RETRY
from .host_manager import Host


class SSHClient:
    def __init__(self, host: Host):
        self.host = host
        self.client = None
        self.sftp = None

    def connect(self) -> bool:
        for attempt in range(SSH_RETRY):
            try:
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                connect_kwargs = {
                    'hostname': self.host.ip,
                    'port': self.host.port,
                    'username': self.host.username,
                    'timeout': SSH_TIMEOUT,
                    'banner_timeout': SSH_TIMEOUT
                }
                
                if self.host.private_key:
                    private_key = paramiko.RSAKey.from_private_key(
                        io.StringIO(self.host.private_key)
                    )
                    connect_kwargs['pkey'] = private_key
                elif self.host.password:
                    connect_kwargs['password'] = self.host.password
                
                self.client.connect(**connect_kwargs)
                return True
            except Exception as e:
                if attempt == SSH_RETRY - 1:
                    raise Exception(f"SSH连接失败: {str(e)}")
        return False

    def close(self):
        if self.sftp:
            self.sftp.close()
            self.sftp = None
        if self.client:
            self.client.close()
            self.client = None

    def execute_command(self, command: str) -> Dict[str, Any]:
        if not self.client:
            self.connect()
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=SSH_TIMEOUT)
            exit_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode('utf-8', errors='replace')
            stderr_data = stderr.read().decode('utf-8', errors='replace')
            
            return {
                'success': exit_code == 0,
                'exit_code': exit_code,
                'stdout': stdout_data,
                'stderr': stderr_data,
                'command': command
            }
        except Exception as e:
            return {
                'success': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': str(e),
                'command': command
            }

    def execute_commands(self, commands: list) -> Dict[str, Any]:
        results = []
        all_success = True
        
        for cmd in commands:
            result = self.execute_command(cmd)
            results.append(result)
            if not result['success']:
                all_success = False
        
        return {
            'success': all_success,
            'results': results
        }

    def _get_sftp(self):
        if not self.sftp:
            if not self.client:
                self.connect()
            self.sftp = self.client.open_sftp()
        return self.sftp

    def upload_file(self, local_path: str, remote_path: str) -> Dict[str, Any]:
        try:
            sftp = self._get_sftp()
            sftp.put(local_path, remote_path)
            return {
                'success': True,
                'local_path': local_path,
                'remote_path': remote_path
            }
        except Exception as e:
            return {
                'success': False,
                'local_path': local_path,
                'remote_path': remote_path,
                'error': str(e)
            }

    def upload_content(self, content: str, remote_path: str) -> Dict[str, Any]:
        try:
            sftp = self._get_sftp()
            with sftp.file(remote_path, 'w') as f:
                f.write(content)
            return {
                'success': True,
                'remote_path': remote_path,
                'size': len(content)
            }
        except Exception as e:
            return {
                'success': False,
                'remote_path': remote_path,
                'error': str(e)
            }

    def download_file(self, remote_path: str, local_path: Optional[str] = None) -> Dict[str, Any]:
        try:
            sftp = self._get_sftp()
            if local_path:
                sftp.get(remote_path, local_path)
                return {
                    'success': True,
                    'remote_path': remote_path,
                    'local_path': local_path
                }
            else:
                with sftp.file(remote_path, 'r') as f:
                    content = f.read().decode('utf-8', errors='replace')
                return {
                    'success': True,
                    'remote_path': remote_path,
                    'content': content
                }
        except Exception as e:
            return {
                'success': False,
                'remote_path': remote_path,
                'error': str(e)
            }

    def file_exists(self, remote_path: str) -> bool:
        try:
            sftp = self._get_sftp()
            sftp.stat(remote_path)
            return True
        except:
            return False

    def get_file_hash(self, remote_path: str) -> Optional[str]:
        try:
            result = self.execute_command(f"md5sum {remote_path} 2>/dev/null | cut -d' ' -f1")
            if result['success'] and result['stdout'].strip():
                return result['stdout'].strip()
        except:
            pass
        return None

    def get_file_info(self, remote_path: str) -> Dict[str, Any]:
        result = {
            'exists': False,
            'size': 0,
            'mtime': None,
            'hash': None
        }
        try:
            stat_result = self.execute_command(f"stat -c '%s %Y' {remote_path} 2>/dev/null")
            if stat_result['success'] and stat_result['stdout'].strip():
                parts = stat_result['stdout'].strip().split()
                if len(parts) >= 2:
                    result['exists'] = True
                    result['size'] = int(parts[0])
                    result['mtime'] = int(parts[1])
                result['hash'] = self.get_file_hash(remote_path)
        except:
            pass
        return result

    def backup_file(self, remote_path: str, version_id: Optional[str] = None, 
                   backup_dir: Optional[str] = None) -> Dict[str, Any]:
        if version_id is None:
            version_id = str(int(time.time()))
        
        if backup_dir:
            backup_path = f"{backup_dir}/{version_id}_{remote_path.replace('/', '_')}"
            self.execute_command(f"mkdir -p {backup_dir}")
        else:
            backup_path = f"{remote_path}.v{version_id}"
        
        file_info = self.get_file_info(remote_path)
        
        result = self.execute_command(f"cp -f {remote_path} {backup_path}")
        
        return {
            'success': result['success'],
            'backup_path': backup_path,
            'original_path': remote_path,
            'version_id': version_id,
            'file_info': file_info,
            'error': result.get('stderr')
        }

    def restore_file(self, backup_path: str, original_path: str, 
                    create_backup: bool = True) -> Dict[str, Any]:
        current_backup = None
        
        if create_backup:
            version_id = f"pre_restore_{int(time.time())}"
            backup_result = self.backup_file(original_path, version_id)
            if backup_result['success']:
                current_backup = backup_result['backup_path']
        
        result = self.execute_command(f"cp -f {backup_path} {original_path}")
        
        return {
            'success': result['success'],
            'restored_path': original_path,
            'backup_path': backup_path,
            'current_backup': current_backup,
            'error': result.get('stderr')
        }

    def list_backups(self, remote_path: str, backup_dir: Optional[str] = None) -> Dict[str, Any]:
        if backup_dir:
            pattern = f"*{remote_path.replace('/', '_')}"
            cmd = f"ls -lt {backup_dir}/{pattern} 2>/dev/null | head -20"
        else:
            cmd = f"ls -lt {remote_path}.v* 2>/dev/null | head -20"
        
        result = self.execute_command(cmd)
        backups = []
        
        if result['success'] and result['stdout'].strip():
            for line in result['stdout'].strip().split('\n'):
                parts = line.split()
                if len(parts) >= 9:
                    filename = parts[-1]
                    backups.append({
                        'path': filename,
                        'size': parts[4],
                        'date': f"{parts[5]} {parts[6]} {parts[7]}",
                    })
        
        return {
            'success': True,
            'original_path': remote_path,
            'backups': backups
        }

    def delete_backup(self, backup_path: str) -> Dict[str, Any]:
        result = self.execute_command(f"rm -f {backup_path}")
        return {
            'success': result['success'],
            'backup_path': backup_path,
            'error': result.get('stderr')
        }

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
