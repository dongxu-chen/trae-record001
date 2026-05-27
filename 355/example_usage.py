import cv2
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from morphology_lib import (
    erode, dilate, open_op, close_op,
    top_hat, black_hat, morphological_gradient,
    create_rect, create_ellipse, create_cross,
    process_large_image, LargeImageProcessor
)


def example_basic_usage():
    print("示例1: 基本用法")
    print("-" * 40)

    img = cv2.imread('original.png', cv2.IMREAD_GRAYSCALE)
    if img is None:
        print("请先运行 test_morphology.py 生成测试图像")
        return

    se = create_rect((3, 3))
    result = erode(img, se)

    print(f"输入图像形状: {img.shape}")
    print(f"输出图像形状: {result.shape}")
    print("腐蚀操作完成!")


def example_chain_operations():
    print("\n示例2: 链式操作")
    print("-" * 40)

    img = cv2.imread('original.png', cv2.IMREAD_GRAYSCALE)
    if img is None:
        print("请先运行 test_morphology.py 生成测试图像")
        return

    se = create_rect((5, 5))
    result = open_op(img, se)
    result = close_op(result, se)

    print("先开运算后闭运算完成!")
    print(f"结果非零像素数: {np.count_nonzero(result)}")


def example_different_kernels():
    print("\n示例3: 使用不同的结构元素")
    print("-" * 40)

    img = cv2.imread('original.png', cv2.IMREAD_GRAYSCALE)
    if img is None:
        print("请先运行 test_morphology.py 生成测试图像")
        return

    se1 = create_rect((5, 5))
    se2 = create_ellipse((5, 5))
    se3 = create_cross((5, 5))

    for name, se in [('矩形', se1), ('椭圆', se2), ('十字形', se3)]:
        result = dilate(img, se)
        print(f"{name}结构元素膨胀 - 非零像素数: {np.count_nonzero(result)}")


def example_color_image():
    print("\n示例4: 处理彩色图像")
    print("-" * 40)

    color_img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    se = create_rect((3, 3))
    result = erode(color_img, se)

    print(f"彩色图像输入形状: {color_img.shape}")
    print(f"彩色图像输出形状: {result.shape}")
    print("彩色图像腐蚀完成!")


def example_top_hat_black_hat():
    print("\n示例5: 顶帽和黑帽变换")
    print("-" * 40)

    img = cv2.imread('original.png', cv2.IMREAD_GRAYSCALE)
    if img is None:
        print("请先运行 test_morphology.py 生成测试图像")
        return

    se = create_rect((9, 9))

    th = top_hat(img, se)
    bh = black_hat(img, se)

    print(f"顶帽变换 - 突出亮小区域: {np.count_nonzero(th)} 像素")
    print(f"黑帽变换 - 突出暗小区域: {np.count_nonzero(bh)} 像素")

    cv2.imwrite('example_tophat.png', th)
    cv2.imwrite('example_blackhat.png', bh)
    print("结果已保存!")


def example_large_image():
    print("\n示例6: 大图像分块处理")
    print("-" * 40)

    large_img = np.random.randint(0, 256, (2000, 2000, 3), dtype=np.uint8)
    print(f"大图像尺寸: {large_img.shape}")

    se = create_rect((3, 3))

    def progress_callback(p):
        print(f"\r处理进度: {p * 100:.1f}%", end='')

    print("开始处理...")
    result = process_large_image(
        large_img, se, 'dilate',
        block_size=(512, 512),
        progress_callback=progress_callback
    )
    print(f"\n处理完成! 输出形状: {result.shape}")


def example_gradient():
    print("\n示例7: 形态学梯度")
    print("-" * 40)

    img = cv2.imread('original.png', cv2.IMREAD_GRAYSCALE)
    if img is None:
        print("请先运行 test_morphology.py 生成测试图像")
        return

    se = create_rect((3, 3))
    grad = morphological_gradient(img, se)

    print(f"形态学梯度 - 边缘像素数: {np.count_nonzero(grad)}")
    cv2.imwrite('example_gradient.png', grad)
    print("梯度图像已保存!")


def example_custom_kernel():
    print("\n示例8: 自定义结构元素")
    print("-" * 40)

    from morphology_lib.structuring_element import StructuringElement

    custom_kernel = np.array([
        [0, 1, 0],
        [1, 1, 1],
        [0, 1, 0]
    ], dtype=np.uint8)

    custom_se = StructuringElement(custom_kernel, anchor=(1, 1))

    img = cv2.imread('original.png', cv2.IMREAD_GRAYSCALE)
    if img is not None:
        result = dilate(img, custom_se)
        print(f"自定义结构元素膨胀完成!")
        print(f"非零像素数: {np.count_nonzero(result)}")


def example_processor_class():
    print("\n示例9: 使用 LargeImageProcessor 类")
    print("-" * 40)

    processor = LargeImageProcessor(block_size=(256, 256))

    img = cv2.imread('original.png', cv2.IMREAD_GRAYSCALE)
    if img is None:
        print("请先运行 test_morphology.py 生成测试图像")
        return

    se = create_rect((3, 3))
    result = processor.open_op(img, se)

    print(f"处理器类开运算完成!")
    print(f"最终进度: {processor.get_progress() * 100:.1f}%")


def main():
    print("=" * 50)
    print("形态学图像处理库 - 使用示例")
    print("=" * 50)

    example_basic_usage()
    example_chain_operations()
    example_different_kernels()
    example_color_image()
    example_top_hat_black_hat()
    example_large_image()
    example_gradient()
    example_custom_kernel()
    example_processor_class()

    print("\n" + "=" * 50)
    print("所有示例运行完成!")
    print("=" * 50)

    print("\n快速入门代码:")
    print("""
    from morphology_lib import *

    # 1. 创建结构元素
    se = create_rect((3, 3))

    # 2. 加载图像
    img = cv2.imread('image.png')

    # 3. 执行操作
    result = erode(img, se)      # 腐蚀
    result = dilate(img, se)     # 膨胀
    result = open_op(img, se)    # 开运算
    result = close_op(img, se)   # 闭运算

    # 4. 保存结果
    cv2.imwrite('result.png', result)
    """)


if __name__ == '__main__':
    main()
