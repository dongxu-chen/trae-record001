import os
import json
import logging
from datetime import datetime
from .database import DatabaseFactory
from .crypto import Compressor, Encryptor
from .storage import StorageFactory
from .utils import ensure_dir, generate_backup_id, calculate_md5, get_file_size, format_size


class BackupEngine:
    def __init__(self, config, db_type):
        self.config = config
        self.db_type = db_type
        self.logger = logging.getLogger('dbbackup')
        
        db_config = config.get_database_config(db_type)
        self.db_connector = DatabaseFactory.get_connector(db_type, db_config)
        
        backup_config = config.get_backup_config()
        self.backup_dir = backup_config.get('backup_dir', './backups')
        self.temp_dir = backup_config.get('temp_dir', './temp')
        self.retention_days = backup_config.get('retention_days', 30)
        self.position_tracker_file = os.path.join(self.backup_dir, f'{db_type}_position_tracker.json')
        
        ensure_dir(self.backup_dir)
        ensure_dir(self.temp_dir)
        
        self.compressor = Compressor(config.get_compression_config())
        self.encryptor = Encryptor(config.get_encryption_config())
        self.storage = StorageFactory.get_storage(config.get_storage_config())
        
        self.verification_config = config.get_verification_config()
        self.last_position = self._load_last_position()

    def _load_last_position(self):
        if os.path.exists(self.position_tracker_file):
            try:
                with open(self.position_tracker_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return None

    def _save_last_position(self, position_info):
        with open(self.position_tracker_file, 'w') as f:
            json.dump(position_info, f, indent=2)

    def check_binlog_changes(self):
        if self.last_position:
            last_file = self.last_position.get('file')
            last_pos = self.last_position.get('position') or self.last_position.get('lsn')
            changed, result = self.db_connector.monitor_binlog_changes(last_file, last_pos)
            return changed, result
        return True, "No previous position recorded"

    def create_backup(self, strategy='full'):
        backup_id = generate_backup_id(self.db_type, strategy)
        self.logger.info(f"Starting backup: {backup_id}")
        
        backup_info = {
            'backup_id': backup_id,
            'db_type': self.db_type,
            'strategy': strategy,
            'timestamp': datetime.now().isoformat(),
            'status': 'started'
        }
        
        try:
            if strategy == 'full':
                success, msg, position_info = self._create_full_backup(backup_id, backup_info)
            elif strategy == 'incremental':
                success, msg, position_info = self._create_incremental_backup(backup_id, backup_info)
            else:
                raise ValueError(f"Unsupported backup strategy: {strategy}")
            
            if not success:
                raise Exception(f"Backup failed: {msg}")
            
            if position_info:
                backup_info['binlog_position'] = position_info
                self._save_last_position(position_info)
            
            self.logger.info(f"Backup completed: {backup_id}")
            return backup_info
            
        except Exception as e:
            backup_info['status'] = 'failed'
            backup_info['error'] = str(e)
            self.logger.error(f"Backup failed: {backup_id} - {str(e)}")
            raise

    def _create_full_backup(self, backup_id, backup_info):
        raw_backup_path = os.path.join(self.temp_dir, f"{backup_id}.sql")
        
        success, msg = self.db_connector.full_backup(raw_backup_path)
        if not success:
            return False, msg, None
        
        backup_info['raw_size'] = get_file_size(raw_backup_path)
        
        compressed_path = os.path.join(self.temp_dir, f"{backup_id}.gz")
        success, msg = self.compressor.compress(raw_backup_path, compressed_path)
        if not success:
            return False, msg, None
        
        backup_info['compressed_size'] = get_file_size(compressed_path)
        
        encrypted_path = os.path.join(self.backup_dir, f"{backup_id}.enc")
        success, msg = self.encryptor.encrypt(compressed_path, encrypted_path)
        if not success:
            return False, msg, None
        
        backup_info['final_size'] = get_file_size(encrypted_path)
        backup_info['md5'] = calculate_md5(encrypted_path)
        
        success, position_info = self.db_connector.get_current_binlog_position()
        if success:
            backup_info['binlog_position_at_backup'] = position_info
        
        remote_path = f"{self.db_type}/full/{backup_id}.enc"
        success, msg = self.storage.upload(encrypted_path, remote_path)
        if not success:
            return False, msg, None
        
        backup_info['remote_path'] = remote_path
        backup_info['status'] = 'completed'
        
        metadata_path = os.path.join(self.backup_dir, f"{backup_id}.json")
        with open(metadata_path, 'w') as f:
            json.dump(backup_info, f, indent=2)
        
        metadata_remote = f"{self.db_type}/full/{backup_id}.json"
        self.storage.upload(metadata_path, metadata_remote)
        
        self._cleanup_temp_files([raw_backup_path, compressed_path])
        
        return True, "Full backup completed", position_info

    def _create_incremental_backup(self, backup_id, backup_info):
        changed, change_info = self.check_binlog_changes()
        self.logger.info(f"Binlog changes detected: {changed}")
        
        if not changed:
            self.logger.info("No binlog changes detected, skipping incremental backup")
            return True, "No changes detected", None
        
        start_file = None
        start_position = None
        if self.last_position:
            start_file = self.last_position.get('file')
            start_position = self.last_position.get('position') or self.last_position.get('lsn')
            self.logger.info(f"Starting from last known position: {start_file} @ {start_position}")
        
        raw_backup_path = os.path.join(self.temp_dir, f"{backup_id}.binlog")
        
        success, result = self.db_connector.incremental_backup(
            raw_backup_path,
            start_file=start_file,
            start_position=start_position
        )
        
        if not success:
            return False, result, None
        
        position_info = result if isinstance(result, dict) else None
        
        backup_info['raw_size'] = get_file_size(raw_backup_path)
        
        compressed_path = os.path.join(self.temp_dir, f"{backup_id}.gz")
        success, msg = self.compressor.compress(raw_backup_path, compressed_path)
        if not success:
            return False, msg, None
        
        backup_info['compressed_size'] = get_file_size(compressed_path)
        
        encrypted_path = os.path.join(self.backup_dir, f"{backup_id}.enc")
        success, msg = self.encryptor.encrypt(compressed_path, encrypted_path)
        if not success:
            return False, msg, None
        
        backup_info['final_size'] = get_file_size(encrypted_path)
        backup_info['md5'] = calculate_md5(encrypted_path)
        
        position_file_local = raw_backup_path + '.position'
        if os.path.exists(position_file_local):
            position_enc_path = os.path.join(self.backup_dir, f"{backup_id}.position")
            with open(position_file_local, 'r') as f:
                position_data = json.load(f)
                backup_info['position_data'] = position_data
            
            position_remote = f"{self.db_type}/incremental/{backup_id}.position"
            self.storage.upload(position_file_local, position_remote)
        
        success, current_position = self.db_connector.get_current_binlog_position()
        if success:
            position_info = current_position
        
        remote_path = f"{self.db_type}/incremental/{backup_id}.enc"
        success, msg = self.storage.upload(encrypted_path, remote_path)
        if not success:
            return False, msg, None
        
        backup_info['remote_path'] = remote_path
        backup_info['status'] = 'completed'
        
        metadata_path = os.path.join(self.backup_dir, f"{backup_id}.json")
        with open(metadata_path, 'w') as f:
            json.dump(backup_info, f, indent=2)
        
        metadata_remote = f"{self.db_type}/incremental/{backup_id}.json"
        self.storage.upload(metadata_path, metadata_remote)
        
        self._cleanup_temp_files([raw_backup_path, compressed_path, position_file_local])
        
        self.logger.info(f"  Raw size: {format_size(backup_info['raw_size'])}")
        self.logger.info(f"  Compressed size: {format_size(backup_info['compressed_size'])}")
        self.logger.info(f"  Final size: {format_size(backup_info['final_size'])}")
        
        return True, "Incremental backup completed", position_info

    def _cleanup_temp_files(self, files):
        for f in files:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass

    def list_backups(self, strategy=None):
        prefix = f"{self.db_type}/"
        if strategy:
            prefix += f"{strategy}/"
        
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

    def get_latest_backup(self, strategy='full'):
        backups = self.list_backups(strategy)
        return backups[0] if backups else None
