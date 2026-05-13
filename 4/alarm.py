#!/usr/bin/env python3
"""
Docker 日志错误报警脚本
功能：监控日志文件中的错误关键字，触发多渠道报警
"""

import os
import sys
import time
import smtplib
import signal
import logging
import argparse
import threading
import requests
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from collections import defaultdict, deque
from typing import List, Dict, Any

try:
    import yaml
except ImportError as e:
    print(f"缺少依赖库: {e.name}")
    print("请运行: pip install pyyaml requests")
    sys.exit(1)


class Alarm:
    """日志错误报警器"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.running = False
        self._setup_logging()
        self._init_alarm_state()

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

        log_level = self.config["alarm"].get("log_level", "INFO")
        log_file = log_dir / "alarm.log"

        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format=sys_cfg.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger("Alarm")

    def _init_alarm_state(self):
        """初始化报警状态"""
        alarm_cfg = self.config["alarm"]
        self.error_keywords = alarm_cfg.get(
            "error_keywords",
            ["ERROR", "Exception", "Traceback", "FATAL", "CRITICAL"]
        )
        self.error_threshold = alarm_cfg.get("error_threshold", 5)
        self.cooldown_period = alarm_cfg.get("cooldown_period", 300)

        self.file_positions: Dict[str, int] = {}
        self.error_counts: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.error_threshold)
        )
        self.last_alarm_time: Dict[str, float] = defaultdict(float)

    def _get_log_files(self) -> List[Path]:
        """获取日志目录中的所有日志文件"""
        alarm_cfg = self.config["alarm"]
        log_dir = Path(alarm_cfg.get("log_dir", "./logs"))

        if not log_dir.exists():
            self.logger.warning(f"日志目录不存在: {log_dir}")
            return []

        log_files = []
        for f in log_dir.iterdir():
            if f.is_file() and f.suffix in [".log", ".txt"]:
                log_files.append(f)

        return log_files

    def _check_line_for_errors(self, line: str) -> List[str]:
        """检查一行日志中是否包含错误关键字"""
        found_errors = []
        line_lower = line.lower()
        for keyword in self.error_keywords:
            if keyword.lower() in line_lower:
                found_errors.append(keyword)
        return found_errors

    def _should_alert(self, file_name: str) -> bool:
        """判断是否需要触发报警"""
        now = time.time()
        last_time = self.last_alarm_time.get(file_name, 0)

        if now - last_time < self.cooldown_period:
            return False

        error_times = self.error_counts[file_name]
        if len(error_times) >= self.error_threshold:
            return True

        return False

    def _record_error(self, file_name: str):
        """记录一次错误"""
        self.error_counts[file_name].append(time.time())

    def _send_console_alert(self, message: str, details: Dict[str, Any]):
        """发送控制台报警"""
        channels = self.config["alarm"].get("channels", {})
        console_cfg = channels.get("console", {})

        if not console_cfg.get("enabled", True):
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alert_msg = (
            f"\n{'='*60}\n"
            f"[ALARM] {timestamp}\n"
            f"容器: {details.get('container', 'unknown')}\n"
            f"错误类型: {details.get('error_type', 'unknown')}\n"
            f"错误计数: {details.get('error_count', 0)}\n"
            f"消息: {message}\n"
            f"{'='*60}\n"
        )
        print(alert_msg)
        self.logger.warning(f"报警已输出到控制台: {details.get('container')}")

    def _send_email_alert(self, message: str, details: Dict[str, Any]):
        """发送邮件报警"""
        channels = self.config["alarm"].get("channels", {})
        email_cfg = channels.get("email", {})

        if not email_cfg.get("enabled", False):
            return

        try:
            subject_prefix = email_cfg.get("subject_prefix", "[DOCKER-LOG-ALARM]")
            subject = f"{subject_prefix} {details.get('container', 'unknown')} - {details.get('error_type', 'Error')}"

            body = f"""
Docker 容器日志报警
====================

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
容器: {details.get('container', 'unknown')}
错误类型: {details.get('error_type', 'unknown')}
错误计数: {details.get('error_count', 0)}

详细信息:
{message}

请尽快检查相关容器状态。
"""

            msg = MIMEMultipart()
            msg["From"] = email_cfg["from_email"]
            msg["To"] = ", ".join(email_cfg.get("to_email", []))
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP(email_cfg["smtp_server"], email_cfg.get("smtp_port", 587)) as server:
                server.starttls()
                server.login(email_cfg["smtp_username"], email_cfg["smtp_password"])
                server.sendmail(
                    email_cfg["from_email"],
                    email_cfg.get("to_email", []),
                    msg.as_string()
                )

            self.logger.info(f"邮件报警已发送到: {email_cfg.get('to_email', [])}")
        except Exception as e:
            self.logger.error(f"发送邮件报警失败: {e}")

    def _send_webhook_alert(self, message: str, details: Dict[str, Any]):
        """发送 Webhook 报警（带指数退避重试机制）"""
        channels = self.config["alarm"].get("channels", {})
        webhook_cfg = channels.get("webhook", {})

        if not webhook_cfg.get("enabled", False):
            return

        max_retries = webhook_cfg.get("max_retries", 3)
        base_retry_delay = webhook_cfg.get("retry_delay", 2)
        retryable_status_codes = webhook_cfg.get(
            "retryable_status_codes",
            [429, 500, 502, 503, 504]
        )

        payload = {
            "timestamp": datetime.now().isoformat(),
            "level": "critical",
            "source": "docker-log-alarm",
            "container": details.get("container", "unknown"),
            "error_type": details.get("error_type", "unknown"),
            "error_count": details.get("error_count", 0),
            "message": message
        }

        url = webhook_cfg["url"]
        method = webhook_cfg.get("method", "POST")
        headers = webhook_cfg.get("headers", {"Content-Type": "application/json"})
        timeout = webhook_cfg.get("timeout", 10)

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=data,
                    timeout=timeout
                )

                if 200 <= response.status_code < 300:
                    self.logger.info(
                        f"Webhook 报警发送成功 (第 {attempt} 次尝试): {url}"
                    )
                    return

                if response.status_code in retryable_status_codes and attempt < max_retries:
                    delay = min(base_retry_delay * (2 ** (attempt - 1)), 30)
                    self.logger.warning(
                        f"Webhook 返回 {response.status_code}，第 {attempt}/{max_retries} 次重试，等待 {delay} 秒: {url}"
                    )
                    time.sleep(delay)
                    continue

                self.logger.warning(
                    f"Webhook 报警失败，状态码 {response.status_code}: {url}"
                )
                return

            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries:
                    delay = min(base_retry_delay * (2 ** (attempt - 1)), 30)
                    self.logger.warning(
                        f"Webhook 连接错误，第 {attempt}/{max_retries} 次重试，等待 {delay} 秒: {url}"
                    )
                    time.sleep(delay)
                    continue
                self.logger.error(f"Webhook 连接失败（已重试 {max_retries} 次）: {url}, 错误: {e}")
                return

            except requests.exceptions.Timeout as e:
                if attempt < max_retries:
                    delay = min(base_retry_delay * (2 ** (attempt - 1)), 30)
                    self.logger.warning(
                        f"Webhook 超时，第 {attempt}/{max_retries} 次重试，等待 {delay} 秒: {url}"
                    )
                    time.sleep(delay)
                    continue
                self.logger.error(f"Webhook 超时（已重试 {max_retries} 次）: {url}, 错误: {e}")
                return

            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    delay = min(base_retry_delay * (2 ** (attempt - 1)), 30)
                    self.logger.warning(
                        f"Webhook 请求异常，第 {attempt}/{max_retries} 次重试，等待 {delay} 秒: {url}"
                    )
                    time.sleep(delay)
                    continue
                self.logger.error(f"Webhook 请求失败（已重试 {max_retries} 次）: {url}, 错误: {e}")
                return

    def _send_alert(self, message: str, details: Dict[str, Any]):
        """发送报警（所有启用的渠道）"""
        file_name = details.get("container", "unknown")
        self.last_alarm_time[file_name] = time.time()

        self._send_console_alert(message, details)
        self._send_email_alert(message, details)
        self._send_webhook_alert(message, details)

    def _scan_log_file(self, log_file: Path):
        """扫描单个日志文件"""
        file_name = log_file.name
        container_name = log_file.stem

        try:
            file_size = log_file.stat().st_size

            if file_name not in self.file_positions:
                self.file_positions[file_name] = file_size
                return

            old_pos = self.file_positions[file_name]

            if file_size < old_pos:
                self.file_positions[file_name] = 0
                old_pos = 0

            if file_size == old_pos:
                return

            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                f.seek(old_pos)
                new_content = f.read()
                self.file_positions[file_name] = f.tell()

            lines = new_content.strip().split("\n")
            error_lines = []

            for line in lines:
                if not line.strip():
                    continue

                errors = self._check_line_for_errors(line)
                if errors:
                    self._record_error(file_name)
                    error_lines.append({
                        "keyword": errors[0],
                        "line": line[:200]
                    })

            if error_lines:
                self.logger.info(
                    f"在 {container_name} 中发现 {len(error_lines)} 条错误日志"
                )

                if self._should_alert(file_name):
                    error_msg = "\n".join(
                        [f"[{e['keyword']}] {e['line']}" for e in error_lines[:5]]
                    )
                    self._send_alert(
                        message=error_msg,
                        details={
                            "container": container_name,
                            "error_type": error_lines[0]["keyword"],
                            "error_count": len(self.error_counts[file_name])
                        }
                    )
                    self.error_counts[file_name].clear()

        except Exception as e:
            self.logger.error(f"扫描日志文件 {file_name} 出错: {e}")

    def scan_once(self):
        """执行一次完整扫描"""
        log_files = self._get_log_files()
        if not log_files:
            return

        threads = []
        for log_file in log_files:
            t = threading.Thread(
                target=self._scan_log_file,
                args=(log_file,),
                daemon=True
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

    def start_monitoring(self):
        """启动持续监控"""
        alarm_cfg = self.config["alarm"]
        scan_interval = alarm_cfg.get("scan_interval", 60)

        self.running = True
        self.logger.info(f"启动日志监控，扫描间隔: {scan_interval} 秒")

        def handle_signal(signum, frame):
            self.logger.info("收到停止信号，正在优雅退出...")
            self.running = False
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        self.logger.info("监控器已启动，按 Ctrl+C 退出")

        while self.running:
            self.scan_once()
            time.sleep(scan_interval)


def main():
    parser = argparse.ArgumentParser(description="Docker 日志错误报警工具")
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="配置文件路径（默认: config.yaml）"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="仅执行一次扫描后退出"
    )
    parser.add_argument(
        "-d", "--daemon",
        action="store_true",
        help="以守护进程方式持续监控"
    )
    args = parser.parse_args()

    alarm = Alarm(config_path=args.config)

    if args.once:
        alarm.scan_once()
    else:
        alarm.start_monitoring()


if __name__ == "__main__":
    main()
