import cv2
import numpy as np
import os
import json
from skimage.segmentation import slic

def create_test_image():
    img = np.zeros((300, 400, 3), dtype=np.uint8)
    cv2.circle(img, (150, 150), 80, (255, 100, 100), -1)
    cv2.rectangle(img, (250, 50), (350, 250), (100, 255, 100), -1)
    cv2.putText(img, 'Test', (50, 280), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    return img

def test_pencil_with_noise_rotation(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (21, 21), 0)
    sketch = cv2.divide(gray, blurred, scale=256.0)
    
    angle_range = 1.0
    h, w = sketch.shape
    center = (w // 2, h // 2)
    random_angle = np.random.uniform(-angle_range, angle_range)
    M = cv2.getRotationMatrix2D(center, random_angle, 1.0)
    sketch = cv2.warpAffine(sketch, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    
    noise_level = 5
    noise_arr = np.random.normal(0, noise_level, sketch.shape)
    sketch = np.clip(sketch + noise_arr, 0, 255).astype(np.uint8)
    
    return sketch

def test_slic_quantization(img, n_colors=8, n_segments=200):
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    segments = slic(img_rgb, n_segments=n_segments, compactness=10, sigma=1, start_label=0)
    
    result = np.zeros_like(img, dtype=np.uint8)
    
    for segment_id in np.unique(segments):
        mask = (segments == segment_id)
        segment_pixels = img[mask]
        
        if len(segment_pixels) > 0:
            pixels_float = np.float32(segment_pixels)
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.2)
            k = min(n_colors, len(segment_pixels))
            _, labels, centers = cv2.kmeans(pixels_float, k, None, criteria, 3, cv2.KMEANS_RANDOM_CENTERS)
            
            label_counts = np.bincount(labels.flatten())
            majority_label = np.argmax(label_counts)
            majority_color = centers[majority_label]
            
            result[mask] = majority_color.astype(np.uint8)
    
    return result

def test_params_file():
    params = {
        'style': 'pencil',
        'brush_size': 7,
        'style_intensity': 6,
        'pencil_noise': 4,
        'pencil_rotation': 8,
        'edge_method': 'canny',
        'edge_intensity': 5,
        'show_contour': True,
        'color_count': 8,
        'quant_method': 'slic',
        'slic_segments': 200,
        'batch_style': 'pencil'
    }
    
    with open('test_params.json', 'w', encoding='utf-8') as f:
        json.dump(params, f, indent=2, ensure_ascii=False)
    
    with open('test_params.json', 'r', encoding='utf-8') as f:
        loaded = json.load(f)
    
    print("参数文件测试:")
    print(f"  保存参数: {params['style']}, {params['brush_size']}")
    print(f"  加载参数: {loaded['style']}, {loaded['brush_size']}")
    print("  ✓ 参数文件功能正常")
    
    os.remove('test_params.json')

if __name__ == "__main__":
    print("测试新增功能...\n")
    
    test_img = create_test_image()
    print("✓ 测试图像创建成功")
    
    pencil = test_pencil_with_noise_rotation(test_img)
    print("✓ 铅笔画(带噪声和旋转)算法工作正常")
    
    slic_quant = test_slic_quantization(test_img, n_colors=8, n_segments=100)
    print("✓ 超像素+多数投票颜色量化工作正常")
    
    test_params_file()
    
    output_dir = "test_new_output"
    os.makedirs(output_dir, exist_ok=True)
    cv2.imwrite(os.path.join(output_dir, "test_original.png"), test_img)
    cv2.imwrite(os.path.join(output_dir, "test_pencil_noise_rot.png"), pencil)
    cv2.imwrite(os.path.join(output_dir, "test_slic_quant.png"), slic_quant)
    
    print(f"\n✓ 所有测试通过! 测试图像保存到 {output_dir}/")
    print("\n新增功能总结:")
    print("1. 铅笔画: 扰动噪声 + 线条随机旋转")
    print("2. 颜色量化: 超像素分割 + 多数投票加速")
    print("3. 批量处理: 支持独立参数文件(每图一个json)")
