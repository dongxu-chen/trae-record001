import os
import subprocess
import oss2
from abc import ABC, abstractmethod


class StorageBackend(ABC):
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
        self.priority = config.get('priority', 100)

    @abstractmethod
    def upload(self, local_path, remote_path):
        pass

    @abstractmethod
    def download(self, remote_path, local_path):
        pass

    @abstractmethod
    def list_files(self, prefix=''):
        pass

    @abstractmethod
    def delete(self, remote_path):
        pass

    @abstractmethod
    def exists(self, remote_path):
        pass

    @abstractmethod
    def health_check(self):
        pass


class AliyunOSSStorage(StorageBackend):
    def __init__(self, name, config):
        super().__init__(name, config)
        self.endpoint = config.get('endpoint')
        self.access_key_id = config.get('access_key_id')
        self.access_key_secret = config.get('access_key_secret')
        self.bucket_name = config.get('bucket_name')
        self.prefix = config.get('prefix', '')
        
        auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)

    def _get_full_path(self, remote_path):
        if self.prefix:
            return os.path.join(self.prefix, remote_path).replace('\\', '/')
        return remote_path.replace('\\', '/')

    def upload(self, local_path, remote_path):
        try:
            full_path = self._get_full_path(remote_path)
            self.bucket.put_object_from_file(full_path, local_path)
            return True, f"Uploaded to OSS: {full_path}"
        except Exception as e:
            return False, str(e)

    def download(self, remote_path, local_path):
        try:
            full_path = self._get_full_path(remote_path)
            self.bucket.get_object_to_file(full_path, local_path)
            return True, f"Downloaded from OSS: {full_path}"
        except Exception as e:
            return False, str(e)

    def list_files(self, prefix=''):
        try:
            full_prefix = self._get_full_path(prefix)
            files = []
            for obj in oss2.ObjectIterator(self.bucket, prefix=full_prefix):
                files.append(obj.key)
            return files
        except Exception as e:
            return []

    def delete(self, remote_path):
        try:
            full_path = self._get_full_path(remote_path)
            self.bucket.delete_object(full_path)
            return True, f"Deleted from OSS: {full_path}"
        except Exception as e:
            return False, str(e)

    def exists(self, remote_path):
        try:
            full_path = self._get_full_path(remote_path)
            return self.bucket.object_exists(full_path)
        except Exception:
            return False

    def health_check(self):
        try:
            self.bucket.get_bucket_info()
            return True, "OK"
        except Exception as e:
            return False, str(e)


class TencentCOSStorage(StorageBackend):
    def __init__(self, name, config):
        super().__init__(name, config)
        self.secret_id = config.get('secret_id')
        self.secret_key = config.get('secret_key')
        self.region = config.get('region')
        self.bucket_name = config.get('bucket_name')
        self.prefix = config.get('prefix', '')
        
        try:
            from qcloud_cos import CosConfig, CosS3Client
            cos_config = CosConfig(
                Region=self.region,
                SecretId=self.secret_id,
                SecretKey=self.secret_key
            )
            self.client = CosS3Client(cos_config)
        except ImportError:
            self.client = None

    def _get_full_path(self, remote_path):
        if self.prefix:
            return os.path.join(self.prefix, remote_path).replace('\\', '/')
        return remote_path.replace('\\', '/')

    def upload(self, local_path, remote_path):
        if not self.client:
            return False, "cos-python-sdk-v5 not installed"
        try:
            full_path = self._get_full_path(remote_path)
            self.client.upload_file(
                Bucket=self.bucket_name,
                Key=full_path,
                LocalFilePath=local_path
            )
            return True, f"Uploaded to COS: {full_path}"
        except Exception as e:
            return False, str(e)

    def download(self, remote_path, local_path):
        if not self.client:
            return False, "cos-python-sdk-v5 not installed"
        try:
            full_path = self._get_full_path(remote_path)
            self.client.download_file(
                Bucket=self.bucket_name,
                Key=full_path,
                DestFilePath=local_path
            )
            return True, f"Downloaded from COS: {full_path}"
        except Exception as e:
            return False, str(e)

    def list_files(self, prefix=''):
        if not self.client:
            return []
        try:
            full_prefix = self._get_full_path(prefix)
            files = []
            marker = ''
            while True:
                response = self.client.list_objects(
                    Bucket=self.bucket_name,
                    Prefix=full_prefix,
                    Marker=marker
                )
                for content in response.get('Contents', []):
                    files.append(content['Key'])
                if not response.get('IsTruncated'):
                    break
                marker = response.get('NextMarker')
            return files
        except Exception:
            return []

    def delete(self, remote_path):
        if not self.client:
            return False, "cos-python-sdk-v5 not installed"
        try:
            full_path = self._get_full_path(remote_path)
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=full_path
            )
            return True, f"Deleted from COS: {full_path}"
        except Exception as e:
            return False, str(e)

    def exists(self, remote_path):
        if not self.client:
            return False
        try:
            full_path = self._get_full_path(remote_path)
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=full_path
            )
            return True
        except Exception:
            return False

    def health_check(self):
        if not self.client:
            return False, "cos-python-sdk-v5 not installed"
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            return True, "OK"
        except Exception as e:
            return False, str(e)


class AWSS3Storage(StorageBackend):
    def __init__(self, name, config):
        super().__init__(name, config)
        self.access_key_id = config.get('access_key_id')
        self.secret_access_key = config.get('secret_access_key')
        self.region = config.get('region', 'us-east-1')
        self.bucket_name = config.get('bucket_name')
        self.prefix = config.get('prefix', '')
        
        try:
            import boto3
            self.s3 = boto3.client(
                's3',
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region
            )
        except ImportError:
            self.s3 = None

    def _get_full_path(self, remote_path):
        if self.prefix:
            return os.path.join(self.prefix, remote_path).replace('\\', '/')
        return remote_path.replace('\\', '/')

    def upload(self, local_path, remote_path):
        if not self.s3:
            return False, "boto3 not installed"
        try:
            full_path = self._get_full_path(remote_path)
            self.s3.upload_file(local_path, self.bucket_name, full_path)
            return True, f"Uploaded to S3: {full_path}"
        except Exception as e:
            return False, str(e)

    def download(self, remote_path, local_path):
        if not self.s3:
            return False, "boto3 not installed"
        try:
            full_path = self._get_full_path(remote_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.s3.download_file(self.bucket_name, full_path, local_path)
            return True, f"Downloaded from S3: {full_path}"
        except Exception as e:
            return False, str(e)

    def list_files(self, prefix=''):
        if not self.s3:
            return []
        try:
            full_prefix = self._get_full_path(prefix)
            files = []
            paginator = self.s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=full_prefix):
                for obj in page.get('Contents', []):
                    files.append(obj['Key'])
            return files
        except Exception:
            return []

    def delete(self, remote_path):
        if not self.s3:
            return False, "boto3 not installed"
        try:
            full_path = self._get_full_path(remote_path)
            self.s3.delete_object(Bucket=self.bucket_name, Key=full_path)
            return True, f"Deleted from S3: {full_path}"
        except Exception as e:
            return False, str(e)

    def exists(self, remote_path):
        if not self.s3:
            return False
        try:
            full_path = self._get_full_path(remote_path)
            self.s3.head_object(Bucket=self.bucket_name, Key=full_path)
            return True
        except Exception:
            return False

    def health_check(self):
        if not self.s3:
            return False, "boto3 not installed"
        try:
            self.s3.head_bucket(Bucket=self.bucket_name)
            return True, "OK"
        except Exception as e:
            return False, str(e)


class RcloneStorage(StorageBackend):
    def __init__(self, name, config):
        super().__init__(name, config)
        self.remote_name = config.get('remote_name', 'remote')
        self.remote_path = config.get('remote_path', '')
        self.rclone_path = config.get('rclone_path', 'rclone')

    def _get_remote_url(self, remote_path):
        if self.remote_path:
            return f"{self.remote_name}:{os.path.join(self.remote_path, remote_path)}"
        return f"{self.remote_name}:{remote_path}"

    def upload(self, local_path, remote_path):
        try:
            remote_url = self._get_remote_url(remote_path)
            cmd = [self.rclone_path, 'copy', local_path, os.path.dirname(remote_url)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0, result.stderr or result.stdout
        except Exception as e:
            return False, str(e)

    def download(self, remote_path, local_path):
        try:
            remote_url = self._get_remote_url(remote_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            cmd = [self.rclone_path, 'copy', remote_url, os.path.dirname(local_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0, result.stderr or result.stdout
        except Exception as e:
            return False, str(e)

    def list_files(self, prefix=''):
        try:
            remote_url = self._get_remote_url(prefix)
            cmd = [self.rclone_path, 'lsf', remote_url]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return [line.strip() for line in result.stdout.strip().split('\n') if line]
            return []
        except Exception:
            return []

    def delete(self, remote_path):
        try:
            remote_url = self._get_remote_url(remote_path)
            cmd = [self.rclone_path, 'delete', remote_url]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0, result.stderr or result.stdout
        except Exception as e:
            return False, str(e)

    def exists(self, remote_path):
        try:
            remote_url = self._get_remote_url(remote_path)
            cmd = [self.rclone_path, 'lsf', remote_url]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0 and result.stdout.strip()
        except Exception:
            return False

    def health_check(self):
        try:
            remote_url = f"{self.remote_name}:"
            cmd = [self.rclone_path, 'about', remote_url]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0, "OK" if result.returncode == 0 else result.stderr
        except Exception as e:
            return False, str(e)


class MultiStorageManager:
    def __init__(self, storages_config):
        self.storages = []
        self._initialize_storages(storages_config)

    def _initialize_storages(self, storages_config):
        storage_classes = {
            'aliyun_oss': AliyunOSSStorage,
            'tencent_cos': TencentCOSStorage,
            'aws_s3': AWSS3Storage,
            'rclone': RcloneStorage,
        }
        
        for name, config in storages_config.items():
            storage_type = config.get('type')
            if storage_type in storage_classes:
                storage = storage_classes[storage_type](name, config)
                if storage.enabled:
                    self.storages.append(storage)
        
        self.storages.sort(key=lambda x: x.priority)

    def upload(self, local_path, remote_path):
        results = []
        for storage in self.storages:
            success, msg = storage.upload(local_path, remote_path)
            results.append({
                'storage': storage.name,
                'success': success,
                'message': msg
            })
        
        success_count = sum(1 for r in results if r['success'])
        return success_count > 0, results

    def download(self, remote_path, local_path):
        for storage in self.storages:
            try:
                if storage.exists(remote_path):
                    success, msg = storage.download(remote_path, local_path)
                    if success:
                        return True, f"Downloaded from {storage.name}: {msg}"
            except:
                continue
        
        return False, "File not found in any storage"

    def list_files(self, prefix=''):
        all_files = set()
        for storage in self.storages:
            try:
                files = storage.list_files(prefix)
                all_files.update(files)
            except:
                continue
        return sorted(list(all_files))

    def delete(self, remote_path):
        results = []
        for storage in self.storages:
            success, msg = storage.delete(remote_path)
            results.append({
                'storage': storage.name,
                'success': success,
                'message': msg
            })
        return results

    def exists(self, remote_path):
        for storage in self.storages:
            try:
                if storage.exists(remote_path):
                    return True
            except:
                continue
        return False

    def health_check(self):
        results = []
        for storage in self.storages:
            success, msg = storage.health_check()
            results.append({
                'storage': storage.name,
                'success': success,
                'message': msg
            })
        return results

    def get_available_storage(self):
        available = []
        for storage in self.storages:
            success, _ = storage.health_check()
            if success:
                available.append(storage)
        return available


class StorageFactory:
    @staticmethod
    def get_storage(config):
        storage_type = config.get('type', 'multi')
        
        if storage_type == 'multi':
            return MultiStorageManager(config.get('storages', {}))
        elif storage_type == 'oss':
            return AliyunOSSStorage('default', config.get('oss', {}))
        elif storage_type == 'rclone':
            return RcloneStorage('default', config.get('rclone', {}))
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")
