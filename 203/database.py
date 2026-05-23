import os
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import contextmanager


class BackupDatabase:
    def __init__(self, db_path: str = "backup_history.db"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backup_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    backup_type TEXT NOT NULL,
                    source_dir TEXT NOT NULL,
                    status TEXT NOT NULL,
                    files_backed_up INTEGER DEFAULT 0,
                    total_files INTEGER DEFAULT 0,
                    archive_size_mb REAL DEFAULT 0,
                    deleted_old_backups INTEGER DEFAULT 0,
                    freed_space_mb REAL DEFAULT 0,
                    md5_hash TEXT,
                    remote_path TEXT,
                    error_message TEXT,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    duration_seconds REAL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stat_type TEXT NOT NULL,
                    stat_value TEXT NOT NULL,
                    recorded_at DATETIME NOT NULL
                )
            """)

    def record_backup_start(self, task_name: str, backup_type: str, source_dir: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO backup_history (
                    task_name, backup_type, source_dir, status, start_time
                ) VALUES (?, ?, ?, 'running', ?)
            """, (task_name, backup_type, source_dir, datetime.now().isoformat()))
            return cursor.lastrowid

    def record_backup_success(
        self,
        record_id: int,
        files_backed_up: int,
        total_files: int,
        archive_size_mb: float,
        deleted_old_backups: int,
        freed_space_mb: float,
        md5_hash: str,
        remote_path: str
    ) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE backup_history SET
                    status = 'success',
                    files_backed_up = ?,
                    total_files = ?,
                    archive_size_mb = ?,
                    deleted_old_backups = ?,
                    freed_space_mb = ?,
                    md5_hash = ?,
                    remote_path = ?,
                    end_time = ?,
                    duration_seconds = (julianday(?) - julianday(start_time)) * 86400
                WHERE id = ?
            """, (
                files_backed_up, total_files, archive_size_mb,
                deleted_old_backups, freed_space_mb, md5_hash, remote_path,
                datetime.now().isoformat(), datetime.now().isoformat(), record_id
            ))

    def record_backup_failure(self, record_id: int, error_message: str) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE backup_history SET
                    status = 'failed',
                    error_message = ?,
                    end_time = ?,
                    duration_seconds = (julianday(?) - julianday(start_time)) * 86400
                WHERE id = ?
            """, (error_message, datetime.now().isoformat(), datetime.now().isoformat(), record_id))

    def get_backup_history(self, task_name: str = None, limit: int = 100) -> List[Dict]:
        with self._get_connection() as conn:
            if task_name:
                cursor = conn.execute("""
                    SELECT * FROM backup_history
                    WHERE task_name = ?
                    ORDER BY start_time DESC
                    LIMIT ?
                """, (task_name, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM backup_history
                    ORDER BY start_time DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]

    def get_latest_backup(self, task_name: str) -> Optional[Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM backup_history
                WHERE task_name = ? AND status = 'success'
                ORDER BY start_time DESC
                LIMIT 1
            """, (task_name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_backup_statistics(self, task_name: str = None, days: int = 30) -> Dict:
        with self._get_connection() as conn:
            query = """
                SELECT
                    COUNT(*) as total_backups,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_backups,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_backups,
                    SUM(archive_size_mb) as total_data_backed_up_mb,
                    AVG(duration_seconds) as avg_duration_seconds
                FROM backup_history
                WHERE start_time >= datetime('now', ?)
            """
            params = [f'-{days} days']
            
            if task_name:
                query += " AND task_name = ?"
                params.append(task_name)
            
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            
            return {
                'total_backups': row['total_backups'] or 0,
                'successful_backups': row['successful_backups'] or 0,
                'failed_backups': row['failed_backups'] or 0,
                'total_data_backed_up_mb': round(row['total_data_backed_up_mb'] or 0, 2),
                'avg_duration_seconds': round(row['avg_duration_seconds'] or 0, 2),
                'success_rate': round(
                    (row['successful_backups'] or 0) / (row['total_backups'] or 1) * 100, 2
                )
            }

    def record_system_stat(self, stat_type: str, stat_value: str) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO system_stats (stat_type, stat_value, recorded_at)
                VALUES (?, ?, ?)
            """, (stat_type, stat_value, datetime.now().isoformat()))

    def get_system_stats(self, stat_type: str, limit: int = 50) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM system_stats
                WHERE stat_type = ?
                ORDER BY recorded_at DESC
                LIMIT ?
            """, (stat_type, limit))
            return [dict(row) for row in cursor.fetchall()]

    def clear_old_records(self, days: int = 90) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM backup_history
                WHERE start_time < datetime('now', ?)
            """, (f'-{days} days',))
            deleted_count = cursor.rowcount
            
            conn.execute("""
                DELETE FROM system_stats
                WHERE recorded_at < datetime('now', ?)
            """, (f'-{days} days',))
            
            return deleted_count
