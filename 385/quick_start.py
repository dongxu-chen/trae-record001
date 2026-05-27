"""
快速开始脚本 - 演示图像风格迁移的基本用法
"""

import sys
sys.path.insert(0, ".")

from style_transfer import Stylizer, list_available_styles
from style_transfer.utils import show_images, load_image, save_image
from pathlib import Path


def quick_start():
    """快速开始示例"""
    print("=" * 60)
    print("图像风格迁移库 - 快速开始")
    print("=" * 60)

    print("\n1. 查看可用的预训练风格:")
    print("-" * 40)
    list_available_styles()

    print("\n2. 初始化风格迁移器:")
    print("-" * 40)

    stylizer = Stylizer(
        image_size=512,
        content_weight=1.0,
        style_weight=1e4,
        num_steps=500,
    )

    print(f"   设备: {stylizer.device}")
    print(f"   图像大小: {stylizer.image_size}")
    print(f"   优化步数: {stylizer.num_steps}")

    content_path = "content.jpg"
    style_path = "style.jpg"
    output_path = "output/stylized.png"

    if not Path(content_path).exists():
        print(f"\n提示: 请准备内容图像 '{content_path}'")
        print("或者使用以下代码指定路径:")
        print("  stylizer.stylize(content_image='path/to/content.jpg', ...)")

    if not Path(style_path).exists():
        print(f"\n提示: 请准备风格图像 '{style_path}'")
        print("或者使用预训练风格:")
        print("  stylizer.stylize(content_image='content.jpg', style_name='starry_night')")

    print("\n3. 基本用法:")
    print("-" * 40)
    print("""
    # 使用自定义内容图和风格图
    stylizer.stylize_and_save(
        content_image='content.jpg',
        style_image='style.jpg',
        output_path='output/stylized.png'
    )

    # 使用预训练风格
    stylizer.stylize_and_save(
        content_image='content.jpg',
        style_name='starry_night',
        output_path='output/starry_night.png'
    )
    """)

    print("4. 调整风格强度:")
    print("-" * 40)
    print("""
    # 方法1: 直接设置强度
    stylizer.style_intensity = 10.0  # 值越大风格越明显

    # 方法2: 使用方法
    stylizer.set_style_strength(10.0)

    # 方法3: 生成不同强度的对比图
    results = stylizer.stylize_with_different_strengths(
        content_image='content.jpg',
        style_name='starry_night',
        strengths=[1, 5, 10, 50],
        output_dir='output/different_strengths'
    )
    """)

    print("5. 批量处理:")
    print("-" * 40)
    print("""
    from pathlib import Path

    content_dir = Path('path/to/images')
    image_extensions = ['.jpg', '.jpeg', '.png']

    content_images = [
        str(p) for p in content_dir.iterdir()
        if p.suffix.lower() in image_extensions
    ]

    output_paths = stylizer.stylize_batch(
        content_images=content_images,
        output_dir='output/batch',
        style_name='starry_night',
        output_prefix='stylized'
    )
    """)

    print("=" * 60)
    print("完成! 详细示例请查看 examples/demo.py")
    print("=" * 60)


if __name__ == "__main__":
    quick_start()
