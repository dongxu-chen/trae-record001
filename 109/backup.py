import os
import subprocess
import datetime
import logging
import gzip
import shutil
import json
import tempfile
import pymysql
from crypto_utils import decrypt_password, AESCrypto

logger = logging.getLogger(__name__)


class DatabaseBackup:
    def __init__(self, config):
        self.config = config
        self.local_dir = config['backup']['local_dir']
        self.compress = config['backup']['compress']
        self.encrypt = config['backup'].get('encrypt', False)
        self.incremental_dir = os.path.join(self.local_dir, 'incremental')
        self.state_file = os.path.join(self.local_dir, 'backup_state.json')
        os.makedirs(self.local_dir, exist_ok=True)
        os.makedirs(self.incremental_dir, exist_ok=True)
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = {'last_binlog': None, 'last_binlog_pos': 0}

    def _save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def backup_mysql(self):
        mysql_config = self.config['database']['mysql']
        backup_files = []
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        for db_name in mysql_config['databases']:
            try:
                logger.info(f"开始备份MySQL数据库: {db_name}")
                filename = f"mysql_{db_name}_{timestamp}.sql"
                filepath = os.path.join(self.local_dir, filename)

                mysql_password = decrypt_password(mysql_config['password'])
                cmd = [
                    mysql_config['mysqldump_path'],
                    f"--host={mysql_config['host']}",
                    f"--port={mysql_config['port']}",
                    f"--user={mysql_config['user']}",
                    f"--password={mysql_password}",
                    '--single-transaction',
                    '--quick',
                    '--lock-tables=false',
                    '--master-data=2',
                    '--flush-logs',
                    db_name
                ]

                with open(filepath, 'w', encoding='utf-8') as f:
                    result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)

                if result.returncode != 0:
                    logger.error(f"MySQL备份失败 {db_name}: {result.stderr}")
                    continue

                if self.compress:
                    filepath = self._compress_file(filepath)

                if self.encrypt:
                    filepath = self._encrypt_file(filepath)

                backup_files.append(filepath)
                logger.info(f"MySQL备份成功: {filepath}")

            except Exception as e:
                logger.error(f"MySQL备份异常 {db_name}: {str(e)}")

        return backup_files

    def backup_mysql_binlog(self):
        mysql_config = self.config['database']['mysql']
        backup_files = []
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        try:
            logger.info("开始MySQL binlog增量备份")
            mysql_password = decrypt_password(mysql_config['password'])

            connection = pymysql.connect(
                host=mysql_config['host'],
                port=int(mysql_config['port']),
                user=mysql_config['user'],
                password=mysql_password
            )

            with connection.cursor() as cursor:
                cursor.execute("SHOW BINARY LOGS")
                binlogs = cursor.fetchall()
                cursor.execute("SHOW MASTER STATUS")
                master_status = cursor.fetchone()

                if master_status:
                    current_binlog = master_status[0]
                    current_pos = master_status[1]

                    for binlog in binlogs:
                        binlog_name = binlog[0]
                        if self.state['last_binlog'] and binlog_name <= self.state['last_binlog']:
                            continue

                        filename = f"mysql_binlog_{binlog_name}_{timestamp}.sql"
                        filepath = os.path.join(self.incremental_dir, filename)

                        cmd = [
                            mysql_config.get('mysqlbinlog_path', 'mysqlbinlog'),
                            f"--host={mysql_config['host']}",
                            f"--port={mysql_config['port']}",
                            f"--user={mysql_config['user']}",
                            f"--password={mysql_password}",
                            binlog_name
                        ]

                        with open(filepath, 'w', encoding='utf-8') as f:
                            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)

                        if result.returncode == 0:
                            if self.compress:
                                filepath = self._compress_file(filepath)
                            if self.encrypt:
                                filepath = self._encrypt_file(filepath)
                            backup_files.append(filepath)
                            logger.info(f"Binlog备份成功: {filepath}")

                    self.state['last_binlog'] = current_binlog
                    self.state['last_binlog_pos'] = current_pos
                    self._save_state()

            connection.close()

        except Exception as e:
            logger.error(f"MySQL binlog备份异常: {str(e)}")

        return backup_files

    def backup_postgresql(self):
        pg_config = self.config['database']['postgresql']
        backup_files = []
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        env = os.environ.copy()
        env['PGPASSWORD'] = decrypt_password(pg_config['password'])

        for db_name in pg_config['databases']:
            try:
                logger.info(f"开始备份PostgreSQL数据库: {db_name}")
                filename = f"postgresql_{db_name}_{timestamp}.sql"
                filepath = os.path.join(self.local_dir, filename)

                cmd = [
                    pg_config['pg_dump_path'],
                    f"--host={pg_config['host']}",
                    f"--port={pg_config['port']}",
                    f"--username={pg_config['user']}",
                    '--no-password',
                    '--no-owner',
                    '--no-privileges',
                    db_name
                ]

                with open(filepath, 'w', encoding='utf-8') as f:
                    result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, env=env)

                if result.returncode != 0:
                    logger.error(f"PostgreSQL备份失败 {db_name}: {result.stderr}")
                    continue

                if self.compress:
                    filepath = self._compress_file(filepath)

                if self.encrypt:
                    filepath = self._encrypt_file(filepath)

                backup_files.append(filepath)
                logger.info(f"PostgreSQL备份成功: {filepath}")

            except Exception as e:
                logger.error(f"PostgreSQL备份异常 {db_name}: {str(e)}")

        return backup_files

    def _compress_file(self, filepath):
        compressed_path = filepath + '.gz'
        with open(filepath, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(filepath)
        return compressed_path

    def _encrypt_file(self, filepath):
        try:
            crypto = AESCrypto()
            encrypted_path = filepath + '.aes'

            with open(filepath, 'rb') as f_in:
                data = f_in.read()

            iv = os.urandom(16)
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import padding

            cipher = Cipher(algorithms.AES(crypto.key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(data) + padder.finalize()
            ciphertext = encryptor.update(padded_data) + encryptor.finalize()

            with open(encrypted_path, 'wb') as f_out:
                f_out.write(iv + ciphertext)

            os.remove(filepath)
            logger.info(f"文件加密成功: {encrypted_path}")
            return encrypted_path
        except Exception as e:
            logger.error(f"文件加密失败: {str(e)}")
            return filepath

    def _decrypt_file(self, filepath):
        if not filepath.endswith('.aes'):
            return filepath

        try:
            crypto = AESCrypto()
            decrypted_path = filepath[:-4]

            with open(filepath, 'rb') as f_in:
                data = f_in.read()

            iv = data[:16]
            ciphertext = data[16:]

            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import padding

            cipher = Cipher(algorithms.AES(crypto.key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

            with open(decrypted_path, 'wb') as f_out:
                f_out.write(plaintext)

            logger.info(f"文件解密成功: {decrypted_path}")
            return decrypted_path
        except Exception as e:
            logger.error(f"文件解密失败: {str(e)}")
            return filepath

    def verify_backup(self, backup_file, db_type='mysql'):
        logger.info(f"开始验证备份文件: {backup_file}")
        temp_dir = tempfile.mkdtemp(prefix='backup_verify_')
        result = {'success': False, 'table_count': 0, 'error': None}

        try:
            work_file = backup_file
            if work_file.endswith('.aes'):
                work_file = self._decrypt_file(work_file)

            if work_file.endswith('.gz'):
                sql_file = work_file[:-3]
                with gzip.open(work_file, 'rb') as f_in:
                    with open(sql_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                work_file = sql_file

            temp_db_name = f"verify_temp_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

            if db_type == 'mysql':
                mysql_config = self.config['database']['mysql']
                mysql_password = decrypt_password(mysql_config['password'])

                conn = pymysql.connect(
                    host=mysql_config['host'],
                    port=int(mysql_config['port']),
                    user=mysql_config['user'],
                    password=mysql_password
                )

                with conn.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {temp_db_name}")
                    conn.commit()

                conn.close()

                cmd = [
                    'mysql',
                    f"--host={mysql_config['host']}",
                    f"--port={mysql_config['port']}",
                    f"--user={mysql_config['user']}",
                    f"--password={mysql_password}",
                    temp_db_name
                ]

                with open(work_file, 'r', encoding='utf-8') as f:
                    subprocess.run(cmd, stdin=f, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                conn = pymysql.connect(
                    host=mysql_config['host'],
                    port=int(mysql_config['port']),
                    user=mysql_config['user'],
                    password=mysql_password,
                    database=temp_db_name
                )

                with conn.cursor() as cursor:
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()
                    result['table_count'] = len(tables)

                conn.close()

                conn = pymysql.connect(
                    host=mysql_config['host'],
                    port=int(mysql_config['port']),
                    user=mysql_config['user'],
                    password=mysql_password
                )

                with conn.cursor() as cursor:
                    cursor.execute(f"DROP DATABASE IF EXISTS {temp_db_name}")
                    conn.commit()

                conn.close()

                result['success'] = result['table_count'] > 0
                logger.info(f"备份验证成功，表数量: {result['table_count']}")

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"备份验证失败: {str(e)}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return result

    def backup_all(self):
        all_files = []
        all_files.extend(self.backup_mysql())
        all_files.extend(self.backup_mysql_binlog())
        all_files.extend(self.backup_postgresql())
        return all_files
