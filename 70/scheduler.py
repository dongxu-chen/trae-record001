import os
import sys
import yaml
import threading
import time
import signal
from typing import Dict, Any, Optional, Callable
from datetime import datetime


class CrontabParser:
    @staticmethod
    def parse(cron_expr: str) -> Dict[str, Any]:
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            raise ValueError(f"无效的 cron 表达式: {cron_expr} (需要 5 个字段)")

        return {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "weekday": parts[4]
        }

    @staticmethod
    def _matches(field: str, value: int) -> bool:
        if field == "*":
            return True

        for part in field.split(","):
            if "/" in part:
                base, step = part.split("/", 1)
                if base == "*":
                    if value % int(step) == 0:
                        return True
                else:
                    start, end = CrontabParser._parse_range(base)
                    if start <= value <= end and (value - start) % int(step) == 0:
                        return True
            elif "-" in part:
                start, end = CrontabParser._parse_range(part)
                if start <= value <= end:
                    return True
            else:
                if int(part) == value:
                    return True

        return False

    @staticmethod
    def _parse_range(range_str: str) -> tuple:
        if "-" in range_str:
            start, end = range_str.split("-")
            return int(start), int(end)
        val = int(range_str)
        return val, val

    @staticmethod
    def should_run(cron_expr: str, now: Optional[datetime] = None) -> bool:
        if now is None:
            now = datetime.now()

        schedule = CrontabParser.parse(cron_expr)

        return (
            CrontabParser._matches(schedule["minute"], now.minute) and
            CrontabParser._matches(schedule["hour"], now.hour) and
            CrontabParser._matches(schedule["day"], now.day) and
            CrontabParser._matches(schedule["month"], now.month) and
            CrontabParser._matches(schedule["weekday"], now.weekday())
        )


class TestScheduler:
    def __init__(self):
        self._config = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_minute = -1
        self._job: Optional[Callable] = None
        self._stop_event = threading.Event()

    def load_config(self) -> Dict[str, Any]:
        if self._config is None:
            config_file = os.path.join(os.path.dirname(__file__), "test_data.yaml")
            with open(config_file, "r", encoding="utf-8") as f:
                full_config = yaml.safe_load(f) or {}
            self._config = full_config.get("schedule", {})
        return self._config

    def set_job(self, job: Callable):
        self._job = job

    def _scheduler_loop(self):
        config = self.load_config()
        cron_expr = config.get("cron", "*/5 * * * *")

        print(f"[调度器] 已启动，Cron 表达式: {cron_expr}")
        print(f"[调度器] 按 Ctrl+C 停止...")

        self._last_minute = datetime.now().minute

        while not self._stop_event.is_set():
            now = datetime.now()
            current_minute = now.minute

            if current_minute != self._last_minute:
                self._last_minute = current_minute

                if CrontabParser.should_run(cron_expr, now):
                    print(f"\n[调度器] {now.strftime('%Y-%m-%d %H:%M:%S')} - 触发测试执行")
                    try:
                        if self._job:
                            self._job()
                    except Exception as e:
                        print(f"[调度器] 任务执行出错: {e}")

            self._stop_event.wait(10)

        print("[调度器] 已停止")

    def start(self):
        if self._running:
            return

        config = self.load_config()
        if not config.get("enabled", False):
            print("[调度器] 定时任务未启用，跳过")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def run_once(self):
        if self._job:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n[调度器] {now} - 手动触发测试执行")
            self._job()


def run_tests_job():
    script_dir = os.path.dirname(__file__)
    import subprocess
    result = subprocess.run(
        [sys.executable, os.path.join(script_dir, "runner.py")],
        cwd=script_dir
    )
    return result.returncode


def main():
    scheduler = TestScheduler()
    scheduler.set_job(run_tests_job)

    def signal_handler(signum, frame):
        print("\n[调度器] 收到停止信号...")
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        scheduler.run_once()
        return

    scheduler.start()

    try:
        while scheduler._running:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()


if __name__ == "__main__":
    main()
