import sys
import time
from typing import Optional, Callable


class ProgressBar:
    def __init__(self, total: float, width: int = 50, description: str = "Processing"):
        self.total = total
        self.width = width
        self.description = description
        self.current = 0.0
        self.start_time = time.time()
        self._closed = False

    def update(self, current: float):
        if self._closed:
            return
        self.current = min(current, self.total)
        self._render()

    def increment(self, amount: float = 1.0):
        if self._closed:
            return
        self.current = min(self.current + amount, self.total)
        self._render()

    def _render(self):
        if self.total <= 0:
            percent = 100.0
        else:
            percent = 100.0 * self.current / self.total

        filled = int(self.width * percent / 100)
        bar = '█' * filled + '░' * (self.width - filled)

        elapsed = time.time() - self.start_time
        if percent > 0:
            eta = elapsed * (100 - percent) / percent
        else:
            eta = 0

        time_str = self._format_time(elapsed)
        eta_str = self._format_time(eta)

        line = f"\r{self.description}: [{bar}] {percent:5.1f}% | {time_str} elapsed | ETA: {eta_str}"
        sys.stdout.write(line)
        sys.stdout.flush()

    def close(self):
        if not self._closed:
            self._render()
            sys.stdout.write('\n')
            sys.stdout.flush()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @staticmethod
    def _format_time(seconds: float) -> str:
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            m = int(seconds // 60)
            s = int(seconds % 60)
            return f"{m}m{s:02d}s"
        else:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            return f"{h}h{m:02d}m{s:02d}s"


class FFmpegProgressParser:
    def __init__(self, total_duration: float, progress_callback: Optional[Callable[[float], None]] = None):
        self.total_duration = total_duration
        self.progress_callback = progress_callback
        self.current_time = 0.0

    def parse_line(self, line: str) -> Optional[float]:
        line = line.strip()
        if line.startswith('time='):
            time_str = line[5:].strip()
            try:
                seconds = self._time_to_seconds(time_str)
                self.current_time = seconds
                if self.progress_callback:
                    self.progress_callback(seconds)
                return seconds
            except ValueError:
                pass
        return None

    @staticmethod
    def _time_to_seconds(time_str: str) -> float:
        if '.' in time_str:
            time_part, ms_part = time_str.split('.')
            milliseconds = int(ms_part.ljust(6, '0')[:6]) / 1000000
        else:
            time_part = time_str
            milliseconds = 0.0

        parts = time_part.split(':')
        if len(parts) == 3:
            h, m, s = parts
            total_seconds = int(h) * 3600 + int(m) * 60 + int(s)
        elif len(parts) == 2:
            m, s = parts
            total_seconds = int(m) * 60 + int(s)
        else:
            total_seconds = int(parts[0])

        return total_seconds + milliseconds


class SilentProgress:
    def __init__(self):
        pass

    def update(self, current: float):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
