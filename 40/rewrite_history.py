#!/usr/bin/env python3
import json
import os
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def load_config(config_path: str = "config.json") -> dict:
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def check_bfg_installed(bfg_jar_path: str) -> bool:
    if os.path.exists(bfg_jar_path):
        return True
    try:
        result = subprocess.run(
            ["java", "-jar", bfg_jar_path, "--version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return False


def check_java_installed() -> bool:
    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def create_temp_file(content: str, suffix: str = "") -> str:
    temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)
    os.close(temp_fd)
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content)
    return temp_path


def run_git_command(repo_path: str, args_list: list, dry_run: bool = False, verbose: bool = False):
    if verbose:
        cmd_str = " ".join(["git"] + args_list)
        print(f"执行命令: {cmd_str}")

    if dry_run:
        print("[DRY RUN] 未实际执行 Git 命令")
        return True

    try:
        result = subprocess.run(
            ["git"] + args_list,
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if verbose and result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"执行 Git 命令时出错: {e}")
        return False


def run_bfg(args_list: list, dry_run: bool = False, verbose: bool = False):
    if verbose:
        cmd_str = " ".join(args_list)
        print(f"执行命令: {cmd_str}")

    if dry_run:
        print("[DRY RUN] 未实际执行 BFG 命令")
        return True

    try:
        result = subprocess.run(
            args_list,
            capture_output=True,
            text=True
        )
        if verbose and result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"执行 BFG 时出错: {e}")
        return False


def cleanup_after_bfg(repo_path: str, dry_run: bool = False, verbose: bool = False):
    if verbose:
        print("\n开始执行 BFG 后清理...")

    if verbose:
        print("步骤 1: 过期 reflog")
    success = run_git_command(repo_path, ["reflog", "expire", "--expire=now", "--all"], dry_run, verbose)
    if not success:
        print("警告: reflog 过期失败")

    if verbose:
        print("步骤 2: 执行 git gc")
    success = run_git_command(repo_path, ["gc", "--prune=now", "--aggressive"], dry_run, verbose)
    if not success:
        print("警告: git gc 失败")

    return True


def push_to_remote(repo_path: str, dry_run: bool = False, verbose: bool = False):
    if verbose:
        print("\n准备推送到远程仓库...")

    success = run_git_command(repo_path, ["push", "--force", "--all"], dry_run, verbose)
    if not success:
        print("警告: 推送所有分支失败")
        return False

    success = run_git_command(repo_path, ["push", "--force", "--tags"], dry_run, verbose)
    if not success:
        print("警告: 推送标签失败")
        return False

    if verbose:
        print("已成功推送到远程仓库")
    return True


def rewrite_history(repo_path: str = ".", config: dict = None, auto_cleanup: bool = False, auto_push: bool = False):
    if config is None:
        config = load_config()

    general_config = config.get("general", {})
    bfg_config = config.get("rewrite_history", {})

    dry_run = general_config.get("dry_run", False)
    verbose = general_config.get("verbose", True)

    bfg_jar_path = bfg_config.get("bfg_jar_path", "bfg.jar")
    delete_files = bfg_config.get("delete_files", [])
    delete_folders = bfg_config.get("delete_folders", [])
    strip_blobs_over = bfg_config.get("strip_blobs_over", None)
    replace_text = bfg_config.get("replace_text", {})
    replace_secrets = bfg_config.get("replace_secrets", {})

    if verbose:
        print("开始重写 Git 历史...")
        print(f"BFG JAR 路径: {bfg_jar_path}")

    if not check_java_installed():
        print("错误: 未找到 Java，请先安装 Java 运行时环境")
        return False

    if not check_bfg_installed(bfg_jar_path):
        print(f"错误: 未找到 BFG JAR 文件: {bfg_jar_path}")
        print("请从 https://rtyley.github.io/bfg-repo-cleaner/ 下载 BFG")
        return False

    git_dir = os.path.join(repo_path, ".git")
    if not os.path.exists(git_dir):
        print(f"错误: {repo_path} 不是有效的 Git 仓库")
        return False

    base_args = ["java", "-jar", bfg_jar_path]
    temp_files = []

    if delete_files:
        files_list = "\n".join(delete_files)
        temp_file = create_temp_file(files_list, suffix=".txt")
        temp_files.append(temp_file)
        base_args.extend(["--delete-files", temp_file])
        if verbose:
            print(f"将删除的文件模式: {delete_files}")

    if delete_folders:
        folders_list = "\n".join(delete_folders)
        temp_file = create_temp_file(folders_list, suffix=".txt")
        temp_files.append(temp_file)
        base_args.extend(["--delete-folders", temp_file])
        if verbose:
            print(f"将删除的文件夹: {delete_folders}")

    if strip_blobs_over:
        base_args.extend(["--strip-blobs-bigger-than", strip_blobs_over])
        if verbose:
            print(f"将删除大于 {strip_blobs_over} 的文件")

    if replace_text or replace_secrets:
        replacements = []
        for original, replacement in replace_text.items():
            replacements.append(f"ORIGINAL={original}==>REPLACEMENT={replacement}")
        for original, replacement in replace_secrets.items():
            replacements.append(f"ORIGINAL={original}==>REPLACEMENT={replacement}")

        if replacements:
            replace_content = "\n".join(replacements)
            temp_file = create_temp_file(replace_content, suffix=".txt")
            temp_files.append(temp_file)
            base_args.extend(["--replace-text", temp_file])
            if verbose:
                print("将执行文本替换")

    if len(base_args) <= 2:
        print("错误: 未指定任何操作，请在配置文件中设置 delete_files、delete_folders、strip_blobs_over 或 replace_text")
        return False

    base_args.append(repo_path)

    if verbose:
        print("准备执行 BFG 重写历史...")
        print("警告: 这将修改 Git 历史，操作不可逆！")

    success = run_bfg(base_args, dry_run=dry_run, verbose=verbose)

    for temp_file in temp_files:
        try:
            os.remove(temp_file)
        except Exception:
            pass

    if success and not dry_run:
        if verbose:
            print("\nBFG 执行完成！")

        if auto_cleanup:
            cleanup_after_bfg(repo_path, dry_run=dry_run, verbose=verbose)

            if auto_push:
                push_to_remote(repo_path, dry_run=dry_run, verbose=verbose)
        else:
            if verbose:
                print("接下来需要执行以下命令来清理和推送更改:")
                print("  cd", repo_path)
                print("  git reflog expire --expire=now --all")
                print("  git gc --prune=now --aggressive")
                print("  git push --force --all")
                print("  git push --force --tags")

    return success


def main():
    parser = argparse.ArgumentParser(description="使用 BFG 重写 Git 历史，删除敏感数据和大文件")
    parser.add_argument("-r", "--repo", default=".", help="Git 仓库路径 (默认: 当前目录)")
    parser.add_argument("-c", "--config", default="config.json", help="配置文件路径 (默认: config.json)")
    parser.add_argument("--bfg-jar", help="BFG JAR 文件路径 (覆盖配置文件)")
    parser.add_argument("--strip-blobs", help="删除大于指定大小的文件 (例如: 100M)")
    parser.add_argument("-n", "--dry-run", action="store_true", help="试运行模式，不实际执行")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("--auto-cleanup", action="store_true", help="BFG 执行后自动执行 reflog expire 和 git gc")
    parser.add_argument("--auto-push", action="store_true", help="清理完成后自动推送到远程仓库 (需要 --auto-cleanup)")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.bfg_jar:
        config.setdefault("rewrite_history", {})["bfg_jar_path"] = args.bfg_jar

    if args.strip_blobs:
        config.setdefault("rewrite_history", {})["strip_blobs_over"] = args.strip_blobs

    if args.dry_run:
        config.setdefault("general", {})["dry_run"] = True

    if args.verbose:
        config.setdefault("general", {})["verbose"] = True

    auto_cleanup = args.auto_cleanup
    auto_push = args.auto_push

    if auto_push and not auto_cleanup:
        print("警告: --auto-push 需要 --auto-cleanup，自动启用 --auto-cleanup")
        auto_cleanup = True

    success = rewrite_history(
        repo_path=args.repo,
        config=config,
        auto_cleanup=auto_cleanup,
        auto_push=auto_push
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
