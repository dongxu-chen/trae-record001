import io
import base64
from PIL import Image
import requests

def create_test_image(width=224, height=224, color=(255, 200, 150)):
    img = Image.new('RGB', (width, height), color)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()

def test_sync_audit():
    print("Testing sync audit...")
    image_data = create_test_image()
    
    files = {'file': ('test.jpg', image_data, 'image/jpeg')}
    data = {'enable_cache': 'true', 'enable_review': 'true'}
    
    try:
        response = requests.post(
            'http://localhost:8000/api/audit/sync',
            files=files,
            data=data
        )
        print(f"Status: {response.status_code}")
        print(f"Result: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_async_audit():
    print("\nTesting async audit...")
    image_data = create_test_image(color=(100, 150, 200))
    
    files = {'file': ('test_async.jpg', image_data, 'image/jpeg')}
    data = {'enable_cache': 'true'}
    
    try:
        response = requests.post(
            'http://localhost:8000/api/audit/async',
            files=files,
            data=data
        )
        print(f"Status: {response.status_code}")
        print(f"Result: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_batch_sync():
    print("\nTesting batch sync audit...")
    files = []
    for i in range(3):
        image_data = create_test_image(color=(50 + i * 50, 100 + i * 30, 150 + i * 20))
        files.append(('files', (f'test_{i}.jpg', image_data, 'image/jpeg')))
    
    data = {'enable_cache': 'true', 'enable_review': 'true'}
    
    try:
        response = requests.post(
            'http://localhost:8000/api/audit/batch/sync',
            files=files,
            data=data
        )
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Processed {len(result.get('results', []))} images")
        return result
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_base64_audit():
    print("\nTesting base64 audit...")
    image_data = create_test_image(color=(200, 100, 100))
    base64_str = base64.b64encode(image_data).decode('utf-8')
    
    data = {
        'image': base64_str,
        'enable_cache': 'true',
        'enable_review': 'true'
    }
    
    try:
        response = requests.post(
            'http://localhost:8000/api/audit/sync/base64',
            data=data
        )
        print(f"Status: {response.status_code}")
        print(f"Result: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_stats():
    print("\nTesting stats endpoint...")
    try:
        response = requests.get('http://localhost:8000/api/stats')
        print(f"Status: {response.status_code}")
        print(f"Stats: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_health():
    print("\nTesting health check...")
    try:
        response = requests.get('http://localhost:8000/api/health')
        print(f"Status: {response.status_code}")
        print(f"Health: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_cache_performance():
    print("\nTesting cache performance...")
    image_data = create_test_image(color=(128, 128, 128))
    
    files = {'file': ('test_cache.jpg', image_data, 'image/jpeg')}
    data = {'enable_cache': 'true', 'enable_review': 'false'}
    
    import time
    
    start = time.time()
    response1 = requests.post(
        'http://localhost:8000/api/audit/sync',
        files=files,
        data=data
    )
    time1 = time.time() - start
    print(f"First request: {time1:.3f}s, cached: {response1.json().get('cached')}")
    
    files = {'file': ('test_cache.jpg', image_data, 'image/jpeg')}
    start = time.time()
    response2 = requests.post(
        'http://localhost:8000/api/audit/sync',
        files=files,
        data=data
    )
    time2 = time.time() - start
    print(f"Second request: {time2:.3f}s, cached: {response2.json().get('cached')}")
    
    if time2 < time1:
        print(f"Cache speedup: {time1/time2:.2f}x")

if __name__ == "__main__":
    print("=" * 50)
    print("Image Audit Service Test Suite")
    print("=" * 50)
    
    test_health()
    test_sync_audit()
    test_async_audit()
    test_batch_sync()
    test_base64_audit()
    test_stats()
    test_cache_performance()
    
    print("\n" + "=" * 50)
    print("All tests completed!")
    print("=" * 50)
