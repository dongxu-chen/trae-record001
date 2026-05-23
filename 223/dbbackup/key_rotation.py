import os
import json
import logging
from datetime import datetime
from .crypto import Encryptor
from .storage import StorageFactory
from .utils import ensure_dir


class KeyRotationManager:
    def __init__(self, config, db_type):
        self.config = config
        self.db_type = db_type
        self.logger = logging.getLogger('dbbackup')
        
        self.encryption_config = config.get_encryption_config()
        self.current_key = self.encryption_config.get('key')
        
        self.storage = StorageFactory.get_storage(config.get_storage_config())
        
        backup_config = config.get_backup_config()
        self.temp_dir = backup_config.get('temp_dir', './temp')
        self.key_history_file = os.path.join(self.temp_dir, f'{db_type}_key_history.json')
        
        ensure_dir(self.temp_dir)
        self.key_history = self._load_key_history()

    def _load_key_history(self):
        if os.path.exists(self.key_history_file):
            try:
                with open(self.key_history_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'current_version': 0,
            'keys': []
        }

    def _save_key_history(self):
        with open(self.key_history_file, 'w') as f:
            json.dump(self.key_history, f, indent=2)

    def generate_new_key(self, key_length=32):
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
        new_key = ''.join(secrets.choice(alphabet) for _ in range(key_length))
        return new_key

    def rotate_key(self, new_key=None, re_encrypt_history=True):
        self.logger.info("Starting key rotation...")
        
        if not new_key:
            new_key = self.generate_new_key()
        
        new_version = self.key_history['current_version'] + 1
        
        key_entry = {
            'version': new_version,
            'key': new_key,
            'created_at': datetime.now().isoformat(),
            'status': 'active'
        }
        
        if self.key_history['keys']:
            self.key_history['keys'][-1]['status'] = 'deprecated'
            self.key_history['keys'][-1]['deprecated_at'] = datetime.now().isoformat()
        
        self.key_history['keys'].append(key_entry)
        self.key_history['current_version'] = new_version
        self._save_key_history()
        
        self.logger.info(f"New key generated (version {new_version})")
        
        if re_encrypt_history:
            self._reencrypt_all_backups(self.current_key, new_key)
        
        return {
            'new_version': new_version,
            'new_key': new_key,
            're_encrypted': re_encrypt_history
        }

    def _reencrypt_all_backups(self, old_key, new_key):
        self.logger.info("Re-encrypting all historical backups...")
        
        old_encryptor = Encryptor({'enabled': True, 'key': old_key})
        new_encryptor = Encryptor({'enabled': True, 'key': new_key})
        
        prefix = f"{self.db_type}/"
        files = self.storage.list_files(prefix)
        
        encrypted_files = [f for f in files if f.endswith('.enc')]
        
        success_count = 0
        fail_count = 0
        
        for remote_path in encrypted_files:
            try:
                self.logger.info(f"Re-encrypting: {remote_path}")
                
                local_old = os.path.join(self.temp_dir, 'reencrypt_old.enc')
                local_decrypted = os.path.join(self.temp_dir, 'reencrypt_decrypted.tmp')
                local_new = os.path.join(self.temp_dir, 'reencrypt_new.enc')
                
                self.storage.download(remote_path, local_old)
                old_encryptor.decrypt(local_old, local_decrypted)
                new_encryptor.encrypt(local_decrypted, local_new)
                self.storage.upload(local_new, remote_path)
                
                for f in [local_old, local_decrypted, local_new]:
                    if os.path.exists(f):
                        os.remove(f)
                
                success_count += 1
                
            except Exception as e:
                self.logger.error(f"Failed to re-encrypt {remote_path}: {e}")
                fail_count += 1
        
        self.logger.info(f"Re-encryption complete: {success_count} success, {fail_count} failed")
        
        return {
            'success': success_count,
            'failed': fail_count,
            'total': len(encrypted_files)
        }

    def should_rotate(self, rotation_days=30):
        if not self.key_history['keys']:
            return True
        
        last_key = self.key_history['keys'][-1]
        created_at = datetime.fromisoformat(last_key['created_at'])
        days_since = (datetime.now() - created_at).days
        
        return days_since >= rotation_days

    def auto_rotate_if_needed(self, rotation_days=30):
        if self.should_rotate(rotation_days):
            self.logger.info(f"Key older than {rotation_days} days, performing rotation")
            return self.rotate_key()
        else:
            self.logger.info("Key rotation not needed yet")
            return None

    def get_key_by_version(self, version):
        for key_entry in self.key_history['keys']:
            if key_entry['version'] == version:
                return key_entry['key']
        return None

    def list_key_history(self):
        return self.key_history['keys']

    def get_current_key_info(self):
        if not self.key_history['keys']:
            return None
        return self.key_history['keys'][-1]
