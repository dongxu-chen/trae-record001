import json
import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from config import ROLLBACK_DIR
from .ssh_client import SSHClient
from .ssh_pool import get_pooled_client
from .host_manager import Host, HostManager
from .audit import AuditLogger


class VersionedRollbackManager:
    def __init__(self):
        self.rollback_dir = ROLLBACK_DIR
        self.host_manager = HostManager()
        self.audit_logger = AuditLogger()
        self._ensure_rollback_dir()
        self.versions_file = os.path.join(self.rollback_dir, 'versions.json')
        self._load_versions_index()

    def _ensure_rollback_dir(self):
        if not os.path.exists(self.rollback_dir):
            os.makedirs(self.rollback_dir, exist_ok=True)

    def _load_versions_index(self):
        if os.path.exists(self.versions_file):
            with open(self.versions_file, 'r', encoding='utf-8') as f:
                self.versions_index = json.load(f)
        else:
            self.versions_index = {
                'files': {},
                'tasks': {}
            }

    def _save_versions_index(self):
        with open(self.versions_file, 'w', encoding='utf-8') as f:
            json.dump(self.versions_index, f, indent=2, ensure_ascii=False)

    def _get_file_key(self, hostname: str, remote_path: str) -> str:
        return f"{hostname}:{remote_path}"

    def create_version(self, hostname: str, remote_path: str, 
                      description: str = '', operator: str = 'system',
                      use_pool: bool = True) -> Dict[str, Any]:
        host = self.host_manager.get_host(hostname)
        if not host:
            return {
                'success': False,
                'error': 'Host not found'
            }

        version_id = str(int(time.time()))
        version_key = self._get_file_key(hostname, remote_path)

        try:
            client_context = get_pooled_client(host) if use_pool else SSHClient(host)
            with client_context as client:
                backup_result = client.backup_file(remote_path, version_id)
                
                if not backup_result['success']:
                    return {
                        'success': False,
                        'error': backup_result.get('error', 'Backup failed')
                    }

                file_info = backup_result.get('file_info', {})
                
                version_info = {
                    'version_id': version_id,
                    'hostname': hostname,
                    'remote_path': remote_path,
                    'backup_path': backup_result['backup_path'],
                    'description': description,
                    'operator': operator,
                    'created_at': datetime.now().isoformat(),
                    'file_hash': file_info.get('hash'),
                    'file_size': file_info.get('size'),
                    'task_id': None
                }

                if version_key not in self.versions_index['files']:
                    self.versions_index['files'][version_key] = []
                
                self.versions_index['files'][version_key].insert(0, version_info)
                self._save_versions_index()

                return {
                    'success': True,
                    'version_id': version_id,
                    'hostname': hostname,
                    'remote_path': remote_path,
                    'backup_path': backup_result['backup_path'],
                    'file_info': file_info
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_file_versions(self, hostname: str, remote_path: str, 
                         limit: int = 20) -> List[Dict[str, Any]]:
        version_key = self._get_file_key(hostname, remote_path)
        versions = self.versions_index['files'].get(version_key, [])
        return versions[:limit]

    def list_all_versions(self, hostname: Optional[str] = None) -> List[Dict[str, Any]]:
        all_versions = []
        for version_key, versions in self.versions_index['files'].items():
            hn, _ = version_key.split(':', 1)
            if hostname and hn != hostname:
                continue
            all_versions.extend(versions)
        return sorted(all_versions, key=lambda x: x['created_at'], reverse=True)

    def restore_version(self, hostname: str, remote_path: str, version_id: str,
                       operator: str = 'system', use_pool: bool = True) -> Dict[str, Any]:
        host = self.host_manager.get_host(hostname)
        if not host:
            return {
                'success': False,
                'error': 'Host not found'
            }

        version_key = self._get_file_key(hostname, remote_path)
        versions = self.versions_index['files'].get(version_key, [])
        
        target_version = None
        for v in versions:
            if v['version_id'] == version_id:
                target_version = v
                break

        if not target_version:
            return {
                'success': False,
                'error': 'Version not found'
            }

        try:
            client_context = get_pooled_client(host) if use_pool else SSHClient(host)
            with client_context as client:
                restore_result = client.restore_file(
                    target_version['backup_path'],
                    remote_path,
                    create_backup=True
                )

                if restore_result['success']:
                    self.audit_logger.log_rollback(
                        task_id=f"restore_{version_id}",
                        hostname=hostname,
                        original_path=remote_path,
                        backup_path=target_version['backup_path'],
                        success=True,
                        operator=operator
                    )

                    if restore_result.get('current_backup'):
                        auto_version_info = {
                            'version_id': f"auto_{int(time.time())}",
                            'hostname': hostname,
                            'remote_path': remote_path,
                            'backup_path': restore_result['current_backup'],
                            'description': f"Auto backup before restore to version {version_id}",
                            'operator': 'system',
                            'created_at': datetime.now().isoformat(),
                            'file_hash': None,
                            'file_size': 0,
                            'task_id': None,
                            'auto_created': True
                        }
                        self.versions_index['files'][version_key].insert(0, auto_version_info)
                        self._save_versions_index()

                return {
                    'success': restore_result['success'],
                    'version_id': version_id,
                    'hostname': hostname,
                    'remote_path': remote_path,
                    'restored_from': target_version['backup_path'],
                    'auto_backup': restore_result.get('current_backup'),
                    'error': restore_result.get('error')
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def compare_versions(self, hostname: str, remote_path: str,
                        version_id1: str, version_id2: str,
                        use_pool: bool = True) -> Dict[str, Any]:
        host = self.host_manager.get_host(hostname)
        if not host:
            return {
                'success': False,
                'error': 'Host not found'
            }

        version_key = self._get_file_key(hostname, remote_path)
        versions = self.versions_index['files'].get(version_key, [])
        
        v1 = v2 = None
        for v in versions:
            if v['version_id'] == version_id1:
                v1 = v
            if v['version_id'] == version_id2:
                v2 = v

        if not v1 or not v2:
            return {
                'success': False,
                'error': 'One or both versions not found'
            }

        try:
            client_context = get_pooled_client(host) if use_pool else SSHClient(host)
            with client_context as client:
                diff_result = client.execute_command(
                    f"diff -u {v1['backup_path']} {v2['backup_path']} 2>/dev/null || true"
                )

                return {
                    'success': True,
                    'hostname': hostname,
                    'remote_path': remote_path,
                    'version1': version_id1,
                    'version2': version_id2,
                    'diff': diff_result.get('stdout', ''),
                    'has_changes': bool(diff_result.get('stdout', '').strip())
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def delete_version(self, hostname: str, remote_path: str, 
                      version_id: str, use_pool: bool = True) -> Dict[str, Any]:
        host = self.host_manager.get_host(hostname)
        if not host:
            return {
                'success': False,
                'error': 'Host not found'
            }

        version_key = self._get_file_key(hostname, remote_path)
        versions = self.versions_index['files'].get(version_key, [])
        
        target_version = None
        target_index = None
        for i, v in enumerate(versions):
            if v['version_id'] == version_id:
                target_version = v
                target_index = i
                break

        if not target_version:
            return {
                'success': False,
                'error': 'Version not found'
            }

        try:
            client_context = get_pooled_client(host) if use_pool else SSHClient(host)
            with client_context as client:
                client.delete_backup(target_version['backup_path'])

            del self.versions_index['files'][version_key][target_index]
            if not self.versions_index['files'][version_key]:
                del self.versions_index['files'][version_key]
            self._save_versions_index()

            return {
                'success': True,
                'version_id': version_id,
                'hostname': hostname,
                'remote_path': remote_path
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def save_task_versions(self, task_id: str, task_type: str,
                          results: List[Dict[str, Any]], operator: str = 'system'):
        task_info = {
            'task_id': task_id,
            'task_type': task_type,
            'operator': operator,
            'created_at': datetime.now().isoformat(),
            'versions': []
        }

        for result in results:
            if result.get('success') and result.get('backup_path'):
                task_info['versions'].append({
                    'hostname': result.get('hostname'),
                    'remote_path': result.get('remote_path'),
                    'backup_path': result.get('backup_path'),
                    'version_id': result.get('version_id')
                })

        self.versions_index['tasks'][task_id] = task_info
        self._save_versions_index()

        return task_info

    def get_task_versions(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.versions_index['tasks'].get(task_id)

    def rollback_task(self, task_id: str, operator: str = 'system',
                     use_pool: bool = True) -> Dict[str, Any]:
        task_info = self.get_task_versions(task_id)
        if not task_info:
            return {
                'success': False,
                'task_id': task_id,
                'error': 'Task versions not found'
            }

        results = []
        success_count = 0

        for version in task_info['versions']:
            hostname = version['hostname']
            remote_path = version['remote_path']
            backup_path = version['backup_path']

            host = self.host_manager.get_host(hostname)
            if not host:
                results.append({
                    'hostname': hostname,
                    'success': False,
                    'error': 'Host not found'
                })
                continue

            try:
                client_context = get_pooled_client(host) if use_pool else SSHClient(host)
                with client_context as client:
                    restore_result = client.restore_file(backup_path, remote_path)
                    results.append({
                        'hostname': hostname,
                        'remote_path': remote_path,
                        'backup_path': backup_path,
                        'success': restore_result['success'],
                        'error': restore_result.get('error')
                    })
                    if restore_result['success']:
                        success_count += 1

                    self.audit_logger.log_rollback(
                        task_id=task_id,
                        hostname=hostname,
                        original_path=remote_path,
                        backup_path=backup_path,
                        success=restore_result['success'],
                        operator=operator,
                        error=restore_result.get('error')
                    )
            except Exception as e:
                results.append({
                    'hostname': hostname,
                    'success': False,
                    'error': str(e)
                })

        return {
            'success': success_count == len(task_info['versions']),
            'task_id': task_id,
            'total_count': len(task_info['versions']),
            'success_count': success_count,
            'results': results
        }

    def list_tasks(self) -> List[Dict[str, Any]]:
        tasks = list(self.versions_index['tasks'].values())
        return sorted(tasks, key=lambda x: x['created_at'], reverse=True)


RollbackManager = VersionedRollbackManager
