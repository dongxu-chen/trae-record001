import os
import json
import logging
from datetime import datetime


class BackupVerifier:
    def __init__(self, config, db_type):
        self.config = config
        self.db_type = db_type
        self.logger = logging.getLogger('dbbackup')
        
        self.verify_config = config.get_verification_config()
        self.enabled = self.verify_config.get('enabled', False)
        self.keep_versions = self.verify_config.get('keep_versions', 3)
        
        from .database import DatabaseFactory
        from .crypto import Compressor, Encryptor
        from .storage import StorageFactory
        from .utils import ensure_dir
        
        db_config = config.get_database_config(db_type)
        self.db_connector = DatabaseFactory.get_connector(db_type, db_config)
        
        backup_config = config.get_backup_config()
        self.temp_dir = backup_config.get('temp_dir', './temp')
        self.verify_history_file = os.path.join(self.temp_dir, f'{db_type}_verify_history.json')
        ensure_dir(self.temp_dir)
        
        self.compressor = Compressor(config.get_compression_config())
        self.encryptor = Encryptor(config.get_encryption_config())
        self.storage = StorageFactory.get_storage(config.get_storage_config())
        
        self.test_queries = self.verify_config.get('test_queries', ['SELECT 1'])

    def _load_verify_history(self):
        if os.path.exists(self.verify_history_file):
            try:
                with open(self.verify_history_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save_verify_history(self, history):
        with open(self.verify_history_file, 'w') as f:
            json.dump(history, f, indent=2)

    def _cleanup_old_verifications(self):
        history = self._load_verify_history()
        if len(history) <= self.keep_versions:
            return
        
        self.logger.info(f"Cleaning up old verifications. Keep: {self.keep_versions}, Current: {len(history)}")
        
        history_sorted = sorted(history, key=lambda x: x['verified_at'], reverse=True)
        to_remove = history_sorted[self.keep_versions:]
        
        for entry in to_remove:
            self.logger.info(f"Removing old verification: {entry['backup_id']}")
            try:
                self._drop_verify_database(entry.get('database_name'))
            except Exception as e:
                self.logger.warning(f"Failed to drop verification database: {e}")
        
        self._save_verify_history(history_sorted[:self.keep_versions])

    def _drop_verify_database(self, db_name):
        if not db_name:
            return
        
        base_db = self.verify_config.get('verify_database', 'verify_db')
        self.logger.info(f"Dropping verification database: {db_name}")
        
        try:
            if self.db_type == 'mysql':
                drop_query = f"DROP DATABASE IF EXISTS `{db_name}`"
                admin_config = {
                    'host': self.verify_config.get('verify_host', 'localhost'),
                    'port': self.verify_config.get('verify_port'),
                    'user': self.verify_config.get('verify_user'),
                    'password': self.verify_config.get('verify_password'),
                    'database': 'mysql'
                }
                success, _ = self.db_connector.execute_query(drop_query, admin_config)
                return success
            elif self.db_type == 'postgresql':
                drop_query = f"DROP DATABASE IF EXISTS {db_name}"
                admin_config = {
                    'host': self.verify_config.get('verify_host', 'localhost'),
                    'port': self.verify_config.get('verify_port'),
                    'user': self.verify_config.get('verify_user'),
                    'password': self.verify_config.get('verify_password'),
                    'database': 'postgres'
                }
                success, _ = self.db_connector.execute_query(drop_query, admin_config)
                return success
        except Exception as e:
            self.logger.warning(f"Error dropping database {db_name}: {e}")
        
        return False

    def _create_verify_database(self, db_name):
        self.logger.info(f"Creating verification database: {db_name}")
        
        try:
            if self.db_type == 'mysql':
                create_query = f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                admin_config = {
                    'host': self.verify_config.get('verify_host', 'localhost'),
                    'port': self.verify_config.get('verify_port'),
                    'user': self.verify_config.get('verify_user'),
                    'password': self.verify_config.get('verify_password'),
                    'database': 'mysql'
                }
                success, _ = self.db_connector.execute_query(create_query, admin_config)
                return success
            elif self.db_type == 'postgresql':
                create_query = f"CREATE DATABASE {db_name}"
                admin_config = {
                    'host': self.verify_config.get('verify_host', 'localhost'),
                    'port': self.verify_config.get('verify_port'),
                    'user': self.verify_config.get('verify_user'),
                    'password': self.verify_config.get('verify_password'),
                    'database': 'postgres'
                }
                success, _ = self.db_connector.execute_query(create_query, admin_config)
                return success
        except Exception as e:
            self.logger.warning(f"Error creating database {db_name}: {e}")
        
        return False

    def verify_backup(self, backup_info):
        if not self.enabled:
            self.logger.info("Verification disabled, skipping")
            return True, "Verification disabled"
        
        self._cleanup_old_verifications()
        
        self.logger.info(f"Starting verification of backup: {backup_info['backup_id']}")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        verify_db_name = f"verify_{backup_info['backup_id']}_{timestamp}"
        
        self._create_verify_database(verify_db_name)
        
        verify_db_config = {
            'host': self.verify_config.get('verify_host', 'localhost'),
            'port': self.verify_config.get('verify_port'),
            'user': self.verify_config.get('verify_user'),
            'password': self.verify_config.get('verify_password'),
            'database': verify_db_name,
            'mysql_path': self.db_connector.mysql_path if hasattr(self.db_connector, 'mysql_path') else None,
            'psql_path': self.db_connector.psql_path if hasattr(self.db_connector, 'psql_path') else None,
        }
        
        try:
            remote_path = backup_info['remote_path']
            encrypted_path = os.path.join(self.temp_dir, f"verify_{backup_info['backup_id']}.enc")
            
            self.logger.info(f"Downloading backup from OSS...")
            success, msg = self.storage.download(remote_path, encrypted_path)
            if not success:
                raise Exception(f"Download failed: {msg}")
            
            decrypted_path = os.path.join(self.temp_dir, f"verify_{backup_info['backup_id']}.gz")
            self.logger.info(f"Decrypting backup...")
            success, msg = self.encryptor.decrypt(encrypted_path, decrypted_path)
            if not success:
                raise Exception(f"Decryption failed: {msg}")
            
            restored_path = os.path.join(self.temp_dir, f"verify_{backup_info['backup_id']}.sql")
            self.logger.info(f"Decompressing backup...")
            success, msg = self.compressor.decrypt(decrypted_path, restored_path) if hasattr(self.compressor, 'decrypt') else self.compressor.decompress(decrypted_path, restored_path)
            if not success:
                raise Exception(f"Decompression failed: {msg}")
            
            self.logger.info(f"Restoring to verification database: {verify_db_name}")
            success, msg = self.db_connector.restore(restored_path, verify_db_config)
            if not success:
                raise Exception(f"Restore failed: {msg}")
            
            self.logger.info(f"Running test queries...")
            all_passed = True
            query_results = []
            
            for query in self.test_queries:
                success, result = self.db_connector.execute_query(query, verify_db_config)
                query_results.append({
                    'query': query,
                    'success': success,
                    'result': str(result)[:100] if success else result
                })
                if not success:
                    all_passed = False
                    self.logger.warning(f"Query failed: {query} - {result}")
            
            self._cleanup_files([encrypted_path, decrypted_path, restored_path])
            
            verification_result = {
                'backup_id': backup_info['backup_id'],
                'database_name': verify_db_name,
                'verified_at': datetime.now().isoformat(),
                'success': all_passed,
                'queries': query_results
            }
            
            history = self._load_verify_history()
            history.append(verification_result)
            self._save_verify_history(history)
            
            if all_passed:
                self.logger.info(f"Verification passed: {backup_info['backup_id']}")
            else:
                self.logger.error(f"Verification failed: {backup_info['backup_id']}")
            
            return all_passed, verification_result
            
        except Exception as e:
            self.logger.error(f"Verification error: {str(e)}")
            return False, str(e)

    def get_verify_history(self):
        return self._load_verify_history()

    def _cleanup_files(self, files):
        for f in files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
