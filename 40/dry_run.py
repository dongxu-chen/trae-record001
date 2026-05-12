#!/usr/bin/env python3
import json
import os
import argparse
import sys
from datetime import datetime

from reporter import GitCleanupReporter
from mailer import EmailSender


def load_config(config_path: str = "config.json") -> dict:
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def import_clean_branches():
    try:
        from clean_old_branches import clean_old_branches, get_all_branches, is_branch_protected, get_branch_last_commit_date
        return True
    except ImportError as e:
        print(f"警告: 无法导入 clean_old_branches 模块: {e}")
        return False


def import_remove_large_files():
    try:
        from remove_large_files import find_large_files, is_in_whitelist, get_file_size_mb
        return True
    except ImportError as e:
        print(f"警告: 无法导入 remove_large_files 模块: {e}")
        return False


def import_rewrite_history():
    try:
        from rewrite_history import check_bfg_installed, check_java_installed
        return True
    except ImportError as e:
        print(f"警告: 无法导入 rewrite_history 模块: {e}")
        return False


def run_branch_cleanup_dry_run(repo_path: str, repo_name: str, config: dict, reporter: GitCleanupReporter, verbose: bool = False):
    if not import_clean_branches():
        return

    from clean_old_branches import (
        clean_old_branches as _clean_func,
        get_all_branches,
        is_branch_protected,
        get_branch_last_commit_date,
        get_default_branches
    )
    from datetime import datetime, timedelta
    from git import Repo, InvalidGitRepositoryError

    try:
        repo = Repo(repo_path)
    except InvalidGitRepositoryError:
        print(f"  错误: {repo_path} 不是有效的 Git 仓库")
        return

    branch_config = config.get("clean_old_branches", {})
    days_old = branch_config.get("days_old", 90)
    merge_only = branch_config.get("merge_only", True)
    protected_branches = branch_config.get("protected_branches", [])
    exclude_branches = branch_config.get("exclude_branches", [])

    cutoff_date = datetime.now() - timedelta(days=days_old)

    if verbose:
        print(f"  [分支清理] 扫描超过 {days_old} 天的分支 (截止日期: {cutoff_date.strftime('%Y-%m-%d')})")

    default_branches = get_default_branches()

    local_branches = get_all_branches(repo, remote=False)
    remote_branches = get_all_branches(repo, remote=True)

    local_deleted = 0
    remote_deleted = 0
    skipped_protected = 0
    skipped_merged = 0

    main_branch = "main" if "main" in repo.heads else "master"

    for branch_name in local_branches:
        if is_branch_protected(branch_name, protected_branches, default_branches):
            skipped_protected += 1
            if verbose:
                print(f"    [跳过] 本地分支 {branch_name} (受保护)")
            continue

        if is_branch_protected(branch_name, exclude_branches, []):
            if verbose:
                print(f"    [跳过] 本地分支 {branch_name} (排除列表)")
            continue

        last_commit_date = get_branch_last_commit_date(repo, branch_name)
        if last_commit_date is None:
            continue

        if last_commit_date > cutoff_date:
            continue

        try:
            branch_commit = repo.heads[branch_name].commit
            main_branch_ref = repo.heads[main_branch]
            main_commit = main_branch_ref.commit
            is_merged = branch_commit == main_commit or repo.git.merge_base("--is-ancestor", branch_commit.hexsha, main_commit.hexsha) == ""
        except Exception:
            is_merged = False

        if merge_only and not is_merged:
            skipped_merged += 1
            if verbose:
                print(f"    [跳过] 本地分支 {branch_name} (未合并)")
            continue

        local_deleted += 1
        print(f"    [将删除] 本地分支: {branch_name} (最后提交: {last_commit_date.strftime('%Y-%m-%d')})")

    for remote_branch_full in remote_branches:
        branch_name = remote_branch_full.split("/", 1)[1] if "/" in remote_branch_full else remote_branch_full

        if is_branch_protected(branch_name, protected_branches, default_branches):
            skipped_protected += 1
            if verbose:
                print(f"    [跳过] 远程分支 {remote_branch_full} (受保护)")
            continue

        if is_branch_protected(branch_name, exclude_branches, []):
            if verbose:
                print(f"    [跳过] 远程分支 {remote_branch_full} (排除列表)")
            continue

        try:
            ref = repo.remote().refs[branch_name]
            last_commit_date = ref.commit.committed_datetime.replace(tzinfo=None)
        except Exception:
            continue

        if last_commit_date > cutoff_date:
            continue

        if merge_only:
            try:
                branch_commit = ref.commit
                main_branch_ref = repo.heads[main_branch]
                main_commit = main_branch_ref.commit
                is_merged = branch_commit == main_commit or repo.git.merge_base("--is-ancestor", branch_commit.hexsha, main_commit.hexsha) == ""
            except Exception:
                is_merged = False

            if not is_merged:
                skipped_merged += 1
                if verbose:
                    print(f"    [跳过] 远程分支 {remote_branch_full} (未合并)")
                continue

        remote_deleted += 1
        print(f"    [将删除] 远程分支: {remote_branch_full} (最后提交: {last_commit_date.strftime('%Y-%m-%d')})")

    if local_deleted == 0 and remote_deleted == 0:
        print("    没有找到需要删除的过期分支")

    reporter.add_branch_cleanup_report(
        repo_name=repo_name,
        local_deleted=local_deleted,
        remote_deleted=remote_deleted,
        skipped_protected=skipped_protected,
        skipped_merged=skipped_merged,
        dry_run=True
    )


def run_large_files_dry_run(repo_path: str, repo_name: str, config: dict, reporter: GitCleanupReporter, verbose: bool = False):
    if not import_remove_large_files():
        return

    from remove_large_files import find_large_files

    large_files_config = config.get("remove_large_files", {})
    size_threshold_mb = large_files_config.get("size_threshold_mb", 10)
    whitelist = large_files_config.get("whitelist_paths", [])
    allowed_extensions = large_files_config.get("allowed_extensions", [])
    scan_dirs = large_files_config.get("scan_directories", ["."])

    if verbose:
        print(f"  [大文件清理] 扫描超过 {size_threshold_mb} MB 的文件")
        print(f"    白名单: {whitelist}")
        print(f"    允许的扩展名: {allowed_extensions}")

    large_files_generator = find_large_files(
        repo_path=repo_path,
        size_threshold_mb=size_threshold_mb,
        whitelist=whitelist,
        allowed_extensions=allowed_extensions,
        scan_dirs=scan_dirs,
        verbose=verbose
    )

    files_found = 0
    files_deleted = 0
    total_size_mb = 0.0

    for f in large_files_generator:
        files_found += 1
        files_deleted += 1
        total_size_mb += f["size_mb"]
        print(f"    [将删除] {f['path']} - {f['size_mb']} MB")

    if files_found == 0:
        print("    没有找到超过阈值的大文件")

    reporter.add_large_files_report(
        repo_name=repo_name,
        files_found=files_found,
        files_deleted=files_deleted,
        total_size_mb=total_size_mb,
        dry_run=True
    )


def run_history_rewrite_dry_run(repo_path: str, repo_name: str, config: dict, reporter: GitCleanupReporter, verbose: bool = False):
    if not import_rewrite_history():
        return

    from rewrite_history import check_bfg_installed, check_java_installed

    bfg_config = config.get("rewrite_history", {})
    bfg_jar_path = bfg_config.get("bfg_jar_path", "bfg.jar")
    delete_files = bfg_config.get("delete_files", [])
    delete_folders = bfg_config.get("delete_folders", [])
    strip_blobs_over = bfg_config.get("strip_blobs_over", None)
    replace_text = bfg_config.get("replace_text", {})
    replace_secrets = bfg_config.get("replace_secrets", {})

    if verbose:
        print(f"  [历史重写] 检查 BFG 配置...")

    if not check_java_installed():
        print("    错误: 未找到 Java 运行时环境")
        return

    if not check_bfg_installed(bfg_jar_path):
        print(f"    警告: 未找到 BFG JAR 文件: {bfg_jar_path}")

    files_deleted = len(delete_files) if delete_files else 0
    folders_deleted = len(delete_folders) if delete_folders else 0
    blobs_stripped = 1 if strip_blobs_over else 0
    text_replaced = len(replace_text) if replace_text else 0
    secrets_redacted = len(replace_secrets) if replace_secrets else 0

    has_operations = files_deleted > 0 or folders_deleted > 0 or blobs_stripped > 0 or text_replaced > 0 or secrets_redacted > 0

    if not has_operations:
        print("    没有配置历史重写操作")
        return

    print(f"    [将执行] 删除文件模式: {delete_files}")
    print(f"    [将执行] 删除文件夹: {delete_folders}")
    if strip_blobs_over:
        print(f"    [将执行] 清除大于 {strip_blobs_over} 的对象")
    if replace_text:
        print(f"    [将执行] 文本替换: {len(replace_text)} 项")
    if replace_secrets:
        print(f"    [将执行] 机密脱敏: {len(replace_secrets)} 项")

    reporter.add_history_rewrite_report(
        repo_name=repo_name,
        files_deleted=files_deleted,
        folders_deleted=folders_deleted,
        blobs_stripped=blobs_stripped,
        text_replaced=text_replaced,
        secrets_redacted=secrets_redacted,
        cleanup_executed=False,
        push_executed=False,
        dry_run=True
    )


def process_repo(repo_config: dict, global_config: dict, reporter: GitCleanupReporter, verbose: bool = False):
    repo_name = repo_config.get("name", "unknown")
    repo_path = repo_config.get("path", ".")
    tasks = repo_config.get("tasks", {})

    print(f"\n处理仓库: {repo_name}")
    print(f"  路径: {repo_path}")
    print("-" * 50)

    if not os.path.exists(repo_path):
        print(f"  错误: 仓库路径不存在: {repo_path}")
        return

    if tasks.get("clean_old_branches", True):
        run_branch_cleanup_dry_run(repo_path, repo_name, global_config, reporter, verbose)

    if tasks.get("remove_large_files", True):
        run_large_files_dry_run(repo_path, repo_name, global_config, reporter, verbose)

    if tasks.get("rewrite_history", False):
        run_history_rewrite_dry_run(repo_path, repo_name, global_config, reporter, verbose)


def main():
    parser = argparse.ArgumentParser(description="Git 仓库清理工具 - 统一入口 (干运行模式)")
    parser.add_argument("-c", "--config", default="config.json", help="配置文件路径 (默认: config.json)")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("--repo", help="指定单个仓库名称 (只处理该仓库)")
    parser.add_argument("--task", choices=["branches", "large_files", "history"], help="指定执行的任务类型")
    parser.add_argument("--no-report", action="store_true", help="不生成报告")
    parser.add_argument("--no-email", action="store_true", help="不发送邮件")
    parser.add_argument("--email-report", action="store_true", help="强制发送邮件报告 (即使配置中禁用)")
    args = parser.parse_args()

    config = load_config(args.config)

    reporting_config = config.get("reporting", {})
    report_enabled = reporting_config.get("enabled", True) and not args.no_report
    report_dir = reporting_config.get("report_dir", "reports")
    save_format = reporting_config.get("save_format", "both")
    send_email = (reporting_config.get("send_email", False) or args.email_report) and not args.no_email

    reporter = GitCleanupReporter(report_dir=report_dir)

    print("=" * 60)
    print("Git 仓库清理工具 - 干运行模式")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    repositories = config.get("repositories", [])

    if not repositories:
        print("警告: 配置文件中没有配置任何仓库")
        print("将使用当前目录作为单个仓库处理...")
        default_repo = {
            "name": "current_dir",
            "path": config.get("general", {}).get("repo_path", "."),
            "enabled": True,
            "tasks": {
                "clean_old_branches": args.task in [None, "branches"],
                "remove_large_files": args.task in [None, "large_files"],
                "rewrite_history": args.task == "history"
            }
        }
        process_repo(default_repo, config, reporter, args.verbose)
    else:
        for repo_config in repositories:
            if not repo_config.get("enabled", True):
                continue

            if args.repo and repo_config.get("name") != args.repo:
                continue

            if args.task:
                task_key = {
                    "branches": "clean_old_branches",
                    "large_files": "remove_large_files",
                    "history": "rewrite_history"
                }[args.task]
                repo_config["tasks"] = {task_key: True}

            process_repo(repo_config, config, reporter, args.verbose)

    print("\n" + "=" * 60)
    print("处理完成")
    print("=" * 60)

    summary = reporter.get_summary()
    print(f"处理的仓库数: {summary['repos_processed']}")
    print(f"删除的分支总数: {summary['branches_deleted']}")
    print(f"删除的大文件数: {summary['large_files_deleted']}")
    print(f"释放的总空间: {summary['total_size_saved_mb']} MB")
    print(f"历史重写次数: {summary['history_cleanups']}")

    report_files = {}
    if report_enabled:
        print(f"\n生成报告 (格式: {save_format})...")
        report_files = reporter.save_report(format=save_format)
        for fmt, path in report_files.items():
            print(f"  {fmt.upper()} 报告: {path}")

    if send_email and report_files:
        print("\n发送邮件报告...")
        email_sender = EmailSender(config)
        success = email_sender.send_report(
            reporter=reporter,
            report_files=report_files,
            summary=summary,
            dry_run=False,
            verbose=args.verbose
        )
        if success:
            print("邮件发送成功")
        else:
            print("邮件发送失败")


if __name__ == "__main__":
    main()
