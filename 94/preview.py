#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import boto3
from dotenv import load_dotenv


VERSION_MANIFEST_KEY = ".versions.json"


def list_s3_objects(s3, bucket: str, prefix: str) -> list:
    paginator = s3.get_paginator("list_objects_v2")
    objects = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
        if "CommonPrefixes" in page:
            for p in page["CommonPrefixes"]:
                objects.append(p["Prefix"])
        if "Contents" in page:
            for obj in page["Contents"]:
                objects.append(obj["Key"])
    return objects


def get_version_manifest(s3, bucket: str) -> dict:
    try:
        resp = s3.get_object(Bucket=bucket, Key=VERSION_MANIFEST_KEY)
        return json.loads(resp["Body"].read().decode("utf-8"))
    except s3.exceptions.NoSuchKey:
        return {"versions": [], "current": None}
    except Exception:
        return {"versions": [], "current": None}


def list_preview_branches(s3, bucket: str) -> list:
    prefixes = list_s3_objects(s3, bucket, "preview/")
    branches = []
    for p in prefixes:
        if p.startswith("preview/") and p.endswith("/"):
            name = p[len("preview/"):].rstrip("/")
            if name:
                branches.append(name)
    return branches


def get_preview_url(branch: str, preview_base: str) -> str:
    if preview_base:
        return f"{preview_base}/preview/{branch}/"
    return f"/preview/{branch}/"


def get_site_base_url() -> str:
    return os.getenv("SITE_BASE_URL", "").rstrip("/")


def get_preview_base_url() -> str:
    return os.getenv("PREVIEW_BASE_URL", "").rstrip("/")


def report(branch: str = None):
    load_dotenv("config.env")
    bucket = os.getenv("S3_BUCKET")
    region = os.getenv("AWS_REGION", "us-east-1")
    if not bucket:
        raise ValueError("S3_BUCKET 未配置")

    s3 = boto3.client("s3", region_name=region)
    preview_base = get_preview_base_url()
    site_base = get_site_base_url()

    print("=" * 70)
    print("预览环境报告")
    print("=" * 70)

    if branch:
        from utils import sanitize_branch_name
        clean_branch = sanitize_branch_name(branch)
        url = get_preview_url(clean_branch, preview_base or site_base)
        print(f"\n分支: {branch}")
        print(f"预览链接: {url}")
        return

    branches = list_preview_branches(s3, bucket)

    if not branches:
        print("\n暂无预览环境")
    else:
        print(f"\n共 {len(branches)} 个预览环境:\n")
        for b in branches:
            url = get_preview_url(b, preview_base or site_base)
            print(f"  • {b}")
            print(f"    {url}\n")

    manifest = get_version_manifest(s3, bucket)
    versions = manifest.get("versions", [])
    current = manifest.get("current")

    print("\n" + "=" * 70)
    print("生产版本历史")
    print("=" * 70)

    if not versions:
        print("\n暂无生产版本历史")
    else:
        for i, ver in enumerate(versions):
            marker = " [当前]" if ver.get("id") == current else ""
            ts = ver.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                ts = dt.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
            except Exception:
                pass
            print(f"\n  [{i+1}] 版本: {ver.get('id')}{marker}")
            print(f"      分支: {ver.get('branch')}")
            print(f"      Commit: {ver.get('commit')}")
            print(f"      时间: {ts}")


def main():
    parser = argparse.ArgumentParser(description="查看预览环境和版本历史")
    parser.add_argument("--branch", "-b", help="查看指定分支的预览链接")
    args = parser.parse_args()
    report(branch=args.branch)


if __name__ == "__main__":
    main()
