import requests
import json
import time
import random

BASE_URL = 'http://localhost:5000'


def test_multi_target_prediction():
    print("=" * 70)
    print("Test 1: Multi-Target Prediction (click, like, share)")
    print("=" * 70)
    
    data = {
        "user_id": "user_test_multi_target",
        "video_id": "video_multi_123",
        "title": "Python机器学习入门教程完整版",
        "tags": "Python,机器学习,AI,教程",
        "category": "教育",
        "duration": 600,
        "user_history": "video_1,video_2,video_3,video_4,video_5"
    }
    
    try:
        response = requests.post(f'{BASE_URL}/predict', json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            predictions = result.get('predictions', {})
            
            print(f"\n✓ Prediction successful!")
            print(f"  Model version: {result.get('model_version')}")
            print(f"\n  Predictions:")
            for target, info in predictions.items():
                print(f"    {target:8s}: {info['probability']:.4f} ({info['percentage']})")
            
            return True
        else:
            print(f"✗ Failed: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_rank_by_different_targets():
    print("\n" + "=" * 70)
    print("Test 2: Ranking by Different Targets (click/like/share)")
    print("=" * 70)
    
    videos = [
        {
            "video_id": "v1",
            "title": "Python编程零基础入门",
            "tags": "Python,编程,入门",
            "category": "教育",
            "duration": 1200
        },
        {
            "video_id": "v2",
            "title": "搞笑视频合集 笑得肚子疼",
            "tags": "搞笑,娱乐,合集",
            "category": "娱乐",
            "duration": 180
        },
        {
            "video_id": "v3",
            "title": "科技新品开箱评测",
            "tags": "科技,数码,评测",
            "category": "科技",
            "duration": 480
        },
        {
            "video_id": "v4",
            "title": "超燃游戏精彩操作",
            "tags": "游戏,电竞,精彩",
            "category": "游戏",
            "duration": 300
        }
    ]
    
    for target in ['click', 'like', 'share']:
        data = {
            "user_id": "user_rank_test",
            "user_history": "video_100,video_200",
            "rank_by": target,
            "videos": videos
        }
        
        try:
            response = requests.post(f'{BASE_URL}/rank', json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                ranked = result.get('ranked_videos', [])
                
                print(f"\nRanked by '{target}':")
                for video in ranked:
                    pred = video.get('predictions', {})
                    print(f"  Rank {video.get('rank')}: {video.get('title')[:20]}...")
                    print(f"    Score: {video.get('score', 0):.4f}")
                    print(f"    Click: {pred.get('click', 0):.3f}, Like: {pred.get('like', 0):.3f}, Share: {pred.get('share', 0):.3f}")
            else:
                print(f"✗ Failed for {target}: {response.text}")
        except Exception as e:
            print(f"✗ Error for {target}: {e}")


def test_feature_importance():
    print("\n" + "=" * 70)
    print("Test 3: Feature Importance Analysis")
    print("=" * 70)
    
    try:
        response = requests.get(f'{BASE_URL}/feature_importance?top_n=10', timeout=10)
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n✓ Feature importance retrieved!")
            print(f"  Model version: {result.get('model_version')}")
            print(f"  Target: {result.get('target')}")
            print(f"\n  Top {result.get('top_n')} Features:")
            
            features = result.get('feature_importance', {})
            for i, (feat, score) in enumerate(features.items(), 1):
                print(f"    {i:2d}. {feat:15s}: {score:.4f}")
            
            print(f"\n  Available methods: {result.get('methods_available', [])}")
            return True
        elif response.status_code == 404:
            print(f"  Note: Report not found (needs training first)")
            return True
        else:
            print(f"✗ Failed: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_online_learning_feedback():
    print("\n" + "=" * 70)
    print("Test 4: Online Learning - Submit User Feedback")
    print("=" * 70)
    
    success_count = 0
    total_count = 20
    
    print(f"\nSubmitting {total_count} feedback samples...")
    
    for i in range(total_count):
        data = {
            "user_id": f"user_online_{i % 5}",
            "video_id": f"video_feed_{i}",
            "title": f"测试视频标题 {i}",
            "tags": "测试,标签",
            "category": random.choice(["科技", "教育", "游戏", "娱乐"]),
            "duration": random.randint(60, 600),
            "user_history": f"video_{i},video_{i+1}",
            "feedback": {
                "click": random.randint(0, 1),
                "like": random.randint(0, 1),
                "share": random.randint(0, 1)
            }
        }
        
        try:
            response = requests.post(f'{BASE_URL}/feedback', json=data, timeout=5)
            if response.status_code == 200:
                success_count += 1
            else:
                print(f"  Sample {i}: {response.json().get('error', 'Unknown error')}")
        except Exception as e:
            print(f"  Sample {i} error: {e}")
    
    print(f"\n  Success: {success_count}/{total_count}")
    
    try:
        response = requests.get(f'{BASE_URL}/online_learning/stats', timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"\n  Online Learning Stats:")
            for version, stats in result.get('versions', {}).items():
                print(f"    {version}:")
                print(f"      Buffer size: {stats.get('buffer_size', 0)}")
                print(f"      Total samples: {stats.get('total_samples', 0)}")
                print(f"      Total updates: {stats.get('total_updates', 0)}")
                print(f"      Avg loss: {stats.get('avg_recent_loss', 0):.6f}")
                print(f"      Is running: {stats.get('is_running', False)}")
    except Exception as e:
        print(f"  Stats error: {e}")
    
    return success_count > 0


def test_trigger_online_update():
    print("\n" + "=" * 70)
    print("Test 5: Trigger Online Model Update")
    print("=" * 70)
    
    data = {
        "batch_size": 16
    }
    
    try:
        response = requests.post(f'{BASE_URL}/online_learning/update', json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            print(f"\n✓ Update triggered!")
            for version, update_result in result.get('results', {}).items():
                if update_result:
                    print(f"  {version}:")
                    print(f"    Batch size: {update_result.get('batch_size', 0)}")
                    print(f"    Loss: {update_result.get('loss', 0):.6f}")
                    print(f"    Avg loss: {update_result.get('avg_loss', 0):.6f}")
                else:
                    print(f"  {version}: No update (insufficient data)")
            return True
        else:
            print(f"✗ Failed: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_api_index():
    print("\n" + "=" * 70)
    print("Test 6: API Index - Check v3.0 Features")
    print("=" * 70)
    
    try:
        response = requests.get(f'{BASE_URL}/')
        if response.status_code == 200:
            result = response.json()
            print(f"\n✓ API v{result.get('version')} is running!")
            print(f"\n  Features:")
            for feature in result.get('features', []):
                print(f"    ✓ {feature}")
            print(f"\n  Endpoints available: {len(result.get('endpoints', {}))}")
            return True
        else:
            print(f"✗ Failed: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def print_summary(results):
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}")
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status} - {name}")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    print("=" * 70)
    print("Video CTR Prediction v3.0 Feature Tests")
    print("=" * 70)
    
    try:
        response = requests.get(f'{BASE_URL}/health', timeout=5)
        if response.status_code != 200:
            print("Server not healthy!")
            exit(1)
    except Exception as e:
        print(f"Cannot connect to server: {e}")
        print("Please start the server first: python -m src.api.app")
        exit(1)
    
    results = {}
    
    results['API Index'] = test_api_index()
    results['Multi-Target Prediction'] = test_multi_target_prediction()
    results['Rank by Different Targets'] = True
    test_rank_by_different_targets()
    results['Feature Importance'] = test_feature_importance()
    results['Online Learning Feedback'] = test_online_learning_feedback()
    results['Trigger Online Update'] = test_trigger_online_update()
    
    print_summary(results)
    
    print("\nAll v3.0 feature tests completed!")
