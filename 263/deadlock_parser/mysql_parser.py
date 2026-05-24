import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from .base_parser import DeadlockParser, Deadlock, Transaction, Lock


class MySQLDeadlockParser(DeadlockParser):
    MYSQL_VERSION_UNKNOWN = 'unknown'
    MYSQL_VERSION_57 = '5.7'
    MYSQL_VERSION_80 = '8.0'

    def __init__(self):
        self.detected_version = self.MYSQL_VERSION_UNKNOWN

    def parse(self, log_content: str) -> List[Deadlock]:
        self.detected_version = self._detect_version(log_content)
        deadlocks = []
        deadlock_blocks = self._split_deadlock_blocks(log_content)

        for block in deadlock_blocks:
            deadlock = self._parse_deadlock_block(block)
            if deadlock:
                deadlocks.append(deadlock)

        return deadlocks

    def _detect_version(self, log_content: str) -> str:
        if '8.0' in log_content or 'utf8mb4_0900_ai_ci' in log_content:
            return self.MYSQL_VERSION_80
        if '5.7' in log_content or 'utf8mb4_general_ci' in log_content:
            return self.MYSQL_VERSION_57

        patterns_80 = [
            r'ROW LOGGING IS ENABLED.*?8\.0',
            r'json_extract',
            r'utf8mb4_0900'
        ]
        for pattern in patterns_80:
            if re.search(pattern, log_content, re.IGNORECASE | re.DOTALL):
                return self.MYSQL_VERSION_80

        patterns_57 = [
            r'ROW LOGGING IS ENABLED.*?5\.7',
            r'utf8mb4_general_ci',
            r'innodb_file_format'
        ]
        for pattern in patterns_57:
            if re.search(pattern, log_content, re.IGNORECASE | re.DOTALL):
                return self.MYSQL_VERSION_57

        return self.MYSQL_VERSION_UNKNOWN

    def _split_deadlock_blocks(self, log_content: str) -> List[str]:
        patterns = [
            r'(?=\*\*\*\s+\(1\)\s+TRANSACTION)',
            r'(?=------------------------\nLATEST DETECTED DEADLOCK)',
            r'(?=LATEST DETECTED DEADLOCK)'
        ]

        blocks = [log_content]
        for pattern in patterns:
            new_blocks = []
            for b in blocks:
                split_blocks = re.split(pattern, b)
                new_blocks.extend(split_blocks)
            blocks = new_blocks

        return [b for b in blocks if 'TRANSACTION' in b or 'DEADLOCK' in b]

    def _parse_deadlock_block(self, block: str) -> Optional[Deadlock]:
        timestamp = self._extract_timestamp(block)
        transactions = []
        victim_txns = []

        if self.detected_version == self.MYSQL_VERSION_80:
            txn_sections = self._split_80_transactions(block)
        else:
            txn_sections = re.split(r'\*\*\*\s+\(\d+\)\s+TRANSACTION', block)

        for i, txn_section in enumerate(txn_sections[1:], 1):
            parts = re.split(r'\*\*\*\s+\(\d+\)\s+', txn_section)
            txn_part = parts[0].strip()

            txn = self._parse_single_transaction(txn_part, i)
            if txn:
                transactions.append(txn)
                if self._is_victim(txn_part):
                    victim_txns.append(txn.txn_id)

        if not transactions:
            return None

        return Deadlock(
            timestamp=timestamp,
            transactions=transactions,
            victim_txns=victim_txns,
            raw_log=block
        )

    def _split_80_transactions(self, block: str) -> List[str]:
        sections = re.split(r'\*\*\*\s+\(\d+\)\s+TRANSACTION', block)
        if len(sections) > 1:
            return sections

        json_match = re.search(r'"transactions"\s*:\s*\[', block)
        if json_match:
            return self._parse_80_json_transactions(block)

        return sections

    def _parse_80_json_transactions(self, block: str) -> List[str]:
        sections = ['']

        json_match = re.search(r'"transactions"\s*:\s*\[(.*?)\]', block, re.DOTALL)
        if json_match:
            try:
                import json
                json_str = '[' + json_match.group(1) + ']'
                txns = json.loads(json_str)
                for i, txn in enumerate(txns, 1):
                    txn_text = f"TRANSACTION {txn.get('transaction_id', f'{i}')}\n"
                    txn_text += f"ACTIVE {txn.get('active_secs', 0)} sec\n"
                    if txn.get('waiting'):
                        txn_text += "LOCK WAIT\n"
                    for query in txn.get('queries', []):
                        txn_text += f"{query}\n"
                    sections.append(txn_text)
            except Exception:
                pass

        return sections

    def _extract_timestamp(self, block: str) -> Optional[datetime]:
        patterns = []

        if self.detected_version == self.MYSQL_VERSION_80:
            patterns.extend([
                r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)',
                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)',
                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})'
            ])
        else:
            patterns.extend([
                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',
                r'(\d{6}\s+\d{2}:\d{2}:\d{2})',
                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+0x[0-9a-f]+)'
            ])

        for pattern in patterns:
            match = re.search(pattern, block)
            if match:
                ts_str = match.group(1)
                try:
                    ts_str = ts_str.split(' ')[0] + ' ' + ts_str.split(' ')[1].split('0x')[0].strip()

                    if 'T' in ts_str:
                        ts_str = ts_str.replace('T', ' ').replace('Z', '')

                    if len(ts_str) >= 19 and '.' in ts_str:
                        ts_str = ts_str.split('.')[0]

                    if len(ts_str) == 15 and ts_str[6] == ' ':
                        year = '20' + ts_str[:2]
                        month = ts_str[2:4]
                        day = ts_str[4:6]
                        time_part = ts_str[7:]
                        ts_str = f"{year}-{month}-{day} {time_part}"

                    return datetime.strptime(ts_str[:19], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass
        return None

    def _parse_single_transaction(self, txn_text: str, txn_num: int) -> Optional[Transaction]:
        txn_id = self._extract_transaction_id(txn_text, txn_num)
        status = self._extract_txn_status(txn_text)
        wait_time = self._extract_wait_time(txn_text)
        sql_statements = self._extract_sql_statements(txn_text)
        holding_locks = self._extract_holding_locks(txn_text)
        waiting_lock = self._extract_waiting_lock(txn_text)

        return Transaction(
            txn_id=txn_id,
            status=status,
            start_time=None,
            wait_time=wait_time,
            sql_statements=sql_statements,
            holding_locks=holding_locks,
            waiting_lock=waiting_lock
        )

    def _extract_transaction_id(self, txn_text: str, txn_num: int) -> str:
        patterns = [
            r'TRANSACTION\s+([0-9A-F]+)',
            r'TRANSACTION\s+(\d+)',
            r'trx_id["\s:=]+["\']?(\d+)["\']?',
            r'"transaction_id"\s*:\s*["\']?(\d+)["\']?'
        ]

        for pattern in patterns:
            match = re.search(pattern, txn_text, re.IGNORECASE)
            if match:
                return match.group(1)

        return f"TXN-{txn_num}"

    def _extract_txn_status(self, block: str) -> str:
        if 'LOCK WAIT' in block:
            return 'WAITING'
        if 'HOLDS THE LOCK' in block:
            return 'HOLDING'
        if 'ROLLING BACK' in block:
            return 'ROLLING BACK'
        if '"waiting"\s*:\s*true' in block.lower():
            return 'WAITING'
        return 'ACTIVE'

    def _extract_wait_time(self, block: str) -> Optional[int]:
        patterns = [
            r'ACTIVE\s+(\d+)\s+sec',
            r'wait\s+for\s+(\d+)\s+sec',
            r'LOCK WAIT\s+(\d+)\s+lock',
            r'wait_time["\s:=]+["\']?(\d+)["\']?',
            r'"wait_time"\s*:\s*(\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, block, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass
        return None

    def _extract_sql_statements(self, block: str) -> List[str]:
        sqls = []

        lines = block.split('\n')
        in_sql_section = False

        for line in lines:
            line = line.strip()

            if re.match(r'(?:MySQL thread id|Thread id|Query id|Connection id)', line, re.IGNORECASE):
                in_sql_section = True
                continue

            if re.match(r'(?:RECORD LOCKS|TABLE LOCK|HOLDS THE LOCK|WAITING FOR|\*\*\*)', line):
                in_sql_section = False

            if in_sql_section and line:
                if re.match(r'^(SELECT|INSERT|UPDATE|DELETE|BEGIN|COMMIT|ROLLBACK|ALTER|CREATE|DROP|REPLACE|MERGE)', line, re.IGNORECASE):
                    normalized = self._normalize_sql(line)
                    if normalized:
                        sqls.append(normalized)
                elif sqls and not line.startswith('RECORD') and not line.startswith('HOLDS') and not line.startswith('WAITING'):
                    sqls[-1] += ' ' + line

        json_sqls = re.findall(r'"query"\s*:\s*"([^"]+)"', block)
        for sql in json_sqls:
            normalized = self._normalize_sql(sql)
            if normalized and normalized not in sqls:
                sqls.append(normalized)

        return sqls

    def _extract_holding_locks(self, block: str) -> List[Lock]:
        locks = []

        holds_section = re.search(r'HOLDS THE LOCK\(S\):(.*?)(?=WAITING FOR|\*\*\*|WE ROLL BACK|$)', block, re.DOTALL)
        if holds_section:
            holds_text = holds_section.group(1)
            locks.extend(self._parse_lock_entries(holds_text))

        json_holds = re.findall(r'"holding_locks"\s*:\s*\[(.*?)\]', block, re.DOTALL)
        for holds_json in json_holds:
            try:
                import json
                lock_list = json.loads('[' + holds_json + ']')
                for lock_data in lock_list:
                    locks.append(Lock(
                        lock_type=lock_data.get('type', 'RECORD'),
                        lock_mode=lock_data.get('mode', 'X'),
                        table_name=lock_data.get('table', ''),
                        index_name=lock_data.get('index'),
                        record_info=lock_data.get('record')
                    ))
            except Exception:
                pass

        return locks

    def _extract_waiting_lock(self, block: str) -> Optional[Lock]:
        waiting_section = re.search(r'WAITING FOR THIS LOCK TO BE GRANTED:(.*?)(?=\*\*\*|HOLDS THE|$)', block, re.DOTALL)
        if waiting_section:
            waiting_text = waiting_section.group(1)
            locks = self._parse_lock_entries(waiting_text)
            if locks:
                return locks[0]

        json_wait = re.search(r'"waiting_lock"\s*:\s*\{(.*?)\}', block, re.DOTALL)
        if json_wait:
            try:
                import json
                lock_data = json.loads('{' + json_wait.group(1) + '}')
                return Lock(
                    lock_type=lock_data.get('type', 'RECORD'),
                    lock_mode=lock_data.get('mode', 'X'),
                    table_name=lock_data.get('table', ''),
                    index_name=lock_data.get('index'),
                    record_info=lock_data.get('record')
                )
            except Exception:
                pass

        return None

    def _parse_lock_entries(self, text: str) -> List[Lock]:
        locks = []

        if self.detected_version == self.MYSQL_VERSION_80:
            lock_pattern = r'RECORD LOCKS.*?index\s+`([^`]+)`\s+of\s+table\s+`([^`]+)`.*?lock\s+mode\s+(\S+)(?:\s+(.*?))?(?=\n(?:RECORD LOCKS|TABLE LOCK|$))'
        else:
            lock_pattern = r'RECORD LOCKS.*?index\s+`([^`]+)`\s+of\s+table\s+`([^`]+)`.*?lock\s+mode\s+(\S+)(?:\s+(.*?))?(?=\n(?:RECORD LOCKS|TABLE LOCK|$))'

        for match in re.finditer(lock_pattern, text, re.DOTALL):
            index_name, table_full, lock_mode, record_info = match.groups()
            table_name = table_full.split('.')[-1]

            record_info_text = None
            if record_info:
                record_match = re.search(r'(?:Record lock|PHYSICAL RECORD).*', record_info)
                if record_match:
                    record_info_text = record_match.group(0).strip()

            locks.append(Lock(
                lock_type='RECORD',
                lock_mode=lock_mode.strip(),
                table_name=table_name,
                index_name=index_name,
                record_info=record_info_text
            ))

        table_lock_pattern = r'TABLE LOCK.*?table\s+`([^`]+)`.*?lock\s+mode\s+(\S+)'
        for match in re.finditer(table_lock_pattern, text):
            table_full, lock_mode = match.groups()
            table_name = table_full.split('.')[-1]

            locks.append(Lock(
                lock_type='TABLE',
                lock_mode=lock_mode.strip(),
                table_name=table_name,
                index_name=None,
                record_info=None
            ))

        return locks

    def _is_victim(self, block: str) -> bool:
        patterns = [
            r'WE ROLL BACK TRANSACTION',
            r'chosen as deadlock victim',
            r'"is_victim"\s*:\s*true',
            r'ROLLING BACK.*?transaction'
        ]
        return any(re.search(p, block, re.IGNORECASE) for p in patterns)

    def get_detected_version(self) -> str:
        return self.detected_version
