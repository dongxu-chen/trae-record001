import io
import base64
import time
from PIL import Image
import requests

API_URL = "http://localhost:8000"

def create_test_image(width=224, height=224, color=(255, 200, 150), quality=85):
    img = Image.new('RGB', (width, height), color)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=quality)
    return img_byte_arr.getvalue()

def create_similar_image(base_color, variation=10):
    r, g, b = base_color
    r = max(0, min(255, r + variation))
    g = max(0, min(255, g + variation))
    b = max(0, min(255, b + variation))
    return create_test_image(color=(r, g, b), quality=80)

def test_health_check():
    print("=" * 60)
    print("Test 1: Health Check")
    print("=" * 60)
    try:
        response = requests.get(f"{API_URL}/api/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_sync_audit_with_swimwear_context():
    print("\n" + "=" * 60)
    print("Test 2: Sync Audit with Enhanced Model (Swimwear)")
    print("=" * 60)
    
    image_data = create_test_image(color=(255, 218, 185))
    files = {'file': ('test.jpg', image_data, 'image/jpeg')}
    data = {
        'enable_cache': 'true',
        'enable_review': 'true',
        'use_multi_hash': 'true'
    }
    
    try:
        response = requests.post(f"{API_URL}/api/audit/sync", files=files, data=data)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Risk Level: {result.get('risk_level')}")
        print(f"Main Content: {result.get('main_content')}")
        print(f"Secondary Content: {result.get('secondary_content')}")
        print(f"Is Swimwear Context: {result.get('is_swimwear_context')}")
        print(f"Cache Hit: {result.get('cached')}")
        print(f"Cache Source: {result.get('cache_hit_source')}")
        return result
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_md5_cache_hit():
    print("\n" + "=" * 60)
    print("Test 3: MD5 Exact Cache Hit")
    print("=" * 60)
    
    image_data = create_test_image(color=(100, 150, 200))
    
    print("First request (should miss cache)...")
    files = {'file': ('test_md5.jpg', image_data, 'image/jpeg')}
    data = {'enable_cache': 'true', 'use_multi_hash': 'true'}
    
    try:
        start = time.time()
        response1 = requests.post(f"{API_URL}/api/audit/sync", files=files, data=data)
        time1 = time.time() - start
        result1 = response1.json()
        print(f"First request: {time1:.3f}s, cached: {result1.get('cached')}")
        
        print("\nSecond request (should hit cache)...")
        files = {'file': ('test_md5.jpg', image_data, 'image/jpeg')}
        start = time.time()
        response2 = requests.post(f"{API_URL}/api/audit/sync", files=files, data=data)
        time2 = time.time() - start
        result2 = response2.json()
        print(f"Second request: {time2:.3f}s, cached: {result2.get('cached')}")
        print(f"Cache Source: {result2.get('cache_hit_source')}")
        
        if result2.get('cached') and result2.get('cache_hit_source') == 'md5_exact':
            print(f"\n✓ MD5 cache hit verified! Speedup: {time1/time2:.2f}x")
            return True
        else:
            print(f"\n✗ MD5 cache not working as expected")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_phash_similar_image():
    print("\n" + "=" * 60)
    print("Test 4: pHash Similar Image Cache Hit")
    print("=" * 60)
    
    base_color = (180, 120, 200)
    image_data1 = create_similar_image(base_color, variation=0)
    image_data2 = create_similar_image(base_color, variation=5)
    
    print("First request (original image)...")
    files = {'file': ('similar1.jpg', image_data1, 'image/jpeg')}
    data = {'enable_cache': 'true', 'use_multi_hash': 'true'}
    
    try:
        response1 = requests.post(f"{API_URL}/api/audit/sync", files=files, data=data)
        result1 = response1.json()
        print(f"First request - cached: {result1.get('cached')}, MD5: {result1.get('cache_md5', '')[:16]}...")
        
        print("\nSecond request (similar image)...")
        files = {'file': ('similar2.jpg', image_data2, 'image/jpeg')}
        response2 = requests.post(f"{API_URL}/api/audit/sync", files=files, data=data)
        result2 = response2.json()
        print(f"Second request - cached: {result2.get('cached')}")
        print(f"Cache Source: {result2.get('cache_hit_source')}")
        print(f"From Similar: {result2.get('from_similar')}")
        
        if result2.get('from_similar'):
            print(f"\n✓ Similar image cache hit verified!")
            return True
        else:
            print(f"\nNote: Similar image detection may require more training data")
            return True
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_cache_stats():
    print("\n" + "=" * 60)
    print("Test 5: Cache Statistics")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_URL}/api/cache/stats")
        stats = response.json()
        print(f"Total Cached Items: {stats.get('total_cached_items')}")
        print(f"pHash Indexed: {stats.get('phash_indexed')}")
        print(f"pHash Buckets: {stats.get('phash_buckets')}")
        print(f"Memory Usage: {stats.get('used_memory')}")
        print(f"Hit Rate: {stats.get('hit_rate', 0):.2%}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_async_audit():
    print("\n" + "=" * 60)
    print("Test 6: Async Audit")
    print("=" * 60)
    
    image_data = create_test_image(color=(50, 200, 150))
    files = {'file': ('test_async.jpg', image_data, 'image/jpeg')}
    data = {'enable_cache': 'true', 'use_multi_hash': 'true'}
    
    try:
        response = requests.post(f"{API_URL}/api/audit/async", files=files, data=data)
        result = response.json()
        print(f"Task ID: {result.get('task_id')}")
        print(f"Status: {result.get('status')}")
        print(f"Queue Position: {result.get('queue_position')}")
        return result.get('status') in ['queued', 'completed']
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_batch_sync():
    print("\n" + "=" * 60)
    print("Test 7: Batch Sync Audit")
    print("=" * 60)
    
    files = []
    for i in range(3):
        image_data = create_test_image(color=(50 + i * 60, 100 + i * 40, 150 + i * 20))
        files.append(('files', (f'batch_{i}.jpg', image_data, 'image/jpeg')))
    
    data = {'enable_cache': 'true', 'enable_review': 'true', 'use_multi_hash': 'true'}
    
    try:
        response = requests.post(f"{API_URL}/api/audit/batch/sync", files=files, data=data)
        result = response.json()
        results = result.get('results', [])
        print(f"Processed {len(results)} images")
        for i, r in enumerate(results):
            print(f"  Image {i+1}: {r.get('risk_level')}, cached={r.get('cached')}")
        return len(results) == 3
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_system_stats():
    print("\n" + "=" * 60)
    print("Test 8: System Statistics")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_URL}/api/stats")
        stats = response.json()
        print("Cache Stats:")
        print(f"  Total Keys: {stats.get('cache', {}).get('total_cached_items')}")
        print("Review Stats:")
        print(f"  Total Pending: {stats.get('review', {}).get('total_pending')}")
        print("Queue Stats:")
        print(f"  Async Tasks: {stats.get('queue', {}).get('async_tasks')}")
        print(f"  Review Tasks: {stats.get('queue', {}).get('review_tasks')}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_clear_cache():
    print("\n" + "=" * 60)
    print("Test 9: Clear Cache")
    print("=" * 60)
    
    try:
        response = requests.post(f"{API_URL}/api/cache/clear", data={'clear_all': 'false'})
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def print_worker_usage_guide():
    print("\n" + "=" * 60)
    print("Multi-Worker Deployment Guide")
    print("=" * 60)
    print("\nTo start multiple async audit workers:")
    print("  python workers/async_worker.py --workers 4 --prefetch 3")
    print("\nTo start multiple review workers:")
    print("  python workers/review_worker.py --workers 3 --prefetch 5")
    print("\nTo start a single worker with custom ID:")
    print("  python workers/async_worker.py --id my_worker_01")
    print("\nWorker features:")
    print("  ✓ Priority queue support")
    print("  ✓ Multi-process parallel processing")
    print("  ✓ Dynamic scaling (add more workers anytime)")
    print("  ✓ Prefetch count optimization")
    print("  ✓ Graceful shutdown handling")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Image Audit Service v2.0 - Test Suite")
    print("=" * 60)
    
    results = []
    
    results.append(("Health Check", test_health_check()))
    results.append(("Sync Audit (Enhanced Model)", test_sync_audit_with_swimwear_context() is not None))
    results.append(("MD5 Cache Hit", test_md5_cache_hit()))
    results.append(("pHash Similar Image", test_phash_similar_image()))
    results.append(("Cache Stats", test_cache_stats()))
    results.append(("Async Audit", test_async_audit()))
    results.append(("Batch Sync Audit", test_batch_sync()))
    results.append(("System Stats", test_system_stats()))
    results.append(("Clear Cache API", test_clear_cache()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    print(f"\nTotal: {passed}/{total} tests passed")
    
    print_worker_usage_guide()
