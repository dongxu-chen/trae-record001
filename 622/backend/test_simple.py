import sys
import io
import time
from PIL import Image
import numpy as np
import requests

BASE_URL = 'http://localhost:8000'

def create_test_image(size=512):
    img = Image.new('RGB', (size, size), color=(100, 150, 200))
    arr = np.array(img).astype(np.int32)
    for i in range(size):
        for j in range(size):
            arr[i, j] = (
                int(100 + 50 * np.sin(i / 50) + 30 * np.cos(j / 40)),
                int(150 + 40 * np.cos(i / 60) - 20 * np.sin(j / 30)),
                int(200 - 30 * np.sin(i / 45) + 40 * np.cos(j / 55))
            )
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)

def upload_test_image():
    img = create_test_image()
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    files = {'file': ('test.jpg', img_byte_arr, 'image/jpeg')}
    response = requests.post(f'{BASE_URL}/api/upload', files=files)
    return response.json()

def test_feedback():
    print("\n" + "="*50)
    print("Test 1: User Feedback System")
    print("="*50)
    data = {
        'style_id': 'vangogh',
        'rating': 5,
        'user_id': 'test_user',
        'content_id': None
    }
    response = requests.post(f'{BASE_URL}/api/feedback', json=data)
    result = response.json()
    print(f"Status: {response.status_code}")
    if response.status_code == 200 and result.get('status') == 'success':
        print("PASS: User feedback test")
        return True
    else:
        print(f"FAIL: {result}")
        return False

def test_feedback_and_train():
    print("\n" + "="*50)
    print("Test 2: Feedback + Training Flow")
    print("="*50)
    upload_result = upload_test_image()
    content_id = upload_result.get('id')
    print(f"Uploaded image ID: {content_id}")
    ratings = [(5, 'vangogh'), (4, 'watercolor'), (5, 'cyberpunk')]
    for rating, style_id in ratings:
        data = {
            'style_id': style_id,
            'rating': rating,
            'user_id': 'test_user',
            'content_id': content_id
        }
        response = requests.post(f'{BASE_URL}/api/feedback', json=data)
        result = response.json()
        print(f"  Rate {style_id}: {rating} - {result.get('feedback_count')} feedbacks")
        time.sleep(0.1)
    train_data = {
        'user_id': 'test_user',
        'name': 'My Art Style',
        'base_styles': {'vangogh': 0.5, 'watercolor': 0.5}
    }
    response = requests.post(f'{BASE_URL}/api/train-model', json=train_data)
    result = response.json()
    print(f"Train status: {response.status_code}")
    if response.status_code == 200 and result.get('status') == 'success':
        model = result.get('model', {})
        print(f"PASS: Training successful! Model ID: {model.get('id')}")
        return True
    else:
        print(f"FAIL: {result.get('error')}")
        return False

def test_mixed_transfer():
    print("\n" + "="*50)
    print("Test 3: Multi-style Weighted Blending")
    print("="*50)
    upload_result = upload_test_image()
    content_id = upload_result.get('id')
    print(f"Uploaded image ID: {content_id}")
    style_weights = {'vangogh': 0.4, 'watercolor': 0.3, 'cyberpunk': 0.3}
    data = {
        'content_id': content_id,
        'style_weights': style_weights,
        'intensity': 0.7,
        'model_type': 'sd_turbo',
        'preview': False
    }
    start_time = time.time()
    response = requests.post(f'{BASE_URL}/api/transfer-mixed', json=data)
    elapsed = time.time() - start_time
    result = response.json()
    print(f"Status: {response.status_code}")
    print(f"Elapsed: {elapsed*1000:.1f}ms")
    if response.status_code == 200 and 'output_url' in result:
        print(f"PASS: Mixed transfer successful! URL: {result['output_url']}")
        print(f"  Inference time: {result.get('inference_time_ms')}ms")
        return True
    else:
        print(f"FAIL: {result.get('error')}")
        return False

def test_batch_transfer():
    print("\n" + "="*50)
    print("Test 4: Batch Transfer (Multi-image Multi-style)")
    print("="*50)
    content_ids = []
    for i in range(3):
        upload_result = upload_test_image()
        content_ids.append(upload_result.get('id'))
        print(f"  Image {i+1} ID: {content_ids[-1]}")
        time.sleep(0.1)
    style_ids = ['vangogh', 'watercolor', 'cyberpunk']
    data = {
        'content_ids': content_ids,
        'style_ids': style_ids,
        'intensity': 0.7,
        'model_type': 'sd_turbo'
    }
    start_time = time.time()
    response = requests.post(f'{BASE_URL}/api/batch-transfer', json=data, timeout=60)
    elapsed = time.time() - start_time
    result = response.json()
    print(f"Status: {response.status_code}")
    print(f"Total time: {elapsed*1000:.1f}ms")
    if response.status_code == 200:
        print(f"PASS: Batch transfer successful!")
        print(f"  Total: {result.get('total')}")
        print(f"  Success: {result.get('success')}")
        print(f"  Failed: {result.get('failed')}")
        print(f"  Total time: {result.get('total_time_ms')}ms")
        avg = float(result.get('total_time_ms', 0)) / max(1, result.get('success', 1))
        print(f"  Average per image: {avg:.1f}ms")
        return result.get('success') > 0
    else:
        print(f"FAIL: {result.get('error')}")
        return False

def test_batch_mixed_transfer():
    print("\n" + "="*50)
    print("Test 5: Batch Mixed Transfer")
    print("="*50)
    content_ids = []
    for i in range(2):
        upload_result = upload_test_image()
        content_ids.append(upload_result.get('id'))
        print(f"  Image {i+1} ID: {content_ids[-1]}")
        time.sleep(0.1)
    style_combinations = [
        {'vangogh': 0.6, 'watercolor': 0.4},
        {'cyberpunk': 0.5, 'picasso': 0.5}
    ]
    data = {
        'content_ids': content_ids,
        'style_combinations': style_combinations,
        'intensity': 0.7,
        'model_type': 'sd_turbo'
    }
    start_time = time.time()
    response = requests.post(f'{BASE_URL}/api/batch-transfer-mixed', json=data, timeout=60)
    elapsed = time.time() - start_time
    result = response.json()
    print(f"Status: {response.status_code}")
    print(f"Total time: {elapsed*1000:.1f}ms")
    if response.status_code == 200:
        print(f"PASS: Batch mixed transfer successful!")
        print(f"  Total: {result.get('total')}")
        print(f"  Success: {result.get('success')}")
        print(f"  Failed: {result.get('failed')}")
        return result.get('success') > 0
    else:
        print(f"FAIL: {result.get('error')}")
        return False

def test_extended_styles():
    print("\n" + "="*50)
    print("Test 6: Extended Styles List (with personalized)")
    print("="*50)
    response = requests.get(f'{BASE_URL}/api/styles/extended', params={'user_id': 'test_user'})
    result = response.json()
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        styles = result.get('styles', [])
        personalized = [s for s in styles if s.get('category') == 'personalized']
        print(f"PASS: Extended styles retrieved!")
        print(f"  Total styles: {len(styles)}")
        print(f"  Base styles: {len(styles) - len(personalized)}")
        print(f"  Personalized models: {len(personalized)}")
        return True
    else:
        print("FAIL: Could not retrieve styles")
        return False

def main():
    print("\nStarting new features tests")
    time.sleep(1)
    results = []
    try:
        results.append(('User feedback system', test_feedback()))
        results.append(('Feedback + training flow', test_feedback_and_train()))
        results.append(('Multi-style blending', test_mixed_transfer()))
        results.append(('Batch transfer', test_batch_transfer()))
        results.append(('Batch mixed transfer', test_batch_mixed_transfer()))
        results.append(('Extended styles list', test_extended_styles()))
    except Exception as e:
        print(f"\nError during tests: {e}")
        import traceback
        traceback.print_exc()
    print("\n" + "="*50)
    print("Test Results Summary")
    print("="*50)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status} - {name}")
    print("-"*50)
    print(f"Total: {passed}/{total} tests passed")
    if passed == total:
        print("\nAll tests passed! New features work correctly!")
    else:
        print(f"\n{total - passed} tests failed")
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
