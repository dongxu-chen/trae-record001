import pymysql
import re
import json
from datetime import datetime
from config import Config

class DeadlockAnalyzer:
    def __init__(self):
        self.connection_params = Config.get_connection_params()
        self.deadlocks = []
        self.conn = None
    
    def get_connection(self):
        if not self.conn or not self.conn.open:
            self.conn = pymysql.connect(**self.connection_params)
        return self.conn
    
    def close_connection(self):
        if self.conn and self.conn.open:
            self.conn.close()
    
    def get_innodb_status(self):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SHOW ENGINE INNODB STATUS")
                result = cursor.fetchone()
                return result[2] if result else None
        finally:
            pass
    
    def get_processlist(self):
        conn = self.get_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("SHOW FULL PROCESSLIST")
                return cursor.fetchall()
        except Exception as e:
            print(f"获取进程列表失败: {e}")
            return []
    
    def get_locks_info(self):
        conn = self.get_connection()
        locks = []
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        r.trx_id waiting_trx_id,
                        r.trx_mysql_thread_id waiting_thread,
                        r.trx_query waiting_query,
                        b.trx_id blocking_trx_id,
                        b.trx_mysql_thread_id blocking_thread,
                        b.trx_query blocking_query,
                        b.trx_state blocking_state,
                        TIMESTAMPDIFF(SECOND, b.trx_wait_started, NOW()) as wait_seconds
                    FROM information_schema.innodb_lock_waits w
                    JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id
                    JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id
                """)
                locks = cursor.fetchall()
        except Exception as e:
            print(f"获取锁信息失败: {e}")
        return locks
    
    def parse_deadlock_log(self, innodb_status):
        deadlock_section = self._extract_deadlock_section(innodb_status)
        if not deadlock_section:
            return None
        
        return self._parse_deadlock_transactions_enhanced(deadlock_section)
    
    def _extract_deadlock_section(self, innodb_status):
        pattern = r'------------------------\nLATEST DETECTED DEADLOCK\n------------------------\n(.*?)\n------------'
        match = re.search(pattern, innodb_status, re.DOTALL)
        return match.group(1) if match else None
    
    def _parse_deadlock_transactions_enhanced(self, deadlock_section):
        transactions = []
        lines = deadlock_section.split('\n')
        
        current_transaction = None
        current_waiting_for = None
        current_holds = []
        
        deadlock_time = self._extract_deadlock_time(lines)
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            txn_match = re.match(r'\*\*\* \((\d+)\) TRANSACTION', line)
            if txn_match:
                if current_transaction:
                    if current_waiting_for:
                        current_transaction['waiting_for'] = current_waiting_for
                    current_transaction['holds'] = current_holds
                    transactions.append(current_transaction)
                
                txn_id = txn_match.group(1)
                current_transaction = {
                    'transaction_id': txn_id,
                    'timestamp': deadlock_time or datetime.now().isoformat(),
                    'queries': [],
                    'holds': [],
                    'waiting_for': None,
                    'thread_id': None,
                    'os_thread_handle': None,
                    'query_id': None,
                    'trx_weight': None,
                    'rows_locked': None,
                    'rows_modified': None
                }
                current_waiting_for = None
                current_holds = []
            
            thread_match = re.search(r'MySQL thread id (\d+), OS thread handle ([\wxa-f0-9]+)(?:, query id (\d+))?', line)
            if thread_match and current_transaction:
                current_transaction['thread_id'] = thread_match.group(1)
                current_transaction['os_thread_handle'] = thread_match.group(2)
                if thread_match.group(3):
                    current_transaction['query_id'] = thread_match.group(3)
            
            trx_info_match = re.search(r'TRX HAS BEEN WAITING (\d+) SEC FOR THIS LOCK TO BE GRANTED', line)
            if trx_info_match and current_transaction:
                current_transaction['wait_seconds'] = int(trx_info_match.group(1))
            
            weight_match = re.search(r'TRX WEIGHT, (\d+) \((\d+) ROW LOCK, (\d+) ROWS MODIFIED\)', line)
            if weight_match and current_transaction:
                current_transaction['trx_weight'] = int(weight_match.group(1))
                current_transaction['rows_locked'] = int(weight_match.group(2))
                current_transaction['rows_modified'] = int(weight_match.group(3))
            
            if (line.startswith('DELETE') or line.startswith('INSERT') or 
                line.startswith('UPDATE') or line.startswith('SELECT') or
                line.startswith('REPLACE') or line.startswith('SET')):
                if current_transaction:
                    current_transaction['queries'].append(line)
            
            if 'WAITING FOR THIS LOCK TO BE GRANTED' in line:
                i += 1
                lock_info = self._parse_lock_details(lines, i)
                current_waiting_for = lock_info
                i += lock_info.get('lines_consumed', 0)
            
            if 'HOLDS THE LOCK(S)' in line:
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('***') and not 'WAITING' in lines[i]:
                    lock_line = lines[i].strip()
                    if lock_line and 'lock struct' not in lock_line.lower():
                        hold_lock = self._parse_lock_details_line(lock_line)
                        if hold_lock:
                            current_holds.append(hold_lock)
                    i += 1
                i -= 1
            
            i += 1
        
        if current_transaction:
            if current_waiting_for:
                current_transaction['waiting_for'] = current_waiting_for
            current_transaction['holds'] = current_holds
            transactions.append(current_transaction)
        
        return {
            'timestamp': deadlock_time or datetime.now().isoformat(),
            'transactions': transactions,
            'raw_log': deadlock_section,
            'victim_index': self._find_victim_index(transactions)
        }
    
    def _extract_deadlock_time(self, lines):
        for line in lines:
            time_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            if time_match:
                return datetime.strptime(time_match.group(1), '%Y-%m-%d %H:%M:%S').isoformat()
        return None
    
    def _find_victim_index(self, transactions):
        for i, txn in enumerate(transactions):
            if txn.get('waiting_for') and not txn.get('holds'):
                return i
        return len(transactions) - 1 if transactions else 0
    
    def _parse_lock_details(self, lines, start_idx):
        lock_info = {
            'type': 'UNKNOWN',
            'mode': 'UNKNOWN',
            'table': 'UNKNOWN',
            'index': 'UNKNOWN',
            'space_id': None,
            'page_no': None,
            'n_bits': None,
            'record_data': None,
            'lines_consumed': 0
        }
        
        i = start_idx
        while i < len(lines):
            line = lines[i].strip()
            if not line or '***' in line or 'WAITING' in line or 'HOLDS' in line:
                break
            
            record_match = re.search(r'RECORD LOCKS space id (\d+) page no (\d+) n bits (\d+) index `([^`]+)` of table `([^`]+)`', line)
            if record_match:
                lock_info['type'] = 'RECORD'
                lock_info['space_id'] = int(record_match.group(1))
                lock_info['page_no'] = int(record_match.group(2))
                lock_info['n_bits'] = int(record_match.group(3))
                lock_info['index'] = record_match.group(4)
                lock_info['table'] = record_match.group(5)
            
            table_match = re.search(r'TABLE LOCK table `([^`]+)`', line)
            if table_match:
                lock_info['type'] = 'TABLE'
                lock_info['table'] = table_match.group(1)
            
            mode_match = re.search(r'lock mode ([:\w/]+)', line)
            if mode_match:
                lock_info['mode'] = mode_match.group(1)
            
            record_data_match = re.search(r'Record lock, heap no (\d+) PHYSICAL RECORD: (.+)', line)
            if record_data_match:
                lock_info['heap_no'] = int(record_data_match.group(1))
                lock_info['record_data'] = record_data_match.group(2).strip()
            
            i += 1
        
        lock_info['lines_consumed'] = i - start_idx
        return lock_info
    
    def _parse_lock_details_line(self, line):
        lock_info = {
            'type': 'UNKNOWN',
            'mode': 'UNKNOWN',
            'table': 'UNKNOWN',
            'index': 'UNKNOWN'
        }
        
        record_match = re.search(r'RECORD LOCKS space id (\d+) page no (\d+) n bits (\d+) index `([^`]+)` of table `([^`]+)`', line)
        if record_match:
            lock_info['type'] = 'RECORD'
            lock_info['space_id'] = int(record_match.group(1))
            lock_info['page_no'] = int(record_match.group(2))
            lock_info['n_bits'] = int(record_match.group(3))
            lock_info['index'] = record_match.group(4)
            lock_info['table'] = record_match.group(5)
        
        table_match = re.search(r'TABLE LOCK table `([^`]+)`', line)
        if table_match:
            lock_info['type'] = 'TABLE'
            lock_info['table'] = table_match.group(1)
        
        mode_match = re.search(r'lock mode ([:\w/]+)', line)
        if mode_match:
            lock_info['mode'] = mode_match.group(1)
        
        if lock_info['table'] != 'UNKNOWN' or lock_info['mode'] != 'UNKNOWN':
            return lock_info
        return None
    
    def analyze_current_deadlock(self):
        innodb_status = self.get_innodb_status()
        if not innodb_status:
            return None
        
        deadlock_data = self.parse_deadlock_log(innodb_status)
        if deadlock_data:
            self.deadlocks.append(deadlock_data)
            return deadlock_data
        return None
    
    def get_blocking_transactions(self):
        return self.get_locks_info()
    
    def kill_transaction(self, thread_id):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"KILL {thread_id}")
                conn.commit()
                print(f"✓ 已终止线程 {thread_id}")
                return True
        except Exception as e:
            print(f"✗ 终止线程 {thread_id} 失败: {e}")
            return False
    
    def get_deadlocks(self):
        return self.deadlocks
