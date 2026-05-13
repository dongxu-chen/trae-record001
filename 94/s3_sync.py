#!/usr/bin/env python3
import os
import hashlib
import mimetypes
from pathlib import Path

import boto3
from dotenv import load_dotenv

CONTENT_TYPE_MAP = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".webp": "image/webp",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".eot": "application/vnd.ms-fontobject",
    ".otf": "font/otf",
    ".txt": "text/plain; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".pdf": "application/pdf",
    ".zip": "application/zip",
}

mimetypes.init()
mimetypes.types_map[".css"] = "text/css; charset=utf-8"


def get_file_hash(file_path: Path) -> str:
    hasher = hashlib.md5()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_content_type(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext in CONTENT_TYPE_MAP:
        return CONTENT_TYPE_MAP[ext]
    content_type, _ = mimetypes.guess_type(str(file_path))
    if content_type is None:
        return "application/octet-stream"
    return content_type


def should_upload(local_file: Path, s3_obj) -> bool:
    if s3_obj is None:
        return True
    local_mtime = local_file.stat().st_mtime
    s3_mtime = s3_obj["LastModified"].timestamp()
    if local_mtime > s3_mtime:
        return True
    local_hash = get_file_hash(local_file)
    if "ETag" in s3_obj:
        s3_etag = s3_obj["ETag"].strip('"')
        if local_hash == s3_etag:
            return False
    return True


def sync(key_prefix: str = "", public_dir: Path = None) -> dict:
    load_dotenv("config.env")
    bucket_name = os.getenv("S3_BUCKET")
    region = os.getenv("AWS_REGION", "us-east-1")
    if public_dir is None:
        public_dir = Path(os.getenv("HUGO_PUBLIC_DIR", "public"))

    if not public_dir.exists():
        raise FileNotFoundError(f"目录不存在: {public_dir}")

    if key_prefix and not key_prefix.endswith("/"):
        key_prefix = key_prefix + "/"
    if key_prefix.startswith("/"):
        key_prefix = key_prefix.lstrip("/")

    s3 = boto3.client("s3", region_name=region)
    paginator = s3.get_paginator("list_objects_v2")
    s3_objects = {}
    for page in paginator.paginate(Bucket=bucket_name, Prefix=key_prefix):
        if "Contents" in page:
            for obj in page["Contents"]:
                key_without_prefix = obj["Key"][len(key_prefix):] if key_prefix else obj["Key"]
                s3_objects[key_without_prefix] = obj

    uploaded = 0
    skipped = 0
    uploaded_files = []

    for root, _, files in os.walk(public_dir):
        for filename in files:
            local_path = Path(root) / filename
            relative_key = str(local_path.relative_to(public_dir)).replace("\\", "/")
            full_key = key_prefix + relative_key if key_prefix else relative_key
            s3_obj = s3_objects.get(relative_key)

            if should_upload(local_path, s3_obj):
                content_type = get_content_type(local_path)
                print(f"上传: {full_key} ({content_type})")
                with local_path.open("rb") as f:
                    s3.put_object(
                        Bucket=bucket_name,
                        Key=full_key,
                        Body=f,
                        ContentType=content_type
                    )
                uploaded += 1
                uploaded_files.append(full_key)
            else:
                skipped += 1

    print(f"\n同步完成: 上传 {uploaded} 个文件, 跳过 {skipped} 个文件")
    return {
        "uploaded_count": uploaded,
        "skipped_count": skipped,
        "uploaded_files": uploaded_files,
        "prefix": key_prefix,
    }


if __name__ == "__main__":
    sync()
