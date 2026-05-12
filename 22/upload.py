#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import configparser
import argparse
import logging
import time
from datetime import datetime

try:
    import oss2
except ImportError:
    print('Error: oss2 library is required. Please install it with: pip install oss2')
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('upload.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def load_config(config_file='config.ini'):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config


def create_oss_client(config):
    oss_config = config['oss']
    
    auth = oss2.Auth(
        oss_config.get('access_key_id'),
        oss_config.get('access_key_secret')
    )
    
    endpoint = oss_config.get('endpoint')
    bucket_name = oss_config.get('bucket_name')
    
    bucket = oss2.Bucket(auth, endpoint, bucket_name)
    
    return bucket


def upload_file_to_oss(bucket, local_file, remote_path):
    if not os.path.exists(local_file):
        logger.error(f'Local file not found: {local_file}')
        raise FileNotFoundError(f'Local file not found: {local_file}')
    
    filename = os.path.basename(local_file)
    remote_key = os.path.join(remote_path, filename).replace('\\', '/')
    
    if remote_key.startswith('/'):
        remote_key = remote_key[1:]
    
    logger.info(f'Uploading {local_file} to OSS: {remote_key}')
    
    try:
        total_size = os.path.getsize(local_file)
        
        if total_size > 100 * 1024 * 1024:
            logger.info('File is large, using resumable upload...')
            resumable_store = oss2.ResumableStore(root='./.oss_resumable')
            oss2.resumable_upload(
                bucket,
                remote_key,
                local_file,
                store=resumable_store,
                multipart_threshold=100 * 1024 * 1024,
                part_size=10 * 1024 * 1024,
                num_threads=3
            )
            logger.info('Resumable upload completed, cleaning up resume data...')
            resumable_store.delete(remote_key)
        else:
            bucket.put_object_from_file(remote_key, local_file)
        
        logger.info(f'Upload completed successfully: {remote_key}')
        return remote_key
    except oss2.exceptions.OssError as e:
        logger.error(f'OSS upload error: {e}')
        raise
    except Exception as e:
        logger.error(f'Error during upload: {e}')
        raise


def upload_directory_to_oss(bucket, local_dir, remote_path):
    if not os.path.exists(local_dir):
        logger.error(f'Local directory not found: {local_dir}')
        raise FileNotFoundError(f'Local directory not found: {local_dir}')
    
    uploaded_files = []
    failed_files = []
    
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            local_file = os.path.join(root, file)
            relative_path = os.path.relpath(local_file, local_dir)
            remote_key = os.path.join(remote_path, relative_path).replace('\\', '/')
            
            try:
                upload_file_to_oss(bucket, local_file, remote_path)
                uploaded_files.append(local_file)
            except Exception as e:
                logger.error(f'Failed to upload {local_file}: {e}')
                failed_files.append(local_file)
    
    logger.info(f'Directory upload completed: {len(uploaded_files)} uploaded, {len(failed_files)} failed')
    return uploaded_files, failed_files


def list_oss_files(bucket, prefix='', max_keys=100):
    logger.info(f'Listing OSS files with prefix: {prefix}')
    
    try:
        files = []
        for obj in oss2.ObjectIterator(bucket, prefix=prefix, max_keys=max_keys):
            files.append({
                'key': obj.key,
                'size': obj.size,
                'last_modified': obj.last_modified
            })
        
        return files
    except oss2.exceptions.OssError as e:
        logger.error(f'OSS list error: {e}')
        raise


def download_from_oss(bucket, remote_key, local_file):
    logger.info(f'Downloading {remote_key} to {local_file}')
    
    try:
        total_size = bucket.get_object_meta(remote_key).content_length
        
        if total_size > 100 * 1024 * 1024:
            logger.info('File is large, using resumable download...')
            resumable_store = oss2.ResumableStore(root='./.oss_resumable')
            oss2.resumable_download(
                bucket,
                remote_key,
                local_file,
                store=resumable_store,
                part_size=10 * 1024 * 1024,
                num_threads=3
            )
            logger.info('Resumable download completed, cleaning up resume data...')
            resumable_store.delete(remote_key)
        else:
            bucket.get_object_to_file(remote_key, local_file)
        
        logger.info(f'Download completed successfully: {local_file}')
        return True
    except oss2.exceptions.OssError as e:
        logger.error(f'OSS download error: {e}')
        raise


def main():
    parser = argparse.ArgumentParser(description='OSS Upload Script')
    parser.add_argument('--file', help='Single file to upload')
    parser.add_argument('--dir', help='Directory to upload')
    parser.add_argument('--list', action='store_true', help='List files in OSS bucket')
    parser.add_argument('--download', help='Remote key to download')
    parser.add_argument('--output', help='Output file path for download')
    parser.add_argument('--prefix', default='', help='Prefix for listing OSS files')
    parser.add_argument('--remote-path', default='', help='Remote path prefix in OSS')
    parser.add_argument('--config', default='config.ini', help='Configuration file path')
    parser.add_argument('--all-backups', action='store_true', help='Upload all backup files from backup directory')
    
    args = parser.parse_args()
    
    try:
        config = load_config(args.config)
        bucket = create_oss_client(config)
        oss_config = config['oss']
        default_remote_path = oss_config.get('backup_path', '')
        
        remote_path = args.remote_path or default_remote_path
        
        if args.list:
            files = list_oss_files(bucket, args.prefix)
            if not files:
                print('No files found in OSS.')
                return
            
            print('OSS files:')
            for i, file in enumerate(files, 1):
                last_modified = datetime.fromtimestamp(file['last_modified']).strftime('%Y-%m-%d %H:%M:%S')
                print(f'{i}. {file["key"]} ({file["size"]} bytes, {last_modified})')
            return
        
        if args.download:
            if not args.output:
                parser.error('Must specify --output when using --download')
            
            download_from_oss(bucket, args.download, args.output)
        elif args.file:
            upload_file_to_oss(bucket, args.file, remote_path)
        elif args.dir:
            upload_directory_to_oss(bucket, args.dir, remote_path)
        elif args.all_backups:
            backup_config = config['backup']
            backup_dir = backup_config.get('backup_dir', './backups')
            
            if os.path.exists(backup_dir):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                remote_backup_path = os.path.join(remote_path, timestamp).replace('\\', '/')
                upload_directory_to_oss(bucket, backup_dir, remote_backup_path)
            else:
                logger.warning(f'Backup directory not found: {backup_dir}')
        else:
            parser.error('Must specify --file, --dir, --list, --download, or --all-backups')
        
        logger.info('OSS operation completed successfully')
    except Exception as e:
        logger.error(f'OSS operation failed: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
