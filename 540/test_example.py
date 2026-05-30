#!/usr/bin/env python3
import os
import numpy as np
import cv2
from raster_to_vector import RasterToVector


def create_test_image(output_path='test_image.png'):
    height, width = 400, 600
    image = np.ones((height, width, 3), dtype=np.uint8) * 240
    
    cv2.circle(image, (150, 150), 80, (255, 100, 100), -1)
    cv2.circle(image, (150, 150), 80, (200, 50, 50), 3)
    
    cv2.rectangle(image, (350, 70), (520, 230), (100, 200, 100), -1)
    cv2.rectangle(image, (350, 70), (520, 230), (50, 150, 50), 3)
    
    pts = np.array([[100, 280], [200, 350], [300, 280], [250, 380], [150, 380]], np.int32)
    cv2.fillPoly(image, [pts], (100, 100, 255))
    cv2.polylines(image, [pts], True, (50, 50, 200), 3)
    
    cv2.ellipse(image, (450, 320), (100, 50), 30, 0, 360, (255, 200, 100), -1)
    cv2.ellipse(image, (450, 320), (100, 50), 30, 0, 360, (200, 150, 50), 3)
    
    for _ in range(200):
        x = np.random.randint(0, width)
        y = np.random.randint(0, height)
        image[y, x] = np.random.randint(0, 255, 3)
    
    cv2.imwrite(output_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    print(f"测试图像已创建: {output_path}")
    return output_path


def test_basic_conversion():
    print("\n=== 测试1: 基本转换 ===")
    input_img = create_test_image()
    output_svg = 'output_basic.svg'
    
    converter = RasterToVector(input_img)
    converter.convert(output_svg, n_colors=8)
    
    print(f"输出文件: {output_svg}")
    print(f"轮廓数量: {len(converter.contours)}")
    return os.path.exists(output_svg)


def test_color_quantization():
    print("\n=== 测试2: 颜色量化效果 ===")
    input_img = 'test_image.png'
    
    converter = RasterToVector(input_img)
    converter.load_image()
    
    for n_colors in [4, 8, 16]:
        quantized = converter.color_quantization(converter.original_image, n_colors=n_colors)
        output_path = f'quantized_{n_colors}.png'
        cv2.imwrite(output_path, cv2.cvtColor(quantized, cv2.COLOR_RGB2BGR))
        print(f"颜色数 {n_colors}: {output_path}")
    
    return True


def test_edge_detection_methods():
    print("\n=== 测试3: 边缘检测方法 ===")
    input_img = 'test_image.png'
    
    converter = RasterToVector(input_img)
    converter.preprocess(n_colors=8)
    
    methods = ['canny', 'sobel', 'laplacian']
    for method in methods:
        edges = converter.detect_edges(method=method)
        output_path = f'edges_{method}.png'
        cv2.imwrite(output_path, edges)
        print(f"方法 {method}: {output_path}")
    
    return True


def test_denoising_methods():
    print("\n=== 测试4: 去噪方法 ===")
    input_img = 'test_image.png'
    
    converter = RasterToVector(input_img)
    converter.load_image()
    
    methods = ['bilateral', 'gaussian', 'median', 'nl_means']
    for method in methods:
        denoised = converter.denoise(converter.original_image, method=method)
        output_path = f'denoised_{method}.png'
        cv2.imwrite(output_path, cv2.cvtColor(denoised, cv2.COLOR_RGB2BGR))
        print(f"方法 {method}: {output_path}")
    
    return True


def test_curve_fitting():
    print("\n=== 测试5: 曲线拟合对比 ===")
    input_img = 'test_image.png'
    
    converter1 = RasterToVector(input_img)
    converter1.convert('output_no_curve.svg', use_curve_fitting=False, n_colors=8)
    print(f"无曲线拟合: output_no_curve.svg (轮廓数: {len(converter1.contours)})")
    
    converter2 = RasterToVector(input_img)
    converter2.convert('output_with_curve.svg', use_curve_fitting=True, n_colors=8)
    print(f"有曲线拟合: output_with_curve.svg (轮廓数: {len(converter2.contours)})")
    
    return True


def test_with_parameters():
    print("\n=== 测试6: 自定义参数 ===")
    input_img = 'test_image.png'
    output_svg = 'output_custom.svg'
    
    converter = RasterToVector(input_img)
    converter.convert(
        output_svg,
        denoise_method='nl_means',
        n_colors=16,
        edge_method='canny',
        low_threshold=30,
        high_threshold=100,
        min_contour_area=20,
        use_curve_fitting=True,
        stroke_width=0.5
    )
    
    print(f"自定义参数输出: {output_svg}")
    return os.path.exists(output_svg)


def main():
    print("=" * 50)
    print("光栅图像矢量化工具 - 测试脚本")
    print("=" * 50)
    
    results = []
    
    results.append(("基本转换", test_basic_conversion()))
    results.append(("颜色量化", test_color_quantization()))
    results.append(("边缘检测方法", test_edge_detection_methods()))
    results.append(("去噪方法", test_denoising_methods()))
    results.append(("曲线拟合", test_curve_fitting()))
    results.append(("自定义参数", test_with_parameters()))
    
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print("=" * 50)
    for name, result in results:
        status = "通过" if result else "失败"
        print(f"  {name}: {status}")
    
    print("\n所有测试完成!")


if __name__ == '__main__':
    main()
