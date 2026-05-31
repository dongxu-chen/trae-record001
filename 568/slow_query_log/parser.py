from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import re
import os


@dataclass
class SlowQueryEntry:
    timestamp: Optional[datetime] = None
    user: str = ""
    host: str = ""
    database: str = ""
    query_time: float = 0.0
    lock_time: float = 0.0
    rows_examined: int = 0
    rows_sent: int = 0
    sql: str = ""
    raw_line: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user": self.user,
            "host": self.host,
            "database": self.database,
            "query_time": self.query_time,
            "lock_time": self.lock_time,
            "rows_examined": self.rows_examined,
            "rows_sent": self.rows_sent,
            "sql": self.sql,
        }


class SlowQueryLogParser:
    def __init__(self, db_type: str = "mysql"):
        self.db_type = db_type.lower()
        self._parsers = {
            "mysql": self._parse_mysql_log,
            "postgresql": self._parse_postgresql_log,
            "pg": self._parse_postgresql_log,
        }

    def parse_file(self, file_path: str, limit: Optional[int] = None) -> List[SlowQueryEntry]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Log file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        parser = self._parsers.get(self.db_type, self._parse_mysql_log)
        entries = parser(content)

        if limit:
            entries = entries[:limit]

        return entries

    def parse_string(self, content: str) -> List[SlowQueryEntry]:
        parser = self._parsers.get(self.db_type, self._parse_mysql_log)
        return parser(content)

    def _parse_mysql_log(self, content: str) -> List[SlowQueryEntry]:
        entries = []
        current_entry = None
        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            if line.startswith("# Time:"):
                if current_entry and current_entry.sql:
                    entries.append(current_entry)
                current_entry = SlowQueryEntry(raw_line=line)

                time_match = re.search(r"# Time:\s+(.+)", line)
                if time_match:
                    try:
                        current_entry.timestamp = datetime.strptime(
                            time_match.group(1).strip(), "%Y-%m-%dT%H:%M:%S.%fZ"
                        )
                    except ValueError:
                        pass

            elif line.startswith("# User@Host:"):
                if current_entry:
                    user_match = re.search(
                        r"# User@Host:\s+(\w+)\[@\s+([^\s]+)", line
                    )
                    if user_match:
                        current_entry.user = user_match.group(1)
                        current_entry.host = user_match.group(2)

            elif line.startswith("# Query_time:"):
                if current_entry:
                    stats_match = re.search(
                        r"# Query_time:\s+([\d.]+)\s+Lock_time:\s+([\d.]+)\s+Rows_sent:\s+(\d+)\s+Rows_examined:\s+(\d+)",
                        line,
                    )
                    if stats_match:
                        current_entry.query_time = float(stats_match.group(1))
                        current_entry.lock_time = float(stats_match.group(2))
                        current_entry.rows_sent = int(stats_match.group(3))
                        current_entry.rows_examined = int(stats_match.group(4))

            elif line.startswith("use "):
                if current_entry:
                    db_match = re.search(r"use\s+(\w+)", line)
                    if db_match:
                        current_entry.database = db_match.group(1)

            elif line and not line.startswith("#") and not line.startswith("SET timestamp"):
                if current_entry:
                    if current_entry.sql:
                        current_entry.sql += " " + line.strip()
                    else:
                        current_entry.sql = line.strip()

            i += 1

        if current_entry and current_entry.sql:
            entries.append(current_entry)

        return entries

    def _parse_postgresql_log(self, content: str) -> List[SlowQueryEntry]:
        entries = []
        lines = content.split("\n")

        duration_pattern = re.compile(
            r"duration:\s+([\d.]+)\s+ms\s+(.+)", re.IGNORECASE
        )
        timestamp_pattern = re.compile(
            r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"
        )

        i = 0
        while i < len(lines):
            line = lines[i]

            duration_match = duration_pattern.search(line)
            if duration_match:
                entry = SlowQueryEntry(raw_line=line)
                entry.query_time = float(duration_match.group(1)) / 1000.0

                timestamp_match = timestamp_pattern.search(line)
                if timestamp_match:
                    try:
                        entry.timestamp = datetime.strptime(
                            timestamp_match.group(1), "%Y-%m-%d %H:%M:%S"
                        )
                    except ValueError:
                        pass

                sql = duration_match.group(2).strip()
                if sql.startswith("statement:"):
                    sql = sql[len("statement:"):].strip()

                entry.sql = sql

                while i + 1 < len(lines) and lines[i + 1].strip() and not duration_pattern.search(lines[i + 1]):
                    i += 1
                    entry.sql += " " + lines[i].strip()

                entries.append(entry)

            i += 1

        return entries

    def filter_by_query_time(self, entries: List[SlowQueryEntry], min_time: float) -> List[SlowQueryEntry]:
        return [e for e in entries if e.query_time >= min_time]

    def sort_by_query_time(self, entries: List[SlowQueryEntry], descending: bool = True) -> List[SlowQueryEntry]:
        return sorted(entries, key=lambda e: e.query_time, reverse=descending)

    def get_summary(self, entries: List[SlowQueryEntry]) -> Dict[str, Any]:
        if not entries:
            return {"count": 0}

        times = [e.query_time for e in entries]
        rows = [e.rows_examined for e in entries if e.rows_examined > 0]

        return {
            "count": len(entries),
            "total_query_time": sum(times),
            "avg_query_time": sum(times) / len(times),
            "max_query_time": max(times),
            "min_query_time": min(times),
            "avg_rows_examined": sum(rows) / len(rows) if rows else 0,
        }
