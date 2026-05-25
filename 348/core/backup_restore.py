import logging
import time
import os
import shutil
import tempfile
from typing import Dict, Optional, Tuple

from config import BackupConfig
from core.db_driver import DatabaseDriver, create_driver
from core.crypto_verify import CryptoVerifier

logger = logging.getLogger(__name__)


class BackupRestoreManager:
    def __init__(self, backup_config: BackupConfig, driver: DatabaseDriver):
        self.backup_config = backup_config
        self.driver = driver
        self.crypto_verifier = None
        self._restore_stats = {}

        if backup_config.encryption_key:
            self.crypto_verifier = CryptoVerifier(
                key=backup_config.encryption_key,
                algorithm=backup_config.encryption_algorithm
            )

    def get_restore_stats(self) -> Dict:
        return self._restore_stats.copy()

    def _preprocess_backup(self, timings: Dict) -> Tuple[str, Optional[str]]:
        backup_path = self.backup_config.backup_file_path

        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        original_hash = None

        file_prep_start = time.time()
        file_size = os.path.getsize(backup_path)
        timings['file_size_bytes'] = file_size
        timings['file_preparation_seconds'] = time.time() - file_prep_start

        if self.crypto_verifier:
            logger.info("Verifying backup encryption integrity...")
            integrity_start = time.time()
            is_valid, original_hash = self.crypto_verifier.verify_file_integrity(backup_path)
            timings['integrity_verification_seconds'] = time.time() - integrity_start

            if not is_valid:
                raise ValueError("Backup file integrity verification failed - file may be corrupted or tampered")

            logger.info("Decrypting backup file...")
            decrypt_start = time.time()
            decrypted_path = backup_path + ".decrypted"
            self.crypto_verifier.decrypt_file(backup_path, decrypted_path)
            backup_path = decrypted_path
            timings['decryption_seconds'] = time.time() - decrypt_start
            logger.info("Backup decrypted successfully")

        if self.backup_config.compression:
            logger.info(f"Decompressing backup ({self.backup_config.compression})...")
            decompress_start = time.time()
            decompressed_path = self._decompress(backup_path)
            timings['decompression_seconds'] = time.time() - decompress_start
            if decompressed_path:
                backup_path = decompressed_path

        return backup_path, original_hash

    def _decompress(self, file_path: str) -> Optional[str]:
        compression = self.backup_config.compression.lower()
        output_path = file_path.rsplit('.', 1)[0] if '.' in file_path else file_path + ".decompressed"

        try:
            if compression in ('gzip', 'gz'):
                import gzip
                with gzip.open(file_path, 'rb') as f_in:
                    with open(output_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                return output_path
            elif compression in ('zip',):
                import zipfile
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(os.path.dirname(output_path))
                return output_path
            else:
                logger.warning(f"Unsupported compression format: {compression}")
                return None
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            return None

    def deploy_and_restore(self) -> Dict:
        timings = {
            'file_preparation_seconds': 0.0,
            'integrity_verification_seconds': 0.0,
            'decryption_seconds': 0.0,
            'decompression_seconds': 0.0,
            'database_restore_seconds': 0.0,
            'hash_verification_seconds': 0.0,
            'cleanup_seconds': 0.0,
            'file_size_bytes': 0,
            'end_to_end_seconds': 0.0
        }

        result = {
            'success': False,
            'start_time': None,
            'end_time': None,
            'duration_seconds': 0,
            'backup_file': self.backup_config.backup_file_path,
            'encryption_verified': False,
            'original_hash': None,
            'restored_hash': None,
            'error': None,
            'timings': timings
        }

        cleanup_start = 0.0
        processed_backup = None

        try:
            result['start_time'] = time.time()
            overall_start = result['start_time']

            processed_backup, original_hash = self._preprocess_backup(timings)
            result['original_hash'] = original_hash
            result['encryption_verified'] = original_hash is not None

            logger.info(f"Restoring backup: {processed_backup}")

            restore_start = time.time()
            restore_success = self.driver.restore_backup(processed_backup)
            timings['database_restore_seconds'] = time.time() - restore_start

            if not restore_success:
                raise RuntimeError("Database restore operation failed")

            logger.info("Backup restore completed successfully")

            if self.crypto_verifier:
                hash_start = time.time()
                restored_hash = self.crypto_verifier.calculate_file_hash(processed_backup)
                timings['hash_verification_seconds'] = time.time() - hash_start
                result['restored_hash'] = restored_hash

            result['success'] = True

        except Exception as e:
            logger.error(f"Backup restore failed: {e}")
            result['error'] = str(e)
        finally:
            cleanup_start = time.time()

            if self.crypto_verifier and processed_backup and processed_backup.endswith('.decrypted'):
                if os.path.exists(processed_backup):
                    try:
                        os.remove(processed_backup)
                        logger.info("Cleaned up decrypted backup file")
                    except Exception:
                        pass

            timings['cleanup_seconds'] = time.time() - cleanup_start

            result['end_time'] = time.time()
            result['duration_seconds'] = result['end_time'] - result['start_time']

            timings['end_to_end_seconds'] = result['duration_seconds']

            for key in timings:
                if key != 'file_size_bytes':
                    if timings[key] < 0:
                        timings[key] = 0.0

        self._restore_stats = result
        self._log_timing_summary(timings)
        return result

    def _log_timing_summary(self, timings: Dict):
        logger.info("=" * 50)
        logger.info("RESTORE TIMING SUMMARY (End-to-End)")
        logger.info("=" * 50)
        logger.info(f"  File Size:          {self._format_bytes(timings.get('file_size_bytes', 0))}")
        logger.info(f"  File Preparation:   {timings.get('file_preparation_seconds', 0):.3f}s")
        if timings.get('integrity_verification_seconds', 0) > 0:
            logger.info(f"  Integrity Verify:   {timings.get('integrity_verification_seconds', 0):.3f}s")
        if timings.get('decryption_seconds', 0) > 0:
            logger.info(f"  Decryption:         {timings.get('decryption_seconds', 0):.3f}s")
        if timings.get('decompression_seconds', 0) > 0:
            logger.info(f"  Decompression:      {timings.get('decompression_seconds', 0):.3f}s")
        logger.info(f"  Database Restore:   {timings.get('database_restore_seconds', 0):.3f}s")
        if timings.get('hash_verification_seconds', 0) > 0:
            logger.info(f"  Hash Verify:        {timings.get('hash_verification_seconds', 0):.3f}s")
        logger.info(f"  Cleanup:            {timings.get('cleanup_seconds', 0):.3f}s")
        logger.info("-" * 50)
        logger.info(f"  END-TO-END TOTAL:   {timings.get('end_to_end_seconds', 0):.3f}s")
        logger.info("=" * 50)

    def _format_bytes(self, bytes_val: int) -> str:
        if bytes_val == 0:
            return "0 B"
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        import math
        i = int(math.floor(math.log(bytes_val, 1024)))
        p = math.pow(1024, i)
        s = round(bytes_val / p, 2)
        return f"{s} {units[i]}"

    def measure_restore_time(self) -> float:
        result = self.deploy_and_restore()
        return result['timings'].get('end_to_end_seconds', result['duration_seconds'])


class AutoDeployer:
    def __init__(self, source_driver: DatabaseDriver, verify_driver: DatabaseDriver):
        self.source_driver = source_driver
        self.verify_driver = verify_driver

    def sync_table_structure(self, tables: list = None) -> Dict:
        result = {
            'success': False,
            'tables_synced': [],
            'errors': []
        }

        try:
            source_tables = self.source_driver.get_tables()
            if tables:
                source_tables = [t for t in source_tables if t in tables]

            for table in source_tables:
                try:
                    columns = self.source_driver.get_table_columns(table)
                    result['tables_synced'].append({'table': table, 'columns': len(columns)})
                except Exception as e:
                    result['errors'].append({'table': table, 'error': str(e)})

            result['success'] = len(result['errors']) == 0
        except Exception as e:
            result['errors'].append({'error': str(e)})

        return result

    def auto_deploy_backup(self, backup_path: str, encryption_key: str = None) -> Dict:
        backup_config = BackupConfig(
            backup_file_path=backup_path,
            encryption_key=encryption_key
        )

        manager = BackupRestoreManager(backup_config, self.verify_driver)
        return manager.deploy_and_restore()
