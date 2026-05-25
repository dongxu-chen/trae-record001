import json
import time
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from config import AUDIT_LOG_FILE, ROLLBACK_DIR


class AuditLogger:
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file or AUDIT_LOG_FILE
        self._ensure_log_file()

    def _ensure_log_file(self):
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                pass

    def _write_log(self, entry: Dict[str, Any]):
        entry['timestamp'] = datetime.now().isoformat()
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def log_command_execution(self, task_id: str, hostname: str, 
                             command: str, result: Dict[str, Any], 
                             operator: str = 'system'):
        entry = {
            'type': 'command_execution',
            'task_id': task_id,
            'operator': operator,
            'hostname': hostname,
            'command': command,
            'success': result.get('success', False),
            'exit_code': result.get('exit_code'),
            'stdout': result.get('stdout', ''),
            'stderr': result.get('stderr', '')
        }
        self._write_log(entry)

    def log_file_distribution(self, task_id: str, hostname: str,
                             remote_path: str, backup_path: Optional[str],
                             success: bool, operator: str = 'system',
                             error: Optional[str] = None):
        entry = {
            'type': 'file_distribution',
            'task_id': task_id,
            'operator': operator,
            'hostname': hostname,
            'remote_path': remote_path,
            'backup_path': backup_path,
            'success': success,
            'error': error
        }
        self._write_log(entry)

    def log_template_render(self, task_id: str, hostname: str,
                           template_name: str, remote_path: str,
                           success: bool, operator: str = 'system',
                           error: Optional[str] = None):
        entry = {
            'type': 'template_render',
            'task_id': task_id,
            'operator': operator,
            'hostname': hostname,
            'template_name': template_name,
            'remote_path': remote_path,
            'success': success,
            'error': error
        }
        self._write_log(entry)

    def log_rollback(self, task_id: str, hostname: str,
                    original_path: str, backup_path: str,
                    success: bool, operator: str = 'system',
                    error: Optional[str] = None):
        entry = {
            'type': 'rollback',
            'task_id': task_id,
            'operator': operator,
            'hostname': hostname,
            'original_path': original_path,
            'backup_path': backup_path,
            'success': success,
            'error': error
        }
        self._write_log(entry)

    def log_task_start(self, task_id: str, task_type: str,
                      hostnames: List[str], operator: str = 'system'):
        entry = {
            'type': 'task_start',
            'task_id': task_id,
            'task_type': task_type,
            'operator': operator,
            'hostnames': hostnames
        }
        self._write_log(entry)

    def log_task_complete(self, task_id: str, task_type: str,
                         success_count: int, total_count: int,
                         operator: str = 'system'):
        entry = {
            'type': 'task_complete',
            'task_id': task_id,
            'task_type': task_type,
            'operator': operator,
            'success_count': success_count,
            'total_count': total_count,
            'success_rate': success_count / total_count if total_count > 0 else 0
        }
        self._write_log(entry)

    def get_logs(self, task_id: Optional[str] = None, 
                log_type: Optional[str] = None,
                limit: int = 100) -> List[Dict[str, Any]]:
        logs = []
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if task_id and entry.get('task_id') != task_id:
                        continue
                    if log_type and entry.get('type') != log_type:
                        continue
                    logs.append(entry)
                except:
                    continue
        return logs[-limit:] if limit > 0 else logs

    def get_task_logs(self, task_id: str) -> Dict[str, Any]:
        logs = self.get_logs(task_id=task_id)
        return {
            'task_id': task_id,
            'logs': logs,
            'count': len(logs)
        }
