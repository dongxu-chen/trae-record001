import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import fnmatch


class BackupEngine:
    def __init__(self, temp_dir: str = "./temp", logger: Optional[logging.Logger] = None):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.temp_dir / "backup_state.json"
        self.logger = logger or logging.getLogger(__name__)
        self._state = self._load_state()

    def _load_state(self) -> Dict:
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"加载备份状态失败: {e}")
        return {}

    def _save_state(self) -> None:
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            self.logger.warning(f"保存备份状态失败: {e}")

    def _should_exclude(self, file_path: str, exclude_patterns: List[str]) -> bool:
        file_name = os.path.basename(file_path)
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(file_path, pattern):
                return True
        return False

    def _get_last_backup_time(self, task_name: str, sftp_uploader=None) -> float:
        if sftp_uploader:
            try:
                remote_time = sftp_uploader.get_latest_backup_time(task_name)
                if remote_time > 0:
                    return remote_time
            except Exception as e:
                self.logger.warning(f"从SFTP获取最新备份时间失败，使用本地记录: {e}")
        
        return self._state.get(task_name, {}).get('last_backup_time', 0)

    def _update_last_backup_time(self, task_name: str, backup_time: float) -> None:
        if task_name not in self._state:
            self._state[task_name] = {}
        self._state[task_name]['last_backup_time'] = backup_time
        self._save_state()

    def get_files_to_backup(
        self,
        source_dir: str,
        backup_type: str,
        task_name: str,
        exclude_patterns: Optional[List[str]] = None,
        sftp_uploader=None
    ) -> Tuple[List[str], int, List[str]]:
        exclude_patterns = exclude_patterns or []
        source_path = Path(source_dir)
        
        if not source_path.exists():
            raise FileNotFoundError(f"源目录不存在: {source_dir}")

        all_files = []
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not self._should_exclude(os.path.join(root, d), exclude_patterns)]
            
            for file in files:
                file_path = os.path.join(root, file)
                if self._should_exclude(file_path, exclude_patterns):
                    continue
                all_files.append(file_path)

        if backup_type == 'full':
            self.logger.info(f"全量备份: 找到 {len(all_files)} 个文件")
            return all_files, len(all_files), all_files
        
        elif backup_type == 'incremental':
            last_backup_time = self._get_last_backup_time(task_name, sftp_uploader)
            if last_backup_time == 0:
                self.logger.info(f"增量备份: 首次执行，执行全量备份")
                return all_files, len(all_files), all_files
            
            changed_files = []
            unchanged_files = []
            
            for file_path in all_files:
                try:
                    mtime = os.path.getmtime(file_path)
                    if mtime > last_backup_time:
                        changed_files.append(file_path)
                    else:
                        unchanged_files.append(file_path)
                except Exception as e:
                    self.logger.warning(f"无法获取文件修改时间 {file_path}: {e}")
                    changed_files.append(file_path)
            
            self.logger.info(f"增量备份: 找到 {len(changed_files)} 个变更文件 (共 {len(all_files)} 个文件, {len(unchanged_files)} 个未变更)")
            return changed_files, len(all_files), unchanged_files
        
        else:
            raise ValueError(f"不支持的备份类型: {backup_type}")

    def generate_backup_filename(self, task_name: str, backup_type: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        type_str = "FULL" if backup_type == "full" else "INC"
        return f"{task_name}_{type_str}_{timestamp}"

    def record_backup_success(self, task_name: str, backup_time: Optional[float] = None) -> None:
        backup_time = backup_time or datetime.now().timestamp()
        self._update_last_backup_time(task_name, backup_time)
        self.logger.info(f"更新备份任务 [{task_name}] 的最后备份时间")

    def get_backup_summary(
        self,
        task_name: str,
        source_dir: str,
        backup_type: str,
        files_backed_up: int,
        total_files: int,
        unchanged_files: int,
        archive_size: int = 0,
        archive_path: str = None,
        deleted_old_backups: int = 0,
        freed_space: int = 0
    ) -> Dict:
        if archive_size == 0 and archive_path and os.path.exists(archive_path):
            archive_size = os.path.getsize(archive_path)
        return {
            'task_name': task_name,
            'source_dir': source_dir,
            'backup_type': backup_type,
            'files_backed_up': files_backed_up,
            'total_files': total_files,
            'unchanged_files': unchanged_files,
            'archive_size_mb': round(archive_size / (1024 * 1024), 2),
            'deleted_old_backups': deleted_old_backups,
            'freed_space_mb': round(freed_space / (1024 * 1024), 2),
            'timestamp': datetime.now().isoformat()
        }
