import os
import json
import logging
from datetime import datetime
from .database import DatabaseFactory
from .crypto import Compressor, Encryptor
from .storage import StorageFactory
from .utils import ensure_dir


class PointInTimeRecovery:
    def __init__(self, config, db_type):
        self.config = config
        self.db_type = db_type
        self.logger = logging.getLogger('dbbackup')
        
        db_config = config.get_database_config(db_type)
        self.db_connector = DatabaseFactory.get_connector(db_type, db_config)
        
        backup_config = config.get_backup_config()
        self.temp_dir = backup_config.get('temp_dir', './temp')
        ensure_dir(self.temp_dir)
        
        self.compressor = Compressor(config.get_compression_config())
        self.encryptor = Encryptor(config.get_encryption_config())
        self.storage = StorageFactory.get_storage(config.get_storage_config())

    def recover_to_point(self, target_time, full_backup_id=None):
        self.logger.info(f"Starting point-in-time recovery to: {target_time}")
        
        if isinstance(target_time, str):
            target_time = datetime.fromisoformat(target_time)
        
        try:
            if full_backup_id:
                full_backup = self._get_backup_by_id(full_backup_id, 'full')
            else:
                full_backup = self._find_latest_full_backup_before(target_time)
            
            if not full_backup:
                raise Exception("No suitable full backup found")
            
            self.logger.info(f"Using full backup: {full_backup['backup_id']}")
            self.logger.info(f"Full backup timestamp: {full_backup['timestamp']}")
            
            self._restore_full_backup(full_backup)
            
            incremental_backups = self._find_incremental_backups_between(
                datetime.fromisoformat(full_backup['timestamp']),
                target_time
            )
            
            self.logger.info(f"Found {len(incremental_backups)} incremental backups to apply")
            
            applied_count = 0
            for i, inc_backup in enumerate(incremental_backups):
                is_last = (i == len(incremental_backups) - 1)
                success = self._apply_incremental_backup_precise(inc_backup, target_time, is_last)
                if success:
                    applied_count += 1
            
            self.logger.info("Point-in-time recovery completed successfully")
            return True, {
                'target_time': target_time.isoformat(),
                'full_backup': full_backup['backup_id'],
                'incremental_count': len(incremental_backups),
                'applied_count': applied_count
            }
            
        except Exception as e:
            self.logger.error(f"PITR failed: {str(e)}")
            return False, str(e)

    def _apply_incremental_backup_precise(self, backup_info, target_time, is_last):
        self.logger.info(f"Applying incremental backup: {backup_info['backup_id']}")
        
        encrypted_path = os.path.join(self.temp_dir, f"inc_{backup_info['backup_id']}.enc")
        decrypted_path = os.path.join(self.temp_dir, f"inc_{backup_info['backup_id']}.gz")
        binlog_path = os.path.join(self.temp_dir, f"inc_{backup_info['backup_id']}.binlog")
        
        try:
            self.storage.download(backup_info['remote_path'], encrypted_path)
            self.encryptor.decrypt(encrypted_path, decrypted_path)
            self.compressor.decompress(decrypted_path, binlog_path)
            
            position_remote = backup_info['remote_path'].replace('.enc', '.position')
            position_local = binlog_path + '.position'
            
            position_data = None
            if self.storage.exists(position_remote):
                self.storage.download(position_remote, position_local)
                if os.path.exists(position_local):
                    with open(position_local, 'r') as f:
                        position_data = json.load(f)
            
            start_position = None
            end_position = None
            
            if position_data:
                start_position = position_data.get('start_position') or position_data.get('start_lsn')
                self.logger.info(f"Start position from metadata: {start_position}")
            
            if is_last:
                self.logger.info(f"Finding precise position for target time: {target_time}")
                success, result = self.db_connector.find_binlog_position_by_time(binlog_path, target_time)
                if success:
                    end_position = result.get('closest_position') or result.get('closest_lsn')
                    self.logger.info(f"Precise position found: {end_position}")
                    self.logger.info(f"Time difference: {result.get('time_diff_seconds', 'N/A')} seconds")
                    self.logger.info(f"Available timestamps: {result.get('available_timestamps', 0)}")
                else:
                    self.logger.warning(f"Could not find precise position: {result}")
            
            success, msg = self.db_connector.apply_binlog(
                binlog_path,
                start_position=start_position,
                end_position=end_position,
                end_time=target_time.isoformat() if not end_position else None
            )
            
            if not success:
                self.logger.warning(f"Binlog apply warning: {msg}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying incremental backup: {str(e)}")
            return False
        finally:
            for f in [encrypted_path, decrypted_path, binlog_path, position_local]:
                if f and os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass

    def analyze_binlog_timeline(self, backup_id):
        self.logger.info(f"Analyzing binlog timeline for: {backup_id}")
        
        encrypted_path = os.path.join(self.temp_dir, f"analyze_{backup_id}.enc")
        decrypted_path = os.path.join(self.temp_dir, f"analyze_{backup_id}.gz")
        binlog_path = os.path.join(self.temp_dir, f"analyze_{backup_id}.binlog")
        
        try:
            backup_info = self._get_backup_by_id(backup_id, 'incremental')
            self.storage.download(backup_info['remote_path'], encrypted_path)
            self.encryptor.decrypt(encrypted_path, decrypted_path)
            self.compressor.decompress(decrypted_path, binlog_path)
            
            timestamps = self.db_connector.parse_binlog_timestamps(binlog_path)
            
            if timestamps:
                self.logger.info(f"Found {len(timestamps)} events in binlog")
                self.logger.info(f"First event: {timestamps[0]['timestamp']}")
                self.logger.info(f"Last event: {timestamps[-1]['timestamp']}")
            
            return timestamps
            
        finally:
            for f in [encrypted_path, decrypted_path, binlog_path]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass

    def _get_backup_by_id(self, backup_id, strategy='full'):
        prefix = f"{self.db_type}/{strategy}/{backup_id}.json"
        files = self.storage.list_files(prefix)
        if not files:
            prefix = f"{self.db_type}/*/{backup_id}.json"
            files = self.storage.list_files(prefix.replace('*', 'full'))
            if not files:
                files = self.storage.list_files(prefix.replace('*', 'incremental'))
        
        if not files:
            raise Exception(f"Backup not found: {backup_id}")
        
        local_json = os.path.join(self.temp_dir, f"{backup_id}.json")
        self.storage.download(files[0], local_json)
        with open(local_json, 'r') as f:
            backup_info = json.load(f)
        os.remove(local_json)
        return backup_info

    def _find_latest_full_backup_before(self, target_time):
        backups = self._list_backups_by_strategy('full')
        for backup in backups:
            backup_time = datetime.fromisoformat(backup['timestamp'])
            if backup_time <= target_time:
                return backup
        return None

    def _list_backups_by_strategy(self, strategy):
        prefix = f"{self.db_type}/{strategy}/"
        files = self.storage.list_files(prefix)
        backups = []
        for f in files:
            if f.endswith('.json'):
                local_path = os.path.join(self.temp_dir, os.path.basename(f))
                self.storage.download(f, local_path)
                with open(local_path, 'r') as fp:
                    backup_info = json.load(fp)
                    backups.append(backup_info)
                os.remove(local_path)
        return sorted(backups, key=lambda x: x['timestamp'], reverse=True)

    def _find_incremental_backups_between(self, start_time, end_time):
        backups = self._list_backups_by_strategy('incremental')
        result = []
        for backup in backups:
            backup_time = datetime.fromisoformat(backup['timestamp'])
            if start_time <= backup_time <= end_time:
                result.append(backup)
        return sorted(result, key=lambda x: x['timestamp'])

    def _restore_full_backup(self, backup_info):
        self.logger.info(f"Restoring full backup: {backup_info['backup_id']}")
        
        encrypted_path = os.path.join(self.temp_dir, f"restore_{backup_info['backup_id']}.enc")
        decrypted_path = os.path.join(self.temp_dir, f"restore_{backup_info['backup_id']}.gz")
        restored_path = os.path.join(self.temp_dir, f"restore_{backup_info['backup_id']}.sql")
        
        try:
            self.storage.download(backup_info['remote_path'], encrypted_path)
            self.encryptor.decrypt(encrypted_path, decrypted_path)
            self.compressor.decompress(decrypted_path, restored_path)
            
            success, msg = self.db_connector.restore(restored_path)
            if not success:
                raise Exception(f"Restore failed: {msg}")
        finally:
            for f in [encrypted_path, decrypted_path, restored_path]:
                if os.path.exists(f):
                    os.remove(f)

    def restore_backup(self, backup_id, target_config=None):
        self.logger.info(f"Restoring backup: {backup_id}")
        
        backup_info = self._get_backup_by_id(backup_id)
        
        encrypted_path = os.path.join(self.temp_dir, f"restore_{backup_id}.enc")
        decrypted_path = os.path.join(self.temp_dir, f"restore_{backup_id}.gz")
        restored_path = os.path.join(self.temp_dir, f"restore_{backup_id}.sql")
        
        try:
            self.storage.download(backup_info['remote_path'], encrypted_path)
            self.encryptor.decrypt(encrypted_path, decrypted_path)
            self.compressor.decompress(decrypted_path, restored_path)
            
            success, msg = self.db_connector.restore(restored_path, target_config)
            if not success:
                raise Exception(f"Restore failed: {msg}")
            
            self.logger.info(f"Restore completed: {backup_id}")
            return True, "Restore completed successfully"
            
        finally:
            for f in [encrypted_path, decrypted_path, restored_path]:
                if os.path.exists(f):
                    os.remove(f)
