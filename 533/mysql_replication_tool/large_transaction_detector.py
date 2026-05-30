import logging
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from .mysql_connection import MySQLConnection

logger = logging.getLogger(__name__)


@dataclass
class LargeTransaction:
    id: int
    user: str
    host: str
    db: str
    command: str
    time: int
    state: str
    info: str
    rows_affected: int
    rows_examined: int
    lock_time: float
    transaction_size_est: int
    estimated_bytes: int
    comprehensive_score: float
    size_level: str
    is_blocking: bool
    blocking_transactions: List[int]


class LargeTransactionDetector:
    def __init__(self, master_conn: MySQLConnection, slave_conn: MySQLConnection, config: Dict[str, Any]):
        self.master_conn = master_conn
        self.slave_conn = slave_conn
        self.config = config
        self.duration_threshold = config.get('large_transaction', {}).get('duration_threshold', 10)
        self.rows_threshold = config.get('large_transaction', {}).get('rows_affected_threshold', 10000)
        self.bytes_threshold = config.get('large_transaction', {}).get('bytes_threshold', 1024 * 1024 * 10)
        self.lock_wait_threshold = config.get('large_transaction', {}).get('lock_wait_threshold', 5)
        self.avg_row_size_bytes = config.get('large_transaction', {}).get('avg_row_size_bytes', 500)

    def detect_large_transactions(self) -> List[LargeTransaction]:
        logger.info("开始检测大事务...")
        transactions = []

        master_transactions = self._detect_on_connection(self.master_conn, "master")
        slave_transactions = self._detect_on_connection(self.slave_conn, "slave")

        transactions.extend(master_transactions)
        transactions.extend(slave_transactions)

        logger.info(f"检测完成，共发现{len(transactions)}个大事务")
        return transactions

    def _detect_on_connection(self, conn: MySQLConnection, role: str) -> List[LargeTransaction]:
        transactions = []

        try:
            processlist = conn.get_processlist()
            innodb_trx = self._get_innodb_transactions(conn)
            innodb_locks = self._get_innodb_locks(conn)

            for process in processlist:
                if self._is_large_transaction(process, innodb_trx, innodb_locks):
                    trans = self._build_transaction(process, innodb_trx, innodb_locks)
                    transactions.append(trans)

        except Exception as e:
            logger.error(f"在{role}检测大事务失败: {str(e)}")

        return transactions

    def _get_innodb_transactions(self, conn: MySQLConnection) -> Dict[int, Dict[str, Any]]:
        try:
            results = conn.execute_query("""
                SELECT
                    trx_id,
                    trx_state,
                    trx_started,
                    trx_wait_started,
                    trx_weight,
                    trx_mysql_thread_id,
                    trx_query,
                    trx_rows_locked,
                    trx_rows_modified,
                    trx_lock_memory_bytes,
                    TIMESTAMPDIFF(SECOND, trx_started, NOW()) as trx_duration
                FROM information_schema.innodb_trx
            """)
            return {int(row['trx_mysql_thread_id']): row for row in results}
        except Exception as e:
            logger.warning(f"获取InnoDB事务信息失败: {str(e)}")
            return {}

    def _get_innodb_locks(self, conn: MySQLConnection) -> Dict[int, List[Dict[str, Any]]]:
        try:
            results = conn.execute_query("""
                SELECT
                    r.trx_id as requesting_trx_id,
                    r.trx_mysql_thread_id as requesting_thread_id,
                    b.trx_id as blocking_trx_id,
                    b.trx_mysql_thread_id as blocking_thread_id
                FROM information_schema.innodb_lock_waits w
                INNER JOIN information_schema.innodb_trx r ON w.requesting_trx_id = r.trx_id
                INNER JOIN information_schema.innodb_trx b ON w.blocking_trx_id = b.trx_id
            """)
            lock_map = {}
            for row in results:
                thread_id = int(row['requesting_thread_id'])
                if thread_id not in lock_map:
                    lock_map[thread_id] = []
                lock_map[thread_id].append(row)
            return lock_map
        except Exception as e:
            logger.warning(f"获取InnoDB锁信息失败: {str(e)}")
            return {}

    def _is_large_transaction(self, process: Dict[str, Any],
                               innodb_trx: Dict[int, Dict[str, Any]],
                               innodb_locks: Dict[int, List[Dict[str, Any]]]) -> bool:
        try:
            process_time = int(process.get('Time', 0) or 0)
            process_id = int(process.get('Id', 0) or 0)
            process_info = process.get('Info', '') or ''

            if process_time >= self.duration_threshold and process.get('Command') == 'Query':
                if self._is_write_operation(process_info):
                    return True

            if process_id in innodb_trx:
                trx = innodb_trx[process_id]
                trx_duration = int(trx.get('trx_duration', 0) or 0)
                rows_modified = int(trx.get('trx_rows_modified', 0) or 0)
                rows_locked = int(trx.get('trx_rows_locked', 0) or 0)
                lock_memory_bytes = int(trx.get('trx_lock_memory_bytes', 0) or 0)
                estimated_bytes = rows_modified * self.avg_row_size_bytes + lock_memory_bytes

                if trx_duration >= self.duration_threshold:
                    return True

                if rows_modified >= self.rows_threshold:
                    return True

                if rows_locked >= self.rows_threshold:
                    return True

                if estimated_bytes >= self.bytes_threshold:
                    return True

            if process_id in innodb_locks:
                return True

            return False

        except Exception as e:
            logger.warning(f"判断事务是否为大事务时出错: {str(e)}")
            return False

    def _calculate_comprehensive_score(self, time_sec: int, rows: int, bytes_est: int,
                                       is_blocking: bool) -> float:
        score = 0.0

        time_score = min(time_sec / 60.0, 1.0) * 30
        rows_score = min(rows / self.rows_threshold, 1.0) * 35
        bytes_score = min(bytes_est / self.bytes_threshold, 1.0) * 25
        blocking_score = 10 if is_blocking else 0

        score = time_score + rows_score + bytes_score + blocking_score
        return min(score, 100.0)

    def _get_size_level(self, score: float) -> str:
        if score >= 80:
            return "CRITICAL"
        elif score >= 60:
            return "LARGE"
        elif score >= 40:
            return "MEDIUM"
        elif score >= 20:
            return "SMALL"
        else:
            return "TINY"

    def _is_write_operation(self, sql: str) -> bool:
        if not sql:
            return False
        sql_upper = sql.upper().strip()
        write_keywords = ['INSERT', 'UPDATE', 'DELETE', 'REPLACE', 'CREATE', 'ALTER', 'DROP', 'TRUNCATE']
        return any(sql_upper.startswith(keyword) for keyword in write_keywords)

    def _build_transaction(self, process: Dict[str, Any],
                           innodb_trx: Dict[int, Dict[str, Any]],
                           innodb_locks: Dict[int, List[Dict[str, Any]]]) -> LargeTransaction:
        process_id = int(process.get('Id', 0) or 0)

        rows_affected = 0
        rows_examined = 0
        lock_time = 0
        transaction_size_est = 0
        estimated_bytes = 0

        if process_id in innodb_trx:
            trx = innodb_trx[process_id]
            rows_affected = int(trx.get('trx_rows_modified', 0) or 0)
            rows_examined = int(trx.get('trx_rows_locked', 0) or 0)
            transaction_size_est = int(trx.get('trx_weight', 0) or 0)
            lock_memory_bytes = int(trx.get('trx_lock_memory_bytes', 0) or 0)
            estimated_bytes = rows_affected * self.avg_row_size_bytes + lock_memory_bytes

        is_blocking = process_id in innodb_locks
        blocking_transactions = []
        if is_blocking:
            for lock in innodb_locks.get(process_id, []):
                blocking_thread_id = int(lock.get('blocking_thread_id', 0) or 0)
                if blocking_thread_id not in blocking_transactions:
                    blocking_transactions.append(blocking_thread_id)

        process_time = int(process.get('Time', 0) or 0)
        comprehensive_score = self._calculate_comprehensive_score(
            process_time, rows_affected, estimated_bytes, is_blocking
        )
        size_level = self._get_size_level(comprehensive_score)

        return LargeTransaction(
            id=process_id,
            user=process.get('User', ''),
            host=process.get('Host', ''),
            db=process.get('db', ''),
            command=process.get('Command', ''),
            time=process_time,
            state=process.get('State', ''),
            info=(process.get('Info', '') or '')[:500],
            rows_affected=rows_affected,
            rows_examined=rows_examined,
            lock_time=lock_time,
            transaction_size_est=transaction_size_est,
            estimated_bytes=estimated_bytes,
            comprehensive_score=comprehensive_score,
            size_level=size_level,
            is_blocking=is_blocking,
            blocking_transactions=blocking_transactions
        )

    def get_transaction_summary(self, transactions: List[LargeTransaction]) -> Dict[str, Any]:
        if not transactions:
            return {
                "count": 0,
                "max_duration": 0,
                "max_rows_affected": 0,
                "max_bytes": 0,
                "max_score": 0,
                "blocking_count": 0,
                "size_distribution": {},
                "high_risk_transactions": []
            }

        high_risk = [
            t for t in transactions
            if t.time >= 60 or t.rows_affected >= self.rows_threshold * 10 or t.is_blocking or t.size_level in ["CRITICAL", "LARGE"]
        ]

        size_distribution = {}
        for t in transactions:
            level = t.size_level
            size_distribution[level] = size_distribution.get(level, 0) + 1

        return {
            "count": len(transactions),
            "max_duration": max(t.time for t in transactions),
            "max_rows_affected": max(t.rows_affected for t in transactions),
            "max_bytes": max(t.estimated_bytes for t in transactions),
            "max_score": max(t.comprehensive_score for t in transactions),
            "blocking_count": sum(1 for t in transactions if t.is_blocking),
            "size_distribution": size_distribution,
            "high_risk_count": len(high_risk),
            "high_risk_transactions": [
                {
                    "id": t.id,
                    "user": t.user,
                    "time": t.time,
                    "rows_affected": t.rows_affected,
                    "estimated_bytes": t.estimated_bytes,
                    "score": t.comprehensive_score,
                    "size_level": t.size_level,
                    "is_blocking": t.is_blocking,
                    "sql": t.info[:100]
                }
                for t in high_risk
            ]
        }

    def generate_kill_recommendations(self, transactions: List[LargeTransaction]) -> List[Dict[str, Any]]:
        recommendations = []
        for t in transactions:
            if t.time >= 300:
                recommendations.append({
                    "action": "KILL",
                    "thread_id": t.id,
                    "reason": f"事务运行时间过长 ({t.time}秒)",
                    "severity": "HIGH"
                })
            elif t.is_blocking and t.time >= 60:
                recommendations.append({
                    "action": "KILL",
                    "thread_id": t.id,
                    "reason": f"阻塞其他事务，运行时间: {t.time}秒",
                    "severity": "HIGH"
                })
            elif t.rows_affected >= self.rows_threshold * 5:
                recommendations.append({
                    "action": "WARNING",
                    "thread_id": t.id,
                    "reason": f"大事务影响行数过多 ({t.rows_affected}行)",
                    "severity": "MEDIUM"
                })

        return recommendations
