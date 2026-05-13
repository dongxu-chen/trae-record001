import os
import threading
import time
from datetime import datetime
from typing import Optional


class ReportManager:
    _instance = None
    _lock = threading.Lock()
    _file_lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._report_dir = None
                cls._instance._current_report_path = None
        return cls._instance

    def __init__(self):
        if self._report_dir is None:
            self._report_dir = self._init_report_dir()

    def _init_report_dir(self) -> str:
        base_dir = os.path.dirname(__file__)
        report_dir = os.path.join(base_dir, "reports")

        with self._file_lock:
            if not os.path.exists(report_dir):
                os.makedirs(report_dir, exist_ok=True)

        return report_dir

    def get_report_dir(self) -> str:
        return self._report_dir

    def generate_report_name(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pid = os.getpid()
        thread_id = threading.get_ident()
        return f"api_test_report_{timestamp}_{pid}_{thread_id}.html"

    def get_report_path(self, unique: bool = True) -> str:
        with self._file_lock:
            if unique or self._current_report_path is None:
                report_name = self.generate_report_name()
                self._current_report_path = os.path.join(self._report_dir, report_name)
            return self._current_report_path

    def get_latest_report(self) -> Optional[str]:
        report_dir = self._report_dir

        if not os.path.exists(report_dir):
            return None

        with self._file_lock:
            reports = []
            for f in os.listdir(report_dir):
                if f.startswith("api_test_report_") and f.endswith(".html"):
                    file_path = os.path.join(report_dir, f)
                    if os.path.isfile(file_path):
                        reports.append((os.path.getmtime(file_path), file_path))

        if not reports:
            return None

        reports.sort(key=lambda x: x[0], reverse=True)
        return reports[0][1]

    def get_all_reports(self) -> list:
        report_dir = self._report_dir

        if not os.path.exists(report_dir):
            return []

        with self._file_lock:
            reports = []
            for f in os.listdir(report_dir):
                if f.startswith("api_test_report_") and f.endswith(".html"):
                    file_path = os.path.join(report_dir, f)
                    if os.path.isfile(file_path):
                        reports.append({
                            "name": f,
                            "path": file_path,
                            "mtime": os.path.getmtime(file_path)
                        })

        reports.sort(key=lambda x: x["mtime"], reverse=True)
        return reports

    def cleanup_old_reports(self, keep_count: int = 10) -> int:
        reports = self.get_all_reports()
        removed = 0

        if len(reports) > keep_count:
            with self._file_lock:
                for report in reports[keep_count:]:
                    try:
                        os.remove(report["path"])
                        removed += 1
                    except (OSError, PermissionError):
                        pass

        return removed


_report_manager = ReportManager()


def get_report_dir() -> str:
    return _report_manager.get_report_dir()


def generate_report_name() -> str:
    return _report_manager.generate_report_name()


def get_report_path() -> str:
    return _report_manager.get_report_path(unique=True)


def get_latest_report() -> Optional[str]:
    return _report_manager.get_latest_report()


def cleanup_old_reports(keep_count: int = 10) -> int:
    return _report_manager.cleanup_old_reports(keep_count)
