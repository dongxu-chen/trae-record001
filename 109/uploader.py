import os
import logging
import oss2

logger = logging.getLogger(__name__)


class OSSUploader:
    def __init__(self, config):
        self.config = config
        oss_config = config['oss']
        auth = oss2.Auth(oss_config['access_key_id'], oss_config['access_key_secret'])
        self.bucket = oss2.Bucket(auth, oss_config['endpoint'], oss_config['bucket_name'])
        self.directory = oss_config.get('directory', 'backups')
        self.chunk_size = oss_config.get('chunk_size', 10 * 1024 * 1024)

    def upload_file(self, local_file_path):
        try:
            filename = os.path.basename(local_file_path)
            oss_key = f"{self.directory}/{filename}"
            file_size = os.path.getsize(local_file_path)

            logger.info(f"开始上传到OSS: {local_file_path} -> {oss_key} (大小: {file_size / 1024 / 1024:.2f} MB)")

            if file_size > self.chunk_size:
                logger.info(f"使用分片上传，分片大小: {self.chunk_size / 1024 / 1024} MB")
                self._multipart_upload(local_file_path, oss_key)
            else:
                logger.info(f"使用简单上传")
                self.bucket.put_object_from_file(oss_key, local_file_path)

            logger.info(f"OSS上传成功: {oss_key}")
            return True, oss_key
        except Exception as e:
            logger.error(f"OSS上传失败 {local_file_path}: {str(e)}")
            return False, str(e)

    def _multipart_upload(self, local_file_path, oss_key):
        upload_id = None
        parts = []
        part_number = 1

        try:
            res = self.bucket.init_multipart_upload(oss_key)
            upload_id = res.upload_id
            logger.info(f"初始化分片上传，upload_id: {upload_id}")

            with open(local_file_path, 'rb') as f:
                while True:
                    data = f.read(self.chunk_size)
                    if not data:
                        break

                    logger.info(f"上传第 {part_number} 分片，大小: {len(data) / 1024 / 1024:.2f} MB")
                    result = self.bucket.upload_part(oss_key, upload_id, part_number, data)
                    parts.append(oss2.models.PartInfo(part_number, result.etag))
                    part_number += 1

            logger.info(f"完成分片上传，共 {len(parts)} 个分片")
            self.bucket.complete_multipart_upload(oss_key, upload_id, parts)

        except Exception as e:
            if upload_id:
                try:
                    self.bucket.abort_multipart_upload(oss_key, upload_id)
                    logger.warning(f"已取消分片上传，upload_id: {upload_id}")
                except:
                    pass
            raise e

    def upload_files(self, file_paths):
        results = []
        for file_path in file_paths:
            success, result = self.upload_file(file_path)
            results.append({
                'file': file_path,
                'success': success,
                'result': result
            })
        return results

    def list_files(self, prefix=None):
        if prefix is None:
            prefix = self.directory
        files = []
        for obj in oss2.ObjectIterator(self.bucket, prefix=prefix):
            files.append({
                'key': obj.key,
                'last_modified': obj.last_modified,
                'size': obj.size
            })
        return files

    def delete_file(self, oss_key):
        try:
            self.bucket.delete_object(oss_key)
            logger.info(f"OSS删除成功: {oss_key}")
            return True
        except Exception as e:
            logger.error(f"OSS删除失败 {oss_key}: {str(e)}")
            return False
