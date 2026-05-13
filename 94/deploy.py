#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import boto3
from dotenv import load_dotenv

from hugo_build import build as hugo_build
from s3_sync import sync as s3_sync
from invalidate import invalidate as cf_invalidate
from utils import (
    get_current_branch,
    get_current_commit,
    get_deploy_prefix,
    get_version_id,
    get_public_dir,
    get_bucket_name,
    get_preview_base_url,
    get_site_base_url,
    get_max_version_history,
    is_preview_branch,
)


VERSION_MANIFEST_KEY = ".versions.json"


def list_s3_objects(s3, bucket: str, prefix: str) -> dict:
    paginator = s3.get_paginator("list_objects_v2")
    objects = {}
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if "Contents" in page:
            for obj in page["Contents"]:
                objects[obj["Key"]] = obj
    return objects


def get_version_manifest(s3, bucket: str) -> dict:
    try:
        resp = s3.get_object(Bucket=bucket, Key=VERSION_MANIFEST_KEY)
        return json.loads(resp["Body"].read().decode("utf-8"))
    except s3.exceptions.NoSuchKey:
        return {"versions": [], "current": None}
    except Exception:
        return {"versions": [], "current": None}


def save_version_manifest(s3, bucket: str, manifest: dict) -> None:
    s3.put_object(
        Bucket=bucket,
        Key=VERSION_MANIFEST_KEY,
        Body=json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json; charset=utf-8",
    )


def copy_to_production(s3, bucket: str, source_prefix: str, dest_prefix: str) -> int:
    source_objects = list_s3_objects(s3, bucket, source_prefix)
    copied = 0
    for source_key in source_objects:
        if not source_key.startswith(source_prefix):
            continue
        relative_key = source_key[len(source_prefix):]
        dest_key = dest_prefix + relative_key if dest_prefix else relative_key
        if dest_key.startswith("/"):
            dest_key = dest_key.lstrip("/")
        if not dest_key:
            continue
        s3.copy_object(
            Bucket=bucket,
            Key=dest_key,
            CopySource={"Bucket": bucket, "Key": source_key},
            MetadataDirective="REPLACE",
        )
        copied += 1
    return copied


def clean_old_versions(s3, bucket: str, manifest: dict) -> None:
    max_versions = get_max_version_history()
    current = manifest.get("current")
    versions = manifest.get("versions", [])
    if len(versions) <= max_versions:
        return
    versions_to_delete = versions[max_versions:]
    for ver in versions_to_delete:
        version_id = ver.get("id")
        if version_id == current:
            continue
        prefix = f"versions/{version_id}/"
        objs = list_s3_objects(s3, bucket, prefix)
        for key in objs:
            s3.delete_object(Bucket=bucket, Key=key)
    manifest["versions"] = versions[:max_versions]


def get_deploy_url(branch: str, deploy_prefix: str) -> str:
    if is_preview_branch(branch):
        preview_base = get_preview_base_url()
        if preview_base:
            return f"{preview_base}/{deploy_prefix}index.html"
        bucket = get_bucket_name()
        return f"https://{bucket}.s3.amazonaws.com/{deploy_prefix}index.html"
    else:
        return get_site_base_url() or f"https://{bucket}.s3.amazonaws.com/"


def deploy(branch_override: str = None):
    load_dotenv("config.env")
    bucket = get_bucket_name()
    region = "us-east-1"
    if not bucket:
        raise ValueError("S3_BUCKET 未配置")

    branch = branch_override or get_current_branch()
    deploy_prefix = get_deploy_prefix(branch)
    version_id = get_version_id()
    commit = get_current_commit()
    is_preview = is_preview_branch(branch)

    print("=" * 70)
    if is_preview:
        print(f"开始部署 PR 预览: {branch} -> {deploy_prefix}")
    else:
        print("开始生产部署")
    print(f"版本: {version_id}")
    print("=" * 70)

    s3 = boto3.client("s3", region_name=region)

    try:
        print("\n[1/4] 构建 Hugo 网站...")
        hugo_build()
        public_dir = get_public_dir()

        if not public_dir.exists():
            raise FileNotFoundError(f"构建输出目录不存在: {public_dir}")

        print("\n[2/4] 同步到版本目录...")
        version_prefix = "" if is_preview else f"versions/{version_id}/"
        s3_sync(key_prefix=deploy_prefix if is_preview else version_prefix, public_dir=public_dir)

        if not is_preview:
            print("\n[3/4] 复制版本到生产...")
            copied = copy_to_production(s3, bucket, f"versions/{version_id}/", "")
            print(f"复制 {copied} 个文件到生产根目录")

            print("\n[3/4] 更新版本清单...")
            manifest = get_version_manifest(s3, bucket)
            version_entry = {
                "id": version_id,
                "commit": commit,
                "branch": branch,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            manifest["versions"].insert(0, version_entry)
            manifest["current"] = version_id
            clean_old_versions(s3, bucket, manifest)
            save_version_manifest(s3, bucket, manifest)

            print("\n[4/4] 刷新 CloudFront 缓存...")
            cf_invalidate()
        else:
            print("\n[3/4] 预览部署跳过 CloudFront 缓存刷新...")
            print("\n[4/4] 预览部署完成")

        deploy_url = get_deploy_url(branch, deploy_prefix)
        print("\n" + "=" * 70)
        print("部署成功!")
        print(f"部署 URL: {deploy_url}")
        print("=" * 70)

        return {
            "branch": branch,
            "version_id": version_id,
            "is_preview": is_preview,
            "deploy_prefix": deploy_prefix,
            "url": deploy_url,
        }

    except Exception as e:
        print(f"\n部署失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="部署 Hugo 网站")
    parser.add_argument("--branch", "-b", help="指定分支名（默认从 Git 获取）")
    args = parser.parse_args()
    deploy(branch_override=args.branch)


if __name__ == "__main__":
    main()
