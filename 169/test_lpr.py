import os
import sys
import cv2
import numpy as np
import argparse
from datetime import datetime

from license_plate_recognition import LicensePlateRecognition
from image_enhancer import ImageEnhancer
from plate_corrector import PlateCorrector
from ocr_recognizer import OCRRecognizer


def create_test_image():
    test_dir = 'test_images'
    os.makedirs(test_dir, exist_ok=True)
    
    test_plates = [
        {
            'filename': os.path.join(test_dir, 'test_blue_plate.jpg'),
            'plate': '京A12345',
            'color': (255, 0, 0)
        },
        {
            'filename': os.path.join(test_dir, 'test_green_plate.jpg'),
            'plate': '沪DF12345',
            'color': (0, 255, 0)
        },
        {
            'filename': os.path.join(test_dir, 'test_yellow_plate.jpg'),
            'plate': '粤B67890',
            'color': (0, 255, 255)
        }
    ]
    
    for test_data in test_plates:
        img = np.ones((300, 600, 3), dtype=np.uint8) * 200
        
        plate_w, plate_h = 440, 140
        x1 = (600 - plate_w) // 2
        y1 = (300 - plate_h) // 2
        x2 = x1 + plate_w
        y2 = y1 + plate_h
        
        cv2.rectangle(img, (x1, y1), (x2, y2), test_data['color'], -1)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), 2)
        
        cv2.putText(
            img,
            test_data['plate'],
            (x1 + 20, y1 + plate_h // 2 + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            2.0,
            (255, 255, 255),
            3
        )
        
        cv2.imwrite(test_data['filename'], img)
        print(f"Created test image: {test_data['filename']}")
    
    return [t['filename'] for t in test_plates]


def test_single_image(lpr, image_path):
    print(f"\n{'='*60}")
    print(f"测试图片: {image_path}")
    print('='*60)
    
    result = lpr.recognize(image_path=image_path, save_images=False)
    
    if 'error' in result:
        print(f"❌ 错误: {result['error']}")
        return False
    
    print(f"✅ 成功: {result['success']}")
    print(f"📊 检测到车牌数: {result['plate_count']}")
    print(f"📐 图片尺寸: {result['image_size']}")
    
    for idx, plate in enumerate(result['results']):
        print(f"\n--- 车牌 #{idx} ---")
        print(f"  车牌号码: {plate['ocr_text']}")
        print(f"  车牌类型: {plate['plate_type_name']}")
        print(f"  检测置信度: {plate['detection_confidence']:.2f}%")
        print(f"  OCR置信度: {plate['ocr_confidence']:.2f}")
        print(f"  边框: {plate['bbox']}")
        print(f"  长宽比: {plate['aspect_ratio']:.2f}")
    
    if result['best_result']:
        print(f"\n🏆 最佳结果: {result['best_result']['ocr_text']}")
        print(f"   综合置信度: {result['overall_confidence']:.2f}")
    
    return result['success']


def test_batch(lpr, image_paths):
    print(f"\n{'='*60}")
    print("批量识别测试")
    print('='*60)
    
    results = lpr.recognize_batch(image_paths)
    
    success_count = 0
    for i, result in enumerate(results):
        print(f"\n图片 #{i}: {image_paths[i]}")
        print(f"  成功: {result.get('success', False)}")
        print(f"  车牌数: {result.get('plate_count', 0)}")
        if result.get('best_result'):
            print(f"  识别结果: {result['best_result'].get('ocr_text', 'N/A')}")
        if result.get('success'):
            success_count += 1
    
    print(f"\n📊 批量识别结果: {success_count}/{len(results)} 成功")
    return success_count


def test_system_info(lpr):
    print(f"\n{'='*60}")
    print("系统信息测试")
    print('='*60)
    
    info = lpr.get_system_info()
    print(f"模块状态:")
    for module, status in info['modules'].items():
        status_str = "✅ 正常" if status else "❌ 不可用"
        print(f"  {module}: {status_str}")
    
    print(f"\n支持的车牌类型:")
    for pt in info['supported_plate_types']:
        print(f"  {pt['name']} ({pt['code']}): {pt['chars']}字符")
    
    print(f"\n功能特性:")
    for feature in info['features']:
        print(f"  ✨ {feature}")


def test_low_light_enhancement(lpr, image_path):
    print(f"\n{'='*60}")
    print("低光照增强测试")
    print('='*60)
    
    image = cv2.imread(image_path)
    if image is None:
        print("❌ 无法加载图片")
        return
    
    bright = cv2.convertScaleAbs(image, alpha=0.3, beta=20)
    
    from image_enhancer import ImageEnhancer
    enhancer = ImageEnhancer()
    enhanced = enhancer.enhance(bright)
    
    test_dir = 'test_output'
    os.makedirs(test_dir, exist_ok=True)
    
    cv2.imwrite(os.path.join(test_dir, 'low_light_original.jpg'), bright)
    cv2.imwrite(os.path.join(test_dir, 'low_light_enhanced.jpg'), enhanced)
    
    print(f"✅ 低光照测试完成")
    print(f"   原始低光照图: {os.path.join(test_dir, 'low_light_original.jpg')}")
    print(f"   增强后图像: {os.path.join(test_dir, 'low_light_enhanced.jpg')}")


def main():
    parser = argparse.ArgumentParser(description='车牌识别系统测试')
    parser.add_argument('--image', type=str, help='测试图片路径')
    parser.add_argument('--dir', type=str, help='测试图片目录')
    parser.add_argument('--create-test', action='store_true', help='创建测试图片')
    parser.add_argument('--test-info', action='store_true', help='测试系统信息')
    parser.add_argument('--test-enhance', action='store_true', help='测试低光照增强')
    parser.add_argument('--test-msrcr', action='store_true', help='测试MSRCR算法')
    parser.add_argument('--test-perspective', action='store_true', help='测试透视变换校正')
    parser.add_argument('--test-new-energy', action='store_true', help='测试新能源车牌识别')
    
    args = parser.parse_args()
    
    print("🚗 车牌识别系统测试启动")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n🔧 初始化车牌识别系统...")
    lpr = LicensePlateRecognition()
    print("✅ 初始化完成")
    
    if args.test_info:
        test_system_info(lpr)
        return
    
    if args.test_new_energy:
        test_new_energy_ocr()
        print(f"\n🎉 测试完成!")
        return
    
    test_images = []
    
    if args.create_test:
        test_images = create_test_image()
    elif args.image:
        if os.path.exists(args.image):
            test_images = [args.image]
        else:
            print(f"❌ 图片不存在: {args.image}")
            return
    elif args.dir:
        if os.path.exists(args.dir):
            for ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                test_images.extend([
                    os.path.join(args.dir, f)
                    for f in os.listdir(args.dir)
                    if f.lower().endswith(ext)
                ])
        else:
            print(f"❌ 目录不存在: {args.dir}")
            return
    else:
        print("ℹ️  使用 --help 查看使用方法")
        print("ℹ️  示例: python test_lpr.py --create-test")
        print("ℹ️  示例: python test_lpr.py --image your_image.jpg")
        print("ℹ️  示例: python test_lpr.py --test-new-energy")
        return
    
    if not test_images:
        print("❌ 没有找到测试图片")
        return
    
    print(f"\n📸 测试图片: {len(test_images)} 张")
    
    if len(test_images) == 1:
        test_single_image(lpr, test_images[0])
    else:
        test_batch(lpr, test_images)
    
    if args.test_enhance and test_images:
        test_low_light_enhancement(lpr, test_images[0])
    
    if args.test_msrcr and test_images:
        test_msrcr_enhancement(test_images[0])
    
    if args.test_perspective and test_images:
        test_perspective_correction(test_images[0])
    
    print(f"\n🎉 测试完成!")


def test_msrcr_enhancement(image_path):
    print(f"\n{'='*60}")
    print("MSRCR 低光照增强测试")
    print('='*60)
    
    image = cv2.imread(image_path)
    if image is None:
        print("❌ 无法加载图片")
        return
    
    enhancer = ImageEnhancer()
    
    low_light = cv2.convertScaleAbs(image, alpha=0.3, beta=10)
    
    enhanced_msrcr = enhancer._msrcr_enhance(low_light)
    
    test_dir = 'test_output'
    os.makedirs(test_dir, exist_ok=True)
    
    cv2.imwrite(os.path.join(test_dir, 'msrcr_original.jpg'), image)
    cv2.imwrite(os.path.join(test_dir, 'msrcr_low_light.jpg'), low_light)
    cv2.imwrite(os.path.join(test_dir, 'msrcr_enhanced.jpg'), enhanced_msrcr)
    
    orig_brightness = np.mean(cv2.cvtColor(low_light, cv2.COLOR_BGR2GRAY))
    enh_brightness = np.mean(cv2.cvtColor(enhanced_msrcr, cv2.COLOR_BGR2GRAY))
    
    print(f"✅ MSRCR增强测试完成")
    print(f"   原始亮度: {orig_brightness:.2f}")
    print(f"   增强后亮度: {enh_brightness:.2f}")
    print(f"   低光照图: {os.path.join(test_dir, 'msrcr_low_light.jpg')}")
    print(f"   MSRCR增强图: {os.path.join(test_dir, 'msrcr_enhanced.jpg')}")


def test_perspective_correction(image_path):
    print(f"\n{'='*60}")
    print("透视变换校正测试")
    print('='*60)
    
    image = cv2.imread(image_path)
    if image is None:
        print("❌ 无法加载图片")
        return
    
    corrector = PlateCorrector()
    
    h, w = image.shape[:2]
    
    test_angles = [-30, -15, 0, 15, 30, 45, 60]
    
    test_dir = 'test_output'
    os.makedirs(test_dir, exist_ok=True)
    
    for angle in test_angles:
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image,
            M,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        
        rect = ((w // 2, h // 2), (min(w, h) * 0.8, min(w, h) * 0.3), angle)
        
        plate_info = {
            'plate_image': rotated,
            'rect': rect
        }
        
        corrected = corrector.correct(image, plate_info)
        
        if corrected is not None:
            output_path = os.path.join(test_dir, f'perspective_angle_{angle}.jpg')
            cv2.imwrite(output_path, corrected)
            print(f"   角度 {angle}°: 校正成功 -> {output_path}")
        else:
            print(f"   角度 {angle}°: 校正失败")
    
    print(f"\n✅ 透视变换校正测试完成")


def test_new_energy_ocr():
    print(f"\n{'='*60}")
    print("新能源车牌OCR识别测试")
    print('='*60)
    
    ocr = OCRRecognizer()
    
    test_cases = [
        ('京AD12345', 'new_energy_8'),
        ('沪AF67890', 'new_energy_8'),
        ('粤A123456', 'normal_7'),
        ('津B654321', 'normal_7'),
        ('京AD1234', 'new_energy_6'),
        ('沪F12345', 'normal_7_missing'),
    ]
    
    print("测试OCR字符校正功能:")
    print("-" * 60)
    
    for plate_text, desc in test_cases:
        simulated_result = ocr._validate_and_correct_plate(plate_text)
        plate_type = ocr._detect_plate_type(plate_text)
        
        print(f"\n测试用例: {plate_text} ({desc})")
        print(f"  检测类型: {plate_type}")
        print(f"  校正结果: {simulated_result}")
        print(f"  格式有效: {ocr._is_valid_format(simulated_result)}")
    
    print(f"\n✅ 新能源车牌OCR测试完成")


def test_new_energy_rules():
    print(f"\n{'='*60}")
    print("新能源车牌识别规则测试")
    print('='*60)
    
    ocr = OCRRecognizer()
    
    test_cases = [
        ('京AD12345', 8, True),
        ('京A123456', 7, True),
        ('京AD1234', 6, True),
        ('沪B12345', 7, False),
        ('粤C1234', 6, False),
    ]
    
    print("测试新能源车牌检测规则:")
    print("-" * 60)
    
    for plate_text, expected_len, should_be_new_energy in test_cases:
        plate_type = ocr._detect_plate_type(plate_text)
        is_new_energy = plate_type == 'new_energy'
        
        status = "✅" if is_new_energy == should_be_new_energy else "❌"
        print(f"{status} {plate_text}: 类型={plate_type}, 预期新能源={should_be_new_energy}")
    
    print(f"\n✅ 新能源车牌规则测试完成")


if __name__ == '__main__':
    main()
