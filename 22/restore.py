#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import configparser
import subprocess
from datetime import datetime
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('restore.log'),
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


def kill_mysql_connections(db_config, database_name):
    logger.info(f'Killing existing MySQL connections to: {database_name}')
    
    kill_sql = f"""
SET SESSION sql_log_bin = 0;
SELECT CONCAT('KILL ', id, ';') 
FROM information_schema.processlist 
WHERE db = '{database_name}' 
AND COMMAND != 'Sleep'
AND USER != 'system user';
"""
    
    try:
        cmd = [
            'mysql',
            f'--host={db_config.get("host", "localhost")}',
            f'--port={db_config.get("port", 3306)}',
            f'--user={db_config.get("user")}',
            f'--password={db_config.get("password")}',
            '-e',
            kill_sql
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info('Existing MySQL connections killed successfully')
        return True
    except Exception as e:
        logger.warning(f'Could not kill MySQL connections: {e}')
        return False


def kill_postgresql_connections(db_config, database_name):
    logger.info(f'Killing existing PostgreSQL connections to: {database_name}')
    
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config.get('password', '')
    
    kill_sql = f"""
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = '{database_name}' 
AND pid <> pg_backend_pid();
"""
    
    try:
        cmd = [
            'psql',
            f'--host={db_config.get("host", "localhost")}',
            f'--port={db_config.get("port", 5432)}',
            f'--username={db_config.get("user", "postgres")}',
            '-d',
            'postgres',
            '-c',
            kill_sql
        ]
        
        subprocess.run(cmd, env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info('Existing PostgreSQL connections killed successfully')
        return True
    except Exception as e:
        logger.warning(f'Could not kill PostgreSQL connections: {e}')
        return False


def kill_mongodb_connections(db_config, database_name):
    logger.info(f'Killing existing MongoDB connections to: {database_name}')
    try:
        cmd = [
            'mongo',
            f'--host={db_config.get("host", "localhost")}',
            f'--port={db_config.get("port", 27017)}',
            '-u',
            db_config.get('user', ''),
            '-p',
            db_config.get('password', ''),
            '--authenticationDatabase',
            db_config.get('authentication_database', 'admin'),
            '--eval',
            f'db.adminCommand({"{currentOp: true, allUsers: true}"})'
        ]
        
        if not db_config.get('user'):
            cmd = [c for c in cmd if c not in ['-u', '-p', '--authenticationDatabase'] and c not in [db_config.get('user', ''), db_config.get('password', ''), db_config.get('authentication_database', 'admin')]]
        
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info('MongoDB cannot forcefully kill connections, skipping')
        return True
    except Exception as e:
        logger.warning(f'MongoDB connection check failed: {e}')
        return False


def mysql_restore(db_config, backup_file, target_db=None, force=False):
    database_name = target_db or db_config.get('database_name')
    
    logger.info(f'Starting MySQL restore: {database_name}')
    logger.info(f'Using backup file: {backup_file}')
    
    if not os.path.exists(backup_file):
        raise FileNotFoundError(f'Backup file not found: {backup_file}')
    
    if force:
        kill_mysql_connections(db_config, database_name)
    
    prep_sql = """
SET FOREIGN_KEY_CHECKS = 0;
SET UNIQUE_CHECKS = 0;
SET AUTOCOMMIT = 0;
"""
    
    post_sql = """
SET FOREIGN_KEY_CHECKS = 1;
SET UNIQUE_CHECKS = 1;
COMMIT;
SET AUTOCOMMIT = 1;
"""
    
    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
        backup_content = f.read()
    
    full_content = prep_sql + '\n' + backup_content + '\n' + post_sql
    
    cmd = [
        'mysql',
        f'--host={db_config.get("host", "localhost")}',
        f'--port={db_config.get("port", 3306)}',
        f'--user={db_config.get("user")}',
        f'--password={db_config.get("password")}',
        '--default-character-set=utf8mb4',
        database_name
    ]
    
    subprocess.run(
        cmd,
        input=full_content.encode('utf-8'),
        check=True,
        stderr=subprocess.PIPE
    )
    
    logger.info(f'MySQL restore completed: {database_name}')
    return True


def postgresql_restore(db_config, backup_file, target_db=None, force=False):
    database_name = target_db or db_config.get('database_name')
    
    logger.info(f'Starting PostgreSQL restore: {database_name}')
    logger.info(f'Using backup file: {backup_file}')
    
    if not os.path.exists(backup_file):
        raise FileNotFoundError(f'Backup file not found: {backup_file}')
    
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config.get('password', '')
    
    if force:
        kill_postgresql_connections(db_config, database_name)
    
    cmd = [
        'psql',
        f'--host={db_config.get("host", "localhost")}',
        f'--port={db_config.get("port", 5432)}',
        f'--username={db_config.get("user", "postgres")}',
        '-d',
        database_name,
        '-f',
        backup_file,
        '--set',
        'ON_ERROR_STOP=1'
    ]
    
    subprocess.run(cmd, env=env, check=True, stderr=subprocess.PIPE)
    
    logger.info(f'PostgreSQL restore completed: {database_name}')
    return True


def mongodb_restore(db_config, backup_dir, target_db=None, force=False):
    database_name = target_db or db_config.get('database_name')
    
    logger.info(f'Starting MongoDB restore: {database_name}')
    logger.info(f'Using backup directory: {backup_dir}')
    
    if not os.path.exists(backup_dir):
        raise FileNotFoundError(f'Backup directory not found: {backup_dir}')
    
    cmd = [
        'mongorestore',
        f'--host={db_config.get("host", "localhost")}',
        f'--port={db_config.get("port", 27017)}',
        f'--username={db_config.get("user", "")}',
        f'--password={db_config.get("password", "")}',
        f'--authenticationDatabase={db_config.get("authentication_database", "admin")}',
        f'--db={database_name}',
        '--drop',
        '--gzip',
        backup_dir
    ]
    
    if not db_config.get('user'):
        cmd = [c for c in cmd if not c.startswith('--username=') and not c.startswith('--password=')]
    
    subprocess.run(cmd, check=True, stderr=subprocess.PIPE)
    
    logger.info(f'MongoDB restore completed: {database_name}')
    return True


RESTORE_HANDLERS = {
    'mysql': mysql_restore,
    'postgresql': postgresql_restore,
    'mongodb': mongodb_restore
}


def restore_single_database(config, backup_source, db_type='mysql', target_db=None, force=False, instance_name=None):
    if instance_name:
        instances = get_db_instances(config, [instance_name])
        if instance_name in instances:
            db_config = instances[instance_name]
            db_type = db_config.get('type', 'mysql').lower()
            if not target_db:
                target_db = db_config.get('database_name')
        else:
            raise ValueError(f'Instance not found: {instance_name}')
    else:
        db_configs = get_db_instances(config)
        db_config = list(db_configs.values())[0] if db_configs else {'type': db_type}
    
    if db_type not in RESTORE_HANDLERS:
        raise ValueError(f'Unknown database type: {db_type}')
    
    handler = RESTORE_HANDLERS[db_type]
    return handler(db_config, backup_source, target_db, force)


def restore_multiple_databases(config, backup_dir, database_names=None, force=False):
    if not os.path.exists(backup_dir):
        raise FileNotFoundError(f'Backup directory not found: {backup_dir}')
    
    success_count = 0
    error_count = 0
    
    db_instances = get_db_instances(config)
    
    for root, dirs, files in os.walk(backup_dir):
        for file in files:
            if file.endswith('.sql') or file.endswith('.sql.gz'):
                backup_path = os.path.join(root, file)
                
                db_name = None
                db_type = 'mysql'
                
                for instance_name, db_config in db_instances.items():
                    if db_config.get('database_name') in file or instance_name in root:
                        db_name = db_config.get('database_name')
                        db_type = db_config.get('type', 'mysql').lower()
                        break
                
                if database_names and db_name not in database_names:
                    continue
                
                try:
                    restore_single_database(config, backup_path, db_type, db_name, force)
                    success_count += 1
                except Exception as e:
                    logger.error(f'Failed to restore {backup_path}: {e}')
                    error_count += 1
        
        for directory in dirs:
            backup_path = os.path.join(root, directory)
            dir_content = os.listdir(backup_path)
            mongo_files = [f for f in dir_content if f.endswith('.bson.gz') or f.endswith('.json.gz')]
            
            if mongo_files:
                db_name = None
                db_type = 'mongodb'
                
                for instance_name, db_config in db_instances.items():
                    if db_config.get('type', '').lower() == 'mongodb':
                        if db_config.get('database_name') in directory or instance_name in root:
                            db_name = db_config.get('database_name')
                            break
                
                if not db_name:
                    db_name = directory
                
                if database_names and db_name not in database_names:
                    continue
                
                try:
                    restore_single_database(config, backup_path, 'mongodb', db_name, force)
                    success_count += 1
                except Exception as e:
                    logger.error(f'Failed to restore {backup_path}: {e}')
                    error_count += 1
    
    logger.info(f'Multiple database restore completed: {success_count} success, {error_count} failed')
    return success_count, error_count


def list_available_backups(backup_dir):
    if not os.path.exists(backup_dir):
        logger.warning(f'Backup directory not found: {backup_dir}')
        return []
    
    backups = []
    for root, dirs, files in os.walk(backup_dir):
        for directory in dirs:
            dir_path = os.path.join(root, directory)
            backup_files = []
            for file in os.listdir(dir_path):
                if file.endswith('.sql') or file.endswith('.sql.gz'):
                    file_path = os.path.join(dir_path, file)
                    stat = os.stat(file_path)
                    backup_files.append({
                        'file': file,
                        'path': file_path,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                        'type': 'sql'
                    })
                elif file.endswith('.bson.gz') or file.endswith('.json.gz'):
                    file_path = os.path.join(dir_path, file)
                    stat = os.stat(file_path)
                    backup_files.append({
                        'file': file,
                        'path': file_path,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                        'type': 'mongo'
                    })
            
            if backup_files:
                backups.append({
                    'directory': dir_path,
                    'files': backup_files
                })
    
    return backups


def main():
    parser = argparse.ArgumentParser(description='Database Restore Script')
    parser.add_argument('--file', '-f', help='Backup file/directory path for restore')
    parser.add_argument('--dir', '-d', help='Backup directory for multiple database restore')
    parser.add_argument('--databases', nargs='*', help='List of database names to restore')
    parser.add_argument('--target', '-t', help='Target database name')
    parser.add_argument('--type', choices=['mysql', 'postgresql', 'mongodb'],
                        default='mysql', help='Database type (mysql/postgresql/mongodb)')
    parser.add_argument('--instance', '-i', help='Database instance name from config')
    parser.add_argument('--list', '-l', action='store_true', help='List available backups')
    parser.add_argument('--force', action='store_true', help='Force restore by killing existing connections')
    parser.add_argument('--config', default='config.ini', help='Configuration file path')
    
    args = parser.parse_args()
    
    try:
        config = load_config(args.config)
        backup_config = config.get('backup', {})
        backup_dir = backup_config.get('backup_dir', './backups') if hasattr(backup_config, 'get') else './backups'
        
        if args.list:
            backups = list_available_backups(backup_dir)
            if not backups:
                print('No backups found.')
                return
            
            print('Available backups:')
            for i, backup in enumerate(backups, 1):
                print(f'\n{i}. Directory: {backup["directory"]}')
                for file in backup['files']:
                    print(f'   - {file["file"]} [{file["type"]}] ({file["created"]}, {file["size"]} bytes)')
            return
        
        if args.file:
            restore_single_database(
                config,
                args.file,
                args.type,
                args.target,
                args.force,
                args.instance
            )
        elif args.dir:
            restore_multiple_databases(config, args.dir, args.databases, args.force)
        else:
            parser.error('Must specify either --file or --dir or --list')
        
        logger.info('Restore process completed successfully')
    except Exception as e:
        logger.error(f'Restore process failed: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
