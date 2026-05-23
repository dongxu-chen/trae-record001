import os
import re
import subprocess
import pymysql
import psycopg2
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path


class DatabaseConnector(ABC):
    def __init__(self, config):
        self.config = config
        self.host = config.get('host', 'localhost')
        self.port = config.get('port')
        self.user = config.get('user')
        self.password = config.get('password')
        self.database = config.get('database')

    @abstractmethod
    def test_connection(self):
        pass

    @abstractmethod
    def full_backup(self, output_path):
        pass

    @abstractmethod
    def incremental_backup(self, output_path):
        pass

    @abstractmethod
    def restore(self, backup_path, target_db=None):
        pass

    @abstractmethod
    def execute_query(self, query, target_config=None):
        pass

    @abstractmethod
    def get_binlog_files(self):
        pass

    @abstractmethod
    def get_current_binlog_position(self):
        pass

    @abstractmethod
    def apply_binlog(self, binlog_path, start_time=None, end_time=None, start_position=None, end_position=None):
        pass

    @abstractmethod
    def parse_binlog_timestamps(self, binlog_path):
        pass

    @abstractmethod
    def find_binlog_position_by_time(self, binlog_path, target_time):
        pass


class MySQLConnector(DatabaseConnector):
    def __init__(self, config):
        super().__init__(config)
        self.mysqldump_path = config.get('mysqldump_path', 'mysqldump')
        self.mysql_path = config.get('mysql_path', 'mysql')
        self.mysqlbinlog_path = config.get('mysqlbinlog_path', 'mysqlbinlog')
        self.binlog_path = config.get('binlog_path', '/var/lib/mysql')
        self.last_binlog_file = None
        self.last_binlog_position = None

    def test_connection(self):
        try:
            conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            conn.close()
            return True, "Connection successful"
        except Exception as e:
            return False, str(e)

    def full_backup(self, output_path):
        cmd = (
            f"{self.mysqldump_path} "
            f"--host={self.host} "
            f"--port={self.port} "
            f"--user={self.user} "
            f"--password='{self.password}' "
            f"--single-transaction "
            f"--master-data=2 "
            f"--routines "
            f"--triggers "
            f"--databases {self.database} "
            f"> {output_path}"
        )
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stderr
        except Exception as e:
            return False, str(e)

    def get_current_binlog_position(self):
        cmd = (
            f"{self.mysql_path} "
            f"--host={self.host} "
            f"--port={self.port} "
            f"--user={self.user} "
            f"--password='{self.password}' "
            f"-e \"SHOW MASTER STATUS;\""
        )
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split('\t')
                    if len(parts) >= 2:
                        file_name = parts[0]
                        position = int(parts[1])
                        self.last_binlog_file = file_name
                        self.last_binlog_position = position
                        return True, {
                            'file': file_name,
                            'position': position,
                            'timestamp': datetime.now().isoformat()
                        }
            return False, "Failed to get binlog position"
        except Exception as e:
            return False, str(e)

    def monitor_binlog_changes(self, last_file=None, last_position=None):
        success, current = self.get_current_binlog_position()
        if not success:
            return False, current
        
        changed = False
        changes = []
        
        if last_file and last_file != current['file']:
            changed = True
            changes.append(f"Binlog file rotated: {last_file} -> {current['file']}")
        
        if last_position and last_position != current['position']:
            changed = True
            changes.append(f"Position changed: {last_position} -> {current['position']}")
        
        return changed, {
            'current': current,
            'changes': changes,
            'changed': changed
        }

    def incremental_backup(self, output_path, start_file=None, start_position=None):
        success, position_info = self.get_current_binlog_position()
        if not success:
            return False, position_info
        
        current_file = position_info['file']
        current_position = position_info['position']
        
        if start_file and start_position:
            success, result = self._extract_binlog_range(
                start_file, start_position,
                current_file, current_position,
                output_path
            )
            return success, result
        
        flush_cmd = (
            f"{self.mysql_path} "
            f"--host={self.host} "
            f"--port={self.port} "
            f"--user={self.user} "
            f"--password='{self.password}' "
            f"-e \"FLUSH BINARY LOGS;\""
        )
        try:
            subprocess.run(flush_cmd, shell=True, check=True)
            
            binlog_src = os.path.join(self.binlog_path, current_file)
            if os.path.exists(binlog_src):
                import shutil
                shutil.copy2(binlog_src, output_path)
                
                position_info_path = output_path + '.position'
                with open(position_info_path, 'w') as f:
                    import json
                    json.dump({
                        'start_file': current_file,
                        'start_position': 4,
                        'end_file': current_file,
                        'end_position': current_position,
                        'timestamp': datetime.now().isoformat()
                    }, f, indent=2)
                
                return True, {
                    'binlog_file': current_file,
                    'start_position': 4,
                    'end_position': current_position,
                    'size': os.path.getsize(binlog_src)
                }
            return False, f"Binlog file not found: {binlog_src}"
        except Exception as e:
            return False, str(e)

    def _extract_binlog_range(self, start_file, start_pos, end_file, end_pos, output_path):
        try:
            binlog_files = self.get_binlog_files()
            start_idx = binlog_files.index(start_file) if start_file in binlog_files else 0
            end_idx = binlog_files.index(end_file) if end_file in binlog_files else len(binlog_files) - 1
            
            files_to_process = binlog_files[start_idx:end_idx + 1]
            
            with open(output_path, 'wb') as out_f:
                for i, binlog_file in enumerate(files_to_process):
                    binlog_src = os.path.join(self.binlog_path, binlog_file)
                    if not os.path.exists(binlog_src):
                        continue
                    
                    if i == 0 and i == len(files_to_process) - 1:
                        cmd = f"{self.mysqlbinlog_path} --start-position={start_pos} --stop-position={end_pos} {binlog_src}"
                    elif i == 0:
                        cmd = f"{self.mysqlbinlog_path} --start-position={start_pos} {binlog_src}"
                    elif i == len(files_to_process) - 1:
                        cmd = f"{self.mysqlbinlog_path} --stop-position={end_pos} {binlog_src}"
                    else:
                        cmd = f"{self.mysqlbinlog_path} {binlog_src}"
                    
                    result = subprocess.run(cmd, shell=True, capture_output=True)
                    out_f.write(result.stdout)
            
            return True, f"Extracted binlog range to {output_path}"
        except Exception as e:
            return False, str(e)

    def restore(self, backup_path, target_config=None):
        config = target_config or self.config
        mysql_path = target_config.get('mysql_path', self.mysql_path) if target_config else self.mysql_path
        
        cmd = (
            f"{mysql_path} "
            f"--host={config.get('host', self.host)} "
            f"--port={config.get('port', self.port)} "
            f"--user={config.get('user', self.user)} "
            f"--password='{config.get('password', self.password)}' "
            f"{config.get('database', self.database)} "
            f"< {backup_path}"
        )
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stderr
        except Exception as e:
            return False, str(e)

    def execute_query(self, query, target_config=None):
        config = target_config or self.config
        try:
            conn = pymysql.connect(
                host=config.get('host', self.host),
                port=config.get('port', self.port),
                user=config.get('user', self.user),
                password=config.get('password', self.password),
                database=config.get('database', self.database)
            )
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return True, results
        except Exception as e:
            return False, str(e)

    def get_binlog_files(self):
        cmd = (
            f"{self.mysql_path} "
            f"--host={self.host} "
            f"--port={self.port} "
            f"--user={self.user} "
            f"--password='{self.password}' "
            f"-e \"SHOW BINARY LOGS;\""
        )
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]
                return [line.split('\t')[0] for line in lines if line]
            return []
        except Exception:
            return []

    def parse_binlog_timestamps(self, binlog_path):
        timestamps = []
        try:
            cmd = f"{self.mysqlbinlog_path} --base64-output=DECODE-ROWS -v {binlog_path}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                content = result.stdout
                
                timestamp_pattern = r'#(\d{6})\s+(\d{1,2}):(\d{2}):(\d{2})\s+server\s+id'
                matches = re.finditer(timestamp_pattern, content)
                
                for match in matches:
                    date_part = match.group(1)
                    hour = match.group(2).zfill(2)
                    minute = match.group(3)
                    second = match.group(4)
                    
                    year = '20' + date_part[0:2]
                    month = date_part[2:4]
                    day = date_part[4:6]
                    
                    timestamp_str = f"{year}-{month}-{day} {hour}:{minute}:{second}"
                    try:
                        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        timestamps.append({
                            'timestamp': dt.isoformat(),
                            'position': match.start(),
                            'datetime': dt
                        })
                    except:
                        continue
                
                if not timestamps:
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(binlog_path))
                    timestamps.append({
                        'timestamp': file_mtime.isoformat(),
                        'position': 0,
                        'datetime': file_mtime
                    })
            
            return timestamps
        except Exception as e:
            return timestamps

    def find_binlog_position_by_time(self, binlog_path, target_time):
        if isinstance(target_time, str):
            target_time = datetime.fromisoformat(target_time)
        
        timestamps = self.parse_binlog_timestamps(binlog_path)
        
        if not timestamps:
            return False, "No timestamps found in binlog"
        
        closest_pos = 4
        min_diff = None
        
        for ts in timestamps:
            diff = abs((ts['datetime'] - target_time).total_seconds())
            if min_diff is None or diff < min_diff:
                min_diff = diff
                closest_pos = ts.get('position', 4)
        
        return True, {
            'target_time': target_time.isoformat(),
            'closest_position': closest_pos,
            'time_diff_seconds': min_diff,
            'available_timestamps': len(timestamps)
        }

    def apply_binlog(self, binlog_path, start_time=None, end_time=None, start_position=None, end_position=None):
        cmd = f"{self.mysqlbinlog_path}"
        
        if start_position:
            cmd += f" --start-position={start_position}"
        elif start_time:
            cmd += f" --start-datetime='{start_time}'"
        
        if end_position:
            cmd += f" --stop-position={end_position}"
        elif end_time:
            cmd += f" --stop-datetime='{end_time}'"
        
        cmd += f" {binlog_path}"
        cmd += (
            f" | {self.mysql_path} "
            f"--host={self.host} "
            f"--port={self.port} "
            f"--user={self.user} "
            f"--password='{self.password}'"
        )
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stderr
        except Exception as e:
            return False, str(e)


class PostgreSQLConnector(DatabaseConnector):
    def __init__(self, config):
        super().__init__(config)
        self.pg_dump_path = config.get('pg_dump_path', 'pg_dump')
        self.psql_path = config.get('psql_path', 'psql')
        self.pg_waldump_path = config.get('pg_waldump_path', 'pg_waldump')
        self.wal_path = config.get('wal_path', '/var/lib/postgresql/14/main/pg_wal')
        self.last_wal_file = None
        self.last_lsn = None

    def test_connection(self):
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            conn.close()
            return True, "Connection successful"
        except Exception as e:
            return False, str(e)

    def full_backup(self, output_path):
        env = os.environ.copy()
        env['PGPASSWORD'] = self.password
        
        cmd = [
            self.pg_dump_path,
            f"--host={self.host}",
            f"--port={self.port}",
            f"--username={self.user}",
            "--format=custom",
            "--blobs",
            self.database,
            f"--file={output_path}"
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            return result.returncode == 0, result.stderr
        except Exception as e:
            return False, str(e)

    def get_current_binlog_position(self):
        env = os.environ.copy()
        env['PGPASSWORD'] = self.password
        
        cmd = [
            self.psql_path,
            f"--host={self.host}",
            f"--port={self.port}",
            f"--username={self.user}",
            "-c", "SELECT pg_current_wal_lsn(), pg_walfile_name(pg_current_wal_lsn());"
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 3:
                    parts = lines[2].split('|')
                    if len(parts) >= 2:
                        lsn = parts[0].strip()
                        wal_file = parts[1].strip()
                        self.last_wal_file = wal_file
                        self.last_lsn = lsn
                        return True, {
                            'file': wal_file,
                            'lsn': lsn,
                            'timestamp': datetime.now().isoformat()
                        }
            return False, "Failed to get WAL position"
        except Exception as e:
            return False, str(e)

    def monitor_binlog_changes(self, last_file=None, last_lsn=None):
        success, current = self.get_current_binlog_position()
        if not success:
            return False, current
        
        changed = False
        changes = []
        
        if last_file and last_file != current['file']:
            changed = True
            changes.append(f"WAL file rotated: {last_file} -> {current['file']}")
        
        if last_lsn and last_lsn != current['lsn']:
            changed = True
            changes.append(f"LSN changed: {last_lsn} -> {current['lsn']}")
        
        return changed, {
            'current': current,
            'changes': changes,
            'changed': changed
        }

    def incremental_backup(self, output_path, start_file=None, start_lsn=None):
        env = os.environ.copy()
        env['PGPASSWORD'] = self.password
        
        success, position_info = self.get_current_binlog_position()
        if not success:
            return False, position_info
        
        current_file = position_info['file']
        current_lsn = position_info['lsn']
        
        switch_cmd = [
            self.psql_path,
            f"--host={self.host}",
            f"--port={self.port}",
            f"--username={self.user}",
            "-c", "SELECT pg_switch_wal();"
        ]
        
        try:
            subprocess.run(switch_cmd, capture_output=True, text=True, env=env)
            
            wal_files = sorted([f for f in os.listdir(self.wal_path) 
                               if len(f) == 24 and f.startswith('000')])
            
            if wal_files:
                target_file = wal_files[-2] if len(wal_files) >= 2 else wal_files[-1]
                wal_src = os.path.join(self.wal_path, target_file)
                
                if os.path.exists(wal_src):
                    import shutil
                    shutil.copy2(wal_src, output_path)
                    
                    position_info_path = output_path + '.position'
                    with open(position_info_path, 'w') as f:
                        import json
                        json.dump({
                            'start_file': target_file,
                            'start_lsn': start_lsn or '0/0',
                            'end_file': current_file,
                            'end_lsn': current_lsn,
                            'timestamp': datetime.now().isoformat()
                        }, f, indent=2)
                    
                    return True, {
                        'wal_file': target_file,
                        'start_lsn': start_lsn or '0/0',
                        'end_lsn': current_lsn,
                        'size': os.path.getsize(wal_src)
                    }
            return False, "No WAL files found"
        except Exception as e:
            return False, str(e)

    def restore(self, backup_path, target_config=None):
        config = target_config or self.config
        env = os.environ.copy()
        env['PGPASSWORD'] = config.get('password', self.password)
        
        psql_path = target_config.get('psql_path', self.psql_path) if target_config else self.psql_path
        
        cmd = [
            'pg_restore',
            f"--host={config.get('host', self.host)}",
            f"--port={config.get('port', self.port)}",
            f"--username={config.get('user', self.user)}",
            f"--dbname={config.get('database', self.database)}",
            "--verbose",
            backup_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            return result.returncode == 0, result.stderr
        except Exception as e:
            return False, str(e)

    def execute_query(self, query, target_config=None):
        config = target_config or self.config
        try:
            conn = psycopg2.connect(
                host=config.get('host', self.host),
                port=config.get('port', self.port),
                user=config.get('user', self.user),
                password=config.get('password', self.password),
                database=config.get('database', self.database)
            )
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return True, results
        except Exception as e:
            return False, str(e)

    def get_binlog_files(self):
        try:
            wal_files = sorted([f for f in os.listdir(self.wal_path) 
                               if len(f) == 24 and f.startswith('000')])
            return wal_files
        except Exception:
            return []

    def parse_binlog_timestamps(self, binlog_path):
        timestamps = []
        try:
            env = os.environ.copy()
            env['PGPASSWORD'] = self.password
            
            cmd = f"{self.pg_waldump_path} -p {binlog_path}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
            
            if result.returncode == 0:
                content = result.stdout
                
                timestamp_pattern = r'COMMIT\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})'
                matches = re.finditer(timestamp_pattern, content)
                
                for match in matches:
                    timestamp_str = match.group(1)
                    try:
                        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        timestamps.append({
                            'timestamp': dt.isoformat(),
                            'position': match.start(),
                            'datetime': dt
                        })
                    except:
                        continue
                
                if not timestamps:
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(binlog_path))
                    timestamps.append({
                        'timestamp': file_mtime.isoformat(),
                        'position': 0,
                        'datetime': file_mtime
                    })
            
            return timestamps
        except Exception as e:
            return timestamps

    def find_binlog_position_by_time(self, binlog_path, target_time):
        if isinstance(target_time, str):
            target_time = datetime.fromisoformat(target_time)
        
        timestamps = self.parse_binlog_timestamps(binlog_path)
        
        if not timestamps:
            return False, "No timestamps found in WAL"
        
        closest_lsn = '0/0'
        min_diff = None
        
        for ts in timestamps:
            diff = abs((ts['datetime'] - target_time).total_seconds())
            if min_diff is None or diff < min_diff:
                min_diff = diff
                closest_lsn = ts.get('lsn', '0/0')
        
        return True, {
            'target_time': target_time.isoformat(),
            'closest_lsn': closest_lsn,
            'time_diff_seconds': min_diff,
            'available_timestamps': len(timestamps)
        }

    def apply_binlog(self, binlog_path, start_time=None, end_time=None, start_position=None, end_position=None):
        env = os.environ.copy()
        env['PGPASSWORD'] = self.password
        
        cmd = f"{self.pg_waldump_path} {binlog_path}"
        
        if start_time:
            cmd += f" --start='{start_time}'"
        if end_time:
            cmd += f" --stop='{end_time}'"
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
            sql_content = result.stdout
            
            psql_cmd = [
                self.psql_path,
                f"--host={self.host}",
                f"--port={self.port}",
                f"--username={self.user}",
                f"--dbname={self.database}"
            ]
            psql_result = subprocess.run(
                psql_cmd,
                input=sql_content,
                capture_output=True,
                text=True,
                env=env
            )
            return psql_result.returncode == 0, psql_result.stderr
        except Exception as e:
            return False, str(e)


class DatabaseFactory:
    @staticmethod
    def get_connector(db_type, config):
        if db_type.lower() == 'mysql':
            return MySQLConnector(config)
        elif db_type.lower() == 'postgresql':
            return PostgreSQLConnector(config)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
