#!/usr/bin/env python3
import json
import os
import argparse
import fnmatch
from pathlib import Path
from git import Repo, InvalidGitRepositoryError


def load_config(config_path: str = "config.json") -> dict:
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_file_size_mb(file_path: str) -> float:
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except OSError:
        return 0


def is_in_whitelist(file_path: str, whitelist: list, allowed_extensions: list = None) -> bool:
    path_obj = Path(file_path)

    if allowed_extensions:
        ext = path_obj.suffix.lower()
        for allowed_ext in allowed_extensions:
            if file_path.lower().endswith(allowed_ext.lower()):
                return True

    for pattern in whitelist:
        if pattern.endswith("/"):
            if pattern in str(path_obj) or path_obj.as_posix().startswith(pattern.rstrip("/")):
                return True
        if fnmatch.fnmatch(str(path_obj), pattern):
            return True
        if fnmatch.fnmatch(path_obj.name, pattern):
            return True
        if fnmatch.fnmatch(path_obj.as_posix(), pattern):
            return True

    return False


def find_large_files(repo_path: str, size_threshold_mb: float, whitelist: list, allowed_extensions: list, scan_dirs: list = None, verbose: bool = False):
    if scan_dirs is None:
        scan_dirs = ["."]

    for scan_dir in scan_dirs:
        base_dir = os.path.join(repo_path, scan_dir)
        if not os.path.exists(base_dir):
            continue

        for root, dirs, files in os.walk(base_dir):
            if ".git" in dirs:
                dirs.remove(".git")

            for file_name in files:
                file_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(file_path, repo_path)

                if is_in_whitelist(relative_path, whitelist, allowed_extensions):
                    if verbose:
                        print(f"跳过敏感文件: {relative_path}")
                    continue

                file_size_mb = get_file_size_mb(file_path)
                if file_size_mb > size_threshold_mb:
                    yield {
                        "path": relative_path,
                        "size_mb": round(file_size_mb, 2)
                    }


def remove_file(file_path: str, dry_run: bool = True, verbose: bool = False):
    abs_path = os.path.abspath(file_path)
    if dry_run:
        if verbose:
            print(f"[DRY RUN] 准备删除: {file_path}")
        return

    try:
        os.remove(abs_path)
        if verbose:
            print(f"已删除: {file_path}")
    except Exception as e:
        print(f"删除文件 {file_path} 时出错: {e}")


def is_file_tracked(repo: Repo, file_path: str) -> bool:
    try:
        repo.git.ls_files("--error-unmatch", file_path)
        return True
    except Exception:
        return False


def git_remove_file(repo: Repo, file_path: str, dry_run: bool = True, verbose: bool = False):
    if dry_run:
        if verbose:
            print(f"[DRY RUN] 准备从 Git 移除: {file_path}")
        return

    try:
        repo.git.rm("--cached", file_path)
        if verbose:
            print(f"已从 Git 暂存区移除: {file_path}")
    except Exception as e:
        print(f"从 Git 移除文件 {file_path} 时出错: {e}")


def remove_large_files(repo_path: str = ".", config: dict = None):
    if config is None:
        config = load_config()

    general_config = config.get("general", {})
    large_files_config = config.get("remove_large_files", {})

    dry_run = general_config.get("dry_run", False)
    verbose = general_config.get("verbose", True)

    size_threshold_mb = large_files_config.get("size_threshold_mb", 10)
    whitelist = large_files_config.get("whitelist_paths", [])
    allowed_extensions = large_files_config.get("allowed_extensions", [])
    scan_dirs = large_files_config.get("scan_directories", ["."])

    if verbose:
        print(f"开始扫描大文件（超过 {size_threshold_mb} MB）...")
        print(f"白名单: {whitelist}")
        print(f"允许的扩展名: {allowed_extensions}")

    try:
        repo = Repo(repo_path)
        is_git_repo = True
    except InvalidGitRepositoryError:
        is_git_repo = False

    large_files_generator = find_large_files(
        repo_path=repo_path,
        size_threshold_mb=size_threshold_mb,
        whitelist=whitelist,
        allowed_extensions=allowed_extensions,
        scan_dirs=scan_dirs,
        verbose=verbose
    )

    count = 0
    print("\n找到的大文件:")
    for f in large_files_generator:
        count += 1
        print(f"  {f['path']} - {f['size_mb']} MB")

        if not dry_run:
            if is_git_repo and is_file_tracked(repo, f["path"]):
                git_remove_file(repo, f["path"], dry_run=dry_run, verbose=verbose)
            remove_file(os.path.join(repo_path, f["path"]), dry_run=dry_run, verbose=verbose)

    if count == 0:
        print("  (无)")
        print("\n没有找到超过阈值的大文件")
        return

    print(f"\n共找到 {count} 个大文件")
    if dry_run:
        print("[DRY RUN] 未执行任何删除操作")


def main():
    parser = argparse.ArgumentParser(description="查找和移除 Git 仓库中的大文件")
    parser.add_argument("-r", "--repo", default=".", help="Git 仓库路径 (默认: 当前目录)")
    parser.add_argument("-c", "--config", default="config.json", help="配置文件路径 (默认: config.json)")
    parser.add_argument("-s", "--size", type=float, help="文件大小阈值（MB）(覆盖配置文件)")
    parser.add_argument("-n", "--dry-run", action="store_true", help="试运行模式，不实际删除")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("-l", "--list-only", action="store_true", help="仅列出大文件，不删除")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.size:
        config.setdefault("remove_large_files", {})["size_threshold_mb"] = args.size

    if args.dry_run or args.list_only:
        config.setdefault("general", {})["dry_run"] = True

    if args.verbose:
        config.setdefault("general", {})["verbose"] = True

    remove_large_files(repo_path=args.repo, config=config)


if __name__ == "__main__":
    main()
