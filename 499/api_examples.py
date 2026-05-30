import json
from datetime import datetime, timedelta


def generate_single_review_example():
    example = {
        "review_id": "r001",
        "user_id": "u001",
        "product_id": "p001",
        "content": "这款手机使用了一个月，整体体验非常好。屏幕显示效果清晰，色彩还原准确。电池续航不错，拍照效果超出预期。",
        "rating": 5,
        "helpful_votes": 156,
        "create_time": (datetime.now() - timedelta(days=7)).isoformat(),
        "is_verified_purchase": True,
        "has_images": True,
        "has_videos": True,
        "user_profile": {
            "user_id": "u001",
            "account_age_days": 365,
            "total_reviews": 50,
            "verified_purchases": 45,
            "helpful_votes_received": 200,
            "review_removal_count": 0,
            "average_rating": 4.2
        }
    }
    print("=" * 60)
    print("单条评论评分 - 请求示例")
    print("=" * 60)
    print("\nPOST /score")
    print("\n请求体:")
    print(json.dumps(example, indent=2, ensure_ascii=False))
    return example


def generate_batch_example():
    reviews = []

    base_time = datetime.now()

    user_profiles = {
        "u001": {
            "user_id": "u001",
            "account_age_days": 365,
            "total_reviews": 50,
            "verified_purchases": 45,
            "helpful_votes_received": 200,
            "review_removal_count": 0,
            "average_rating": 4.2
        },
        "u002": {
            "user_id": "u002",
            "account_age_days": 3,
            "total_reviews": 1,
            "verified_purchases": 0,
            "helpful_votes_received": 0,
            "review_removal_count": 0,
            "average_rating": 5.0
        }
    }

    reviews.append({
        "review_id": "r001",
        "user_id": "u001",
        "product_id": "p001",
        "content": "买的第二件了，之前买过一件质量很好，这次是回购。衣服做工精细，面料很舒服，洗了好几次都没有变形。",
        "rating": 5,
        "helpful_votes": 89,
        "create_time": (base_time - timedelta(days=14)).isoformat(),
        "is_verified_purchase": True,
        "has_images": True,
        "has_videos": False,
        "user_profile": user_profiles["u001"]
    })

    reviews.append({
        "review_id": "r002",
        "user_id": "u002",
        "product_id": "p001",
        "content": "好",
        "rating": 5,
        "helpful_votes": 0,
        "create_time": (base_time - timedelta(hours=1)).isoformat(),
        "is_verified_purchase": False,
        "has_images": False,
        "has_videos": False,
        "user_profile": user_profiles["u002"]
    })

    reviews.append({
        "review_id": "r003",
        "user_id": "u001",
        "product_id": "p001",
        "content": "质量一般，做工有点粗糙。材质和描述的不太一样，尺寸比我预期的小了一点。",
        "rating": 3,
        "helpful_votes": 23,
        "create_time": (base_time - timedelta(days=30)).isoformat(),
        "is_verified_purchase": True,
        "has_images": True,
        "has_videos": False,
        "user_profile": user_profiles["u001"]
    })

    batch = {"reviews": reviews}

    print("\n" + "=" * 60)
    print("批量评分 - 请求示例")
    print("=" * 60)
    print("\nPOST /batch/score")
    print("\n请求体:")
    print(json.dumps(batch, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("批量排序 - 请求示例")
    print("=" * 60)
    print("\nPOST /batch/sort?collapse_low_quality=true")
    print("\n请求体与批量评分相同")

    return batch


def show_endpoints():
    print("\n" + "=" * 60)
    print("API 接口列表")
    print("=" * 60)

    endpoints = [
        ("GET", "/health", "健康检查"),
        ("GET", "/config", "查看系统配置（权重、阈值）"),
        ("GET", "/stats", "查看系统统计信息"),
        ("POST", "/score", "单条评论质量评分"),
        ("POST", "/batch/score", "批量评论质量评分（最多1000条）"),
        ("POST", "/batch/sort", "批量评分并排序，支持自动折叠低质量"),
    ]

    print(f"\n{'方法':<6} {'接口':<20} {'描述'}")
    print("-" * 60)
    for method, path, desc in endpoints:
        print(f"{method:<6} {path:<20} {desc}")


def show_curl_examples():
    print("\n" + "=" * 60)
    print("cURL 调用示例")
    print("=" * 60)

    print("\n1. 健康检查:")
    print("curl http://localhost:8000/health")

    print("\n2. 查看配置:")
    print("curl http://localhost:8000/config")

    print("\n3. 单条评论评分:")
    print("""curl -X POST http://localhost:8000/score \\
  -H "Content-Type: application/json" \\
  -d '{
    "review_id": "r001",
    "user_id": "u001",
    "product_id": "p001",
    "content": "这款手机质量很好，屏幕清晰，电池续航也不错。",
    "rating": 5,
    "helpful_votes": 10,
    "create_time": "2024-01-15T10:30:00",
    "is_verified_purchase": true,
    "has_images": true,
    "has_videos": false
  }'""")


def main():
    print("电商评论质量评分系统 - API 使用指南")
    print("=" * 60)

    generate_single_review_example()
    generate_batch_example()
    show_endpoints()
    show_curl_examples()

    print("\n" + "=" * 60)
    print("启动服务命令:")
    print("  python main.py")
    print("  或: uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
    print("\n访问 API 文档:")
    print("  Swagger UI: http://localhost:8000/docs")
    print("  ReDoc: http://localhost:8000/redoc")
    print("=" * 60)


if __name__ == "__main__":
    main()
