import pymysql
import time
from datetime import datetime
from config import Config

class AutoKillManager:
    def __init__(self):
        self.connection_params = Config.get_connection_params()
        self.enabled = Config.AUTO_KILL_ENABLED
        self.threshold_seconds = Config.AUTO_KILL_THRESHOLD_SECONDS
        self.exclude_users = Config.AUTO_KILL_EXCLUDE_USERS
        self.killed_transactions = []
    
    def get_connection(self):
        conn_params = self.connection_params.copy()
        conn_params['database'] = 'information_schema'
        return pymysql.connect(**conn_params)
    
    def get_blocking_transactions(self):
        conn = self.get_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        p.ID AS blocking_thread_id,
                        p.USER AS blocking_user,
                        p.DB AS blocking_db,
                        p.COMMAND AS blocking_command,
                        p.TIME AS blocking_time,
                        p.STATE AS blocking_state,
                        p.INFO AS blocking_query,
                        w.requesting_trx_id AS waiting_trx_id,
                        w.blocking_trx_id AS blocking_trx_id,
                        TIMESTAMPDIFF(SECOND, t.trx_wait_started, NOW()) AS wait_seconds,
                        t.trx_state,
                        t.trx_started
                    FROM INFORMATION_SCHEMA.INNODB_LOCK_WAITS w
                    JOIN INFORMATION_SCHEMA.INNODB_TRX t ON w.blocking_trx_id = t.trx_id
                    JOIN INFORMATION_SCHEMA.PROCESSLIST p ON t.trx_mysql_thread_id = p.ID
                    WHERE p.USER NOT IN ({})
                """.format(','.join(['%s'] * len(self.exclude_users))), self.exclude_users)
                return cursor.fetchall()
        except Exception as e:
            print(f"获取阻塞事务失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_long_running_transactions(self):
        conn = self.get_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        t.trx_id,
                        t.trx_mysql_thread_id AS thread_id,
                        p.USER,
                        p.DB,
                        p.COMMAND,
                        p.STATE,
                        p.INFO AS query,
                        t.trx_state,
                        t.trx_started,
                        TIMESTAMPDIFF(SECOND, t.trx_started, NOW()) AS runtime_seconds,
                        t.trx_rows_locked,
                        t.trx_rows_modified
                    FROM INFORMATION_SCHEMA.INNODB_TRX t
                    JOIN INFORMATION_SCHEMA.PROCESSLIST p ON t.trx_mysql_thread_id = p.ID
                    WHERE 
                        TIMESTAMPDIFF(SECOND, t.trx_started, NOW()) > %s
                        AND p.USER NOT IN ({})
                    ORDER BY runtime_seconds DESC
                """.format(','.join(['%s'] * len(self.exclude_users))), 
                [self.threshold_seconds] + self.exclude_users)
                return cursor.fetchall()
        except Exception as e:
            print(f"获取长事务失败: {e}")
            return []
        finally:
            conn.close()
    
    def kill_transaction(self, thread_id, reason=""):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"KILL {thread_id}")
                conn.commit()
                
                kill_record = {
                    'timestamp': datetime.now().isoformat(),
                    'thread_id': thread_id,
                    'reason': reason,
                    'success': True
                }
                self.killed_transactions.append(kill_record)
                
                print(f"[KILL] 成功终止线程 {thread_id}, 原因: {reason}")
                return True
        except Exception as e:
            print(f"[KILL] 终止线程 {thread_id} 失败: {e}")
            kill_record = {
                'timestamp': datetime.now().isoformat(),
                'thread_id': thread_id,
                'reason': reason,
                'success': False,
                'error': str(e)
            }
            self.killed_transactions.append(kill_record)
            return False
        finally:
            conn.close()
    
    def check_and_kill_blocking(self):
        if not self.enabled:
            print("[AUTO-KILL] 自动终止功能已禁用")
            return []
        
        blocking = self.get_blocking_transactions()
        killed = []
        
        for txn in blocking:
            wait_seconds = txn.get('wait_seconds', 0)
            thread_id = txn.get('blocking_thread_id')
            user = txn.get('blocking_user')
            
            if wait_seconds >= self.threshold_seconds:
                reason = f"阻塞时间超过阈值 ({wait_seconds}s >= {self.threshold_seconds}s)"
                if self.kill_transaction(thread_id, reason):
                    killed.append(txn)
        
        return killed
    
    def check_and_kill_long_running(self):
        if not self.enabled:
            print("[AUTO-KILL] 自动终止功能已禁用")
            return []
        
        long_running = self.get_long_running_transactions()
        killed = []
        
        for txn in long_running:
            runtime = txn.get('runtime_seconds', 0)
            thread_id = txn.get('thread_id')
            user = txn.get('USER')
            
            reason = f"事务运行时间超过阈值 ({runtime}s >= {self.threshold_seconds}s)"
            if self.kill_transaction(thread_id, reason):
                killed.append(txn)
        
        return killed
    
    def run_diagnostics(self):
        print("=" * 60)
        print(f"数据库事务诊断 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        print(f"\n配置状态:")
        print(f"  自动终止: {'启用' if self.enabled else '禁用'}")
        print(f"  阈值: {self.threshold_seconds}秒")
        print(f"  排除用户: {', '.join(self.exclude_users)}")
        
        blocking = self.get_blocking_transactions()
        print(f"\n当前阻塞事务: {len(blocking)}个")
        for b in blocking:
            print(f"  线程{b.get('blocking_thread_id')}: {b.get('blocking_user')}@{b.get('blocking_db')} - 等待{b.get('wait_seconds', 0)}s")
        
        long_running = self.get_long_running_transactions()
        print(f"\n当前长事务 (>{self.threshold_seconds}s): {len(long_running)}个")
        for t in long_running:
            print(f"  线程{t.get('thread_id')}: {t.get('USER')}@{t.get('DB')} - 运行{t.get('runtime_seconds')}s")
        
        print(f"\n已终止事务: {len(self.killed_transactions)}个")
        
        return {
            'blocking_count': len(blocking),
            'long_running_count': len(long_running),
            'killed_count': len(self.killed_transactions)
        }
    
    def get_kill_history(self):
        return self.killed_transactions
