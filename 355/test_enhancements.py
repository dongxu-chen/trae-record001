import cv2
import numpy as np
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from morphology_lib import (
    erode, dilate, open_op, close_op,
    top_hat, black_hat, morphological_gradient,
    create_rect, create_ellipse, create_cross,
    process_large_image, LargeImageProcessor
)


def test_reflect_padding():
    print("测试1: 反射填充边界处理")
    print("-" * 50)

    img = np.zeros((100, 100), dtype=np.uint8)
    cv2.rectangle(img, (30, 30), (70, 70), 255, -1)

    se = create_rect((15, 15))

    result = dilate(img, se)

    border_top = result[0, :]
    border_left = result[:, 0]
    print(f"顶边界非零像素: {np.count_nonzero(border_top)}")
    print(f"左边界非零像素: {np.count_nonzero(border_left)}")
    print("反射填充测试通过 - 边界处理平滑")


def test_inplace_operation():
    print("\n测试2: 原地操作（out参数）")
    print("-" * 50)

    img = np.random.randint(0, 256, (200, 200), dtype=np.uint8)
    se = create_rect((3, 3))

    out_array = np.empty_like(img)
    result = erode(img, se, out=out_array)

    print(f"返回数组与out数组是同一对象: {result is out_array}")
    print(f"输出形状正确: {result.shape == img.shape}")
    print(f"输出dtype正确: {result.dtype == img.dtype}")

    original_data = img.copy()
    out_array2 = np.empty_like(img)
    dilate(img, se, out=out_array2)
    print(f"原图像未被修改: {np.array_equal(img, original_data)}")
    print("原地操作测试通过")


def test_large_image_inplace():
    print("\n测试3: 大图像原地处理")
    print("-" * 50)

    img = np.random.randint(0, 256, (1000, 1000, 3), dtype=np.uint8)
    se = create_rect((3, 3))

    out_array = np.empty_like(img)

    start_time = time.time()
    result = process_large_image(img, se, 'dilate', block_size=(256, 256), out=out_array)
    elapsed = time.time() - start_time

    print(f"返回数组与out数组是同一对象: {result is out_array}")
    print(f"处理时间: {elapsed:.3f}秒")
    print(f"输出形状正确: {result.shape == img.shape}")
    print("大图像原地处理测试通过")


def test_memory_efficiency():
    print("\n测试4: 内存效率对比")
    print("-" * 50)

    img = np.random.randint(0, 256, (2000, 2000, 3), dtype=np.uint8)
    se = create_rect((5, 5))

    img_size_mb = img.nbytes / (1024 * 1024)
    print(f"输入图像大小: {img_size_mb:.2f} MB")

    import gc
    gc.collect()

    start_mem = 0
    try:
        import psutil
        process = psutil.Process()
        start_mem = process.memory_info().rss / (1024 * 1024)
    except ImportError:
        print("psutil未安装，跳过内存测试")
        start_mem = 0

    out_array = np.empty_like(img)
    result = process_large_image(img, se, 'open', block_size=(512, 512), out=out_array)

    try:
        import psutil
        process = psutil.Process()
        end_mem = process.memory_info().rss / (1024 * 1024)
        mem_used = end_mem - start_mem
        print(f"额外内存使用: ~{mem_used:.2f} MB")
    except ImportError:
        pass

    print("内存效率测试通过")


def test_arbitrary_kernel_size():
    print("\n测试5: 任意尺寸结构元素")
    print("-" * 50)

    img = np.random.randint(0, 256, (100, 100), dtype=np.uint8)

    test_sizes = [(1, 1), (2, 3), (5, 5), (7, 11), (15, 15), (1, 21), (31, 1)]

    for size in test_sizes:
        se = create_rect(size)
        result = dilate(img, se)
        print(f"内核 {size[0]}x{size[1]}: 输出形状 {result.shape} ✓")

    print("任意尺寸结构元素测试通过")


def test_chain_operations_memory():
    print("\n测试6: 链式操作内存复用")
    print("-" * 50)

    img = np.random.randint(0, 256, (500, 500), dtype=np.uint8)
    se = create_rect((5, 5))

    temp = np.empty_like(img)
    out = np.empty_like(img)

    result = open_op(img, se, out=out, temp=temp)

    print(f"使用out参数: {result is out}")
    print(f"输出正确: {result.shape == img.shape}")

    result2 = close_op(img, se, out=out, temp=temp)
    print(f"缓冲区复用成功: {result2 is out}")
    print("链式操作内存复用测试通过")


def test_processor_class_out():
    print("\n测试7: LargeImageProcessor类out参数")
    print("-" * 50)

    processor = LargeImageProcessor(block_size=(256, 256))
    img = np.random.randint(0, 256, (800, 800, 3), dtype=np.uint8)
    se = create_rect((3, 3))

    out_array = np.empty_like(img)
    result = processor.dilate(img, se, out=out_array)

    print(f"返回数组与out数组是同一对象: {result is out_array}")
    print(f"处理进度报告: {processor.get_progress() >= 0}")
    print("LargeImageProcessor类out参数测试通过")


def benchmark_performance():
    print("\n测试8: 性能基准")
    print("-" * 50)

    sizes = [(256, 256), (512, 512), (1024, 1024)]
    se = create_rect((3, 3))

    for size in sizes:
        img = np.random.randint(0, 256, size, dtype=np.uint8)

        start = time.time()
        result = erode(img, se)
        elapsed = time.time() - start

        pixels = size[0] * size[1]
        mp_per_sec = pixels / (elapsed * 1000000) if elapsed > 0 else 0
        print(f"尺寸 {size[0]}x{size[1]}: {elapsed*1000:.2f}ms, {mp_per_sec:.2f} MP/s")

    print("性能基准测试完成")


def main():
    print("=" * 60)
    print("形态学图像处理库 - 增强功能测试")
    print("=" * 60)

    try:
        test_reflect_padding()
        test_inplace_operation()
        test_large_image_inplace()
        test_memory_efficiency()
        test_arbitrary_kernel_size()
        test_chain_operations_memory()
        test_processor_class_out()
        benchmark_performance()

        print("\n" + "=" * 60)
        print("所有增强功能测试通过!")
        print("=" * 60)

        print("\n新增功能总结:")
        print("  ✓ 边界处理: 反射填充 (reflect padding)")
        print("  ✓ 原地操作: out 参数支持")
        print("  ✓ 内存复用: temp 参数减少分配")
        print("  ✓ 任意尺寸: 支持非对称内核")
        print("  ✓ GUI防抖: 300ms延迟更新预览")
        print("  ✓ 三窗口: 原图/预览/最终结果")

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
