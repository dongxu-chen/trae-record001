#!/usr/bin/env python3
import json
import os
import argparse
import fnmatch
from datetime import datetime, timedelta
from git import Repo, InvalidGitRepositoryError


def load_config(config_path: str = "config.json") -> dict:
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_default_branches() -> list:
    return ["main", "master", "trunk"]


def is_branch_protected(branch_name: str, patterns: list, default_branches: list = None) -> bool:
    if default_branches is None:
        default_branches = get_default_branches()

    if branch_name in default_branches:
        return True

    return any(fnmatch.fnmatch(branch_name, pattern) for pattern in patterns)


def get_branch_last_commit_date(repo: Repo, branch_name: str):
    try:
        branch = repo.heads[branch_name]
        return branch.commit.committed_datetime.replace(tzinfo=None)
    except (KeyError, AttributeError):
        return None


def is_branch_merged(repo: Repo, branch_name: str, main_branch: str = "main") -> bool:
    try:
        branch_commit = repo.heads[branch_name].commit
        main_branch_ref = repo.heads[main_branch] if main_branch in repo.heads else repo.heads["master"]
        main_commit = main_branch_ref.commit
        return branch_commit == main_commit or repo.git.merge_base("--is-ancestor", branch_commit.hexsha, main_commit.hexsha) == ""
    except Exception:
        return False


def get_all_branches(repo: Repo, remote: bool = False) -> list:
    if remote:
        return [ref.name for ref in repo.remote().refs]
    return [head.name for head in repo.heads]


def delete_branch(repo: Repo, branch_name: str, remote: bool = False, dry_run: bool = True, verbose: bool = False):
    if dry_run:
        if verbose:
            print(f"[DRY RUN] 准备删除分支: {branch_name}")
        return

    try:
        if remote:
            origin = repo.remote()
            origin.push(refspec=f":{branch_name}")
            if verbose:
                print(f"已删除远程分支: {branch_name}")
        else:
            repo.git.branch("-D", branch_name)
            if verbose:
                print(f"已删除本地分支: {branch_name}")
    except Exception as e:
        print(f"删除分支 {branch_name} 时出错: {e}")


def clean_old_branches(repo_path: str = ".", config: dict = None):
    if config is None:
        config = load_config()

    general_config = config.get("general", {})
    branch_config = config.get("clean_old_branches", {})

    dry_run = general_config.get("dry_run", False)
    verbose = general_config.get("verbose", True)

    try:
        repo = Repo(repo_path)
    except InvalidGitRepositoryError:
        print(f"错误: {repo_path} 不是有效的 Git 仓库")
        return

    if repo.bare:
        print("错误: 不支持裸仓库")
        return

    days_old = branch_config.get("days_old", 90)
    merge_only = branch_config.get("merge_only", True)
    protected_branches = branch_config.get("protected_branches", [])
    exclude_branches = branch_config.get("exclude_branches", [])

    cutoff_date = datetime.now() - timedelta(days=days_old)

    if verbose:
        print(f"开始清理过期分支（超过 {days_old} 天）...")
        print(f"截止日期: {cutoff_date.strftime('%Y-%m-%d')}")

    main_branch = "main" if "main" in repo.heads else "master"

    local_branches = get_all_branches(repo, remote=False)
    remote_branches = get_all_branches(repo, remote=True)

    branches_to_delete = []

    for branch_name in local_branches:
        if is_branch_protected(branch_name, protected_branches):
            if verbose:
                print(f"跳过受保护的本地分支: {branch_name}")
            continue

        if is_branch_protected(branch_name, exclude_branches):
            if verbose:
                print(f"跳过排除的本地分支: {branch_name}")
            continue

        last_commit_date = get_branch_last_commit_date(repo, branch_name)
        if last_commit_date is None:
            if verbose:
                print(f"无法获取分支 {branch_name} 的提交日期")
            continue

        if last_commit_date > cutoff_date:
            continue

        if merge_only and not is_branch_merged(repo, branch_name, main_branch):
            if verbose:
                print(f"跳过未合并的本地分支: {branch_name}")
            continue

        branches_to_delete.append(("local", branch_name, last_commit_date))

    for remote_branch_full in remote_branches:
        branch_name = remote_branch_full.split("/", 1)[1] if "/" in remote_branch_full else remote_branch_full

        if is_branch_protected(branch_name, protected_branches):
            if verbose:
                print(f"跳过受保护的远程分支: {remote_branch_full}")
            continue

        if is_branch_protected(branch_name, exclude_branches):
            if verbose:
                print(f"跳过排除的远程分支: {remote_branch_full}")
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
                if branch_commit != main_commit and repo.git.merge_base("--is-ancestor", branch_commit.hexsha, main_commit.hexsha) != "":
                    if verbose:
                        print(f"跳过未合并的远程分支: {remote_branch_full}")
                    continue
            except Exception:
                continue

        branches_to_delete.append(("remote", branch_name, last_commit_date))

    if not branches_to_delete:
        print("没有找到需要删除的过期分支")
        return

    print(f"\n找到 {len(branches_to_delete)} 个需要删除的过期分支:")
    for source, name, date in branches_to_delete:
        print(f"  [{source}] {name} (最后提交: {date.strftime('%Y-%m-%d')})")

    if dry_run:
        print("\n[DRY RUN] 未执行任何删除操作")
    else:
        print(f"\n开始删除 {len(branches_to_delete)} 个分支...")
        for source, name, _ in branches_to_delete:
            delete_branch(repo, name, remote=(source == "remote"), dry_run=dry_run, verbose=verbose)


def main():
    parser = argparse.ArgumentParser(description="清理 Git 仓库中的过期分支")
    parser.add_argument("-r", "--repo", default=".", help="Git 仓库路径 (默认: 当前目录)")
    parser.add_argument("-c", "--config", default="config.json", help="配置文件路径 (默认: config.json)")
    parser.add_argument("-d", "--days", type=int, help="分支过期天数 (覆盖配置文件)")
    parser.add_argument("-n", "--dry-run", action="store_true", help="试运行模式，不实际删除")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("-a", "--all", action="store_true", help="删除所有过期分支，包括未合并的")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.days:
        config.setdefault("clean_old_branches", {})["days_old"] = args.days

    if args.dry_run:
        config.setdefault("general", {})["dry_run"] = True

    if args.verbose:
        config.setdefault("general", {})["verbose"] = True

    if args.all:
        config.setdefault("clean_old_branches", {})["merge_only"] = False

    clean_old_branches(repo_path=args.repo, config=config)


if __name__ == "__main__":
    main()
