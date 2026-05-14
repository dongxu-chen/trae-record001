#!/usr/bin/env python3
import json
import hmac
import hashlib
import logging
import threading
import subprocess
import configparser
import os
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse

try:
    from http.server import HTTPServer, BaseHTTPRequestHandler
except ImportError:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler


class WebhookHandler(BaseHTTPRequestHandler):
    server: "WebhookServer"

    def _log(self, message: str, level: str = "info"):
        if self.server.logger:
            log_method = getattr(self.server.logger, level, self.server.logger.info)
            log_method(message)

    def _send_response(
        self,
        status_code: int,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ):
        response = {
            "status": "success" if status_code < 400 else "error",
            "message": message,
        }
        if data:
            response.update(data)

        response_bytes = json.dumps(response, ensure_ascii=False).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def _verify_signature(self, body: bytes) -> bool:
        if not self.server.secret:
            return True

        signature_header = self.headers.get("X-Hub-Signature-256") or \
                        self.headers.get("X-Hub-Signature") or \
                        self.headers.get("X-Gitlab-Token")

        if not signature_header:
            self._log("缺少签名头", level="warning")
            return False

        if self.server.platform == "github" and signature_header:
            if signature_header.startswith("sha256="):
                expected = "sha256=" + hmac.new(
                    self.server.secret.encode(),
                    body,
                    hashlib.sha256
                ).hexdigest()
                return hmac.compare_digest(signature_header, expected)
            elif signature_header.startswith("sha1="):
                expected = "sha1=" + hmac.new(
                    self.server.secret.encode(),
                    body,
                    hashlib.sha1
                ).hexdigest()
                return hmac.compare_digest(signature_header, expected)

        if self.server.platform == "gitlab" and signature_header:
            return hmac.compare_digest(signature_header, self.server.secret)

        return True

    def do_POST(self):
        path = self.path.rstrip("/")
        
        if path != self.server.endpoint:
            self._send_response(404, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if not self._verify_signature(body):
            self._log("签名验证失败", level="warning")
            self._send_response(403, "签名验证失败")
            return

        event_type = self.headers.get("X-GitHub-Event") or \
                    self.headers.get("X-Gitlab-Event") or "push"

        self._log(f"收到 webhook 请求: {event_type}")

        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._log("无效的 JSON 格式", level="error")
            self._send_response(400, "无效的 JSON 格式")
            return

        self._send_response(200, "Webhook 已接收")

        repo_info = self._extract_repo_info(event_type, payload)
        self.server.queue_event(event_type, repo_info, payload)

    def _extract_repo_info(
        self,
        event_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        info = {"event": event_type}

        if "repository" in payload:
            repo = payload["repository"]
            info["repo_name"] = repo.get("full_name") or repo.get("name")
            info["repo_url"] = repo.get("html_url") or repo.get("url")
            info["default_branch"] = repo.get("default_branch", "main")

        if "ref" in payload:
            ref = payload["ref"]
            info["branch"] = ref.replace("refs/heads/", "")

        if "commits" in payload:
            commits = payload["commits"]
            info["commit_count"] = len(commits)
            if commits:
                info["latest_commit"] = commits[-1].get("id")
                info["latest_message"] = commits[-1].get("message")

        if "pusher" in payload:
            pusher = payload["pusher"]
            info["pusher_name"] = pusher.get("name")
            info["pusher_email"] = pusher.get("email")

        return info

    def log_message(self, format: str, *args):
        pass


class WebhookServer:
    def __init__(self, config_path: str = "config.ini"):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logger()
        
        self.host = self.config.get("webhook", "host", fallback="0.0.0.0")
        self.port = self.config.getint("webhook", "port", fallback=8080)
        self.endpoint = self.config.get("webhook", "endpoint", fallback="/webhook")
        self.secret = self.config.get("webhook", "secret", fallback=None)
        self.platform = self.config.get("webhook", "platform", fallback="github")
        
        self.repo_mapping: Dict[str, str] = {}
        self._load_repo_mapping()
        
        self._event_handlers = []
        self._lock = threading.Lock()

        self.httpd: Optional[HTTPServer] = None
        self._running = False

    def _load_config(self, config_path: str) -> configparser.ConfigParser:
        config = configparser.ConfigParser()
        if os.path.exists(config_path):
            config.read(config_path, encoding="utf-8")
        return config

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("webhook")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            log_enabled = self.config.getboolean("log", "enabled", fallback=True)
            if log_enabled:
                log_file = self.config.get("log", "log_file", fallback="webhook.log")
                file_handler = logging.FileHandler(log_file, encoding="utf-8")
                console_handler = logging.StreamHandler()

                formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
                file_handler.setFormatter(formatter)
                console_handler.setFormatter(formatter)

                logger.addHandler(file_handler)
                logger.addHandler(console_handler)

            log_level = self.config.get("log", "log_level", fallback="INFO")
            logger.setLevel(getattr(logging, log_level.upper(), logging.INFO)

        return logger

    def _load_repo_mapping(self):
        if self.config.has_section("webhook_repos"):
            for repo_name, local_path in self.config.items("webhook_repos"):
                self.repo_mapping[repo_name] = local_path
                self.logger.info(f"映射仓库: {repo_name} -> {local_path}")

    def add_event_handler(self, handler):
        with self._lock:
            self._event_handlers.append(handler)

    def queue_event(
        self,
        event_type: str,
        repo_info: Dict[str, Any],
        payload: Dict[str, Any]
    ):
        self.logger.info(f"事件: {event_type}, 仓库: {repo_info.get('repo_name')}")

        with self._lock:
            handlers = list(self._event_handlers)

        for handler in handlers:
            try:
                handler(event_type, repo_info, payload)
            except Exception as e:
                self.logger.error(f"处理器错误: {e}", exc_info=True)

    def auto_pull_handler(
        self,
        event_type: str,
        repo_info: Dict[str, Any],
        payload: Dict[str, Any]
    ):
        if event_type != "push":
            self.logger.info(f"跳过非 push 事件: {event_type}")
            return

        repo_name = repo_info.get("repo_name")
        if not repo_name:
            self.logger.warning("未找到仓库名称")
            return

        local_path = None
        if repo_name in self.repo_mapping:
            local_path = self.repo_mapping[repo_name]
        elif "default" in self.repo_mapping:
            local_path = self.repo_mapping["default"]

        if not local_path or not os.path.exists(local_path):
            self.logger.warning(f"未找到本地路径: {repo_name}")
            return

        self.logger.info(f"开始拉取: {repo_name} -> {local_path}")

        def pull_task():
            try:
                fetch_result = subprocess.run(
                    ["git", "fetch", "origin"],
                    cwd=local_path,
                    capture_output=True,
                    text=True
                )
                if fetch_result.returncode != 0:
                    self.logger.error(f"fetch 失败: {fetch_result.stderr}")
                    return

                pull_result = subprocess.run(
                    ["git", "pull", "--rebase", "origin", "HEAD"],
                    cwd=local_path,
                    capture_output=True,
                    text=True
                )

                if pull_result.returncode == 0:
                    self.logger.info(f"拉取成功: {repo_name}")
                else:
                    self.logger.error(f"pull 失败: {pull_result.stderr}")
            except Exception as e:
                self.logger.error(f"拉取任务错误: {e}", exc_info=True)

        threading.Thread(target=pull_task, daemon=True).start()

    def start(self, auto_pull: bool = True):
        if auto_pull:
            self.add_event_handler(self.auto_pull_handler)

        handler_class = type("Handler", (WebhookHandler,), {"server": self})
        self.httpd = HTTPServer((self.host, self.port), handler_class)

        self.logger.info(f"启动 Webhook 服务器: http://{self.host}:{self.port}{self.endpoint}")
        self.logger.info(f"平台: {self.platform}")

        self._running = True

        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            self.logger.info("收到中断信号")
        finally:
            self.stop()

    def stop(self):
        self._running = False
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
        self.logger.info("Webhook 服务器已停止")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Git Webhook 服务器")
    parser.add_argument(
        "-c", "--config",
        default="config.ini",
        help="配置文件路径 (默认: config.ini)"
    )
    parser.add_argument(
        "--host",
        default=None,
        help="监听地址"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="监听端口"
    )
    parser.add_argument(
        "--no-auto-pull",
        action="store_true",
        help="禁用自动拉取"
    )

    args = parser.parse_args()

    server = WebhookServer(config_path=args.config)

    if args.host:
        server.host = args.host
    if args.port:
        server.port = args.port

    server.start(auto_pull=not args.no_auto_pull)


if __name__ == "__main__":
    main()
