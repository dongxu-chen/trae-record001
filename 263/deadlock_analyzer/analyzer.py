from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from deadlock_parser import Deadlock, Transaction, Lock
import re


@dataclass
class Statistics:
    total_deadlocks: int = 0
    table_stats: Counter = field(default_factory=Counter)
    sql_pattern_stats: Counter = field(default_factory=Counter)
    lock_mode_stats: Counter = field(default_factory=Counter)
    time_distribution: Dict[str, int] = field(default_factory=dict)
    victim_stats: Counter = field(default_factory=Counter)
    average_wait_time: float = 0.0
    peak_hours: List[tuple] = field(default_factory=list)
    involved_tables: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_deadlocks": self.total_deadlocks,
            "table_stats": dict(self.table_stats),
            "sql_pattern_stats": dict(self.sql_pattern_stats),
            "lock_mode_stats": dict(self.lock_mode_stats),
            "time_distribution": self.time_distribution,
            "victim_stats": dict(self.victim_stats),
            "average_wait_time": round(self.average_wait_time, 2),
            "peak_hours": self.peak_hours,
            "involved_tables": self.involved_tables
        }


class DeadlockAnalyzer:
    def __init__(self):
        self.deadlocks: List[Deadlock] = []
        self.statistics = Statistics()

    def analyze(self, deadlocks: List[Deadlock]) -> Statistics:
        self.deadlocks = deadlocks
        self.statistics = Statistics()
        self.statistics.total_deadlocks = len(deadlocks)

        all_tables = set()
        wait_times = []
        hour_counter = Counter()

        for deadlock in deadlocks:
            self._analyze_tables(deadlock, all_tables)
            self._analyze_sql_patterns(deadlock)
            self._analyze_lock_modes(deadlock)
            self._analyze_victims(deadlock)
            self._analyze_time(deadlock, hour_counter, wait_times)

        self.statistics.involved_tables = sorted(all_tables)
        self._calculate_time_distribution(hour_counter)
        self._calculate_average_wait_time(wait_times)

        return self.statistics

    def _analyze_tables(self, deadlock: Deadlock, all_tables: set):
        for txn in deadlock.transactions:
            tables = set()
            for lock in txn.holding_locks:
                tables.add(lock.table_name)
                all_tables.add(lock.table_name)
            if txn.waiting_lock:
                tables.add(txn.waiting_lock.table_name)
                all_tables.add(txn.waiting_lock.table_name)

            for table in tables:
                self.statistics.table_stats[table] += 1

    def _analyze_sql_patterns(self, deadlock: Deadlock):
        for txn in deadlock.transactions:
            for sql in txn.sql_statements:
                pattern = self._sql_to_pattern(sql)
                if pattern:
                    self.statistics.sql_pattern_stats[pattern] += 1

    def _analyze_lock_modes(self, deadlock: Deadlock):
        for txn in deadlock.transactions:
            for lock in txn.holding_locks:
                self.statistics.lock_mode_stats[lock.lock_mode] += 1
            if txn.waiting_lock:
                self.statistics.lock_mode_stats[txn.waiting_lock.lock_mode] += 1

    def _analyze_victims(self, deadlock: Deadlock):
        for victim in deadlock.victim_txns:
            self.statistics.victim_stats[victim] += 1

    def _analyze_time(self, deadlock: Deadlock, hour_counter: Counter, wait_times: List[int]):
        if deadlock.timestamp:
            hour_key = deadlock.timestamp.strftime('%Y-%m-%d %H:00')
            hour_counter[hour_key] += 1

        for txn in deadlock.transactions:
            if txn.wait_time is not None:
                wait_times.append(txn.wait_time)

    def _calculate_time_distribution(self, hour_counter: Counter):
        if not hour_counter:
            return

        sorted_hours = sorted(hour_counter.items(), key=lambda x: x[1], reverse=True)
        self.statistics.peak_hours = sorted_hours[:5]

        time_dist = defaultdict(int)
        for hour_key, count in hour_counter.items():
            hour = int(hour_key.split(' ')[1].split(':')[0])
            if 0 <= hour < 6:
                time_dist['凌晨 (0-6)'] += count
            elif 6 <= hour < 12:
                time_dist['上午 (6-12)'] += count
            elif 12 <= hour < 18:
                time_dist['下午 (12-18)'] += count
            else:
                time_dist['晚上 (18-24)'] += count

        self.statistics.time_distribution = dict(time_dist)

    def _calculate_average_wait_time(self, wait_times: List[int]):
        if wait_times:
            self.statistics.average_wait_time = sum(wait_times) / len(wait_times)

    def _sql_to_pattern(self, sql: str) -> str:
        pattern = re.sub(r"'[^']*'", '?', sql)
        pattern = re.sub(r'"[^"]*"', '?', pattern)
        pattern = re.sub(r'\b\d+\b', '?', pattern)
        pattern = re.sub(r'\s+', ' ', pattern)
        return pattern.strip()

    def get_deadlocks_by_table(self, table_name: str) -> List[Deadlock]:
        result = []
        for deadlock in self.deadlocks:
            for txn in deadlock.transactions:
                for lock in txn.holding_locks:
                    if lock.table_name == table_name:
                        result.append(deadlock)
                        break
                if txn.waiting_lock and txn.waiting_lock.table_name == table_name:
                    if deadlock not in result:
                        result.append(deadlock)
                        break
        return result

    def get_deadlocks_by_time_range(self, start: datetime, end: datetime) -> List[Deadlock]:
        result = []
        for deadlock in self.deadlocks:
            if deadlock.timestamp and start <= deadlock.timestamp <= end:
                result.append(deadlock)
        return result

    def get_top_sql_patterns(self, limit: int = 10) -> List[tuple]:
        return self.statistics.sql_pattern_stats.most_common(limit)

    def get_top_tables(self, limit: int = 10) -> List[tuple]:
        return self.statistics.table_stats.most_common(limit)
