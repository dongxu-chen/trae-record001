import re
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from .base_parser import DeadlockParser, Deadlock, Transaction, Lock


class PostgreSQLDeadlockParser(DeadlockParser):
    PG_VERSION_UNKNOWN = 'unknown'
    PG_VERSION_96 = '9.6'
    PG_VERSION_10 = '10'
    PG_VERSION_11 = '11'
    PG_VERSION_12 = '12'
    PG_VERSION_13 = '13'
    PG_VERSION_14 = '14'
    PG_VERSION_15 = '15'
    PG_VERSION_16 = '16'

    def __init__(self):
        self.detected_version = self.PG_VERSION_UNKNOWN

    def parse(self, log_content: str) -> List[Deadlock]:
        self.detected_version = self._detect_version(log_content)
        deadlocks = []
        deadlock_groups = self._group_deadlock_logs(log_content)

        for group in deadlock_groups:
            deadlock = self._parse_deadlock_group(group)
            if deadlock:
                deadlocks.append(deadlock)

        return deadlocks

    def _detect_version(self, log_content: str) -> str:
        version_patterns = [
            (r'PostgreSQL\s+16\.', self.PG_VERSION_16),
            (r'PostgreSQL\s+15\.', self.PG_VERSION_15),
            (r'PostgreSQL\s+14\.', self.PG_VERSION_14),
            (r'PostgreSQL\s+13\.', self.PG_VERSION_13),
            (r'PostgreSQL\s+12\.', self.PG_VERSION_12),
            (r'PostgreSQL\s+11\.', self.PG_VERSION_11),
            (r'PostgreSQL\s+10\.', self.PG_VERSION_10),
            (r'PostgreSQL\s+9\.6', self.PG_VERSION_96),
        ]

        for pattern, version in version_patterns:
            if re.search(pattern, log_content, re.IGNORECASE):
                return version

        if 'log_destination' in log_content or 'csvlog' in log_content:
            return self.PG_VERSION_14
        if 'transaction_isolation' in log_content:
            return self.PG_VERSION_13
        if 'idle_in_transaction_session_timeout' in log_content:
            return self.PG_VERSION_10
        if 'lock_timeout' in log_content:
            return self.PG_VERSION_96

        return self.PG_VERSION_UNKNOWN

    def _group_deadlock_logs(self, log_content: str) -> List[List[str]]:
        if self.detected_version in [self.PG_VERSION_14, self.PG_VERSION_15, self.PG_VERSION_16]:
            return self._group_modern_logs(log_content)
        else:
            return self._group_legacy_logs(log_content)

    def _group_modern_logs(self, log_content: str) -> List[List[str]]:
        groups = []
        current_group = []
        in_deadlock = False
        in_detail = False

        lines = log_content.split('\n')
        for line in lines:
            line_lower = line.lower()

            if 'deadlock detected' in line_lower:
                if current_group:
                    groups.append(current_group)
                current_group = [line]
                in_deadlock = True
                in_detail = False
            elif in_deadlock:
                if 'detail:' in line_lower:
                    in_detail = True
                    current_group.append(line)
                elif in_detail and ('query:' in line_lower or 'context:' in line_lower or
                                      re.match(r'^\s*process\s+\d+', line, re.IGNORECASE)):
                    current_group.append(line)
                elif in_detail and (line.strip().startswith('\t') or line.strip().startswith('  ')):
                    current_group.append(line)
                elif line.strip() and not line.strip().startswith('\t') and not line.strip().startswith('  '):
                    if current_group:
                        groups.append(current_group)
                    current_group = []
                    in_deadlock = False
                    in_detail = False

        if current_group:
            groups.append(current_group)

        return groups

    def _group_legacy_logs(self, log_content: str) -> List[List[str]]:
        lines = log_content.split('\n')
        groups = []
        current_group = []
        in_deadlock = False

        for line in lines:
            if 'deadlock detected' in line.lower():
                if current_group:
                    groups.append(current_group)
                current_group = [line]
                in_deadlock = True
            elif in_deadlock:
                if line.strip() and (line.startswith('\t') or line.startswith(' ') or
                                     'PROCESS' in line or 'TRANSACTION' in line or
                                     'DETAIL:' in line or 'QUERY:' in line):
                    current_group.append(line)
                elif line.strip() and not line.startswith('\t') and not line.startswith(' '):
                    if current_group:
                        groups.append(current_group)
                    current_group = []
                    in_deadlock = False

        if current_group:
            groups.append(current_group)

        return groups

    def _parse_deadlock_group(self, group: List[str]) -> Optional[Deadlock]:
        timestamp = self._extract_timestamp(group[0])
        detail_lines = []
        query_lines = []
        context_lines = []

        for line in group:
            if 'DETAIL:' in line:
                detail_lines.append(line)
            elif 'QUERY:' in line:
                query_lines.append(line)
            elif 'CONTEXT:' in line:
                context_lines.append(line)
            elif detail_lines and not query_lines:
                detail_lines.append(line)

        if self.detected_version in [self.PG_VERSION_15, self.PG_VERSION_16]:
            transactions = self._parse_detail_v15(detail_lines)
        elif self.detected_version in [self.PG_VERSION_12, self.PG_VERSION_13, self.PG_VERSION_14]:
            transactions = self._parse_detail_v12(detail_lines)
        else:
            transactions = self._parse_detail_legacy(detail_lines)

        if not transactions:
            return None

        self._associate_queries(transactions, query_lines, context_lines)
        victim_txns = self._find_victims(group)

        return Deadlock(
            timestamp=timestamp,
            transactions=transactions,
            victim_txns=victim_txns,
            raw_log='\n'.join(group)
        )

    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        patterns = []

        if self.detected_version in [self.PG_VERSION_14, self.PG_VERSION_15, self.PG_VERSION_16]:
            patterns.extend([
                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\s+[+-]?\d{4})',
                r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)',
                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)',
            ])
        else:
            patterns.extend([
                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\s+[+-]?\d{4})',
                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)',
                r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)',
            ])

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                ts_str = match.group(1)
                try:
                    if re.search(r'\s+[+-]\d{4}$', ts_str):
                        ts_str = re.sub(r'\s+[+-]\d{4}$', '', ts_str)

                    if 'T' in ts_str:
                        ts_str = ts_str.replace('T', ' ').replace('Z', '')

                    if '.' in ts_str:
                        ts_str = ts_str.split('.')[0]

                    return datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        return datetime.strptime(ts_str, '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        pass
        return None

    def _parse_detail_v15(self, detail_lines: List[str]) -> List[Transaction]:
        return self._parse_detail_v12(detail_lines)

    def _parse_detail_v12(self, detail_lines: List[str]) -> List[Transaction]:
        transactions = {}
        detail_text = ' '.join(detail_lines)

        process_blocks = re.split(r'(?:Process|process)\s+(\d+)', detail_text)

        for i in range(1, len(process_blocks), 2):
            pid = process_blocks[i]
            block = process_blocks[i + 1] if i + 1 < len(process_blocks) else ''

            txn = self._parse_process_block(pid, block)
            if txn:
                transactions[pid] = txn

        return list(transactions.values())

    def _parse_detail_legacy(self, detail_lines: List[str]) -> List[Transaction]:
        return self._parse_detail_v12(detail_lines)

    def _parse_process_block(self, pid: str, block: str) -> Optional[Transaction]:
        txn_id = f"PID-{pid}"

        virtual_xid_match = re.search(r'virtual transaction id\s+([0-9/]+)', block, re.IGNORECASE)
        if virtual_xid_match:
            txn_id = f"VXID-{virtual_xid_match.group(1)}"

        transaction_id_match = re.search(r'transaction id\s+(\d+)', block, re.IGNORECASE)
        if transaction_id_match:
            txn_id = f"TXN-{transaction_id_match.group(1)}"

        holding_locks = []
        waiting_lock = None

        if self.detected_version in [self.PG_VERSION_14, self.PG_VERSION_15, self.PG_VERSION_16]:
            tuple_hold_pattern = r'holds lock on tuple\s+\(([^)]+)\)\s+of\s+relation\s+(\S+?\.)?"?(\w+)"?.*?lockmode\s+(\w+)(?:\s+on\s+transaction\s+(\d+))?'
            tuple_wait_pattern = r'waiting for lock on tuple\s+\(([^)]+)\)\s+of\s+relation\s+(\S+?\.)?"?(\w+)"?.*?lockmode\s+(\w+)(?:\s+on\s+transaction\s+(\d+))?'
        else:
            tuple_hold_pattern = r'holds lock on tuple\s+\(([^)]+)\)\s+of\s+relation\s+(\S+?\.)?"?(\w+)"?.*?lockmode\s+(\w+)'
            tuple_wait_pattern = r'waiting for lock on tuple\s+\(([^)]+)\)\s+of\s+relation\s+(\S+?\.)?"?(\w+)"?.*?lockmode\s+(\w+)'

        relation_hold_pattern = r'holds lock on.*?relation\s+(\S+?\.)?"?(\w+)"?.*?lockmode\s+(\w+)(?=\s*while|$|\s+and|,\s*|Process\s+\d+)'
        relation_wait_pattern = r'waiting for lock on.*?relation\s+(\S+?\.)?"?(\w+)"?.*?lockmode\s+(\w+)(?=\s*while|$|\s+and|,\s*|Process\s+\d+)'

        for match in re.finditer(relation_hold_pattern, block, re.IGNORECASE):
            _, table_name, lock_mode = match.groups()
            table_name = table_name.strip('"').strip("'").strip()
            if table_name:
                holding_locks.append(Lock(
                    lock_type='RELATION',
                    lock_mode=lock_mode.strip(),
                    table_name=table_name
                ))

        for match in re.finditer(tuple_hold_pattern, block, re.IGNORECASE):
            groups = match.groups()
            record_info = groups[0]
            table_name = groups[2].strip('"').strip("'").strip()
            lock_mode = groups[3].strip()

            txn_id_held = groups[4] if len(groups) > 4 else None

            if table_name:
                holding_locks.append(Lock(
                    lock_type='TUPLE',
                    lock_mode=lock_mode,
                    table_name=table_name,
                    record_info=record_info,
                    raw_info=f"held by transaction {txn_id_held}" if txn_id_held else None
                ))

        wait_match = re.search(relation_wait_pattern, block, re.IGNORECASE)
        if wait_match:
            _, table_name, lock_mode = wait_match.groups()
            table_name = table_name.strip('"').strip("'").strip()
            if table_name:
                waiting_lock = Lock(
                    lock_type='RELATION',
                    lock_mode=lock_mode.strip(),
                    table_name=table_name
                )

        tuple_wait_match = re.search(tuple_wait_pattern, block, re.IGNORECASE)
        if tuple_wait_match:
            groups = tuple_wait_match.groups()
            record_info = groups[0]
            table_name = groups[2].strip('"').strip("'").strip()
            lock_mode = groups[3].strip()

            waiting_txn_id = groups[4] if len(groups) > 4 else None

            if table_name:
                waiting_lock = Lock(
                    lock_type='TUPLE',
                    lock_mode=lock_mode,
                    table_name=table_name,
                    record_info=record_info,
                    raw_info=f"waiting for transaction {waiting_txn_id}" if waiting_txn_id else None
                )

        if not holding_locks and not waiting_lock:
            return None

        return Transaction(
            txn_id=txn_id,
            status='WAITING' if waiting_lock else 'HOLDING',
            sql_statements=[],
            holding_locks=holding_locks,
            waiting_lock=waiting_lock
        )

    def _associate_queries(self, transactions: List[Transaction], query_lines: List[str], context_lines: List[str] = None):
        pid_to_sql = {}
        pid_to_context = {}
        current_pid = None

        for line in query_lines:
            pid_match = re.search(r'(?:Process|process)\s+(\d+)', line)
            if pid_match:
                current_pid = pid_match.group(1)
                pid_to_sql[current_pid] = []
            elif current_pid and 'QUERY:' in line:
                query_match = re.search(r'QUERY:\s*(.*)', line, re.DOTALL)
                if query_match:
                    sql = self._normalize_sql(query_match.group(1))
                    if sql:
                        pid_to_sql[current_pid].append(sql)

        if context_lines:
            for line in context_lines:
                pid_match = re.search(r'(?:Process|process)\s+(\d+)', line)
                if pid_match:
                    current_pid = pid_match.group(1)
                    pid_to_context[current_pid] = []
                elif current_pid and 'CONTEXT:' in line:
                    context_match = re.search(r'CONTEXT:\s*(.*)', line, re.DOTALL)
                    if context_match:
                        pid_to_context[current_pid].append(context_match.group(1).strip())

        for txn in transactions:
            pid = txn.txn_id.replace('PID-', '').replace('VXID-', '').replace('TXN-', '')
            for key in pid_to_sql:
                if key in txn.txn_id or txn.txn_id.endswith(key):
                    txn.sql_statements = pid_to_sql[key]
                    if pid_to_context and key in pid_to_context:
                        pass
                    break

    def _find_victims(self, group: List[str]) -> List[str]:
        victims = []
        for line in group:
            match = re.search(r'(?:process|Process)\s+(\d+).*?deadlock victim', line, re.IGNORECASE)
            if match:
                victims.append(f"PID-{match.group(1)}")

            match = re.search(r'(?:process|Process)\s+(\d+).*?rollback', line, re.IGNORECASE)
            if match and f"PID-{match.group(1)}" not in victims:
                victims.append(f"PID-{match.group(1)}")

            match = re.search(r'rollback\s+.*?transaction\s+(\d+)', line, re.IGNORECASE)
            if match:
                victims.append(f"TXN-{match.group(1)}")

            match = re.search(r'chosen as deadlock victim.*?transaction\s+(\d+)', line, re.IGNORECASE)
            if match:
                victims.append(f"TXN-{match.group(1)}")

        return victims

    def get_detected_version(self) -> str:
        return self.detected_version
