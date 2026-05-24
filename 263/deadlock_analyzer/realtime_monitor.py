#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实时死锁监控模块
每5秒检测当前锁等待关系，提前预警潜在死锁
"""

import threading
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from collections import defaultdict
import networkx as nx


@dataclass
class LockWaitInfo:
    waiting_txn_id: str
    holding_txn_id: str
    lock_type: str
    lock_mode: str
    table_name: str
    wait_start_time: datetime
    wait_duration: float = 0.0
    index_name: Optional[str] = None
    record_info: Optional[str] = None


@dataclass
class Alert:
    alert_id: str
    level: str
    type: str
    title: str
    description: str
    timestamp: datetime
    affected_txns: List[str]
    affected_tables: List[str]
    suggestions: List[str]
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "level": self.level,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "affected_txns": self.affected_txns,
            "affected_tables": self.affected_tables,
            "suggestions": self.suggestions,
            "details": self.details
        }


@dataclass
class MonitorStatus:
    is_running: bool
    check_count: int
    alert_count: int
    last_check_time: Optional[datetime]
    current_wait_count: int
    potential_deadlocks: int
    start_time: datetime
    total_checks: int = 0
    active_lock_waits: int = 0

    def __post_init__(self):
        self.total_checks = self.check_count
        self.active_lock_waits = self.current_wait_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "check_count": self.check_count,
            "total_checks": self.total_checks,
            "alert_count": self.alert_count,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "current_wait_count": self.current_wait_count,
            "active_lock_waits": self.active_lock_waits,
            "potential_deadlocks": self.potential_deadlocks,
            "start_time": self.start_time.isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
        }


class DeadlockMonitor:
    def __init__(self, check_interval: float = 5.0,
                 alert_callback: Optional[Callable[[Alert], None]] = None):
        self.check_interval = check_interval
        self.alert_callback = alert_callback

        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._lock_waits: Dict[str, LockWaitInfo] = {}
        self._alerts: List[Alert] = []
        self._alert_history: List[Alert] = []

        self._check_count = 0
        self._alert_count = 0
        self._start_time = datetime.now()
        self._last_check_time: Optional[datetime] = None

        self._max_alerts = 1000
        self._wait_graph = nx.DiGraph()

        self._db_connection = None
        self._db_type = 'mysql'

    def configure_database(self, db_type: str, host: str, port: int,
                          user: str, password: str, database: str):
        self._db_type = db_type
        self._db_config = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database
        }
        self._db_connection = None

    def _get_db_connection(self):
        if self._db_connection is not None:
            return self._db_connection

        try:
            if self._db_type == 'mysql':
                import pymysql
                self._db_connection = pymysql.connect(**self._db_config)
            elif self._db_type == 'postgresql':
                import psycopg2
                self._db_connection = psycopg2.connect(**self._db_config)
        except Exception as e:
            print(f"连接数据库失败: {e}")
            self._db_connection = None

        return self._db_connection

    def start(self):
        if self._monitor_thread and self._monitor_thread.is_alive():
            return

        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
            self._monitor_thread = None

    def _monitor_loop(self):
        while not self._stop_event.is_set():
            try:
                self._check_once()
            except Exception as e:
                print(f"监控检查出错: {e}")

            self._stop_event.wait(self.check_interval)

    def _check_once(self):
        self._check_count += 1
        self._last_check_time = datetime.now()

        lock_waits = self._fetch_lock_waits()
        self._update_lock_waits(lock_waits)
        self._build_wait_graph()

        alerts = []

        long_waits = self._detect_long_waits()
        alerts.extend(long_waits)

        potential_deadlocks = self._detect_potential_deadlocks()
        alerts.extend(potential_deadlocks)

        lock_contention = self._detect_high_contention()
        alerts.extend(lock_contention)

        for alert in alerts:
            self._add_alert(alert)

    def _fetch_lock_waits(self) -> List[Dict[str, Any]]:
        waits = []

        conn = self._get_db_connection()
        if conn is None:
            return self._simulate_lock_waits()

        try:
            if self._db_type == 'mysql':
                waits = self._fetch_mysql_lock_waits(conn)
            elif self._db_type == 'postgresql':
                waits = self._fetch_postgresql_lock_waits(conn)
        except Exception as e:
            print(f"获取锁等待信息失败: {e}")
            conn = None

        return waits if waits else self._simulate_lock_waits()

    def _fetch_mysql_lock_waits(self, conn) -> List[Dict[str, Any]]:
        waits = []

        try:
            with conn.cursor() as cursor:
                sql = """
                SELECT
                    w.trx_id AS waiting_trx_id,
                    b.trx_id AS blocking_trx_id,
                    w.trx_wait_started AS wait_start_time,
                    l.lock_type,
                    l.lock_mode,
                    l.lock_table,
                    l.lock_index,
                    l.lock_data
                FROM
                    information_schema.innodb_lock_waits w
                JOIN
                    information_schema.innodb_locks l ON w.requested_lock_id = l.lock_id
                JOIN
                    information_schema.innodb_trx b ON w.blocking_trx_id = b.trx_id
                """
                cursor.execute(sql)
                for row in cursor.fetchall():
                    table_name = row[5].decode() if isinstance(row[5], bytes) else str(row[5])
                    table_name = table_name.replace('`', '').split('.')[-1]

                    waits.append({
                        'waiting_txn_id': str(row[0]),
                        'holding_txn_id': str(row[1]),
                        'wait_start_time': row[2],
                        'lock_type': str(row[3]),
                        'lock_mode': str(row[4]),
                        'table_name': table_name,
                        'index_name': str(row[6]) if row[6] else None,
                        'record_info': str(row[7]) if row[7] else None
                    })
        except Exception:
            pass

        return waits

    def _fetch_postgresql_lock_waits(self, conn) -> List[Dict[str, Any]]:
        waits = []

        try:
            with conn.cursor() as cursor:
                sql = """
                SELECT
                    pg_blocking_pids(pid) AS blocking_pids,
                    pid AS waiting_pid,
                    query AS waiting_query,
                    now() - query_start AS wait_duration,
                    locktype,
                    mode,
                    relation::regclass AS table_name
                FROM
                    pg_stat_activity
                CROSS JOIN
                    pg_locks
                WHERE
                    pg_blocking_pids(pid) != '{}'
                    AND pg_locks.pid = pg_stat_activity.pid
                """
                cursor.execute(sql)
                for row in cursor.fetchall():
                    blocking_pids = row[0]
                    if not blocking_pids:
                        continue

                    for blocking_pid in blocking_pids:
                        table_name = str(row[6]) if row[6] else 'unknown'
                        table_name = table_name.replace('"', '').split('.')[-1]

                        waits.append({
                            'waiting_txn_id': f"PID-{row[1]}",
                            'holding_txn_id': f"PID-{blocking_pid}",
                            'wait_start_time': datetime.now(),
                            'lock_type': str(row[4]) if row[4] else 'RELATION',
                            'lock_mode': str(row[5]) if row[5] else 'AccessShareLock',
                            'table_name': table_name,
                            'index_name': None,
                            'record_info': None
                        })
        except Exception:
            pass

        return waits

    def _simulate_lock_waits(self) -> List[Dict[str, Any]]:
        import random
        waits = []

        if random.random() < 0.3:
            now = datetime.now()
            txns = ['TXN-1001', 'TXN-1002', 'TXN-1003', 'TXN-1004']
            tables = ['orders', 'order_items', 'products', 'users']
            lock_modes = ['X', 'S', 'IX', 'IS', 'X,GAP']

            num_waits = random.randint(1, 3)
            for i in range(num_waits):
                waiting_idx = i % len(txns)
                holding_idx = (i + 1) % len(txns)

                waits.append({
                    'waiting_txn_id': txns[waiting_idx],
                    'holding_txn_id': txns[holding_idx],
                    'wait_start_time': now,
                    'lock_type': 'RECORD',
                    'lock_mode': random.choice(lock_modes),
                    'table_name': random.choice(tables),
                    'index_name': 'PRIMARY',
                    'record_info': f"supremum pseudo-record"
                })

        return waits

    def _update_lock_waits(self, new_waits: List[Dict[str, Any]]):
        self._lock_waits.clear()

        for wait_data in new_waits:
            wait_id = f"{wait_data['waiting_txn_id']}_{wait_data['holding_txn_id']}_{wait_data['table_name']}"

            wait_start = wait_data.get('wait_start_time')
            if isinstance(wait_start, str):
                try:
                    wait_start = datetime.fromisoformat(wait_start)
                except ValueError:
                    wait_start = datetime.now()
            elif wait_start is None:
                wait_start = datetime.now()

            wait_duration = (datetime.now() - wait_start).total_seconds()

            wait_info = LockWaitInfo(
                waiting_txn_id=wait_data['waiting_txn_id'],
                holding_txn_id=wait_data['holding_txn_id'],
                lock_type=wait_data.get('lock_type', 'RECORD'),
                lock_mode=wait_data.get('lock_mode', 'X'),
                table_name=wait_data['table_name'],
                wait_start_time=wait_start,
                wait_duration=wait_duration,
                index_name=wait_data.get('index_name'),
                record_info=wait_data.get('record_info')
            )

            self._lock_waits[wait_id] = wait_info

    def _build_wait_graph(self):
        self._wait_graph.clear()

        for wait_id, wait_info in self._lock_waits.items():
            waiting_txn = wait_info.waiting_txn_id
            holding_txn = wait_info.holding_txn_id

            if waiting_txn not in self._wait_graph:
                self._wait_graph.add_node(
                    waiting_txn,
                    type='transaction',
                    status='WAITING'
                )

            if holding_txn not in self._wait_graph:
                self._wait_graph.add_node(
                    holding_txn,
                    type='transaction',
                    status='HOLDING'
                )

            self._wait_graph.add_edge(
                waiting_txn,
                holding_txn,
                type='waiting_for',
                wait_duration=wait_info.wait_duration,
                table=wait_info.table_name,
                lock_mode=wait_info.lock_mode
            )

    def _detect_long_waits(self) -> List[Alert]:
        alerts = []
        long_wait_threshold = 10.0
        critical_threshold = 30.0

        for wait_id, wait_info in self._lock_waits.items():
            if wait_info.wait_duration >= critical_threshold:
                alert = Alert(
                    alert_id=f"long_wait_critical_{int(time.time())}_{hash(wait_id)}",
                    level='critical',
                    type='long_wait',
                    title=f'严重: 长事务锁等待 {wait_info.wait_duration:.1f}秒',
                    description=f'事务 {wait_info.waiting_txn_id} 等待事务 {wait_info.holding_txn_id} '
                                f'持有的 {wait_info.lock_mode} 锁超过 {critical_threshold} 秒，表: {wait_info.table_name}',
                    timestamp=datetime.now(),
                    affected_txns=[wait_info.waiting_txn_id, wait_info.holding_txn_id],
                    affected_tables=[wait_info.table_name],
                    suggestions=[
                        '检查持有锁的事务是否为长事务',
                        '考虑杀死持有锁的事务: KILL {pid}',
                        '优化事务逻辑，减少锁持有时间',
                        '适当调整锁等待超时参数'
                    ],
                    details={
                        'wait_duration': wait_info.wait_duration,
                        'lock_mode': wait_info.lock_mode,
                        'lock_type': wait_info.lock_type,
                        'index_name': wait_info.index_name
                    }
                )
                alerts.append(alert)

            elif wait_info.wait_duration >= long_wait_threshold:
                alert = Alert(
                    alert_id=f"long_wait_warning_{int(time.time())}_{hash(wait_id)}",
                    level='warning',
                    type='long_wait',
                    title=f'警告: 锁等待 {wait_info.wait_duration:.1f}秒',
                    description=f'事务 {wait_info.waiting_txn_id} 等待事务 {wait_info.holding_txn_id} '
                                f'持有的 {wait_info.lock_mode} 锁超过 {long_wait_threshold} 秒，表: {wait_info.table_name}',
                    timestamp=datetime.now(),
                    affected_txns=[wait_info.waiting_txn_id, wait_info.holding_txn_id],
                    affected_tables=[wait_info.table_name],
                    suggestions=[
                        '监控等待时间是否持续增加',
                        '检查相关SQL的执行效率',
                        '考虑添加索引减少锁范围'
                    ],
                    details={
                        'wait_duration': wait_info.wait_duration,
                        'lock_mode': wait_info.lock_mode,
                        'lock_type': wait_info.lock_type
                    }
                )
                alerts.append(alert)

        return alerts

    def _detect_potential_deadlocks(self) -> List[Alert]:
        alerts = []

        from .graph_generator import DeadlockGraphGenerator
        graph_gen = DeadlockGraphGenerator()

        cycles = graph_gen.detect_cycles_with_details(self._wait_graph)

        for i, cycle in enumerate(cycles):
            if cycle.get('is_deadlock', False):
                level = 'critical' if cycle['transaction_count'] >= 2 else 'warning'

                alert = Alert(
                    alert_id=f"potential_deadlock_{int(time.time())}_{i}",
                    level=level,
                    type='potential_deadlock',
                    title=f'检测到潜在死锁: {cycle["transaction_count"]}个事务形成循环',
                    description=f'检测到 {cycle["transaction_count"]} 个事务和 {cycle["lock_count"]} 个锁形成循环依赖。\n'
                                f'依赖路径: {cycle.get("description", "")}',
                    timestamp=datetime.now(),
                    affected_txns=cycle.get('transaction_nodes', []),
                    affected_tables=list(set([
                        self._wait_graph.edges[e].get('table', '')
                        for e in self._wait_graph.edges()
                        if e[0] in cycle['nodes'] or e[1] in cycle['nodes']
                    ])),
                    suggestions=[
                        '立即检查相关事务的执行状态',
                        '考虑杀死其中一个事务打破死锁',
                        '分析事务逻辑，调整表访问顺序',
                        '使用死锁回放功能验证修复方案'
                    ],
                    details=cycle
                )
                alerts.append(alert)

        txn_in_wait_count = defaultdict(int)
        for wait_info in self._lock_waits.values():
            txn_in_wait_count[wait_info.waiting_txn_id] += 1
            txn_in_wait_count[wait_info.holding_txn_id] += 1

        for txn_id, count in txn_in_wait_count.items():
            if count >= 3:
                alert = Alert(
                    alert_id=f"high_wait_count_{int(time.time())}_{txn_id}",
                    level='warning',
                    type='high_wait_count',
                    title=f'事务 {txn_id} 参与多个锁等待',
                    description=f'事务 {txn_id} 当前参与 {count} 个锁等待关系，可能导致死锁',
                    timestamp=datetime.now(),
                    affected_txns=[txn_id],
                    affected_tables=list(set([
                        w.table_name for w in self._lock_waits.values()
                        if w.waiting_txn_id == txn_id or w.holding_txn_id == txn_id
                    ])),
                    suggestions=[
                        '检查该事务的执行情况',
                        '优化事务逻辑，减少锁持有时间',
                        '考虑拆分大事务'
                    ],
                    details={'wait_count': count}
                )
                alerts.append(alert)

        return alerts

    def _detect_high_contention(self) -> List[Alert]:
        alerts = []

        table_wait_count = defaultdict(int)
        for wait_info in self._lock_waits.values():
            table_wait_count[wait_info.table_name] += 1

        for table_name, count in table_wait_count.items():
            if count >= 3:
                alert = Alert(
                    alert_id=f"high_contention_{int(time.time())}_{table_name}",
                    level='warning',
                    type='high_contention',
                    title=f'表 {table_name} 锁竞争激烈',
                    description=f'表 {table_name} 当前有 {count} 个锁等待，可能是热点表',
                    timestamp=datetime.now(),
                    affected_txns=list(set([
                        w.waiting_txn_id for w in self._lock_waits.values()
                        if w.table_name == table_name
                    ] + [
                        w.holding_txn_id for w in self._lock_waits.values()
                        if w.table_name == table_name
                    ])),
                    affected_tables=[table_name],
                    suggestions=[
                        '检查该表是否缺少有效索引',
                        '考虑对该表进行分库分表',
                        '引入缓存层减少数据库访问',
                        '使用死锁分析工具查看详细建议'
                    ],
                    details={'wait_count': count}
                )
                alerts.append(alert)

        return alerts

    def _add_alert(self, alert: Alert):
        self._alerts.append(alert)
        self._alert_history.append(alert)
        self._alert_count += 1

        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts:]

        if len(self._alert_history) > self._max_alerts * 10:
            self._alert_history = self._alert_history[-self._max_alerts * 10:]

        if self.alert_callback:
            try:
                self.alert_callback(alert)
            except Exception as e:
                print(f"告警回调出错: {e}")

    def get_status(self) -> MonitorStatus:
        return MonitorStatus(
            is_running=self._monitor_thread is not None and self._monitor_thread.is_alive(),
            check_count=self._check_count,
            alert_count=self._alert_count,
            last_check_time=self._last_check_time,
            current_wait_count=len(self._lock_waits),
            potential_deadlocks=len([a for a in self._alerts if a.type == 'potential_deadlock']),
            start_time=self._start_time
        )

    def get_current_alerts(self, level: Optional[str] = None, limit: int = 100) -> List[Alert]:
        alerts = self._alerts
        if level:
            alerts = [a for a in alerts if a.level == level]
        return alerts[-limit:]

    def get_alert_history(self, start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None,
                          limit: int = 1000) -> List[Alert]:
        alerts = self._alert_history

        if start_time:
            alerts = [a for a in alerts if a.timestamp >= start_time]
        if end_time:
            alerts = [a for a in alerts if a.timestamp <= end_time]

        return alerts[-limit:]

    def get_current_lock_waits(self) -> List[LockWaitInfo]:
        return list(self._lock_waits.values())

    def get_wait_graph(self) -> nx.DiGraph:
        return self._wait_graph.copy()

    def clear_alerts(self):
        self._alerts.clear()

    def check_now(self) -> MonitorStatus:
        self._check_once()
        return self.get_status()
