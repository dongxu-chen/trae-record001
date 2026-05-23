#!/usr/bin/env python3
import os
import sys
import logging
import argparse
import traceback
import io
import threading
from logging.handlers import RotatingFileHandler
from datetime import datetime

from config_loader import ConfigLoader
from backup_engine import BackupEngine
from compressor import Compressor
from sftp_uploader import SFTPUploader
from email_notifier import EmailNotifier
from task_scheduler import TaskScheduler
from encryption import Encryptor
from database import BackupDatabase


def setup_logging(log_file: str, log_level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("backup_tool")
    logger.setLevel(getattr(logging, log_level.upper()))

    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    return logger


class BackupTool:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.load()
        
        self.logger = setup_logging(
            self.config.global_config.log_file,
            self.config.global_config.log_level
        )

        self.backup_engine = BackupEngine(
            temp_dir=self.config.global_config.temp_dir,
            logger=self.logger
        )
        self.compressor = Compressor(
            temp_dir=self.config.global_config.temp_dir,
            logger=self.logger
        )
        self.email_notifier = EmailNotifier(
            enabled=self.config.email.enabled,
            smtp_server=self.config.email.smtp_server,
            smtp_port=self.config.email.smtp_port,
            smtp_username=self.config.email.smtp_username,
            smtp_password=self.config.email.smtp_password,
            use_tls=self.config.email.use_tls,
            sender=self.config.email.sender,
            recipients=self.config.email.recipients,
            logger=self.logger
        )
        self.scheduler = TaskScheduler(logger=self.logger)
        self.encryptor = Encryptor(logger=self.logger)
        self.db = BackupDatabase()
        self.sftp_uploader = None

    def _get_sftp_uploader(self) -> SFTPUploader:
        if not self.sftp_uploader:
            self.sftp_uploader = SFTPUploader(
                host=self.config.sftp.host,
                port=self.config.sftp.port,
                username=self.config.sftp.username,
                password=self.config.sftp.password,
                remote_base_dir=self.config.sftp.remote_base_dir,
                logger=self.logger
            )
        return self.sftp_uploader

    def execute_backup_task(self, task_name: str) -> None:
        task = next((t for t in self.config.backup_tasks if t.name == task_name), None)
        if not task:
            self.logger.error(f"未找到备份任务: {task_name}")
            return

        if not task.enabled:
            self.logger.info(f"备份任务已禁用: {task_name}")
            return

        self.logger.info(f"开始执行备份任务: {task_name}")
        
        backup_time = datetime.now().timestamp()
        deleted_old_backups = 0
        freed_space = 0
        record_id = None
        md5_hash = None
        remote_path = None

        try:
            record_id = self.db.record_backup_start(task_name, task.backup_type, task.source_dir)

            sftp = self._get_sftp_uploader()
            sftp.connect()

            files_to_backup, total_files, unchanged_files = self.backup_engine.get_files_to_backup(
                source_dir=task.source_dir,
                backup_type=task.backup_type,
                task_name=task_name,
                exclude_patterns=task.exclude_patterns,
                sftp_uploader=sftp
            )

            if not files_to_backup:
                self.logger.info(f"没有需要备份的文件，跳过备份: {task_name}")
                self.db.record_backup_success(
                    record_id, 0, total_files, 0, 0, 0, '', ''
                )
                return

            backup_filename = self.backup_engine.generate_backup_filename(
                task_name=task_name,
                backup_type=task.backup_type
            )

            if task.compression:
                remote_dir = f"{sftp.remote_base_dir}/{task_name}"
                sftp.ensure_remote_dir(remote_dir)
                
                file_extension = ".tar.gz"
                if self.encryptor.is_available():
                    file_extension += ".gpg"
                    backup_filename += "_encrypted"
                
                remote_path = f"{remote_dir}/{backup_filename}{file_extension}"

                compressed_data = io.BytesIO()
                
                with __import__('tarfile').open(fileobj=compressed_data, mode='w:gz') as tar:
                    source_path = __import__('pathlib').Path(task.source_dir)
                    if task.backup_type == 'incremental':
                        for file_path in files_to_backup:
                            full_path = __import__('pathlib').Path(file_path)
                            if full_path.exists():
                                arcname = str(full_path.relative_to(source_path.parent))
                                tar.add(full_path, arcname=arcname)
                    else:
                        import fnmatch
                        for root, dirs, files in os.walk(task.source_dir):
                            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(os.path.join(root, d), p) for p in task.exclude_patterns)]
                            for file in files:
                                file_path = os.path.join(root, file)
                                if any(fnmatch.fnmatch(file_path, p) for p in task.exclude_patterns):
                                    continue
                                full_path = __import__('pathlib').Path(file_path)
                                arcname = str(full_path.relative_to(source_path.parent))
                                tar.add(full_path, arcname=arcname)
                
                compressed_size = compressed_data.tell()
                compressed_data.seek(0)

                if self.encryptor.is_available():
                    self.logger.info("启用GPG加密")
                    compressed_data = self.encryptor.encrypt_stream(compressed_data)
                    compressed_size = compressed_data.getbuffer().nbytes

                md5_hash, _ = self.encryptor.calculate_stream_md5(compressed_data)
                self.logger.info(f"本地文件MD5: {md5_hash}")

                upload_success = sftp.stream_upload_with_verification(
                    compressed_data, remote_path, md5_hash, max_retries=3
                )

                if not upload_success:
                    raise RuntimeError("文件上传失败，MD5校验不通过")

                self.logger.info(f"备份上传完成: {remote_path}, 大小: {compressed_size / (1024*1024):.2f} MB")
            else:
                self.logger.warning("未启用压缩，跳过压缩步骤")
                return

            deleted_old_backups, freed_space = sftp.cleanup_old_backups(task_name, task.retention_days)

            backup_summary = self.backup_engine.get_backup_summary(
                task_name=task_name,
                source_dir=task.source_dir,
                backup_type=task.backup_type,
                files_backed_up=len(files_to_backup),
                total_files=total_files,
                unchanged_files=len(unchanged_files),
                archive_size=compressed_size,
                deleted_old_backups=deleted_old_backups,
                freed_space=freed_space
            )

            self.db.record_backup_success(
                record_id,
                len(files_to_backup),
                total_files,
                backup_summary['archive_size_mb'],
                deleted_old_backups,
                backup_summary['freed_space_mb'],
                md5_hash,
                remote_path
            )

            self.backup_engine.record_backup_success(task_name, backup_time)

            self.email_notifier.send_backup_success(backup_summary)

            self.logger.info(f"备份任务完成: {task_name}")

        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.logger.error(f"备份任务失败 {task_name}: {error_msg}")
            if record_id:
                self.db.record_backup_failure(record_id, str(e))
            try:
                task_type = task.backup_type if task else "未知"
                self.email_notifier.send_backup_failure(task_name, str(e), task_type)
            except:
                pass
        finally:
            if self.sftp_uploader:
                self.sftp_uploader.disconnect()
                self.sftp_uploader = None

    def schedule_tasks(self) -> None:
        enabled_tasks = self.config_loader.get_enabled_tasks()
        self.logger.info(f"发现 {len(enabled_tasks)} 个启用的备份任务")

        for task in enabled_tasks:
            self.scheduler.add_job(
                job_id=task.name,
                func=self.execute_backup_task,
                cron_expression=task.cron,
                args=(task.name,)
            )

    def run_scheduler(self) -> None:
        self.schedule_tasks()
        self.scheduler.run_forever()

    def run_task_now(self, task_name: str) -> None:
        self.execute_backup_task(task_name)

    def pause_task(self, task_name: str) -> None:
        if self.scheduler.pause_job(task_name):
            print(f"✅ 任务 {task_name} 已暂停")
        else:
            print(f"❌ 暂停任务 {task_name} 失败")

    def resume_task(self, task_name: str) -> None:
        if self.scheduler.resume_job(task_name):
            print(f"✅ 任务 {task_name} 已恢复")
        else:
            print(f"❌ 恢复任务 {task_name} 失败")

    def list_tasks(self) -> None:
        print("\n备份任务列表:")
        print("-" * 80)
        for task in self.config.backup_tasks:
            status = "启用" if task.enabled else "禁用"
            backup_type = "全量" if task.backup_type == "full" else "增量"
            print(f"任务名称: {task.name}")
            print(f"  状态: {status}")
            print(f"  源目录: {task.source_dir}")
            print(f"  备份类型: {backup_type}")
            print(f"  Cron表达式: {task.cron}")
            print(f"  保留天数: {task.retention_days} 天")
            print("-" * 80)

    def show_status(self) -> None:
        if not self.scheduler.scheduler.running:
            print("调度器未运行")
            return
        
        jobs = self.scheduler.list_jobs()
        print("\n调度器状态:")
        print("-" * 80)
        if not jobs:
            print("没有定时任务")
        else:
            for job in jobs:
                status = "⏸️ 暂停" if job['paused'] else "▶️ 运行中"
                print(f"任务: {job['id']}")
                print(f"  状态: {status}")
                print(f"  下次执行: {job['next_run_time']}")
                print("-" * 80)

    def start_web_server(self, host='0.0.0.0', port=5000):
        from web_app import run_web_server
        self.logger.info(f"启动Web管理界面: http://{host}:{port}")
        run_web_server(host, port)


def main():
    parser = argparse.ArgumentParser(description="自动化数据备份工具")
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)"
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="列出所有备份任务"
    )
    parser.add_argument(
        "-r", "--run",
        metavar="TASK_NAME",
        help="立即执行指定的备份任务"
    )
    parser.add_argument(
        "-s", "--schedule",
        action="store_true",
        help="启动定时任务调度器"
    )
    parser.add_argument(
        "--pause",
        metavar="TASK_NAME",
        help="暂停指定的备份任务"
    )
    parser.add_argument(
        "--resume",
        metavar="TASK_NAME",
        help="恢复指定的备份任务"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="显示调度器状态"
    )
    parser.add_argument(
        "-w", "--web",
        action="store_true",
        help="启动Web管理界面"
    )
    parser.add_argument(
        "--web-host",
        default="0.0.0.0",
        help="Web服务器监听地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=5000,
        help="Web服务器端口 (默认: 5000)"
    )
    parser.add_argument(
        "--web-and-schedule",
        action="store_true",
        help="同时启动Web管理界面和任务调度器"
    )

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        return

    try:
        tool = BackupTool(args.config)

        if args.list:
            tool.list_tasks()
        elif args.run:
            tool.run_task_now(args.run)
        elif args.schedule:
            tool.run_scheduler()
        elif args.web:
            tool.start_web_server(args.web_host, args.web_port)
        elif args.web_and_schedule:
            web_thread = threading.Thread(
                target=tool.start_web_server,
                args=(args.web_host, args.web_port),
                daemon=True
            )
            web_thread.start()
            tool.run_scheduler()
        elif args.pause:
            tool.schedule_tasks()
            tool.scheduler.start()
            tool.pause_task(args.pause)
        elif args.resume:
            tool.schedule_tasks()
            tool.scheduler.start()
            tool.resume_task(args.resume)
        elif args.status:
            tool.schedule_tasks()
            tool.scheduler.start()
            tool.show_status()

    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"发生错误: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
