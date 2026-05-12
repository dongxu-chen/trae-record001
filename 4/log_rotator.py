#!/usr/bin/env python3
"""
Docker 日志轮转压缩脚本
功能：按大小/时间轮转日志文件，压缩归档，清理过期日志
"""

import os
import sys
import gzip
import time
import shutil
import zipfile
import signal
import logging
import argparse
import schedule
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

try:
    import yaml
except ImportError as e:
    print(f"缺少依赖库: {e.name}")
    print("请运行: pip install pyyaml schedule")
    sys.exit(1)


class LogRotator:
    """日志轮转器"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.running = False
        self._setup_logging()

    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"配置文件不存在: {config_path}")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"配置文件解析错误: {e}")
            sys.exit(1)

    def _setup_logging(self):
        """设置脚本自身的日志"""
        sys_cfg = self.config.get("system_log", {})
        log_dir = Path(sys_cfg.get("directory", "./system_logs"))
        log_dir.mkdir(parents=True, exist_ok=True)

        log_level = self.config["log_rotator"].get("log_level", "INFO")
        log_file = log_dir / "log_rotator.log"

        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format=sys_cfg.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger("LogRotator")

    def _get_log_files(self) -> List[Path]:
        """获取日志目录中的所有日志文件（支持主机子目录）"""
        rotator_cfg = self.config["log_rotator"]
        log_dir = Path(rotator_cfg.get("log_dir", "./logs"))

        if not log_dir.exists():
            self.logger.warning(f"日志目录不存在: {log_dir}")
            return []

        log_files = []

        for item in log_dir.iterdir():
            if item.is_file() and item.suffix in [".log", ".txt"]:
                log_files.append(item)
            elif item.is_dir():
                for sub_item in item.iterdir():
                    if sub_item.is_file() and sub_item.suffix in [".log", ".txt"]:
                        log_files.append(sub_item)

        self.logger.info(f"找到 {len(log_files)} 个日志文件（含主机子目录）")
        return log_files

    def _get_file_size_mb(self, file_path: Path) -> float:
        """获取文件大小（MB）"""
        return file_path.stat().st_size / (1024 * 1024)

    def _compress_file(self, src_file: Path) -> Path:
        """压缩文件"""
        rotator_cfg = self.config["log_rotator"]
        compress_format = rotator_cfg.get("compress_format", "gzip")
        dst_file = src_file.with_suffix(src_file.suffix + f".{compress_format}")

        self.logger.info(f"正在压缩文件: {src_file.name} -> {dst_file.name}")

        max_retries = rotator_cfg.get("compress_retries", 3)
        retry_delay = rotator_cfg.get("compress_retry_delay", 2)

        for attempt in range(1, max_retries + 1):
            try:
                if compress_format == "gzip":
                    with open(src_file, "rb") as f_in:
                        with gzip.open(dst_file, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                elif compress_format == "zip":
                    with zipfile.ZipFile(dst_file, "w", zipfile.ZIP_DEFLATED) as zf:
                        zf.write(src_file, src_file.name)
                else:
                    self.logger.warning(f"不支持的压缩格式: {compress_format}")
                    return src_file

                src_file.unlink()
                self.logger.info(f"压缩完成: {dst_file.name}")
                return dst_file
            except PermissionError as e:
                if attempt < max_retries:
                    self.logger.warning(
                        f"压缩文件被占用，第 {attempt}/{max_retries} 次重试: {src_file.name}，等待 {retry_delay} 秒"
                    )
                    time.sleep(retry_delay)
                else:
                    self.logger.error(
                        f"压缩失败，文件持续被占用 {max_retries} 次: {src_file.name}"
                    )
                    return src_file
            except Exception as e:
                self.logger.error(f"压缩失败 {src_file.name}: {e}")
                return src_file

        return src_file

    def _rotate_by_size(self, log_file: Path) -> bool:
        """按文件大小轮转（使用 copy-truncate 策略避免文件占用问题）"""
        rotator_cfg = self.config["log_rotator"]
        max_size = rotator_cfg.get("max_file_size", 10)
        file_size = self._get_file_size_mb(log_file)

        if file_size < max_size:
            return False

        self.logger.info(f"文件 {log_file.name} 大小 {file_size:.2f}MB 超过阈值 {max_size}MB，执行轮转")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_name = f"{log_file.stem}_{timestamp}{log_file.suffix}"
        rotated_file = log_file.with_name(rotated_name)

        max_retries = rotator_cfg.get("rotate_retries", 3)
        retry_delay = rotator_cfg.get("rotate_retry_delay", 1)

        for attempt in range(1, max_retries + 1):
            try:
                shutil.copy2(str(log_file), str(rotated_file))

                with open(log_file, "w", encoding="utf-8") as f:
                    f.truncate(0)

                self.logger.info(f"copy-truncate 完成: {log_file.name} -> {rotated_file.name}")

                if rotator_cfg.get("compress", True):
                    self._compress_file(rotated_file)

                return True
            except PermissionError as e:
                if attempt < max_retries:
                    self.logger.warning(
                        f"文件被占用，第 {attempt}/{max_retries} 次重试: {log_file.name}，等待 {retry_delay} 秒"
                    )
                    time.sleep(retry_delay)
                else:
                    self.logger.error(
                        f"轮转失败，文件持续被占用 {max_retries} 次: {log_file.name}"
                    )
                    if rotated_file.exists():
                        try:
                            rotated_file.unlink()
                        except:
                            pass
                    return False
            except Exception as e:
                self.logger.error(f"轮转失败 {log_file.name}: {e}")
                if rotated_file.exists():
                    try:
                        rotated_file.unlink()
                    except:
                        pass
                return False

        return False

    def _rotate_by_count(self, log_file: Path) -> bool:
        """按文件数量轮转（清理旧文件，支持主机子目录）"""
        rotator_cfg = self.config["log_rotator"]
        max_count = rotator_cfg.get("max_file_count", 5)
        log_dir = log_file.parent
        stem = log_file.stem

        all_versions = sorted(
            [f for f in log_dir.glob(f"{stem}_*") if not f.name.endswith("~")],
            key=lambda x: x.stat().st_mtime
        )

        while len(all_versions) > max_count:
            old_file = all_versions.pop(0)
            try:
                old_file.unlink()
                self.logger.info(f"删除过期文件: {old_file.name}")
            except Exception as e:
                self.logger.error(f"删除文件失败 {old_file.name}: {e}")

        return True

    def _cleanup_old_archives(self):
        """按保留天数清理归档文件（支持主机子目录递归）"""
        rotator_cfg = self.config["log_rotator"]
        retention_days = rotator_cfg.get("retention_days", 30)
        log_dir = Path(rotator_cfg.get("log_dir", "./logs"))

        if not log_dir.exists():
            return

        cutoff_time = time.time() - (retention_days * 24 * 3600)

        def cleanup_directory(directory: Path):
            for f in directory.iterdir():
                if f.is_file():
                    suffixes = f.suffixes
                    if len(suffixes) >= 2 and suffixes[-1] in [".gz", ".zip"]:
                        if f.stat().st_mtime < cutoff_time:
                            try:
                                f.unlink()
                                self.logger.info(f"清理过期归档: {f.relative_to(log_dir)}")
                            except Exception as e:
                                self.logger.error(f"清理归档失败 {f.name}: {e}")
                elif f.is_dir():
                    cleanup_directory(f)

        cleanup_directory(log_dir)

    def rotate_all(self):
        """执行一次完整的轮转检查"""
        self.logger.info("开始日志轮转检查")

        log_files = self._get_log_files()
        rotated_count = 0

        for log_file in log_files:
            if self._rotate_by_size(log_file):
                rotated_count += 1
            self._rotate_by_count(log_file)

        self._cleanup_old_archives()
        self.logger.info(f"轮转检查完成，轮转了 {rotated_count} 个文件")

    def start_scheduler(self):
        """启动定时调度器"""
        rotator_cfg = self.config["log_rotator"]
        rotation_interval = rotator_cfg.get("rotation_interval", "daily")
        cleanup_interval = rotator_cfg.get("cleanup_interval", 3600)

        self.logger.info(f"启动日志轮转调度器，间隔: {rotation_interval}")

        if rotation_interval == "hourly":
            schedule.every().hour.do(self.rotate_all)
        elif rotation_interval == "daily":
            schedule.every().day.at("00:00").do(self.rotate_all)
        elif rotation_interval == "weekly":
            schedule.every().monday.at("00:00").do(self.rotate_all)
        else:
            self.logger.warning(f"未知的轮转间隔: {rotation_interval}，使用默认 hourly")
            schedule.every().hour.do(self.rotate_all)

        schedule.every(cleanup_interval).seconds.do(self._cleanup_old_archives)

        self.running = True

        def handle_signal(signum, frame):
            self.logger.info("收到停止信号，正在优雅退出...")
            self.running = False
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        self.logger.info("调度器已启动，按 Ctrl+C 退出")

        while self.running:
            schedule.run_pending()
            time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description="Docker 日志轮转压缩工具")
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="配置文件路径（默认: config.yaml）"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="仅执行一次轮转检查后退出"
    )
    parser.add_argument(
        "-d", "--daemon",
        action="store_true",
        help="以守护进程方式运行定时轮转"
    )
    args = parser.parse_args()

    rotator = LogRotator(config_path=args.config)

    if args.once:
        rotator.rotate_all()
    else:
        rotator.start_scheduler()


if __name__ == "__main__":
    main()
