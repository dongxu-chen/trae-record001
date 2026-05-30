import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import base64
import numpy as np
import cv2
from config import Config

Config.ensure_dirs()

BASE_URL = f"http://localhost:{Config.FLASK_PORT}"


def create_test_image():
    img = np.zeros((300, 400, 3), dtype=np.uint8)
    cv2.circle(img, (200, 150), 80, (255, 100, 100), -1)
    cv2.rectangle(img, (50, 50), (150, 250), (100, 255, 100), -1)
    return img


def image_to_base64(image):
    _, buffer = cv2.imencode('.png', image)
    return base64.b64encode(buffer).decode('utf-8')


def test_health():
    print("测试健康检查接口...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"  状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  状态: {data.get('status')}")
            print(f"  当前模型: {data.get('model', {}).get('current_model')}")
            print(f"  设备: {data.get('device')}")
            print("  ✓ 健康检查通过")
        return True
    except Exception as e:
        print(f"  ✗ 健康检查失败: {e}")
        return False


def test_models():
    print("\n测试模型列表接口...")
    try:
        response = requests.get(f"{BASE_URL}/api/models")
        print(f"  状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  当前模型: {data.get('current_model')}")
            print(f"  可用模型: {list(data.get('available_models', {}).keys())}")
            print("  ✓ 获取模型列表成功")
        return True
    except Exception as e:
        print(f"  ✗ 获取模型列表失败: {e}")
        return False


def test_switch_model():
    print("\n测试模型切换接口...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/switch-model",
            data={'model_name': 'poolnet'}
        )
        print(f"  状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  成功: {data.get('success')}")
            print(f"  消息: {data.get('message')}")
            print("  ✓ 模型切换成功")
        
        response = requests.post(
            f"{BASE_URL}/api/switch-model",
            data={'model_name': 'basnet'}
        )
        print(f"  切回basnet: {response.status_code == 200}")
        return True
    except Exception as e:
        print(f"  ✗ 模型切换失败: {e}")
        return False


def test_predict_upload():
    print("\n测试单图预测接口(文件上传)...")
    try:
        test_img = create_test_image()
        _, img_buffer = cv2.imencode('.png', test_img)
        
        files = {'image': ('test.png', img_buffer.tobytes(), 'image/png')}
        data = {
            'threshold': 0.5,
            'edge_refinement': 'true',
            'return_base64': 'true'
        }
        
        response = requests.post(f"{BASE_URL}/api/predict", files=files, data=data)
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  成功: {result.get('success')}")
            print(f"  文件名: {result.get('filename')}")
            print(f"  原始尺寸: {result.get('original_size')}")
            print(f"  平均显著值: {result.get('stats', {}).get('mean_saliency'):.4f}")
            print(f"  返回saliency_map: {'saliency_map' in result}")
            print(f"  返回binary_mask: {'binary_mask' in result}")
            print(f"  返回overlay: {'overlay' in result}")
            print("  ✓ 单图预测成功")
        return True
    except Exception as e:
        print(f"  ✗ 单图预测失败: {e}")
        return False


def test_predict_base64():
    print("\n测试单图预测接口(Base64)...")
    try:
        test_img = create_test_image()
        img_base64 = image_to_base64(test_img)
        
        data = {
            'image_base64': f"data:image/png;base64,{img_base64}",
            'threshold': 0.5,
            'edge_refinement': 'true',
            'return_base64': 'false'
        }
        
        response = requests.post(f"{BASE_URL}/api/predict", data=data)
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  成功: {result.get('success')}")
            print(f"  掩膜面积比: {result.get('stats', {}).get('mask_area_ratio'):.4f}")
            print("  ✓ Base64预测成功")
        return True
    except Exception as e:
        print(f"  ✗ Base64预测失败: {e}")
        return False


def test_batch_predict():
    print("\n测试批量预测接口...")
    try:
        files = []
        for i in range(3):
            img = create_test_image()
            _, img_buffer = cv2.imencode('.png', img)
            files.append(('images', (f'test_{i}.png', img_buffer.tobytes(), 'image/png')))
        
        data = {
            'threshold': 0.5,
            'edge_refinement': 'true',
            'return_base64': 'false'
        }
        
        response = requests.post(f"{BASE_URL}/api/predict/batch", files=files, data=data)
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  成功: {result.get('success')}")
            print(f"  处理图像数: {result.get('total_images')}")
            print(f"  结果数: {len(result.get('results', []))}")
            print("  ✓ 批量预测成功")
        return True
    except Exception as e:
        print(f"  ✗ 批量预测失败: {e}")
        return False


def test_segment():
    print("\n测试目标分割接口...")
    try:
        test_img = create_test_image()
        _, img_buffer = cv2.imencode('.png', test_img)
        
        files = {'image': ('test.png', img_buffer.tobytes(), 'image/png')}
        data = {
            'threshold': 0.5,
            'edge_refinement': 'true',
            'apply_type': 'segment'
        }
        
        response = requests.post(f"{BASE_URL}/api/segment", files=files, data=data)
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  成功: {result.get('success')}")
            print(f"  检测到目标数: {result.get('num_objects')}")
            print(f"  边界框数: {len(result.get('bounding_boxes', []))}")
            print(f"  返回分割图: {'segmented_image' in result}")
            print(f"  返回Alpha掩膜: {'alpha_mask' in result}")
            print("  ✓ 目标分割成功")
        
        print("\n  测试模糊背景模式...")
        data['apply_type'] = 'blur_background'
        response = requests.post(f"{BASE_URL}/api/segment", files=files, data=data)
        print(f"  模糊背景: {response.status_code == 200}")
        
        print("\n  测试纯色背景模式...")
        data['apply_type'] = 'color_background'
        data['bg_color'] = '255,255,255'
        response = requests.post(f"{BASE_URL}/api/segment", files=files, data=data)
        print(f"  纯色背景: {response.status_code == 200}")
        
        return True
    except Exception as e:
        print(f"  ✗ 目标分割失败: {e}")
        return False


def run_all_tests():
    print("=" * 60)
    print("Flask API 自动化测试")
    print("=" * 60)
    
    tests = [
        test_health,
        test_models,
        test_switch_model,
        test_predict_upload,
        test_predict_base64,
        test_batch_predict,
        test_segment
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    print(f"请确保Flask服务已启动: python run_api.py")
    print(f"服务地址: {BASE_URL}")
    print()
    
    choice = input("开始测试? (y/n): ").strip().lower()
    if choice == 'y':
        run_all_tests()
