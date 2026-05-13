#!/usr/bin/env python3
import argparse
import json
import os
import sys

import boto3
from dotenv import load_dotenv

from invalidate import invalidate as cf_invalidate


VERSION_MANIFEST_KEY = ".versions.json"


def list_s3_objects(s3, bucket: str, prefix: str) -> list:
    paginator = s3.get_paginator("list_objects_v2")
    objects = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
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


def save_version_manifest(s3, bucket: str, manifest: dict) -> None:
    s3.put_object(
        Bucket=bucket,
        Key=VERSION_MANIFEST_KEY,
        Body=json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json; charset=utf-8",
    )


def list_root_objects(s3, bucket: str) -> list:
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=bucket):
        if "Contents" in page:
            for obj in page["Contents"]:
                key = obj["Key"]
                if not key.startswith("preview/") and not key.startswith("versions/") and key != VERSION_MANIFEST_KEY:
                    keys.append(key)
    return keys


def copy_version_to_production(s3, bucket: str, version_id: str) -> int:
    source_prefix = f"versions/{version_id}/"
    source_objects = list_s3_objects(s3, bucket, source_prefix)
    if not source_objects:
        raise ValueError(f"版本 {version_id} 不存在")

    root_keys = list_root_objects(s3, bucket)
    for key in root_keys:
        s3.delete_object(Bucket=bucket, Key=key)

    copied = 0
    for source_key in source_objects:
        if not source_key.startswith(source_prefix):
            continue
        relative_key = source_key[len(source_prefix):]
        if not relative_key:
            continue
        s3.copy_object(
            Bucket=bucket,
            Key=relative_key,
            CopySource={"Bucket": bucket, "Key": source_key},
            MetadataDirective="REPLACE",
        )
        copied += 1
    return copied


def rollback(target_version: str = None):
    load_dotenv("config.env")
    bucket = os.getenv("S3_BUCKET")
    region = os.getenv("AWS_REGION", "us-east-1")
    if not bucket:
        raise ValueError("S3_BUCKET 未配置")

    s3 = boto3.client("s3", region_name=region)
    manifest = get_version_manifest(s3, bucket)
    versions = manifest.get("versions", [])

    if not versions:
        print("没有可用的版本历史")
        sys.exit(1)

    if target_version:
        target = next((v for v in versions if v.get("id") == target_version), None)
        if target is None:
            print(f"未找到版本: {target_version}")
            print("\n可用版本:")
            for i, v in enumerate(versions):
                print(f"  [{i+1}] {v.get('id')} ({v.get('commit', '')[:7]})")
            sys.exit(1)
    else:
        current_id = manifest.get("current")
        candidates = [v for v in versions if v.get("id") != current_id]
        if not candidates:
            print("没有可回滚的上一版本")
            sys.exit(1)
        target = candidates[0]

    target_id = target.get("id")
    target_commit = target.get("commit")
    target_branch = target.get("branch")

    print("=" * 70)
    print("生产版本回滚")
    print("=" * 70)
    print(f"\n当前版本: {manifest.get('current')}")
    print(f"回滚目标: {target_id}")
    print(f"分支: {target_branch}")
    print(f"Commit: {target_commit}")

    print(f"\n开始将生产环境回滚到 {target_id}...")
    copied = copy_version_to_production(s3, bucket, target_id)
    print(f"复制 {copied} 个文件到生产根目录")

    manifest["current"] = target_id
    save_version_manifest(s3, bucket, manifest)
    print("版本清单已更新")

    print("\n刷新 CloudFront 缓存...")
    cf_invalidate()

    print("\n" + "=" * 70)
    print(f"回滚成功！当前版本: {target_id}")
    print("=" * 70)

    return {"version_id": target_id, "copied": copied}


def main():
    parser = argparse.ArgumentParser(description="回滚生产版本")
    parser.add_argument("--version", "-v", help="指定回滚目标版本 ID（默认回滚到上一版本）")
    args = parser.parse_args()
    rollback(target_version=args.version)


if __name__ == "__main__":
    main()
