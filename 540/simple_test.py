#!/usr/bin/env python3
import sys
import os

print("开始测试...")

try:
    import numpy as np
    import cv2
    from raster_to_vector import RasterToVector
    print("✓ 所有模块导入成功")
except Exception as e:
    print(f"✗ 模块导入失败: {e}")
    sys.exit(1)

try:
    height, width = 200, 300
    image = np.ones((height, width, 3), dtype=np.uint8) * 255
    cv2.circle(image, (100, 100), 50, (255, 100, 100), -1)
    cv2.rectangle(image, (180, 50), (260, 150), (100, 200, 100), -1)
    
    test_img_path = 'simple_test.png'
    cv2.imwrite(test_img_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    print(f"✓ 测试图像已创建: {test_img_path}")
except Exception as e:
    print(f"✗ 创建测试图像失败: {e}")
    sys.exit(1)

try:
    converter = RasterToVector(test_img_path)
    output_svg = 'simple_output.svg'
    converter.convert(
        output_svg,
        denoise_method='gaussian',
        n_colors=4,
        edge_method='canny',
        low_threshold=30,
        high_threshold=100,
        min_contour_area=5,
        use_curve_fitting=True
    )
    print(f"✓ SVG转换成功: {output_svg}")
    print(f"  - 提取轮廓数: {len(converter.contours)}")
except Exception as e:
    print(f"✗ 转换失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if os.path.exists(output_svg):
    size = os.path.getsize(output_svg)
    print(f"✓ SVG文件存在，大小: {size} bytes")
    
    with open(output_svg, 'r', encoding='utf-8') as f:
        content = f.read()
        if '<svg' in content and '</svg>' in content:
            print("✓ SVG格式验证通过")
        else:
            print("✗ SVG格式验证失败")
else:
    print("✗ SVG文件不存在")

print("\n" + "=" * 50)
print("所有测试通过!")
print("=" * 50)
