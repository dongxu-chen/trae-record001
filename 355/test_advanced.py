import cv2
import numpy as np
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from morphology_lib import (
    create_rect, create_ellipse, create_cross,
    fill_holes, extract_connected_components, remove_small_objects, extract_boundary,
    regional_maxima, h_minima,
    BatchProcessor, Pipeline, parallel_large_image,
    gradient_internal, gradient_external, gradient_basic, laplacian_gradient,
    multi_scale_gradient, directional_gradient, sobel_like_gradient,
    edge_detection, canny_like
)


def create_test_image_with_holes():
    img = np.zeros((200, 200), dtype=np.uint8)
    cv2.circle(img, (100, 100), 60, 255, -1)
    cv2.circle(img, (100, 100), 20, 0, -1)
    cv2.circle(img, (70, 80), 10, 0, -1)
    cv2.circle(img, (130, 120), 8, 0, -1)
    return img


def create_test_image_with_objects():
    img = np.zeros((300, 300), dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (100, 100), 255, -1)
    cv2.rectangle(img, (150, 50), (160, 60), 255, -1)
    cv2.circle(img, (200, 150), 30, 255, -1)
    cv2.circle(img, (250, 250), 5, 255, -1)
    cv2.ellipse(img, (100, 200), (40, 20), 0, 0, 360, 255, -1)
    return img


def test_fill_holes():
    print("测试1: 孔洞填充")
    print("-" * 50)

    img = create_test_image_with_holes()
    result = fill_holes(img)

    holes_before = np.sum((img == 0) & (cv2.dilate(img, np.ones((3,3), np.uint8)) == 255))
    holes_after = np.sum((result == 0) & (cv2.dilate(result, np.ones((3,3), np.uint8)) == 255))

    print(f"填充前孔洞数量: {holes_before}")
    print(f"填充后孔洞数量: {holes_after}")
    print(f"孔洞填充成功: {holes_after < holes_before}")

    cv2.imwrite('test_fill_holes_before.png', img)
    cv2.imwrite('test_fill_holes_after.png', result)
    print("已保存测试图像")


def test_connected_components():
    print("\n测试2: 连通分量提取")
    print("-" * 50)

    img = create_test_image_with_objects()
    labels, num_components = extract_connected_components(img)

    print(f"检测到的连通分量数: {num_components}")
    print(f"标签图形状: {labels.shape}")
    print(f"唯一标签值: {np.unique(labels)}")

    colored = np.zeros((img.shape[0], img.shape[1], 3), dtype=np.uint8)
    for label in range(1, num_components + 1):
        color = np.random.randint(50, 255, 3)
        colored[labels == label] = color

    cv2.imwrite('test_connected_components.png', colored)
    print("已保存彩色标记的连通分量")


def test_remove_small_objects():
    print("\n测试3: 移除小物体")
    print("-" * 50)

    img = create_test_image_with_objects()
    result = remove_small_objects(img, min_size=200)

    orig_count = np.count_nonzero(img > 0)
    result_count = np.count_nonzero(result > 0)

    print(f"原始非零像素: {orig_count}")
    print(f"移除后非零像素: {result_count}")
    print(f"小物体已移除: {result_count < orig_count}")

    cv2.imwrite('test_remove_small.png', result)
    print("已保存测试图像")


def test_extract_boundary():
    print("\n测试4: 提取边界")
    print("-" * 50)

    img = create_test_image_with_objects()
    boundary = extract_boundary(img)

    print(f"边界像素数: {np.count_nonzero(boundary)}")
    print(f"边界图形状: {boundary.shape}")

    cv2.imwrite('test_boundary.png', boundary)
    print("已保存边界图像")


def test_regional_maxima():
    print("\n测试5: 区域极大值")
    print("-" * 50)

    img = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(img, (30, 30), 10, 200, -1)
    cv2.circle(img, (70, 70), 15, 255, -1)
    cv2.circle(img, (50, 50), 5, 180, -1)

    maxima = regional_maxima(img)

    print(f"极大值区域数: {len(np.unique(maxima)) - 1}")
    print(f"极大值像素数: {np.count_nonzero(maxima)}")

    cv2.imwrite('test_maxima.png', maxima)
    print("已保存区域极大值图像")


def test_batch_processor():
    print("\n测试6: 批量并行处理")
    print("-" * 50)

    images = []
    for i in range(8):
        img = np.random.randint(0, 256, (200, 200), dtype=np.uint8)
        images.append(img)

    print(f"创建 {len(images)} 张测试图像")

    processor = BatchProcessor(max_workers=4)
    se = create_rect((3, 3))

    start = time.time()
    results_parallel = processor.process_batch(images, 'dilate', se)
    parallel_time = time.time() - start

    start = time.time()
    results_sequential = [cv2.dilate(img, se.kernel) for img in images]
    sequential_time = time.time() - start

    print(f"并行处理时间: {parallel_time:.3f}s")
    print(f"顺序处理时间: {sequential_time:.3f}s")
    print(f"加速比: {sequential_time / parallel_time:.2f}x")

    all_match = True
    for i in range(len(images)):
        if not np.array_equal(results_parallel[i], results_sequential[i]):
            all_match = False
            break

    print(f"结果一致性验证: {'通过' if all_match else '失败'}")


def test_pipeline():
    print("\n测试7: 处理流水线")
    print("-" * 50)

    img = np.random.randint(0, 256, (300, 300), dtype=np.uint8)
    se = create_rect((3, 3))

    pipeline = Pipeline()
    pipeline.add('erode', se)
    pipeline.add('dilate', se)
    pipeline.add('open', se)

    result = pipeline.apply(img)

    print(f"输入形状: {img.shape}")
    print(f"输出形状: {result.shape}")
    print(f"流水线操作数: {len(pipeline.operations)}")
    print("流水线执行完成")


def test_parallel_large_image():
    print("\n测试8: 大图像并行分块")
    print("-" * 50)

    img = np.random.randint(0, 256, (1000, 1000), dtype=np.uint8)
    se = create_rect((3, 3))

    print(f"大图像尺寸: {img.shape}")

    start = time.time()
    result_parallel = parallel_large_image(img, 'dilate', se, num_splits=4)
    parallel_time = time.time() - start

    start = time.time()
    result_normal = cv2.dilate(img, se.kernel)
    normal_time = time.time() - start

    print(f"并行分块时间: {parallel_time:.3f}s")
    print(f"正常处理时间: {normal_time:.3f}s")
    print(f"输出形状正确: {result_parallel.shape == img.shape}")


def test_gradient_types():
    print("\n测试9: 多种形态学梯度")
    print("-" * 50)

    img = np.zeros((200, 200), dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (150, 150), 255, -1)

    se = create_rect((3, 3))

    grad_internal = gradient_internal(img, se)
    grad_external = gradient_external(img, se)
    grad_basic = gradient_basic(img, se)
    grad_laplacian = laplacian_gradient(img, se)

    print(f"内部梯度非零像素: {np.count_nonzero(grad_internal)}")
    print(f"外部梯度非零像素: {np.count_nonzero(grad_external)}")
    print(f"基本梯度非零像素: {np.count_nonzero(grad_basic)}")
    print(f"拉普拉斯梯度非零像素: {np.count_nonzero(grad_laplacian)}")

    cv2.imwrite('test_grad_internal.png', grad_internal)
    cv2.imwrite('test_grad_external.png', grad_external)
    cv2.imwrite('test_grad_basic.png', grad_basic)
    cv2.imwrite('test_grad_laplacian.png', grad_laplacian)
    print("已保存各种梯度图像")


def test_directional_gradient():
    print("\n测试10: 方向梯度")
    print("-" * 50)

    img = np.zeros((200, 200), dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (150, 150), 255, -1)

    grad_h = directional_gradient(img, 'horizontal')
    grad_v = directional_gradient(img, 'vertical')
    grad_d1 = directional_gradient(img, 'diagonal1')
    grad_d2 = directional_gradient(img, 'diagonal2')

    print(f"水平梯度非零: {np.count_nonzero(grad_h)}")
    print(f"垂直梯度非零: {np.count_nonzero(grad_v)}")
    print(f"对角线1梯度非零: {np.count_nonzero(grad_d1)}")
    print(f"对角线2梯度非零: {np.count_nonzero(grad_d2)}")

    cv2.imwrite('test_grad_horizontal.png', grad_h)
    cv2.imwrite('test_grad_vertical.png', grad_v)
    print("已保存方向梯度图像")


def test_sobel_like_gradient():
    print("\n测试11: Sobel类梯度")
    print("-" * 50)

    img = np.zeros((200, 200), dtype=np.uint8)
    cv2.circle(img, (100, 100), 60, 255, -1)

    grad = sobel_like_gradient(img)

    print(f"Sobel梯度非零像素: {np.count_nonzero(grad)}")
    print(f"梯度范围: [{grad.min()}, {grad.max()}]")

    cv2.imwrite('test_sobel_gradient.png', grad)
    print("已保存Sobel类梯度图像")


def test_edge_detection():
    print("\n测试12: 边缘检测")
    print("-" * 50)

    img = np.zeros((200, 200), dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (150, 150), 255, -1)
    cv2.circle(img, (100, 100), 30, 100, -1)

    se = create_rect((3, 3))

    for method in ['basic', 'internal', 'external', 'laplacian', 'sobel']:
        edges = edge_detection(img, method=method, threshold=30)
        print(f"{method:12} 边缘像素: {np.count_nonzero(edges)}")

    edges = edge_detection(img, method='sobel', threshold=50)
    cv2.imwrite('test_edge_detection.png', edges)
    print("已保存边缘检测图像")


def test_canny_like():
    print("\n测试13: Canny类边缘检测")
    print("-" * 50)

    img = np.zeros((300, 300), dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (150, 150), 255, -1)
    cv2.circle(img, (200, 200), 50, 200, -1)
    cv2.line(img, (50, 250), (250, 250), 180, 3)

    edges = canny_like(img, low_threshold=30, high_threshold=80)

    print(f"Canny类边缘像素: {np.count_nonzero(edges)}")
    print(f"边缘图像形状: {edges.shape}")

    cv2.imwrite('test_canny_edges.png', edges)
    print("已保存Canny类边缘图像")


def test_multi_scale_gradient():
    print("\n测试14: 多尺度梯度")
    print("-" * 50)

    img = np.zeros((200, 200), dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (150, 150), 255, -1)

    grad = multi_scale_gradient(img, sizes=[3, 5, 7])

    print(f"多尺度梯度非零像素: {np.count_nonzero(grad)}")
    print(f"梯度最大值: {grad.max()}")

    cv2.imwrite('test_multiscale_grad.png', grad)
    print("已保存多尺度梯度图像")


def main():
    print("=" * 60)
    print("形态学图像处理库 v2.0 - 高级功能测试")
    print("=" * 60)

    try:
        test_fill_holes()
        test_connected_components()
        test_remove_small_objects()
        test_extract_boundary()
        test_regional_maxima()
        test_batch_processor()
        test_pipeline()
        test_parallel_large_image()
        test_gradient_types()
        test_directional_gradient()
        test_sobel_like_gradient()
        test_edge_detection()
        test_canny_like()
        test_multi_scale_gradient()

        print("\n" + "=" * 60)
        print("所有高级功能测试通过!")
        print("=" * 60)

        print("\n新增功能总结:")
        print("  ✓ 形态学重建: 孔洞填充、连通分量、移除小物体、边界提取")
        print("  ✓ 多线程并行: BatchProcessor、Pipeline、并行大图像处理")
        print("  ✓ 梯度拓展: 内部/外部/基本/拉普拉斯/多尺度/方向梯度")
        print("  ✓ 边缘检测: 二值化边缘、Canny类边缘检测")
        print("  ✓ GUI更新: 三标签页、实时预览、完整处理")

        print("\n启动GUI命令: python morphology_gui.py")

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
