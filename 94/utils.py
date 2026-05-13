#!/usr/bin/env python3
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def get_current_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def get_current_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception:
        return datetime.now().strftime("%Y%m%d%H%M%S")


def sanitize_branch_name(branch: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "-", branch)
    return sanitized.strip("-")


def get_deploy_prefix(branch: str) -> str:
    sanitized = sanitize_branch_name(branch)
    if sanitized in ["main", "master", "production", "prod"]:
        return ""
    return f"preview/{sanitized}/"


def is_preview_branch(branch: str) -> bool:
    return branch not in ["main", "master", "production", "prod"]


def get_version_id() -> str:
    commit = get_current_commit()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{ts}-{commit}"


def get_public_dir() -> Path:
    return Path(os.getenv("HUGO_PUBLIC_DIR", "public"))


def get_bucket_name() -> str:
    return os.getenv("S3_BUCKET", "")


def get_preview_base_url() -> str:
    return os.getenv("PREVIEW_BASE_URL", "").rstrip("/")


def get_site_base_url() -> str:
    return os.getenv("SITE_BASE_URL", "").rstrip("/")


def get_max_version_history() -> int:
    return int(os.getenv("MAX_VERSION_HISTORY", "10"))


def get_preview_expire_days() -> int:
    return int(os.getenv("PREVIEW_EXPIRE_DAYS", "30"))
