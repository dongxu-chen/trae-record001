#!/usr/bin/env python3
import argparse
import os
import sys
from datetime import datetime, timezone, timedelta

import boto3
from dotenv import load_dotenv

from utils import get_preview_expire_days


def list_s3_objects(s3, bucket: str, prefix: str) -> list:
    paginator = s3.get_paginator("list_objects_v2")
    objects = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if "Contents" in page:
            for obj in page["Contents"]:
                objects.append({
                    "Key": obj["Key"],
                    "LastModified": obj["LastModified"],
                })
    return objects


def get_active_branches() -> set:
    try:
        import subprocess
        result = subprocess.run(
            ["git", "branch", "-r", "--format=%(refname:short)"],
            capture_output=True,
            text=True,
            check=True
        )
        branches = set()
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line and "/" in line:
                branch = line.split("/", 1)[1]
                branches.add(branch)
        return branches
    except Exception:
        return set()


def cleanup(branch: str = None, all_expired: bool = False, dry_run: bool = False):
    load_dotenv("config.env")
    bucket = os.getenv("S3_BUCKET")
    region = os.getenv("AWS_REGION", "us-east-1")
    if not bucket:
        raise ValueError("S3_BUCKET 未配置")

    s3 = boto3.client("s3", region_name=region)
    expire_days = get_preview_expire_days()
    cutoff = datetime.now(timezone.utc) - timedelta(days=expire_days)
    active_branches = get_active_branches()

    print("=" * 70)
    print("预览环境清理")
    print("=" * 70)
    print(f"过期天数: {expire_days} 天")
    print(f"截止时间: {cutoff.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    from utils import sanitize_branch_name

    if branch:
        clean_branch = sanitize_branch_name(branch)
        prefix = f"preview/{clean_branch}/"
        print(f"\n目标: 删除分支 {branch} 的预览环境")
        objects = list_s3_objects(s3, bucket, prefix)
        if not objects:
            print("未找到该分支的预览文件")
            return
        count = len(objects)
        if dry_run:
            print(f"[模拟] 将删除 {count} 个对象")
        else:
            for obj in objects:
                s3.delete_object(Bucket=bucket, Key=obj["Key"])
            print(f"已删除 {count} 个对象")
        return

    if all_expired:
        paginator = s3.get_paginator("list_objects_v2")
        branch_dates = {}
        for page in paginator.paginate(Bucket=bucket, Prefix="preview/"):
            if "Contents" in page:
                for obj in page["Contents"]:
                    key = obj["Key"]
                    parts = key.split("/")
                    if len(parts) >= 3:
                        branch_name = parts[1]
                        if branch_name not in branch_dates:
                            branch_dates[branch_name] = obj["LastModified"]
                        else:
                            if obj["LastModified"] > branch_dates[branch_name]:
                                branch_dates[branch_name] = obj["LastModified"]

        to_delete = []
        for branch_name, last_modified in branch_dates.items():
            if branch_name in active_branches:
                continue
            if last_modified < cutoff:
                to_delete.append({
                    "branch": branch_name,
                    "last_modified": last_modified,
                })

        if not to_delete:
            print("\n没有需要清理的过期预览环境")
            return

        print(f"\n发现 {len(to_delete)} 个过期预览环境:\n")
        total_deleted = 0

        for item in to_delete:
            branch_name = item["branch"]
            last_modified = item["last_modified"]
            prefix = f"preview/{branch_name}/"
            objects = list_s3_objects(s3, bucket, prefix)
            count = len(objects)
            age = (datetime.now(timezone.utc) - last_modified).days

            print(f"  • {branch_name} ({count} 文件, {age} 天前更新)")

            if not dry_run:
                for obj in objects:
                    s3.delete_object(Bucket=bucket, Key=obj["Key"])
                total_deleted += count

        print(f"\n已清理 {len(to_delete)} 个预览环境, {total_deleted} 个文件")


def main():
    parser = argparse.ArgumentParser(description="清理过期的预览环境")
    parser.add_argument("--branch", "-b", help="删除指定分支的预览环境")
    parser.add_argument("--all", "-a", action="store_true", help="清理所有过期预览环境")
    parser.add_argument("--dry-run", "-n", action="store_true", help="模拟运行，不实际删除")
    args = parser.parse_args()

    if not args.branch and not args.all:
        parser.error("请指定 --branch 或 --all")

    cleanup(branch=args.branch, all_expired=args.all, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
