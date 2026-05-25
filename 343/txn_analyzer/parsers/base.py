"""
Base parser and shared data models.
共享数据模型与解析器基类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TxnStatus(str, Enum):
    COMMIT = "COMMIT"
    ROLLBACK = "ROLLBACK"
    IN_PROGRESS = "IN_PROGRESS"


class LockMode(str, Enum):
    ROW_SHARED = "RS"
    ROW_EXCLUSIVE = "RX"
    SHARE = "S"
    EXCLUSIVE = "X"
    INTENTION_SHARED = "IS"
    INTENTION_EXCLUSIVE = "IX"
    AUTO_INC = "AUTO_INC"
    UNKNOWN = "UNKNOWN"


@dataclass
class TransactionEvent:
    """事务事件 - 事务开始/提交/回滚"""
    xid: str
    timestamp: datetime
    status: TxnStatus
    schema: Optional[str] = None
    query: Optional[str] = None
    thread_id: Optional[int] = None
    duration_ms: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LockEvent:
    """锁事件 - 锁获取/等待/释放"""
    xid: str
    timestamp: datetime
    lock_mode: LockMode
    object_name: str
    schema: Optional[str] = None
    wait_ms: float = 0.0
    granted: bool = True
    thread_id: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeadlockEvent:
    """死锁事件"""
    timestamp: datetime
    txn1_xid: str
    txn2_xid: str
    txn1_query: str
    txn2_query: str
    txn1_lock: str
    txn2_lock: str
    victim: str
    schema: Optional[str] = None
    detail: str = ""


@dataclass
class ConnectionContext:
    """连接上下文 - 跟踪线程/连接级别的事务归属"""
    thread_id: int
    user: str = ""
    host: str = ""
    schema: Optional[str] = None
    current_xid: Optional[str] = None
    last_used: Optional[datetime] = None
    txn_count: int = 0

    def to_dict(self) -> dict:
        return {
            "thread_id": self.thread_id,
            "user": self.user,
            "host": self.host,
            "schema": self.schema,
            "current_xid": self.current_xid,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "txn_count": self.txn_count,
        }


@dataclass
class TxnRecord:
    """完整事务记录 - 聚合后输出给分析层"""
    xid: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: TxnStatus = TxnStatus.IN_PROGRESS
    schema: Optional[str] = None
    duration_ms: float = 0.0
    row_ops_count: int = 0
    table_ops: Dict[str, int] = field(default_factory=dict)
    lock_events: List[LockEvent] = field(default_factory=list)
    total_lock_wait_ms: float = 0.0
    max_lock_wait_ms: float = 0.0
    bytes_written: int = 0
    queries: List[str] = field(default_factory=list)
    deadlock_victim: bool = False
    thread_id: Optional[int] = None
    user: str = ""
    host: str = ""
    source_binlog_file: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def add_lock_event(self, evt: LockEvent):
        self.lock_events.append(evt)
        if evt.wait_ms > 0:
            self.total_lock_wait_ms += evt.wait_ms
            self.max_lock_wait_ms = max(self.max_lock_wait_ms, evt.wait_ms)

    def increment_table_op(self, table: str):
        self.table_ops[table] = self.table_ops.get(table, 0) + 1
        self.row_ops_count += 1


class BaseParser(ABC):
    """解析器基类"""

    def __init__(self, config=None):
        self.config = config
        self.txn_events: List[TransactionEvent] = []
        self.lock_events: List[LockEvent] = []
        self.deadlock_events: List[DeadlockEvent] = []
        self._active_txns: Dict[str, TxnRecord] = {}
        self._completed_txns: List[TxnRecord] = []
        self._connections: Dict[int, ConnectionContext] = {}
        self._thread_to_xid: Dict[int, str] = {}
        self._current_binlog_file: str = ""

    @abstractmethod
    def parse(self) -> List[TxnRecord]:
        """解析数据源并返回聚合后的事务记录列表"""
        ...

    def _start_txn(self, xid: str, ts: datetime, schema: Optional[str] = None,
                    query: Optional[str] = None, thread_id: Optional[int] = None,
                    user: str = "", host: str = ""):
        if xid not in self._active_txns:
            self._active_txns[xid] = TxnRecord(
                xid=xid,
                start_time=ts,
                schema=schema,
                queries=[query] if query else [],
                thread_id=thread_id,
                user=user,
                host=host,
                source_binlog_file=self._current_binlog_file,
            )
        else:
            txn = self._active_txns[xid]
            if txn.start_time is None:
                txn.start_time = ts
            if schema and txn.schema is None:
                txn.schema = schema
            if query:
                txn.queries.append(query)
            if thread_id and txn.thread_id is None:
                txn.thread_id = thread_id
            if user and not txn.user:
                txn.user = user
            if host and not txn.host:
                txn.host = host

        if thread_id is not None:
            self._thread_to_xid[thread_id] = xid
            ctx = self._connections.setdefault(
                thread_id,
                ConnectionContext(thread_id=thread_id, user=user, host=host)
            )
            ctx.current_xid = xid
            ctx.last_used = ts
            if schema:
                ctx.schema = schema

    def _commit_txn(self, xid: str, ts: datetime):
        if xid in self._active_txns:
            txn = self._active_txns.pop(xid)
            txn.end_time = ts
            txn.status = TxnStatus.COMMIT
            if txn.start_time:
                txn.duration_ms = (ts - txn.start_time).total_seconds() * 1000
            self._completed_txns.append(txn)
            if txn.thread_id in self._thread_to_xid:
                del self._thread_to_xid[txn.thread_id]
            if txn.thread_id in self._connections:
                ctx = self._connections[txn.thread_id]
                ctx.current_xid = None
                ctx.txn_count += 1
                ctx.last_used = ts

    def _rollback_txn(self, xid: str, ts: datetime):
        if xid in self._active_txns:
            txn = self._active_txns.pop(xid)
            txn.end_time = ts
            txn.status = TxnStatus.ROLLBACK
            if txn.start_time:
                txn.duration_ms = (ts - txn.start_time).total_seconds() * 1000
            self._completed_txns.append(txn)
            if txn.thread_id in self._thread_to_xid:
                del self._thread_to_xid[txn.thread_id]
            if txn.thread_id in self._connections:
                ctx = self._connections[txn.thread_id]
                ctx.current_xid = None
                ctx.txn_count += 1
                ctx.last_used = ts

    def _record_lock(self, xid: str, evt: LockEvent):
        if xid in self._active_txns:
            self._active_txns[xid].add_lock_event(evt)
        self.lock_events.append(evt)

    def get_all_txns(self) -> List[TxnRecord]:
        remaining = [
            TxnRecord(
                xid=t.xid,
                start_time=t.start_time,
                end_time=t.end_time,
                status=TxnStatus.IN_PROGRESS,
                schema=t.schema,
                duration_ms=t.duration_ms,
                row_ops_count=t.row_ops_count,
                table_ops=dict(t.table_ops),
                lock_events=list(t.lock_events),
                total_lock_wait_ms=t.total_lock_wait_ms,
                max_lock_wait_ms=t.max_lock_wait_ms,
                bytes_written=t.bytes_written,
                queries=list(t.queries),
                deadlock_victim=t.deadlock_victim,
                thread_id=t.thread_id,
                user=t.user,
                host=t.host,
                source_binlog_file=t.source_binlog_file,
                extra=dict(t.extra),
            )
            for t in self._active_txns.values()
        ]
        return self._completed_txns + remaining

    def get_connections(self) -> List[ConnectionContext]:
        return [
            ConnectionContext(
                thread_id=c.thread_id,
                user=c.user,
                host=c.host,
                schema=c.schema,
                current_xid=c.current_xid,
                last_used=c.last_used,
                txn_count=c.txn_count,
            )
            for c in self._connections.values()
        ]
