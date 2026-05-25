import requests
import json
import time
from collections import Counter

BASE_URL = 'http://localhost:5000'


def test_grayscale_routing(num_requests=100):
    print("=" * 60)
    print(f"Testing Grayscale Routing - {num_requests} requests")
    print("=" * 60)
    
    version_counts = Counter()
    
    for i in range(num_requests):
        user_id = f"user_test_{i}"
        data = {
            "user_id": user_id,
            "video_id": f"video_{i}",
            "title": "测试视频标题",
            "tags": "测试,标签",
            "category": "科技",
            "duration": 300,
            "user_history": "video_1,video_2,video_3"
        }
        
        try:
            response = requests.post(f'{BASE_URL}/predict', json=data, timeout=5)
            if response.status_code == 200:
                result = response.json()
                version = result.get('model_version', 'unknown')
                version_counts[version] += 1
        except Exception as e:
            print(f"Request {i} failed: {e}")
    
    print(f"\nRouting distribution:")
    for version, count in version_counts.most_common():
        ratio = count / num_requests * 100
        print(f"  {version}: {count} ({ratio:.1f}%)")
    
    print("\nChecking routing stats...")
    try:
        response = requests.get(f'{BASE_URL}/router/stats')
        if response.status_code == 200:
            stats = response.json()
            print(f"  Total requests: {stats.get('total_requests', 0)}")
            print(f"  Default version: {stats.get('default_version', 'N/A')}")
            for version, info in stats.get('versions', {}).items():
                print(f"  {version}: {info.get('requests', 0)} requests, "
                      f"configured ratio: {info.get('traffic_ratio_configured', 0):.1%}")
    except Exception as e:
        print(f"Failed to get stats: {e}")


def test_user_consistent_routing():
    print("\n" + "=" * 60)
    print("Testing User-Consistent Routing")
    print("=" * 60)
    
    user_id = "consistent_user_12345"
    results = []
    
    for i in range(10):
        data = {
            "user_id": user_id,
            "video_id": f"video_{i}",
            "title": "测试视频",
            "tags": "测试",
            "category": "游戏",
            "duration": 200,
            "user_history": "video_100"
        }
        
        try:
            response = requests.post(f'{BASE_URL}/predict', json=data, timeout=5)
            if response.status_code == 200:
                version = response.json().get('model_version', 'unknown')
                results.append(version)
        except Exception as e:
            print(f"Request failed: {e}")
    
    unique_versions = set(results)
    print(f"\nUser {user_id} was routed to: {unique_versions}")
    if len(unique_versions) == 1:
        print("✓ User consistently routed to the same model version!")
    else:
        print(f"✗ User routed to {len(unique_versions)} different versions")


def test_cold_start_users():
    print("\n" + "=" * 60)
    print("Testing Cold Start Handling")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "New user (no history)",
            "user_id": "new_user_" + str(int(time.time())),
            "user_history": "",
            "category": "科技"
        },
        {
            "name": "User with minimal history",
            "user_id": "minimal_user_" + str(int(time.time())),
            "user_history": "video_1",
            "category": "游戏"
        },
        {
            "name": "Existing user simulation",
            "user_id": "user_123",
            "user_history": "video_1,video_2,video_3,video_4,video_5,video_6,video_7,video_8,video_9,video_10",
            "category": "娱乐"
        }
    ]
    
    for test_case in test_cases:
        data = {
            "user_id": test_case['user_id'],
            "video_id": "video_test",
            "title": f"{test_case['name']}测试视频",
            "tags": "测试,视频",
            "category": test_case['category'],
            "duration": 300,
            "user_history": test_case['user_history']
        }
        
        try:
            response = requests.post(f'{BASE_URL}/predict', json=data, timeout=5)
            if response.status_code == 200:
                result = response.json()
                cold_start_info = result.get('cold_start_info', {})
                
                print(f"\n{test_case['name']}:")
                print(f"  User ID: {test_case['user_id']}")
                print(f"  Is cold start: {cold_start_info.get('is_cold_start', 'N/A')}")
                print(f"  Data source: {cold_start_info.get('source', 'N/A')}")
                print(f"  Confidence: {cold_start_info.get('confidence', 0):.2f}")
                print(f"  Model CTR: {result.get('model_ctr', 0):.4f}")
                print(f"  Final CTR: {result.get('predicted_ctr', 0):.4f}")
        except Exception as e:
            print(f"\n{test_case['name']} failed: {e}")


def test_version_update():
    print("\n" + "=" * 60)
    print("Testing Traffic Ratio Update")
    print("=" * 60)
    
    update_data = {
        "version": "v2",
        "traffic_ratio": 0.5
    }
    
    try:
        response = requests.post(f'{BASE_URL}/router/update_ratio', json=update_data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Updated v2 traffic ratio to {result.get('new_traffic_ratio', 0):.1%}")
        else:
            print(f"✗ Update failed: {response.text}")
    except Exception as e:
        print(f"✗ Request failed: {e}")


def test_rank_with_cold_start():
    print("\n" + "=" * 60)
    print("Testing Ranking with Cold Start")
    print("=" * 60)
    
    data = {
        "user_id": "cold_start_rank_user_" + str(int(time.time())),
        "user_history": "",
        "videos": [
            {
                "video_id": "v1",
                "title": "Python编程教程",
                "tags": "Python,编程,教程",
                "category": "教育",
                "duration": 600
            },
            {
                "video_id": "v2",
                "title": "游戏精彩集锦",
                "tags": "游戏,电竞,精彩",
                "category": "游戏",
                "duration": 180
            },
            {
                "video_id": "v3",
                "title": "美食制作",
                "tags": "美食,烹饪,家常菜",
                "category": "美食",
                "duration": 420
            }
        ]
    }
    
    try:
        response = requests.post(f'{BASE_URL}/rank', json=data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"\nRanked videos for cold start user:")
            for video in result.get('ranked_videos', []):
                cold_info = video.get('cold_start_info', {})
                print(f"  Rank {video.get('rank')}: {video.get('title')}")
                print(f"    CTR: {video.get('predicted_ctr', 0):.4f}")
                print(f"    Cold start: {cold_info.get('is_cold_start', False)}")
                print(f"    Source: {cold_info.get('source', 'N/A')}")
    except Exception as e:
        print(f"✗ Request failed: {e}")


def test_specific_version():
    print("\n" + "=" * 60)
    print("Testing Specific Version Request")
    print("=" * 60)
    
    data = {
        "user_id": "user_specific_version",
        "video_id": "video_test",
        "title": "指定版本测试",
        "tags": "测试",
        "category": "科技",
        "duration": 300,
        "user_history": "video_1,video_2",
        "model_version": "v1"
    }
    
    try:
        response = requests.post(f'{BASE_URL}/predict', json=data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            version = result.get('model_version', 'unknown')
            print(f"Requested v1, got: {version}")
            if version == 'v1':
                print("✓ Successfully routed to requested version!")
            else:
                print(f"✗ Expected v1 but got {version}")
    except Exception as e:
        print(f"✗ Request failed: {e}")


if __name__ == '__main__':
    print("=" * 60)
    print("Advanced Features Test Suite")
    print("  - Grayscale Routing")
    print("  - Cold Start Handling")
    print("  - Model Versioning")
    print("=" * 60)
    
    try:
        response = requests.get(f'{BASE_URL}/health', timeout=5)
        if response.status_code != 200:
            print("Server not healthy!")
            exit(1)
    except Exception as e:
        print(f"Cannot connect to server: {e}")
        print("Please start the server first: python -m src.api.app")
        exit(1)
    
    try:
        test_grayscale_routing(num_requests=50)
        test_user_consistent_routing()
        test_cold_start_users()
        test_version_update()
        test_rank_with_cold_start()
        test_specific_version()
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
