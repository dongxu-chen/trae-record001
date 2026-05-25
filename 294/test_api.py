import requests
import json
import time

BASE_URL = 'http://localhost:5000'


def test_health():
    print("Testing /health endpoint...")
    response = requests.get(f'{BASE_URL}/health')
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()


def test_predict():
    print("\nTesting /predict endpoint...")
    data = {
        "user_id": "user_123",
        "video_id": "video_456",
        "title": "Python机器学习入门教程",
        "tags": "Python,机器学习,AI",
        "category": "科技",
        "duration": 300,
        "user_history": "video_100,video_200,video_300"
    }
    response = requests.post(f'{BASE_URL}/predict', json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()


def test_rank():
    print("\nTesting /rank endpoint...")
    data = {
        "user_id": "user_789",
        "user_history": "video_100,video_200,video_300,video_400",
        "videos": [
            {
                "video_id": "video_001",
                "title": "如何学好Python编程",
                "tags": "Python,编程,教程",
                "category": "教育",
                "duration": 600
            },
            {
                "video_id": "video_002",
                "title": "游戏精彩操作集锦",
                "tags": "游戏,电竞,精彩",
                "category": "游戏",
                "duration": 180
            },
            {
                "video_id": "video_003",
                "title": "美食制作全过程",
                "tags": "美食,烹饪,家常菜",
                "category": "美食",
                "duration": 420
            },
            {
                "video_id": "video_004",
                "title": "科技产品开箱评测",
                "tags": "科技,数码,评测",
                "category": "科技",
                "duration": 540
            },
            {
                "video_id": "video_005",
                "title": "旅游vlog分享",
                "tags": "旅游,旅行,vlog",
                "category": "旅游",
                "duration": 360
            }
        ]
    }
    response = requests.post(f'{BASE_URL}/rank', json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    if 'ranked_videos' in result:
        print("Ranked videos:")
        for video in result['ranked_videos']:
            print(f"  Rank {video['rank']}: {video['title']} - CTR: {video['predicted_ctr']:.4f}")
    else:
        print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
    return result


def test_batch_predict():
    print("\nTesting /batch_predict endpoint...")
    data = {
        "samples": [
            {
                "user_id": "user_001",
                "video_id": "video_101",
                "title": "深度学习入门",
                "tags": "深度学习,AI,机器学习",
                "category": "教育",
                "duration": 900,
                "user_history": "video_1,video_2"
            },
            {
                "user_id": "user_002",
                "video_id": "video_102",
                "title": "音乐MV首播",
                "tags": "音乐,歌曲,原创",
                "category": "音乐",
                "duration": 240,
                "user_history": "video_3,video_4"
            }
        ]
    }
    response = requests.post(f'{BASE_URL}/batch_predict', json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()


def test_index():
    print("\nTesting / endpoint...")
    response = requests.get(f'{BASE_URL}/')
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()


if __name__ == '__main__':
    print("=" * 60)
    print("Video CTR Prediction API Test Suite")
    print("=" * 60)
    
    try:
        test_index()
        test_health()
        test_predict()
        test_rank()
        test_batch_predict()
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to the API server.")
        print("Please make sure the server is running: python -m src.api.app")
        print("Or: python src/api/app.py")
    except Exception as e:
        print(f"\nError: {e}")
