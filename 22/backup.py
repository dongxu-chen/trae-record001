#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import configparser
import subprocess
from datetime import datetime, timedelta
import argparse
import shutil
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def load_config(config_file='config.ini'):
    config = configparser.ConfigParser()
    config.read(config_file, encoding='utf-8')
    return config


def get_db_instances(config, instance_names=None):
    instances = {}
    for section in config.sections():
        if section.startswith('database:'):
            instance_name = section.split(':', 1)[1]
            if config.getboolean(section, 'enabled', fallback=True):
                if instance_names is None or 'all' in instance_names or instance_name in instance_names:
                    instances[instance_name] = dict(config[section])
                    instances[instance_name]['instance_name'] = instance_name
    return instances


def get_backup_path(backup_dir, instance_name, backup_type):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, instance_name, f'{backup_type}_{timestamp}')
    if not os.path.exists(backup_path):
        os.makedirs(backup_path)
    return backup_path


def mysql_backup_full(db_config, backup_path):
    database_name = db_config.get('database_name')
    backup_file = os.path.join(backup_path, f'{database_name}_full.sql')
    
    logger.info(f'Starting MySQL full backup: {database_name}')
    
    cmd = [
        'mysqldump',
        f'--host={db_config.get("host", "localhost")}',
        f'--port={db_config.get("port", 3306)}',
        f'--user={db_config.get("user")}',
        f'--password={db_config.get("password")}',
        '--default-character-set=utf8mb4',
        '--single-transaction',
        '--routines',
        '--triggers',
        '--events',
        '--column-statistics=0',
        '--ssl-mode=DISABLED',
        database_name
    ]
    
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            subprocess.run(cmd, stdout=f, check=True, stderr=subprocess.PIPE)
        
        logger.info(f'MySQL full backup completed: {backup_file}')
        return backup_file
    except subprocess.CalledProcessError as e:
        logger.error(f'MySQL full backup failed: {e.stderr.decode()}')
        raise


def mysql_backup_incremental(db_config, backup_path):
    database_name = db_config.get('database_name')
    backup_file = os.path.join(backup_path, f'{database_name}_incr.sql')
    
    logger.info(f'Starting MySQL incremental backup: {database_name}')
    
    cmd = [
        'mysqldump',
        f'--host={db_config.get("host", "localhost")}',
        f'--port={db_config.get("port", 3306)}',
        f'--user={db_config.get("user")}',
        f'--password={db_config.get("password")}',
        '--default-character-set=utf8mb4',
        '--single-transaction',
        '--routines',
        '--triggers',
        '--events',
        '--column-statistics=0',
        '--ssl-mode=DISABLED',
        '--where=update_time >= DATE_SUB(NOW(), INTERVAL 1 DAY)',
        database_name
    ]
    
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)
        
        if result.returncode == 0:
            logger.info(f'MySQL incremental backup completed: {backup_file}')
            return backup_file
        else:
            logger.warning(f'MySQL incremental backup issues: {result.stderr.decode()}')
            return backup_file
    except Exception as e:
        logger.error(f'MySQL incremental backup failed: {e}')
        raise


def postgresql_backup_full(db_config, backup_path):
    database_name = db_config.get('database_name')
    backup_file = os.path.join(backup_path, f'{database_name}_full.sql')
    
    logger.info(f'Starting PostgreSQL full backup: {database_name}')
    
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config.get('password', '')
    
    cmd = [
        'pg_dump',
        f'--host={db_config.get("host", "localhost")}',
        f'--port={db_config.get("port", 5432)}',
        f'--username={db_config.get("user", "postgres")}',
        '--format=p',
        '--create',
        '--clean',
        '--if-exists',
        '--encoding=UTF8',
        database_name
    ]
    
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            subprocess.run(cmd, env=env, stdout=f, check=True, stderr=subprocess.PIPE)
        
        logger.info(f'PostgreSQL full backup completed: {backup_file}')
        return backup_file
    except subprocess.CalledProcessError as e:
        logger.error(f'PostgreSQL full backup failed: {e.stderr.decode()}')
        raise


def postgresql_backup_incremental(db_config, backup_path):
    database_name = db_config.get('database_name')
    backup_file = os.path.join(backup_path, f'{database_name}_incr.sql')
    
    logger.warning(f'PostgreSQL incremental backup not fully supported, using full backup for: {database_name}')
    
    return postgresql_backup_full(db_config, backup_path)


def mongodb_backup_full(db_config, backup_path):
    database_name = db_config.get('database_name')
    dump_dir = os.path.join(backup_path, f'{database_name}_full')
    
    logger.info(f'Starting MongoDB full backup: {database_name}')
    
    cmd = [
        'mongodump',
        f'--host={db_config.get("host", "localhost")}',
        f'--port={db_config.get("port", 27017)}',
        f'--username={db_config.get("user", "")}',
        f'--password={db_config.get("password", "")}',
        f'--authenticationDatabase={db_config.get("authentication_database", "admin")}',
        f'--db={database_name}',
        f'--out={dump_dir}',
        '--gzip'
    ]
    
    if not db_config.get('user'):
        cmd = [c for c in cmd if not c.startswith('--username=') and not c.startswith('--password=')]
    
    try:
        subprocess.run(cmd, check=True, stderr=subprocess.PIPE)
        
        logger.info(f'MongoDB full backup completed: {dump_dir}')
        return dump_dir
    except subprocess.CalledProcessError as e:
        logger.error(f'MongoDB full backup failed: {e.stderr.decode()}')
        raise


def mongodb_backup_incremental(db_config, backup_path):
    database_name = db_config.get('database_name')
    
    logger.warning(f'MongoDB incremental backup requires oplog, using full backup for: {database_name}')
    
    return mongodb_backup_full(db_config, backup_path)


BACKUP_HANDLERS = {
    'mysql': {
        'full': mysql_backup_full,
        'incremental': mysql_backup_incremental
    },
    'postgresql': {
        'full': postgresql_backup_full,
        'incremental': postgresql_backup_incremental
    },
    'mongodb': {
        'full': mongodb_backup_full,
        'incremental': mongodb_backup_incremental
    }
}


def backup_instance(db_config, backup_type, backup_dir):
    db_type = db_config.get('type', 'mysql').lower()
    instance_name = db_config.get('instance_name')
    
    if db_type not in BACKUP_HANDLERS:
        raise ValueError(f'Unknown database type: {db_type}')
    
    if backup_type not in BACKUP_HANDLERS[db_type]:
        raise ValueError(f'Backup type {backup_type} not supported for {db_type}')
    
    backup_path = get_backup_path(backup_dir, instance_name, backup_type)
    handler = BACKUP_HANDLERS[db_type][backup_type]
    
    return handler(db_config, backup_path)


def backup_all(config, backup_type, instances=None):
    backup_config = config['backup']
    backup_dir = backup_config.get('backup_dir', './backups')
    
    db_instances = get_db_instances(config, instances)
    
    if not db_instances:
        logger.warning('No enabled database instances found')
        return {}
    
    results = {}
    for instance_name, db_config in db_instances.items():
        try:
            backup_file = backup_instance(db_config, backup_type, backup_dir)
            results[instance_name] = {'status': 'success', 'file': backup_file}
            logger.info(f'Backup completed for {instance_name}: {backup_file}')
        except Exception as e:
            results[instance_name] = {'status': 'failed', 'error': str(e)}
            logger.error(f'Backup failed for {instance_name}: {e}')
    
    return results


def cleanup_old_backups(config):
    backup_config = config['backup']
    backup_dir = backup_config.get('backup_dir', './backups')
    retention_days = int(backup_config.get('retention_days', 30))
    
    if not os.path.exists(backup_dir):
        return
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    logger.info(f'Cleaning up backups older than {retention_days} days')
    
    for root, dirs, files in os.walk(backup_dir):
        for directory in dirs:
            dir_path = os.path.join(root, directory)
            try:
                dir_time = datetime.fromtimestamp(os.path.getctime(dir_path))
                if dir_time < cutoff_date:
                    shutil.rmtree(dir_path)
                    logger.info(f'Deleted old backup directory: {dir_path}')
            except Exception as e:
                logger.error(f'Error deleting old backup {dir_path}: {e}')


def main():
    parser = argparse.ArgumentParser(description='Database Backup Script')
    parser.add_argument('--type', choices=['full', 'incremental', 'auto'], default='auto',
                        help='Backup type: full, incremental, or auto (default)')
    parser.add_argument('--instance', '-i', action='append', help='Database instance name(s)')
    parser.add_argument('--config', default='config.ini', help='Configuration file path')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old backups')
    parser.add_argument('--list', '-l', action='store_true', help='List all database instances')
    
    args = parser.parse_args()
    
    try:
        config = load_config(args.config)
        
        if args.list:
            instances = get_db_instances(config)
            if not instances:
                print('No database instances configured.')
                return
            
            print('Available database instances:')
            for name, cfg in instances.items():
                db_type = cfg.get('type', 'mysql')
                host = cfg.get('host', 'localhost')
                port = cfg.get('port', 'N/A')
                db = cfg.get('database_name', 'N/A')
                print(f'  - {name} [{db_type}]: {host}:{port}/{db}')
            return
        
        if args.cleanup:
            cleanup_old_backups(config)
            return
        
        backup_config = config['backup']
        backup_type = args.type
        
        if backup_type == 'auto':
            today = datetime.now().weekday()
            full_interval = int(backup_config.get('full_backup_interval', 7))
            backup_type = 'full' if today % full_interval == 0 else 'incremental'
        
        instances = args.instance if args.instance else ['all']
        
        results = backup_all(config, backup_type, instances)
        
        success_count = sum(1 for r in results.values() if r.get('status') == 'success')
        fail_count = len(results) - success_count
        
        logger.info(f'Backup process completed: {success_count} success, {fail_count} failed')
        
        cleanup_old_backups(config)
        
        if fail_count > 0:
            sys.exit(1)
    except Exception as e:
        logger.error(f'Backup process failed: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
