import sys
import os
import io
import time
from PIL import Image
import numpy as np
import requests

BASE_URL = 'http://localhost:8000'

def create_test_image(size=512):
    img = Image.new('RGB', (size, size), color=(100, 150, 200))
    arr = np.array(img)
    for i in range(size):
        for j in range(size):
            arr[i, j] = (
                int(100 + 50 * np.sin(i / 50) + 30 * np.cos(j / 40)),
                int(150 + 40 * np.cos(i / 60) - 20 * np.sin(j / 30)),
                int(200 - 30 * np.sin(i / 45) + 40 * np.cos(j / 55))
            )
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
    print("测试1: 用户反馈评分系统")
    print("="*50)
    
    data = {
        'style_id': 'vangogh',
        'rating': 5,
        'user_id': 'test_user',
        'content_id': None
    }
    
    response = requests.post(f'{BASE_URL}/api/feedback', json=data)
    result = response.json()
    
    print(f"状态: {response.status_code}")
    print(f"结果: {result}")
    
    if response.status_code == 200 and result.get('status') == 'success':
        print("✅ 用户反馈测试通过")
        return True
    else:
        print("❌ 用户反馈测试失败")
        return False

def test_feedback_flow():
    print("\n" + "="*50)
    print("测试2: 完整反馈流程 (上传→评分→训练)")
    print("="*50)
    
    print("\n步骤1: 上传测试图片")
    upload_result = upload_test_image()
    content_id = upload_result.get('id')
    print(f"上传成功，图片ID: {content_id}")
    
    print("\n步骤2: 提交3条评分反馈 (需要至少3条才能训练)")
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
        print(f"  评分 {style_id}: {rating}星 - {result.get('feedback_count')}条反馈")
        time.sleep(0.1)
    
    print("\n步骤3: 训练个性化模型")
    train_data = {
        'user_id': 'test_user',
        'name': '我的艺术风格',
        'base_styles': {'vangogh': 0.5, 'watercolor': 0.5}
    }
    response = requests.post(f'{BASE_URL}/api/train-model', json=train_data)
    result = response.json()
    
    print(f"训练状态: {response.status_code}")
    
    if response.status_code == 200 and result.get('status') == 'success':
        model = result.get('model', {})
        print(f"✅ 训练成功! 模型ID: {model.get('id')}")
        print(f"   模型名称: {model.get('name')}")
        print(f"   风格权重: {model.get('style_weights')}")
        return True
    else:
        print(f"❌ 训练失败: {result.get('error')}")
        return False

def test_mixed_style_transfer():
    print("\n" + "="*50)
    print("测试3: 多风格加权融合")
    print("="*50)
    
    print("\n步骤1: 上传测试图片")
    upload_result = upload_test_image()
    content_id = upload_result.get('id')
    print(f"上传成功，图片ID: {content_id}")
    
    print("\n步骤2: 调用多风格融合API")
    style_weights = {
        'vangogh': 0.4,
        'watercolor': 0.3,
        'cyberpunk': 0.3
    }
    
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
    print(f"状态: {response.status_code}")
    print(f"推理时间: {elapsed*1000:.1f}ms")
    
    if response.status_code == 200 and 'output_url' in result:
        print(f"✅ 多风格融合成功! 输出URL: {result['output_url']}")
        print(f"   推理时间: {result.get('inference_time_ms')}ms")
        return True
    else:
        print(f"❌ 多风格融合失败: {result.get('error')}")
        return False

def test_batch_transfer():
    print("\n" + "="*50)
    print("测试4: 批量生成 (多图多风格)")
    print("="*50)
    
    print("\n步骤1: 上传3张测试图片")
    content_ids = []
    for i in range(3):
        upload_result = upload_test_image()
        content_id = upload_result.get('id')
        content_ids.append(content_id)
        print(f"  图片{i+1} ID: {content_id}")
        time.sleep(0.1)
    
    print("\n步骤2: 调用批量生成API (3图 × 3风格 = 9张)")
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
    print(f"状态: {response.status_code}")
    print(f"总耗时: {elapsed*1000:.1f}ms")
    
    if response.status_code == 200:
        print(f"✅ 批量生成成功!")
        print(f"   总数: {result.get('total')}")
        print(f"   成功: {result.get('success')}")
        print(f"   失败: {result.get('failed')}")
        print(f"   总耗时: {result.get('total_time_ms')}ms")
        print(f"   平均每张: {float(result.get('total_time_ms', 0)) / max(1, result.get('success', 1)):.1f}ms")
        
        if result.get('results'):
            first_success = next((r for r in result['results'] if r.get('success')), None)
            if first_success:
                print(f"   第一张输出: {first_success.get('output_url')}")
        
        return True
    else:
        print(f"❌ 批量生成失败: {result.get('error')}")
        return False

def test_batch_mixed_transfer():
    print("\n" + "="*50)
    print("测试5: 批量风格组合生成")
    print("="*50)
    
    print("\n步骤1: 上传2张测试图片")
    content_ids = []
    for i in range(2):
        upload_result = upload_test_image()
        content_id = upload_result.get('id')
        content_ids.append(content_id)
        print(f"  图片{i+1} ID: {content_id}")
        time.sleep(0.1)
    
    print("\n步骤2: 定义3个风格组合")
    style_combinations = [
        {'vangogh': 0.6, 'watercolor': 0.4},
        {'cyberpunk': 0.5, 'picasso': 0.5},
        {'monet': 0.3, 'watercolor': 0.4, 'oil_painting': 0.3}
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
    print(f"状态: {response.status_code}")
    print(f"总耗时: {elapsed*1000:.1f}ms")
    
    if response.status_code == 200:
        print(f"✅ 批量风格组合生成成功!")
        print(f"   总数: {result.get('total')}")
        print(f"   成功: {result.get('success')}")
        print(f"   失败: {result.get('failed')}")
        print(f"   总耗时: {result.get('total_time_ms')}ms")
        return True
    else:
        print(f"❌ 批量风格组合生成失败: {result.get('error')}")
        return False

def test_extended_styles():
    print("\n" + "="*50)
    print("测试6: 获取扩展风格列表 (包含个性化模型)")
    print("="*50)
    
    response = requests.get(f'{BASE_URL}/api/styles/extended', params={'user_id': 'test_user'})
    result = response.json()
    
    print(f"状态: {response.status_code}")
    
    if response.status_code == 200:
        styles = result.get('styles', [])
        personalized = [s for s in styles if s.get('category') == 'personalized']
        print(f"✅ 获取扩展风格列表成功!")
        print(f"   总风格数: {len(styles)}")
        print(f"   基础风格: {len(styles) - len(personalized)}")
        print(f"   个性化模型: {len(personalized)}")
        
        if personalized:
            print(f"   个性化模型列表:")
            for p in personalized:
                print(f"     - {p.get('name')} ({p.get('id')})")
        
        return True
    else:
        print(f"❌ 获取扩展风格列表失败")
        return False

def main():
    print("\n" + "🚀"*20)
    print("开始测试新功能: 反馈评分、个性化模型、风格融合、批量生成")
    print("🚀"*20)
    
    time.sleep(1)
    
    results = []
    
    try:
        results.append(('用户反馈系统', test_feedback()))
        results.append(('完整反馈+训练流程', test_feedback_flow()))
        results.append(('多风格加权融合', test_mixed_style_transfer()))
        results.append(('批量生成 (多图多风格)', test_batch_transfer()))
        results.append(('批量风格组合生成', test_batch_mixed_transfer()))
        results.append(('扩展风格列表', test_extended_styles()))
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*50)
    print("测试结果汇总")
    print("="*50)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("-"*50)
    print(f"总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过! 新功能运行正常!")
    else:
        print(f"\n⚠️  {total - passed} 项测试失败，请检查错误信息")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
