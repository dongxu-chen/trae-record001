import os
import logging
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path


def setup_logging(config):
    log_config = config.get_logging_config()
    log_level = getattr(logging, log_config.get('level', 'INFO').upper())
    log_file = log_config.get('file', './backup.log')
    
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('dbbackup')


def run_command(cmd, shell=True, capture_output=True):
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=capture_output,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, '', str(e)


def generate_backup_id(db_type, strategy):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{db_type}_{strategy}_{timestamp}"


def calculate_md5(file_path):
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def get_file_size(file_path):
    if os.path.exists(file_path):
        return os.path.getsize(file_path)
    return 0


def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
