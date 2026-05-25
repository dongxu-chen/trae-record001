"""
MySQL Binlog Parser - MySQL binlog 解析器
解析 binlog 中的 XID、GTID、QUERY 事件，提取事务边界、行操作、锁等待信息。

依赖: mysql-replication (pymysqlreplication)
"""
import re
import struct
from datetime import datetime
from typing import Dict, List, Optional

from ..config import MySQLConfig
from ..logger import setup_logger
from .base import (
    BaseParser, LockEvent, LockMode, TxnRecord, TxnStatus,
    DeadlockEvent,
)

logger = setup_logger("mysql_parser")

try:
    from pymysqlreplication import BinLogStreamReader
    from pymysqlreplication.event import (
        QueryEvent, XidEvent, GtidEvent, RotateEvent,
        FormatDescriptionEvent, MariadbGtidEvent,
    )
    from pymysqlreplication.row_event import (
        WriteRowsEvent, UpdateRowsEvent, DeleteRowsEvent,
    )
    _HAS_MYSQL_REPLICATION = True
except ImportError:
    _HAS_MYSQL_REPLICATION = False


class MySQLBinlogParser(BaseParser):
    """
    MySQL Binlog 解析器
    使用 pymysqlreplication 连接 MySQL 读取 binlog，
    或离线解析 binlog 文件（通过 mysqlbinlog 工具）。
    支持多文件顺序解析以重建跨文件的事务上下文。
    """

    def __init__(self, config: MySQLConfig):
        super().__init__(config)
        self.config = config
        self._current_gtid: Optional[str] = None
        self._current_xid: Optional[str] = None
        self._table_cache: Dict[str, str] = {}
        self._txn_start_times: Dict[str, datetime] = {}
        self._binlog_files_parsed: List[str] = []
        self._cross_file_txns: int = 0

    def parse(self) -> List[TxnRecord]:
        """
        解析 binlog，返回聚合后的事务记录列表。
        优先通过 pymysqlreplication 连接；若不可用则回退到 mysqlbinlog 文本解析。
        """
        if _HAS_MYSQL_REPLICATION and not self.config.binlog_file:
            return self._parse_streaming()
        elif self.config.binlog_file:
            return self._parse_offline()
        else:
            logger.error(
                "mysql-replication 未安装且未指定 binlog 文件路径。"
                "请 pip install mysql-replication 或提供 binlog_file 路径。"
            )
            return []

    def parse_files(self, binlog_files: List[str]) -> List[TxnRecord]:
        """
        顺序解析多个 binlog 文件，保留活跃事务以支持跨文件重建。
        当一个文件结束时仍在进行的事务会在后续文件中继续跟踪。
        """
        self._binlog_files_parsed = []
        self._cross_file_txns = 0
        prev_active_count = 0

        for filepath in binlog_files:
            self._current_binlog_file = filepath
            self._binlog_files_parsed.append(filepath)
            prev_active_count = len(self._active_txns)

            logger.info("解析 binlog 文件: %s (活跃事务: %d)", filepath, prev_active_count)
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except FileNotFoundError:
                logger.error("binlog 文件不存在: %s", filepath)
                continue

            self._parse_offline_content(content)

            new_active = len(self._active_txns)
            if new_active > prev_active_count:
                self._cross_file_txns += (new_active - prev_active_count)
            logger.info("  文件 %s 解析完成: 活跃事务 %d, 已完成 %d",
                        filepath, new_active, len(self._completed_txns))

        # 将剩余活跃事务标记为 IN_PROGRESS
        unfinished = list(self._active_txns.values())
        if unfinished:
            logger.info("跨文件未完成事务: %d 条", len(unfinished))

        logger.info("多文件解析完成: 共 %d 个文件, %d 条已完成事务, %d 条跨文件事务",
                    len(self._binlog_files_parsed), len(self._completed_txns),
                    self._cross_file_txns)

        return self.get_all_txns()

    def parse_connection_info(self, events: List) -> Dict[int, dict]:
        """从事件列表中提取连接上下文信息"""
        connections: Dict[int, dict] = {}
        for event in events:
            if hasattr(event, "slave_thread_id") and event.slave_thread_id:
                tid = event.slave_thread_id
                if tid not in connections:
                    connections[tid] = {
                        "thread_id": tid,
                        "user": "",
                        "host": "",
                        "schema": getattr(event, "schema", ""),
                    }
            if hasattr(event, "user") and hasattr(event, "slave_thread_id"):
                connections[event.slave_thread_id]["user"] = event.user
        return connections

    # ------------------------------------------------------------------
    #  在线 / 流式解析（pymysqlreplication）
    # ------------------------------------------------------------------

    def _parse_streaming(self) -> List[TxnRecord]:
        logger.info("开始 MySQL binlog 流式解析 ...")
        conn_settings = {
            "host": self.config.host,
            "port": self.config.port,
            "user": self.config.user,
            "passwd": self.config.password,
        }
        try:
            stream = BinLogStreamReader(
                connection_settings=conn_settings,
                server_id=self.config.server_id,
                only_schemas=self.config.only_schemas,
                only_tables=self.config.only_tables,
                resume_stream=True,
                blocking=False,
            )
        except Exception as exc:
            logger.error("连接 MySQL 失败: %s", exc)
            return []

        for binlog_event in stream:
            self._handle_event(binlog_event)

        stream.close()
        logger.info("MySQL binlog 解析完成，共 %d 条事务记录", len(self._completed_txns))
        return self.get_all_txns()

    def _handle_event(self, event):
        ts = datetime.fromtimestamp(event.timestamp) if hasattr(event, "timestamp") else datetime.now()
        thread_id = getattr(event, "slave_thread_id", None)

        # ---- GTID / XID 跟踪 ----
        if isinstance(event, GtidEvent):
            self._current_gtid = event.gtid
            self._current_xid = event.gtid
            self._start_txn(self._current_xid, ts, thread_id=thread_id)
            self._txn_start_times[self._current_xid] = ts
            return

        if isinstance(event, MariadbGtidEvent):
            self._current_gtid = f"{event.domain_id}-{event.server_id}-{event.sequence}"
            self._current_xid = self._current_gtid
            self._start_txn(self._current_xid, ts, thread_id=thread_id)
            return

        # ---- QUERY 事件：BEGIN / COMMIT / 实际 SQL ----
        if isinstance(event, QueryEvent):
            query = event.query.upper().strip()
            schema = event.schema

            if query in ("BEGIN", "START TRANSACTION"):
                if self._current_xid is None:
                    self._current_xid = f"qtxn_{event.timestamp}_{id(event)}"
                self._start_txn(self._current_xid, ts, schema, thread_id=thread_id)
                self._txn_start_times[self._current_xid] = ts
                return

            if query in ("COMMIT",):
                if self._current_xid:
                    self._commit_txn(self._current_xid, ts)
                    self._current_xid = None
                return

            if query in ("ROLLBACK",):
                if self._current_xid:
                    self._rollback_txn(self._current_xid, ts)
                    self._current_xid = None
                return

            # 实际 SQL (DDL / 在非事务模式下的 DML)
            if self._current_xid:
                txn = self._active_txns.get(self._current_xid)
                if txn:
                    if event.query not in txn.queries:
                        txn.queries.append(event.query)
                    if schema and not txn.schema:
                        txn.schema = schema
                    if thread_id and txn.thread_id is None:
                        txn.thread_id = thread_id

            # 检测死锁
            if "DEADLOCK" in query and "INNODB" in query:
                self._try_extract_deadlock(event.query, ts)

        # ---- XID 事件（XA / 隐式提交） ----
        if isinstance(event, XidEvent):
            if self._current_xid:
                self._commit_txn(self._current_xid, ts)
                self._current_xid = None

        # ---- 行事件 ----
        if isinstance(event, (WriteRowsEvent, UpdateRowsEvent, DeleteRowsEvent)):
            if self._current_xid is None:
                self._current_xid = f"auto_{event.timestamp}_{id(event)}"
                self._start_txn(self._current_xid, ts, event.schema, thread_id=thread_id)
                self._txn_start_times[self._current_xid] = ts

            table = f"{event.schema}.{event.table}" if event.schema else event.table
            row_count = len(event.rows)

            txn = self._active_txns.get(self._current_xid)
            if txn:
                txn.increment_table_op(table)
                txn.bytes_written += row_count * 256
                if event.schema and not txn.schema:
                    txn.schema = event.schema
                if thread_id and txn.thread_id is None:
                    txn.thread_id = thread_id

            # 推断锁模式
            lock_mode = self._infer_lock_mode(event)
            self._record_lock(self._current_xid, LockEvent(
                xid=self._current_xid,
                timestamp=ts,
                lock_mode=lock_mode,
                object_name=table,
                schema=event.schema,
                granted=True,
                thread_id=thread_id,
            ))

    @staticmethod
    def _infer_lock_mode(event) -> LockMode:
        if isinstance(event, WriteRowsEvent):
            return LockMode.ROW_EXCLUSIVE
        if isinstance(event, UpdateRowsEvent):
            return LockMode.ROW_EXCLUSIVE
        if isinstance(event, DeleteRowsEvent):
            return LockMode.ROW_EXCLUSIVE
        return LockMode.UNKNOWN

    # ------------------------------------------------------------------
    #  离线 / 文件解析（解析 mysqlbinlog 文本输出）
    # ------------------------------------------------------------------

    def _parse_offline(self) -> List[TxnRecord]:
        """解析 mysqlbinlog 文本输出的单文件入口"""
        filepath = self.config.binlog_file
        self._current_binlog_file = filepath
        logger.info("开始离线解析 binlog 文件: %s", filepath)

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except FileNotFoundError:
            logger.error("binlog 文件不存在: %s", filepath)
            return []

        self._parse_offline_content(content)
        logger.info("离线解析完成，共 %d 条事务记录", len(self._completed_txns))
        return self.get_all_txns()

    def _parse_offline_content(self, content: str):
        """解析 mysqlbinlog 文本内容（可被多文件解析复用）"""
        gtid_pattern = re.compile(
            r"#(\d{6}\s+\d{1,2}:\d{2}:\d{2})[^#]*GTID\s+([0-9a-fA-F-]+-[0-9a-fA-F-]+-[0-9]+)"
        )
        block_pattern = re.compile(
            r"(BEGIN|START TRANSACTION).*?(COMMIT|ROLLBACK)",
            re.DOTALL | re.IGNORECASE,
        )

        for gtid_match in gtid_pattern.finditer(content):
            ts_str, gtid = gtid_match.group(1), gtid_match.group(2)
            ts = self._parse_mysql_timestamp(ts_str)
            xid = gtid
            self._current_xid = xid
            self._start_txn(xid, ts)
            self._txn_start_times[xid] = ts

            start_pos = gtid_match.end()
            block_match = block_pattern.search(content, start_pos)
            if block_match:
                end_action = block_match.group(2).upper()
                block_text = content[gtid_match.start():block_match.end()]
                self._parse_txn_block(xid, block_text, ts)

                if end_action == "COMMIT":
                    self._commit_txn(xid, ts)
                else:
                    self._rollback_txn(xid, ts)

    def _parse_txn_block(self, xid: str, block: str, ts: datetime):
        """解析单个事务块中的行操作和 SQL"""
        txn = self._active_txns.get(xid)
        if not txn:
            return

        row_pattern = re.compile(r"### (INSERT|UPDATE|DELETE)\s+INTO\s+`(\w+)`\.`(\w+)`", re.IGNORECASE)
        for m in row_pattern.finditer(block):
            table = f"{m.group(2)}.{m.group(3)}"
            txn.increment_table_op(table)
            txn.bytes_written += 256

        query_pattern = re.compile(r"#(?:\d{6}\s+\d{1,2}:\d{2}:\d{2})?\s*server id.*\n\s*(?!#)(.*)", re.MULTILINE)
        for m in query_pattern.finditer(block):
            q = m.group(1).strip()
            if q and q not in ("BEGIN", "COMMIT", "ROLLBACK", "") and q not in txn.queries:
                txn.queries.append(q)

    @staticmethod
    def _parse_mysql_timestamp(ts_str: str) -> datetime:
        """解析 '250115 10:20:30' 格式"""
        try:
            return datetime.strptime(ts_str.strip(), "%y%m%d %H:%M:%S")
        except ValueError:
            return datetime.now()

    # ------------------------------------------------------------------
    #  死锁提取（从 SHOW ENGINE INNODB STATUS 文本）
    # ------------------------------------------------------------------

    def _try_extract_deadlock(self, text: str, ts: datetime):
        """从 InnoDB 状态文本中提取死锁信息"""
        pattern = re.compile(
            r"LATEST DETECTED DEADLOCK.*?"
            r"TRANSACTION.*?(\d+).*?\n.*?"
            r"(SELECT|INSERT|UPDATE|DELETE).*?\n.*?"
            r"HOLDS THE LOCK.*?\n.*?"
            r"RECORD LOCKS.*?`(\w+)`.(`\w+`)"
            r".*?TRANSACTION.*?(\d+).*?\n.*?"
            r"(SELECT|INSERT|UPDATE|DELETE).*?\n.*?"
            r"RECORD LOCKS.*?`(\w+)`.(`\w+`)"
            r".*?TOO LONG, WE ROLL BACK.*?TRANSACTION (\d+)",
            re.DOTALL,
        )
        m = pattern.search(text)
        if m:
            evt = DeadlockEvent(
                timestamp=ts,
                txn1_xid=m.group(1),
                txn2_xid=m.group(5),
                txn1_query=m.group(2),
                txn2_query=m.group(6),
                txn1_lock=f"{m.group(3)}.{m.group(4)}",
                txn2_lock=f"{m.group(7)}.{m.group(8)}",
                victim=m.group(9),
                detail=text[m.start():m.end()],
            )
            self.deadlock_events.append(evt)
