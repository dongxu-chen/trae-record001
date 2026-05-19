import yaml
import logging
import os
import sys
from backup import DatabaseBackup
from uploader import OSSUploader
from notifier import DingTalkNotifier
from cleanup import BackupCleanup
from reporter import BackupReporter


def setup_logging():
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler('backup.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def load_config(config_path='config.yaml'):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logging.error(f"加载配置文件失败: {str(e)}")
        sys.exit(1)


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("数据库备份巡检器启动")
    logger.info("=" * 60)

    config = load_config()

    backup = DatabaseBackup(config)
    oss_uploader = OSSUploader(config)
    notifier = DingTalkNotifier(config)
    cleanup = BackupCleanup(config)
    reporter = BackupReporter(config)

    logger.info("步骤1: 开始数据库备份")
    backup_files = backup.backup_all()
    if not backup_files:
        logger.warning("没有生成任何备份文件")

    logger.info("步骤2: 开始备份验证")
    verify_results = []
    if config['backup'].get('enable_verify', True):
        for backup_file in backup_files:
            if 'binlog' not in backup_file and 'incremental' not in backup_file:
                db_type = 'mysql' if 'mysql' in backup_file else 'postgresql'
                result = backup.verify_backup(backup_file, db_type)
                result['file'] = backup_file
                verify_results.append(result)

    logger.info("步骤3: 开始上传到OSS")
    upload_results = oss_uploader.upload_files(backup_files)

    logger.info("步骤4: 开始清理过期备份")
    cleanup_results = cleanup.cleanup_all(oss_uploader)

    logger.info("步骤5: 生成巡检报告")
    report_file = reporter.generate_report(backup_files, upload_results, cleanup_results, verify_results)

    logger.info("步骤6: 发送邮件报告")
    reporter.send_email(report_file, backup_files, verify_results)

    logger.info("步骤7: 发送钉钉通知")
    notifier.send_backup_result(backup_files, upload_results, cleanup_results, verify_results)

    logger.info("=" * 60)
    logger.info("数据库备份巡检完成")
    logger.info(f"报告文件: {report_file}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
