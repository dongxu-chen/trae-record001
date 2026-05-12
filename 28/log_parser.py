import re
import gc
import time
import os
from typing import Iterator, Dict, Optional, Callable
from datetime import datetime
from _strptime import _TimeRE_cache

NGINX_COMBINED_FORMAT = r'^(\S+) - (\S+) \[([^\]]+)\] "(\S+) (\S+) (\S+)" (\d+) (\d+) "([^"]*)" "([^"]*)"$'

NGINX_COMMON_FORMAT = r'^(\S+) - (\S+) \[([^\]]+)\] "(\S+) (\S+) (\S+)" (\d+) (\d+)$'

DATE_FORMAT = "%d/%b/%Y:%H:%M:%S %z"

def _parse_timestamp_fast(ts_str: str) -> Optional[datetime]:
    try:
        return datetime.strptime(ts_str, DATE_FORMAT)
    except ValueError:
        return None
    finally:
        if _TimeRE_cache:
            _TimeRE_cache.clear()

class LogParser:
    def __init__(self, log_format: str = "combined"):
        if log_format == "combined":
            self.pattern = re.compile(NGINX_COMBINED_FORMAT)
        elif log_format == "common":
            self.pattern = re.compile(NGINX_COMMON_FORMAT)
        else:
            raise ValueError(f"Unsupported log format: {log_format}")
        
        self.log_format = log_format
        self._line_count = 0
        self._gc_frequency = 100000
        self._stop_flag = False
    
    def parse_line(self, line: str) -> Optional[Dict]:
        if not line:
            return None
        
        if line.endswith('\n'):
            line = line[:-1]
        elif line.endswith('\r\n'):
            line = line[:-2]
        
        if not line:
            return None
        
        match = self.pattern.match(line)
        if not match:
            return None
        
        groups = match.groups()
        result = {
            "ip": groups[0],
            "ident": groups[1],
            "timestamp": _parse_timestamp_fast(groups[2]),
            "method": groups[3],
            "path": groups[4],
            "protocol": groups[5],
            "status": int(groups[6]),
            "bytes": int(groups[7])
        }
        
        if self.log_format == "combined":
            result["referer"] = groups[8]
            result["user_agent"] = groups[9]
        
        return result
    
    def parse_file(self, file_path: str, chunk_size: int = 64 * 1024) -> Iterator[Dict]:
        with open(file_path, 'r', encoding='utf-8', errors='ignore', buffering=chunk_size) as f:
            for line in f:
                self._line_count += 1
                parsed = self.parse_line(line)
                if parsed:
                    yield parsed
                
                if self._line_count % self._gc_frequency == 0:
                    gc.collect()
        
        gc.collect()
    
    def parse_lines(self, lines: Iterator[str]) -> Iterator[Dict]:
        for line in lines:
            self._line_count += 1
            parsed = self.parse_line(line)
            if parsed:
                yield parsed
            
            if self._line_count % self._gc_frequency == 0:
                gc.collect()
        
        gc.collect()
    
    def tail_file(
        self,
        file_path: str,
        from_beginning: bool = False,
        poll_interval: float = 0.5,
        stop_check: Optional[Callable[[], bool]] = None
    ) -> Iterator[Dict]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            if not from_beginning:
                f.seek(0, 2)
            
            buffer = ""
            inode = os.stat(file_path).st_ino
            
            while True:
                if stop_check and stop_check():
                    break
                if self._stop_flag:
                    break
                
                line = f.readline()
                if line:
                    self._line_count += 1
                    parsed = self.parse_line(line)
                    if parsed:
                        yield parsed
                    
                    if self._line_count % self._gc_frequency == 0:
                        gc.collect()
                else:
                    try:
                        current_inode = os.stat(file_path).st_ino
                        if current_inode != inode:
                            f.close()
                            f = open(file_path, 'r', encoding='utf-8', errors='ignore')
                            inode = current_inode
                    except FileNotFoundError:
                        pass
                    
                    time.sleep(poll_interval)
        
        gc.collect()
    
    def stop(self):
        self._stop_flag = True
    
    def __del__(self):
        if hasattr(self, '_TimeRE_cache') and _TimeRE_cache:
            _TimeRE_cache.clear()
