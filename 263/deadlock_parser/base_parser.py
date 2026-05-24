from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import re
import sqlparse


@dataclass
class Lock:
    lock_type: str
    lock_mode: str
    table_name: str
    index_name: Optional[str] = None
    record_info: Optional[str] = None


@dataclass
class Transaction:
    txn_id: str
    status: str
    start_time: Optional[datetime] = None
    wait_time: Optional[int] = None
    sql_statements: List[str] = field(default_factory=list)
    holding_locks: List[Lock] = field(default_factory=list)
    waiting_lock: Optional[Lock] = None


@dataclass
class Deadlock:
    timestamp: Optional[datetime]
    transactions: List[Transaction]
    victim_txns: List[str] = field(default_factory=list)
    raw_log: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "transactions": [
                {
                    "txn_id": t.txn_id,
                    "status": t.status,
                    "start_time": t.start_time.isoformat() if t.start_time else None,
                    "wait_time": t.wait_time,
                    "sql_statements": t.sql_statements,
                    "holding_locks": [
                        {
                            "lock_type": l.lock_type,
                            "lock_mode": l.lock_mode,
                            "table_name": l.table_name,
                            "index_name": l.index_name,
                            "record_info": l.record_info
                        }
                        for l in t.holding_locks
                    ],
                    "waiting_lock": {
                        "lock_type": t.waiting_lock.lock_type,
                        "lock_mode": t.waiting_lock.lock_mode,
                        "table_name": t.waiting_lock.table_name,
                        "index_name": t.waiting_lock.index_name,
                        "record_info": t.waiting_lock.record_info
                    } if t.waiting_lock else None
                }
                for t in self.transactions
            ],
            "victim_txns": self.victim_txns
        }


class DeadlockParser(ABC):
    @abstractmethod
    def parse(self, log_content: str) -> List[Deadlock]:
        pass

    def _normalize_sql(self, sql: str) -> str:
        try:
            formatted = sqlparse.format(sql, strip_comments=True, reindent=False)
            return formatted.strip()
        except Exception:
            return sql.strip()

    def _extract_table_from_sql(self, sql: str) -> List[str]:
        tables = []
        patterns = [
            r'FROM\s+`?(\w+)`?',
            r'INTO\s+`?(\w+)`?',
            r'UPDATE\s+`?(\w+)`?',
            r'JOIN\s+`?(\w+)`?',
            r'TABLE\s+`?(\w+)`?'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            tables.extend(matches)
        return list(set(tables))

    def _sql_to_pattern(self, sql: str) -> str:
        pattern = re.sub(r"'[^']*'", '?', sql)
        pattern = re.sub(r'"[^"]*"', '?', pattern)
        pattern = re.sub(r'\b\d+\b', '?', pattern)
        pattern = re.sub(r'\s+', ' ', pattern)
        return pattern.strip()
