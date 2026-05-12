#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import configparser
import argparse
import logging
import base64
import hashlib
from datetime import datetime

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print('Error: cryptography library is required. Please install it with: pip install cryptography')
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('encrypt.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def load_config(config_file='config.ini'):
    config = configparser.ConfigParser()
    config.read(config_file, encoding='utf-8')
    return config


def generate_key():
    return os.urandom(32)


def save_key(key, key_file):
    key_dir = os.path.dirname(key_file)
    if key_dir and not os.path.exists(key_dir):
        os.makedirs(key_dir)
    
    with open(key_file, 'wb') as f:
        f.write(base64.b64encode(key))
    
    os.chmod(key_file, 0o600)
    logger.info(f'Key saved to: {key_file}')


def load_key(key_file):
    if not os.path.exists(key_file):
        raise FileNotFoundError(f'Key file not found: {key_file}')
    
    with open(key_file, 'rb') as f:
        key_data = f.read()
    
    return base64.b64decode(key_data)


def ensure_key(config):
    encrypt_config = config.get('encryption', {})
    key_file = encrypt_config.get('key_file', './backup.key')
    
    if not os.path.exists(key_file):
        logger.info(f'Key file not found, generating new key: {key_file}')
        key = generate_key()
        save_key(key, key_file)
        return key
    
    return load_key(key_file)


def encrypt_file(input_file, key, output_file=None, delete_original=False):
    if not os.path.exists(input_file):
        raise FileNotFoundError(f'Input file not found: {input_file}')
    
    if output_file is None:
        output_file = input_file + '.enc'
    
    logger.info(f'Encrypting: {input_file} -> {output_file}')
    
    iv = os.urandom(16)
    
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    
    with open(input_file, 'rb') as f_in:
        data = f_in.read()
    
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()
    
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    
    with open(output_file, 'wb') as f_out:
        f_out.write(iv)
        f_out.write(encrypted_data)
    
    if delete_original:
        os.remove(input_file)
        logger.info(f'Deleted original file: {input_file}')
    
    logger.info(f'Encryption completed: {output_file}')
    return output_file


def decrypt_file(input_file, key, output_file=None, delete_original=False):
    if not os.path.exists(input_file):
        raise FileNotFoundError(f'Input file not found: {input_file}')
    
    if output_file is None:
        if input_file.endswith('.enc'):
            output_file = input_file[:-4]
        else:
            output_file = input_file + '.decrypted'
    
    logger.info(f'Decrypting: {input_file} -> {output_file}')
    
    with open(input_file, 'rb') as f_in:
        iv = f_in.read(16)
        encrypted_data = f_in.read()
    
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    
    decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
    
    unpadder = padding.PKCS7(128).unpadder()
    decrypted_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()
    
    with open(output_file, 'wb') as f_out:
        f_out.write(decrypted_data)
    
    if delete_original:
        os.remove(input_file)
        logger.info(f'Deleted encrypted file: {input_file}')
    
    logger.info(f'Decryption completed: {output_file}')
    return output_file


def encrypt_directory(input_dir, key, delete_original=False):
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f'Input directory not found: {input_dir}')
    
    encrypted_files = []
    failed_files = []
    
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            input_file = os.path.join(root, file)
            
            if file.endswith('.enc'):
                continue
            
            try:
                output_file = encrypt_file(input_file, key, delete_original=delete_original)
                encrypted_files.append(output_file)
            except Exception as e:
                logger.error(f'Failed to encrypt {input_file}: {e}')
                failed_files.append(input_file)
    
    logger.info(f'Directory encryption completed: {len(encrypted_files)} encrypted, {len(failed_files)} failed')
    return encrypted_files, failed_files


def decrypt_directory(input_dir, key, delete_original=False):
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f'Input directory not found: {input_dir}')
    
    decrypted_files = []
    failed_files = []
    
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if not file.endswith('.enc'):
                continue
            
            input_file = os.path.join(root, file)
            
            try:
                output_file = decrypt_file(input_file, key, delete_original=delete_original)
                decrypted_files.append(output_file)
            except Exception as e:
                logger.error(f'Failed to decrypt {input_file}: {e}')
                failed_files.append(input_file)
    
    logger.info(f'Directory decryption completed: {len(decrypted_files)} decrypted, {len(failed_files)} failed')
    return decrypted_files, failed_files


def calculate_checksum(file_path):
    hash_sha256 = hashlib.sha256()
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_sha256.update(chunk)
    
    return hash_sha256.hexdigest()


def encrypt_with_checksum(input_file, key, delete_original=False):
    checksum = calculate_checksum(input_file)
    logger.info(f'Original file checksum (SHA-256): {checksum}')
    
    encrypted_file = encrypt_file(input_file, key, delete_original=delete_original)
    
    checksum_file = encrypted_file + '.sha256'
    with open(checksum_file, 'w', encoding='utf-8') as f:
        f.write(checksum)
    
    logger.info(f'Checksum saved to: {checksum_file}')
    return encrypted_file, checksum_file


def decrypt_with_checksum(input_file, key, delete_original=False, verify=True):
    decrypted_file = decrypt_file(input_file, key, delete_original=False)
    
    if verify:
        checksum_file = input_file + '.sha256'
        if os.path.exists(checksum_file):
            with open(checksum_file, 'r', encoding='utf-8') as f:
                original_checksum = f.read().strip()
            
            new_checksum = calculate_checksum(decrypted_file)
            logger.info(f'Original checksum: {original_checksum}')
            logger.info(f'Decrypted checksum:  {new_checksum}')
            
            if original_checksum == new_checksum:
                logger.info('Checksum verification passed!')
            else:
                logger.error('Checksum verification failed! File may be corrupted.')
                raise ValueError('Checksum verification failed')
        else:
            logger.warning('No checksum file found, skipping verification')
    
    if delete_original:
        os.remove(input_file)
        checksum_file = input_file + '.sha256'
        if os.path.exists(checksum_file):
            os.remove(checksum_file)
    
    return decrypted_file


def main():
    parser = argparse.ArgumentParser(description='Backup Encryption Tool')
    parser.add_argument('action', choices=['encrypt', 'decrypt', 'generate-key'],
                        help='Action: encrypt, decrypt, or generate-key')
    parser.add_argument('--input', '-i', help='Input file or directory')
    parser.add_argument('--output', '-o', help='Output file or directory')
    parser.add_argument('--key-file', '-k', help='Encryption key file path')
    parser.add_argument('--delete-original', action='store_true', help='Delete original file after operation')
    parser.add_argument('--verify', action='store_true', help='Verify checksum after decryption')
    parser.add_argument('--checksum', action='store_true', help='Generate checksum during encryption')
    parser.add_argument('--config', default='config.ini', help='Configuration file path')
    parser.add_argument('--all-backups', action='store_true', help='Encrypt/decrypt all files in backup directory')
    
    args = parser.parse_args()
    
    try:
        config = load_config(args.config)
        encrypt_config = config.get('encryption', {})
        default_key_file = encrypt_config.get('key_file', './backup.key')
        key_file = args.key_file or default_key_file
        
        if args.action == 'generate-key':
            key = generate_key()
            save_key(key, key_file)
            print(f'Key generated and saved to: {key_file}')
            return
        
        key = load_key(key_file)
        
        backup_config = config.get('backup', {})
        backup_dir = backup_config.get('backup_dir', './backups')
        
        input_path = args.input
        
        if args.all_backups:
            input_path = backup_dir
        
        if not input_path:
            parser.error('Must specify --input or --all-backups')
        
        if args.action == 'encrypt':
            if os.path.isfile(input_path):
                if args.checksum:
                    encrypt_with_checksum(input_path, key, args.delete_original)
                else:
                    encrypt_file(input_path, key, args.output, args.delete_original)
            elif os.path.isdir(input_path):
                encrypt_directory(input_path, key, args.delete_original)
            else:
                raise FileNotFoundError(f'Input path not found: {input_path}')
        
        elif args.action == 'decrypt':
            if os.path.isfile(input_path):
                if args.verify:
                    decrypt_with_checksum(input_path, key, args.delete_original, args.verify)
                else:
                    decrypt_file(input_path, key, args.output, args.delete_original)
            elif os.path.isdir(input_path):
                decrypt_directory(input_path, key, args.delete_original)
            else:
                raise FileNotFoundError(f'Input path not found: {input_path}')
        
        logger.info('Encryption operation completed successfully')
    except Exception as e:
        logger.error(f'Encryption operation failed: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
