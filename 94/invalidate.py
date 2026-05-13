#!/usr/bin/env python3
import os

import boto3
from dotenv import load_dotenv


def normalize_path(path: str) -> str:
    path = path.strip()
    if not path.startswith("/"):
        path = "/" + path
    return path


def get_default_paths() -> list:
    return [
        "/*",
        "/index.html",
        "/404.html",
        "/css/*",
        "/js/*",
        "/images/*",
        "/img/*",
    ]


def invalidate(paths=None):
    load_dotenv("config.env")
    distribution_id = os.getenv("CLOUDFRONT_DISTRIBUTION_ID")
    region = os.getenv("AWS_REGION", "us-east-1")

    if not distribution_id:
        raise ValueError("CLOUDFRONT_DISTRIBUTION_ID 未配置")

    if paths is None:
        paths = get_default_paths()
    else:
        paths = [normalize_path(p) for p in paths]

    cloudfront = boto3.client("cloudfront", region_name=region)
    response = cloudfront.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            "Paths": {
                "Quantity": len(paths),
                "Items": paths,
            },
            "CallerReference": f"deploy-{os.getpid()}-{int(os.times()[4])}",
        },
    )

    invalidation_id = response["Invalidation"]["Id"]
    status = response["Invalidation"]["Status"]
    print(f"已创建 CloudFront 失效: {invalidation_id}, 状态: {status}")
    print(f"失效路径: {', '.join(paths)}")


if __name__ == "__main__":
    import sys
    paths = sys.argv[1:] if len(sys.argv) > 1 else None
    invalidate(paths)
