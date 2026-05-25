"""
PostgreSQL WAL Parser - PostgreSQL WAL 解析器
通过 pg_waldump 工具解析 WAL 文件，提取事务边界、行操作、锁信息。

依赖: pg_waldump (PostgreSQL 自带工具), psycopg2 (可选，用于在线解析)
"""
import re
import subprocess
import shlex
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..config import PGConfig
from ..logger import setup_logger
from .base import (
    BaseParser, LockEvent, LockMode, TxnRecord, TxnStatus,
    DeadlockEvent,
)

logger = setup_logger("pg_parser")


class PostgresWALParser(BaseParser):
    """
    PostgreSQL WAL 解析器
    使用 pg_waldump 解析 WAL 文件，提取事务和锁信息。
    也可以通过解析 PostgreSQL 日志文件获取死锁信息。
    """

    # pg_waldump 输出中的 XLOG record 类型
    COMMIT_RECORD_TYPES = {"Commit", "CommitPrepared"}
    ROLLBACK_RECORD_TYPES = {"Abort", "RollbackPrepared"}
    START_RECORD_TYPES = {"StartPrepare"}
    ROW_RECORD_TYPES = {
        "INSERT", "UPDATE", "DELETE", "MULTI_INSERT",
        "ON_CONFLICT", "SPECULATIVE_INSERT",
    }

    def __init__(self, config: PGConfig):
        super().__init__(config)
        self.config = config
        self._pg_epoch = datetime(2000, 1, 1)

    def parse(self) -> List[TxnRecord]:
        """解析 WAL 文件，返回聚合后的事务记录"""
        if self.config.wal_file:
            return self._parse_wal_file()
        else:
            logger.warning("未指定 WAL 文件路径，跳过解析")
            return []

    def _parse_wal_file(self) -> List[TxnRecord]:
        """通过 pg_waldump 解析 WAL 文件"""
        wal_path = self.config.wal_file
        logger.info("开始解析 WAL 文件: %s", wal_path)

        try:
            cmd = f"{self.config.pg_waldump_path} --stats=none {wal_path}"
            result = subprocess.run(
                shlex.split(cmd),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                logger.error("pg_waldump 执行失败: %s", result.stderr)
                return []
            output = result.stdout
        except FileNotFoundError:
            logger.error("pg_waldump 工具未找到，请确认路径: %s", self.config.pg_waldump_path)
            return []
        except subprocess.TimeoutExpired:
            logger.error("pg_waldump 执行超时")
            return []

        self._parse_waldump_output(output)
        logger.info("WAL 解析完成，共 %d 条事务记录", len(self._completed_txns))
        return self.get_all_txns()

    def _parse_waldump_output(self, output: str):
        """解析 pg_waldump 文本输出"""
        # XID 跟踪: 按 XID 聚合行操作
        xid_pattern = re.compile(r"xid=(\d+)")
        current_xid: Optional[str] = None
        current_schema: Optional[str] = None

        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # 提取 XID
            xid_match = xid_pattern.search(line)
            if xid_match:
                xid = xid_match.group(1)
                if xid != current_xid:
                    if current_xid and current_xid in self._active_txns:
                        pass  # 保留旧事务
                    current_xid = xid
                    ts = self._extract_timestamp(line)
                    self._start_txn(xid, ts)
                    self._txn_start_times[xid] = ts

            # 识别 Commit / Abort
            if current_xid:
                if self._is_commit_record(line):
                    ts = self._extract_timestamp(line)
                    self._commit_txn(current_xid, ts)
                    current_xid = None
                    continue
                if self._is_rollback_record(line):
                    ts = self._extract_timestamp(line)
                    self._rollback_txn(current_xid, ts)
                    current_xid = None
                    continue

            # 识别行操作 (INSERT/UPDATE/DELETE)
            if current_xid:
                table_match = self._extract_table_info(line)
                if table_match:
                    schema, table = table_match
                    full_table = f"{schema}.{table}" if schema else table
                    txn = self._active_txns.get(current_xid)
                    if txn:
                        txn.increment_table_op(full_table)
                        txn.bytes_written += 256
                        if schema and not txn.schema:
                            txn.schema = schema

                    lock_mode = self._infer_pg_lock_mode(line)
                    ts = self._extract_timestamp(line)
                    self._record_lock(current_xid, LockEvent(
                        xid=current_xid,
                        timestamp=ts,
                        lock_mode=lock_mode,
                        object_name=full_table,
                        schema=schema,
                        granted=True,
                    ))

    def _extract_timestamp(self, line: str) -> datetime:
        """从 pg_waldump 输出中提取时间戳"""
        # 尝试匹配常见的时间格式
        ts_patterns = [
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)",
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
            r"(\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2})",
        ]
        for pat in ts_patterns:
            m = re.search(pat, line)
            if m:
                try:
                    ts_str = m.group(1)
                    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%d-%b-%Y %H:%M:%S"):
                        try:
                            return datetime.strptime(ts_str, fmt)
                        except ValueError:
                            continue
                except Exception:
                    pass
        return datetime.now()

    def _is_commit_record(self, line: str) -> bool:
        """判断是否是提交记录"""
        return any(
            f"XLOG {t}" in line for t in self.COMMIT_RECORD_TYPES
        ) or any(t in line for t in self.COMMIT_RECORD_TYPES)

    def _is_rollback_record(self, line: str) -> bool:
        """判断是否是回滚记录"""
        return any(
            f"XLOG {t}" in line for t in self.ROLLBACK_RECORD_TYPES
        ) or any(t in line for t in self.ROLLBACK_RECORD_TYPES)

    def _extract_table_info(self, line: str) -> Optional[tuple]:
        """从行操作中提取 schema.table"""
        patterns = [
            r"rel (?:(\w+)\.)?(\w+)",
            r"table(?:\s+(\w+)\.)?\s*(\w+)",
            r"`(\w+)`\.`(\w+)`",
            r"\[(\w+)\]\[(\w+)\]",
        ]
        for pat in patterns:
            m = re.search(pat, line, re.IGNORECASE)
            if m:
                schema = m.group(1) or "public"
                table = m.group(2)
                return (schema, table)
        return None

    @staticmethod
    def _infer_pg_lock_mode(line: str) -> LockMode:
        """根据操作类型推断锁模式"""
        upper = line.upper()
        if "INSERT" in upper:
            return LockMode.ROW_EXCLUSIVE
        if "UPDATE" in upper:
            return LockMode.ROW_EXCLUSIVE
        if "DELETE" in upper:
            return LockMode.ROW_EXCLUSIVE
        if "SELECT" in upper:
            return LockMode.ROW_SHARED
        if "TRUNCATE" in upper or "DROP" in upper:
            return LockMode.EXCLUSIVE
        if "CREATE" in upper or "ALTER" in upper:
            return LockMode.EXCLUSIVE
        return LockMode.UNKNOWN

    # ------------------------------------------------------------------
    #  死锁检测（通过 PostgreSQL 日志解析）
    # ------------------------------------------------------------------

    def parse_deadlocks_from_log(self, log_path: str) -> List[DeadlockEvent]:
        """从 PostgreSQL 日志中解析死锁事件"""
        deadlocks: List[DeadlockEvent] = []
        logger.info("从 PostgreSQL 日志解析死锁: %s", log_path)

        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except FileNotFoundError:
            logger.error("日志文件不存在: %s", log_path)
            return deadlocks

        # PostgreSQL 死锁日志格式:
        # 2025-01-15 10:30:45 UTC [12345] ERROR:  deadlock detected
        # ...
        # Process 12345 waits for ShareLock on transaction 100; blocked by process 12346.
        # Process 12346 waits for ShareLock on transaction 101; blocked by process 12345.

        deadlock_blocks = re.split(r"(\d{4}-\d{2}-\d{2}[^E]*?ERROR:\s+deadlock detected)", content)
        pattern = re.compile(
            r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[^E]*?deadlock detected)"
            r".*?"
            r"Process\s+(\d+).*?transaction\s+(\d+).*?blocked by process\s+(\d+)\."
            r".*?"
            r"Process\s+(\d+).*?transaction\s+(\d+).*?blocked by process\s+(\d+)\.",
            re.DOTALL,
        )

        for block in re.finditer(pattern.pattern, content, re.DOTALL):
            try:
                ts_str = block.group(1)
                ts = datetime.now()
                for fmt in ("%Y-%m-%d %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S"):
                    try:
                        ts = datetime.strptime(ts_str.split(" ERROR")[0].strip(), fmt)
                        break
                    except ValueError:
                        continue

                proc1 = block.group(2)
                xid1 = block.group(3)
                proc2 = block.group(4)
                proc3 = block.group(5)
                xid2 = block.group(6)
                proc4 = block.group(7)

                evt = DeadlockEvent(
                    timestamp=ts,
                    txn1_xid=xid1,
                    txn2_xid=xid2,
                    txn1_query=f"Process {proc1}",
                    txn2_query=f"Process {proc3}",
                    txn1_lock=f"Transaction {xid1}",
                    txn2_lock=f"Transaction {xid2}",
                    victim=xid2,
                    detail=block.group(0)[:500],
                )
                deadlocks.append(evt)
                self.deadlock_events.append(evt)
            except (IndexError, ValueError) as exc:
                logger.debug("解析死锁块失败: %s", exc)

        logger.info("解析到 %d 条死锁事件", len(deadlocks))
        return deadlocks

    # ------------------------------------------------------------------
    #  模拟数据生成（用于演示/测试）
    # ------------------------------------------------------------------

    def generate_mock_data(self, count: int = 50) -> List[TxnRecord]:
        """生成模拟的 PostgreSQL 事务数据"""
        import random
        from datetime import timedelta

        logger.info("生成 %d 条模拟 PostgreSQL 事务数据", count)

        schemas = ["public", "sales", "inventory", "reporting"]
        tables = [
            "public.orders", "public.customers", "public.products",
            "sales.sales_order", "sales.sales_detail",
            "inventory.stock", "inventory.warehouse",
            "reporting.daily_stats", "reporting.weekly_agg",
        ]
        operations = ["INSERT", "UPDATE", "DELETE", "SELECT"]

        base_ts = datetime.now() - timedelta(days=1)

        for i in range(count):
            xid = str(500 + i)
            start_ts = base_ts + timedelta(seconds=i * 30)
            duration = random.uniform(1, 5000)
            end_ts = start_ts + timedelta(milliseconds=duration)
            is_large = random.random() < 0.1
            schema = random.choice(schemas)

            txn = TxnRecord(
                xid=xid,
                start_time=start_ts,
                end_time=end_ts,
                status=TxnStatus.COMMIT if random.random() > 0.05 else TxnStatus.ROLLBACK,
                schema=schema,
                duration_ms=duration,
                row_ops_count=random.randint(1, 1000) if is_large else random.randint(1, 50),
                table_ops={},
                total_lock_wait_ms=random.uniform(0, 2000) if random.random() > 0.5 else 0,
                max_lock_wait_ms=random.uniform(0, 1000) if random.random() > 0.5 else 0,
                bytes_written=random.randint(100, 100_000_000) if is_large else random.randint(100, 500_000),
                queries=[f"{random.choice(operations)} INTO {random.choice(tables)}"],
                deadlock_victim=random.random() < 0.02,
            )

            for _ in range(random.randint(1, 5)):
                table = random.choice(tables)
                txn.increment_table_op(table)

            self._completed_txns.append(txn)

        # 生成死锁事件
        for i in range(random.randint(2, 8)):
            evt = DeadlockEvent(
                timestamp=base_ts + timedelta(seconds=i * 600),
                txn1_xid=str(500 + random.randint(0, count - 1)),
                txn2_xid=str(500 + random.randint(0, count - 1)),
                txn1_query=f"UPDATE {random.choice(tables)}",
                txn2_query=f"UPDATE {random.choice(tables)}",
                txn1_lock=f"Row lock on {random.choice(tables)}",
                txn2_lock=f"Row lock on {random.choice(tables)}",
                victim=str(500 + random.randint(0, count - 1)),
                detail="Mock deadlock detail",
            )
            self.deadlock_events.append(evt)

        logger.info("模拟数据生成完成，共 %d 条事务记录", len(self._completed_txns))
        return self.get_all_txns()
