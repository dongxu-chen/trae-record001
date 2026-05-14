#!/usr/bin/env python3
import configparser
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional, Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from commit_message import generate_commit_message
from push_retry import PushRetry, SSHKeyManager
from conflict_handler import ConflictHandler


class SingleRepoBackup:
    def __init__(
        self,
        repo_config: Dict[str, Any],
        global_config: Dict[str, Any],
        logger: Optional[logging.Logger] = None
    ):
        self.repo_config = repo_config
        self.global_config = global_config
        self.logger = logger
        self.repo_path = repo_config.get("path", ".")
        self.branch = repo_config.get("branch", global_config.get("branch", "main"))
        self.remote = repo_config.get("remote", global_config.get("remote", "origin"))
        self.message_template = repo_config.get(
            "message_template",
            global_config.get("message_template", "自动备份: {timestamp}")
        )
        self.add_all = repo_config.get("add_all", global_config.get("add_all", True))
        self.enable_conflict_resolution = repo_config.get(
            "enable_conflict_resolution",
            global_config.get("enable_conflict_resolution", True)
        )
        self.ssh_key = repo_config.get("ssh_key")
        self.repo_name = repo_config.get("name", Path(self.repo_path).name or "repo")

    def _log(self, message: str, level: str = "info"):
        if self.logger:
            log_method = getattr(self.logger, level, self.logger.info)
            log_method(f"[{self.repo_name}] {message}")
        else:
            print(f"[{self.repo_name}] {message}")

    def _run_git(self, *args: str) -> subprocess.CompletedProcess:
        self._log(f"执行: git {' '.join(args)}", level="debug")
        return subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )

    def _setup_ssh(self) -> SSHKeyManager:
        ssh_manager = SSHKeyManager(logger=self.logger)
        if self.ssh_key:
            ssh_manager.configure_ssh_key(self.ssh_key)
        return ssh_manager

    def has_changes(self) -> bool:
        result = self._run_git("status", "--porcelain")
        changes = result.stdout.strip()
        if changes:
            self._log(f"检测到变更:\n{changes}")
            return True
        self._log("未检测到变更")
        return False

    def _has_staged_changes(self) -> bool:
        result = self._run_git("diff", "--cached", "--quiet")
        return result.returncode == 1

    def add_files(self) -> bool:
        if self.add_all:
            result = self._run_git("add", "-A")
        else:
            result = self._run_git("add", "-u")

        if result.returncode != 0:
            self._log(f"添加文件失败: {result.stderr}", level="error")
            return False

        if not self._has_staged_changes():
            self._log("添加后暂存区为空", level="warning")
            return False

        self._log("文件已添加到暂存区")
        return True

    def commit(self) -> bool:
        if not self._has_staged_changes():
            self._log("暂存区为空，无法提交", level="error")
            return False

        commit_msg = generate_commit_message(
            self.message_template,
            {"branch": self.branch, "remote": self.remote, "repo": self.repo_name}
        )

        result = self._run_git("commit", "-m", commit_msg)
        if result.returncode != 0:
            self._log(f"提交失败: {result.stderr}", level="error")
            return False

        self._log(f"已提交: {commit_msg}")
        return True

    def push(self) -> bool:
        retry = PushRetry(
            max_retries=self.global_config.get("max_retries", 3),
            retry_delay=self.global_config.get("retry_delay", 5),
            logger=self.logger
        )

        def push_op():
            r = subprocess.run(
                ["git", "push", self.remote, self.branch],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return r.stdout

        success, result = retry.execute_with_retry(
            push_op,
            f"git push {self.remote} {self.branch}"
        )

        if success:
            self._log("推送成功")
        else:
            self._log(f"推送失败: {result}", level="error")

        return success

    def run(self) -> Dict[str, Any]:
        result = {
            "repo": self.repo_name,
            "path": self.repo_path,
            "success": False,
            "skipped": False,
            "error": None,
            "conflict_resolved": False
        }

        ssh_manager = self._setup_ssh()

        try:
            self._log("=" * 40)
            self._log(f"开始备份 (分支: {self.branch})")
            self._log("=" * 40)

            if not self.has_changes():
                result["skipped"] = True
                result["success"] = True
                self._log("无变更，跳过")
                return result

            if self.enable_conflict_resolution:
                self._log("检查并处理冲突")
                conflict_handler = ConflictHandler(self.repo_path, logger=self.logger)
                conflict_result = conflict_handler.resolve_conflict_pipeline(
                    self.remote, self.branch
                )
                result["conflict_resolved"] = conflict_result.get("pulled", False)
                if conflict_result.get("error"):
                    self._log(f"冲突处理失败: {conflict_result['error']}", level="error")
                    result["error"] = conflict_result["error"]
                    return result

            if not self.add_files():
                result["error"] = "添加文件失败"
                return result

            if not self.commit():
                result["error"] = "提交失败"
                return result

            if not self.push():
                result["error"] = "推送失败"
                return result

            result["success"] = True
            self._log("备份完成")
            self._log("=" * 40)

        except Exception as e:
            result["error"] = str(e)
            self._log(f"发生错误: {e}", level="error")

        finally:
            ssh_manager.restore_default()

        return result


class MultiRepoBackupManager:
    def __init__(self, config_path: str = "config.ini"):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logger()
        self.repos: List[Dict[str, Any]] = []
        self.global_config: Dict[str, Any] = {}
        self.max_workers = self.config.getint(
            "concurrency", "max_workers", fallback=4
        )
        self._parse_config()

    def _load_config(self, config_path: str) -> configparser.ConfigParser:
        config = configparser.ConfigParser()
        if os.path.exists(config_path):
            config.read(config_path, encoding="utf-8")
        return config

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("git_auto_multi")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            log_enabled = self.config.getboolean("log", "enabled", fallback=True)
            if log_enabled:
                log_file = self.config.get("log", "log_file", fallback="git_auto.log")
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
            logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        return logger

    def _parse_repos_from_config(self) -> List[Dict[str, Any]]:
        repos = []

        for section in self.config.sections():
            if section.startswith("repo:"):
                repo_name = section[5:]
                repo_config = {
                    "name": repo_name,
                    "path": self.config.get(section, "path", fallback="."),
                    "branch": self.config.get(section, "branch", fallback=None),
                    "remote": self.config.get(section, "remote", fallback=None),
                    "message_template": self.config.get(
                        section, "message_template", fallback=None
                    ),
                    "add_all": self.config.getboolean(
                        section, "add_all", fallback=None
                    ),
                    "ssh_key": self.config.get(section, "ssh_key", fallback=None),
                    "enable_conflict_resolution": self.config.getboolean(
                        section, "enable_conflict_resolution", fallback=None
                    )
                }
                repos.append(repo_config)

        if not repos:
            default_repo = {
                "name": "default",
                "path": self.config.get("git", "repository_path", fallback="."),
            }
            repos.append(default_repo)

        return repos

    def _parse_ssh_keys_from_config(self) -> Dict[str, str]:
        keys = {}
        if self.config.has_section("ssh_keys"):
            for key, value in self.config.items("ssh_keys"):
                keys[key] = value
        return keys

    def _parse_config(self):
        self.global_config = {
            "branch": self.config.get("git", "branch", fallback="main"),
            "remote": self.config.get("git", "remote", fallback="origin"),
            "message_template": self.config.get(
                "commit", "message_template", fallback="自动备份: {timestamp}"
            ),
            "add_all": self.config.getboolean("commit", "add_all", fallback=True),
            "max_retries": self.config.getint("push", "max_retries", fallback=3),
            "retry_delay": self.config.getint("push", "retry_delay", fallback=5),
            "enable_conflict_resolution": self.config.getboolean(
                "conflict", "enable_resolution", fallback=True
            ),
        }

        self.repos = self._parse_repos_from_config()
        self.ssh_keys = self._parse_ssh_keys_from_config()

        self.logger.info(f"已加载 {len(self.repos)} 个仓库配置")
        for repo in self.repos:
            self.logger.info(f"  - {repo['name']}: {repo['path']}")

    def run_single(self, repo_config: Dict[str, Any]) -> Dict[str, Any]:
        worker = SingleRepoBackup(repo_config, self.global_config, self.logger)
        return worker.run()

    def run_parallel(self) -> Dict[str, Any]:
        self.logger.info(f"开始并行备份，最大并发数: {self.max_workers}")
        results = {"total": len(self.repos), "success": 0, "failed": 0, "skipped": 0, "repos": {}}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_repo = {
                executor.submit(self.run_single, repo): repo["name"]
                for repo in self.repos
            }

            for future in as_completed(future_to_repo):
                repo_name = future_to_repo[future]
                try:
                    result = future.result()
                    results["repos"][repo_name] = result
                    if result["success"]:
                        if result["skipped"]:
                            results["skipped"] += 1
                        else:
                            results["success"] += 1
                    else:
                        results["failed"] += 1
                except Exception as e:
                    results["repos"][repo_name] = {
                        "success": False,
                        "error": str(e)
                    }
                    results["failed"] += 1

        return results

    def run_sequential(self) -> Dict[str, Any]:
        self.logger.info("开始顺序备份")
        results = {"total": len(self.repos), "success": 0, "failed": 0, "skipped": 0, "repos": {}}

        for repo in self.repos:
            result = self.run_single(repo)
            results["repos"][repo["name"]] = result
            if result["success"]:
                if result["skipped"]:
                    results["skipped"] += 1
                else:
                    results["success"] += 1
            else:
                results["failed"] += 1

        return results

    def run(self, parallel: bool = True) -> Dict[str, Any]:
        self.logger.info("=" * 50)
        self.logger.info("Git 多仓库自动备份")
        self.logger.info("=" * 50)

        if parallel and len(self.repos) > 1:
            results = self.run_parallel()
        else:
            results = self.run_sequential()

        self.logger.info("=" * 50)
        self.logger.info(f"备份完成: 总数={results['total']}, "
                        f"成功={results['success']}, "
                        f"跳过={results['skipped']}, "
                        f"失败={results['failed']}")
        self.logger.info("=" * 50)

        return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Git 多仓库自动备份脚本")
    parser.add_argument(
        "-c", "--config",
        default="config.ini",
        help="配置文件路径 (默认: config.ini)"
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="顺序执行（默认并行）"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="并发工作线程数"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅检查配置，不执行操作"
    )

    args = parser.parse_args()

    manager = MultiRepoBackupManager(config_path=args.config)

    if args.workers:
        manager.max_workers = args.workers

    if args.dry_run:
        manager.logger.info("干燥运行模式")
        for repo in manager.repos:
            manager.logger.info(f"  仓库: {repo['name']} -> {repo['path']}")
        sys.exit(0)

    results = manager.run(parallel=not args.sequential)

    all_success = results["failed"] == 0
    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
