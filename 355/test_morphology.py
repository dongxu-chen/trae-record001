import cv2
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from morphology_lib import (
    erode, dilate, open_op, close_op,
    top_hat, black_hat, morphological_gradient,
    create_rect, create_ellipse, create_cross
)


def create_test_image():
    img = np.zeros((200, 400), dtype=np.uint8)

    cv2.circle(img, (80, 100), 40, 255, -1)
    cv2.rectangle(img, (160, 60), (240, 140), 255, -1)
    cv2.rectangle(img, (280, 80), (360, 120), 255, -1)

    for i in range(10):
        x = np.random.randint(0, 400)
        y = np.random.randint(0, 200)
        cv2.circle(img, (x, y), 2, 255, -1)

    for i in range(5):
        x1 = np.random.randint(0, 380)
        y1 = np.random.randint(0, 180)
        x2 = x1 + np.random.randint(5, 20)
        y2 = y1 + np.random.randint(5, 20)
        cv2.rectangle(img, (x1, y1), (x2, y2), 0, -1)

    return img


def test_structuring_elements():
    print("测试结构元素生成...")

    rect = create_rect((5, 5))
    print(f"矩形结构元素 5x5:\n{rect.kernel}")

    ellipse = create_ellipse((5, 5))
    print(f"\n椭圆结构元素 5x5:\n{ellipse.kernel}")

    cross = create_cross((5, 5))
    print(f"\n十字形结构元素 5x5:\n{cross.kernel}")

    print("\n结构元素测试通过!")


def test_basic_operations():
    print("\n测试基本形态学操作...")

    img = create_test_image()

    se = create_rect((3, 3))

    eroded = erode(img, se)
    dilated = dilate(img, se)
    opened = open_op(img, se)
    closed = close_op(img, se)

    print(f"原始图像: {img.shape}, 非零像素数: {np.count_nonzero(img)}")
    print(f"腐蚀后: {eroded.shape}, 非零像素数: {np.count_nonzero(eroded)}")
    print(f"膨胀后: {dilated.shape}, 非零像素数: {np.count_nonzero(dilated)}")
    print(f"开运算后: {opened.shape}, 非零像素数: {np.count_nonzero(opened)}")
    print(f"闭运算后: {closed.shape}, 非零像素数: {np.count_nonzero(closed)}")

    print("\n基本操作测试通过!")


def test_advanced_operations():
    print("\n测试高级形态学操作...")

    img = create_test_image()
    se = create_rect((5, 5))

    th = top_hat(img, se)
    bh = black_hat(img, se)
    grad = morphological_gradient(img, se)

    print(f"顶帽变换: 非零像素数: {np.count_nonzero(th)}")
    print(f"黑帽变换: 非零像素数: {np.count_nonzero(bh)}")
    print(f"形态学梯度: 非零像素数: {np.count_nonzero(grad)}")

    print("\n高级操作测试通过!")


def test_color_image():
    print("\n测试彩色图像处理...")

    img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.circle(img, (50, 50), 30, (255, 255, 255), -1)

    se = create_rect((5, 5))
    eroded = erode(img, se)
    dilated = dilate(img, se)

    print(f"彩色图像形状: {img.shape}")
    print(f"腐蚀后形状: {eroded.shape}")
    print(f"膨胀后形状: {dilated.shape}")

    print("\n彩色图像测试通过!")


def test_different_structuring_elements():
    print("\n测试不同结构元素的效果...")

    img = create_test_image()

    se_rect = create_rect((5, 5))
    se_ellipse = create_ellipse((5, 5))
    se_cross = create_cross((5, 5))

    for name, se in [('矩形', se_rect), ('椭圆', se_ellipse), ('十字形', se_cross)]:
        eroded = erode(img, se)
        print(f"{name}结构元素腐蚀后 - 非零像素数: {np.count_nonzero(eroded)}")

    print("\n结构元素效果测试通过!")


def test_large_image_simulation():
    print("\n测试大图像处理(模拟)...")

    img = np.random.randint(0, 256, (500, 500), dtype=np.uint8)
    se = create_rect((3, 3))

    result = erode(img, se)
    print(f"大图像 ({img.shape}) 腐蚀完成")
    print(f"输出形状: {result.shape}")

    print("\n大图像测试通过!")


def main():
    print("=" * 50)
    print("形态学图像处理库 - 测试脚本")
    print("=" * 50)

    try:
        test_structuring_elements()
        test_basic_operations()
        test_advanced_operations()
        test_color_image()
        test_different_structuring_elements()
        test_large_image_simulation()

        print("\n" + "=" * 50)
        print("所有测试通过!")
        print("=" * 50)

        print("\n生成示例图像...")
        img = create_test_image()
        se = create_rect((5, 5))

        results = [
            ('original', img),
            ('eroded', erode(img, se)),
            ('dilated', dilate(img, se)),
            ('opened', open_op(img, se)),
            ('closed', close_op(img, se)),
            ('top_hat', top_hat(img, se)),
            ('black_hat', black_hat(img, se)),
            ('gradient', morphological_gradient(img, se)),
        ]

        for name, result in results:
            cv2.imwrite(f'{name}.png', result)
            print(f"  已保存: {name}.png")

        print("\n示例图像已生成!")
        print("\n使用说明:")
        print("  1. 运行 'pip install -r requirements.txt' 安装依赖")
        print("  2. 运行 'python morphology_gui.py' 启动GUI界面")
        print("  3. 或者直接在代码中导入 morphology_lib 使用")

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
