import os
import datetime
import logging
import re

logger = logging.getLogger(__name__)


class BackupCleanup:
    def __init__(self, config):
        self.config = config
        self.local_dir = config['backup']['local_dir']
        self.retention_days = config['backup']['retention_days']
        self.cutoff_time = datetime.datetime.now() - datetime.timedelta(days=self.retention_days)

    def cleanup_local(self):
        cleaned_files = []
        if not os.path.exists(self.local_dir):
            return cleaned_files

        try:
            for filename in os.listdir(self.local_dir):
                filepath = os.path.join(self.local_dir, filename)
                if not os.path.isfile(filepath):
                    continue

                file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))

                if file_mtime < self.cutoff_time:
                    try:
                        os.remove(filepath)
                        cleaned_files.append(f"local: {filename}")
                        logger.info(f"清理本地过期备份: {filename}")
                    except Exception as e:
                        logger.error(f"清理本地文件失败 {filename}: {str(e)}")
        except Exception as e:
            logger.error(f"本地清理异常: {str(e)}")

        return cleaned_files

    def cleanup_oss(self, oss_uploader):
        cleaned_files = []
        try:
            files = oss_uploader.list_files()
            for file_info in files:
                last_modified = file_info['last_modified']
                if isinstance(last_modified, (int, float)):
                    file_time = datetime.datetime.fromtimestamp(last_modified)
                else:
                    file_time = last_modified

                if file_time < self.cutoff_time:
                    if oss_uploader.delete_file(file_info['key']):
                        cleaned_files.append(f"oss: {file_info['key']}")
                        logger.info(f"清理OSS过期备份: {file_info['key']}")
        except Exception as e:
            logger.error(f"OSS清理异常: {str(e)}")

        return cleaned_files

    def cleanup_all(self, oss_uploader=None):
        all_cleaned = []
        all_cleaned.extend(self.cleanup_local())
        if oss_uploader:
            all_cleaned.extend(self.cleanup_oss(oss_uploader))
        return all_cleaned
