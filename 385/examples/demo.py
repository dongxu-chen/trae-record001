"""
图像风格迁移库 v2.0 - 使用示例
演示新功能: 分块处理、自适应强度、宽高比保持
"""

import sys
sys.path.insert(0, "..")

from style_transfer import Stylizer, list_available_styles
from style_transfer.utils import show_images, load_image, extract_patches, merge_patches
from pathlib import Path


def example_basic_usage():
    """
    示例1: 基本用法 - 使用自定义内容图和风格图
    默认启用分块处理、自适应调度和宽高比保持
    """
    print("=" * 60)
    print("示例1: 基本用法 (启用新特性)")
    print("=" * 60)

    stylizer = Stylizer(
        image_size=512,
        num_steps=500,
        use_patch_processing=True,
        patch_size=512,
        patch_overlap=128,
        use_adaptive_scheduling=True,
        keep_aspect_ratio=True,
    )

    content_path = "path/to/content.jpg"
    style_path = "path/to/style.jpg"
    output_path = "output/stylized.png"

    if Path(content_path).exists() and Path(style_path).exists():
        stylizer.stylize_and_save(
            content_image=content_path,
            style_image=style_path,
            output_path=output_path,
            keep_original_size=True,
        )
        print(f"风格化图像已保存到: {output_path}")
    else:
        print("请准备内容图和风格图，或使用示例2的预训练风格")


def example_pretrained_style():
    """
    示例2: 使用预训练风格
    """
    print("\n" + "=" * 60)
    print("示例2: 使用预训练风格")
    print("=" * 60)

    list_available_styles()

    stylizer = Stylizer(
        image_size=512,
        num_steps=500,
        keep_aspect_ratio=True,
    )

    content_path = "path/to/content.jpg"
    output_path = "output/starry_night.png"

    if Path(content_path).exists():
        print("\n使用 'starry_night' 风格...")
        stylizer.stylize_and_save(
            content_image=content_path,
            style_name="starry_night",
            output_path=output_path,
            keep_original_size=True,
        )
        print(f"风格化图像已保存到: {output_path}")
    else:
        print("请准备内容图像")


def example_style_intensity():
    """
    示例3: 调整风格强度
    自适应调度会在低强度时保留更多内容纹理
    """
    print("\n" + "=" * 60)
    print("示例3: 自适应强度调度 (低强度保留更多纹理)")
    print("=" * 60)

    stylizer = Stylizer(
        image_size=512,
        num_steps=300,
        use_adaptive_scheduling=True,
        content_preservation_factor=0.5,
    )

    content_path = "path/to/content.jpg"
    output_dir = Path("output/different_strengths")

    if Path(content_path).exists():
        print("生成不同强度的风格化图像...")
        print("注意: 低强度时自适应调度会自动提升内容权重以保留更多纹理")
        results = stylizer.stylize_with_different_strengths(
            content_image=content_path,
            style_name="starry_night",
            strengths=[0.5, 1, 5, 10, 50],
            output_dir=str(output_dir),
        )

        images = [load_image(content_path, 512)[0]]
        titles = ["原图"]
        for strength, img in results.items():
            images.append(img)
            titles.append(f"强度: {strength}")

        show_images(images, titles=titles, save_path=str(output_dir / "comparison.png"))
        print(f"比较图已保存到: {output_dir / 'comparison.png'}")
    else:
        print("请准备内容图像")


def example_batch_processing():
    """
    示例4: 批量处理 (保持宽高比)
    默认使用黑边填充以保持原始宽高比
    """
    print("\n" + "=" * 60)
    print("示例4: 批量处理 (保持宽高比，黑边填充)")
    print("=" * 60)

    stylizer = Stylizer(
        image_size=512,
        num_steps=300,
        keep_aspect_ratio=True,
    )

    content_dir = Path("path/to/images")
    output_dir = Path("output/batch")

    if content_dir.exists():
        image_extensions = [".jpg", ".jpeg", ".png", ".bmp"]
        content_images = [
            str(p) for p in content_dir.iterdir()
            if p.suffix.lower() in image_extensions
        ]

        if content_images:
            print(f"找到 {len(content_images)} 张图像")
            print("使用黑边填充保持原始宽高比")
            output_paths = stylizer.stylize_batch(
                content_images=content_images,
                output_dir=str(output_dir),
                style_name="starry_night",
                output_prefix="stylized",
                keep_aspect_ratio=True,
                keep_original_size=True,
            )
            print(f"已处理 {len(output_paths)} 张图像")
        else:
            print("目录中未找到图像文件")
    else:
        print("请准备内容图像目录")


def example_large_image():
    """
    示例5: 大图分块处理
    自动检测大图并使用分块+重叠拼贴方式处理
    """
    print("\n" + "=" * 60)
    print("示例5: 大图分块处理 (重叠拼贴减少接缝)")
    print("=" * 60)

    stylizer = Stylizer(
        image_size=1024,
        num_steps=300,
        use_patch_processing=True,
        patch_size=512,
        patch_overlap=128,
    )

    content_path = "path/to/large_image.jpg"
    output_path = "output/large_stylized.png"

    if Path(content_path).exists():
        print(f"使用分块处理: 块大小={stylizer.patch_size}, 重叠={stylizer.patch_overlap}")
        print("重叠区域使用加权融合，减少接缝痕迹")
        stylizer.stylize_and_save(
            content_image=content_path,
            style_name="starry_night",
            output_path=output_path,
            keep_original_size=True,
        )
        print(f"大图风格化已保存到: {output_path}")
    else:
        print("请准备大图 (> 512px)")


def example_custom_parameters():
    """
    示例6: 自定义参数 (详细配置)
    """
    print("\n" + "=" * 60)
    print("示例6: 自定义参数")
    print("=" * 60)

    stylizer = Stylizer(
        image_size=1024,
        content_weight=1.0,
        style_weight=1e4,
        tv_weight=1e-5,
        num_steps=1000,
        learning_rate=0.01,
        use_patch_processing=True,
        patch_size=512,
        patch_overlap=128,
        use_adaptive_scheduling=True,
        warmup_steps=200,
        content_preservation_factor=0.7,
        keep_aspect_ratio=True,
    )

    content_path = "path/to/content.jpg"
    style_path = "path/to/style.jpg"
    output_path = "output/high_quality.png"

    if Path(content_path).exists() and Path(style_path).exists():
        print("生成高质量风格化图像:")
        print(f"  - 输出尺寸: 1024x1024")
        print(f"  - 分块大小: 512, 重叠: 128")
        print(f"  - 自适应调度: 预热200步, 内容保留因子0.7")
        print(f"  - 宽高比保持: 启用")
        stylizer.stylize_and_save(
            content_image=content_path,
            style_image=style_path,
            output_path=output_path,
            keep_original_size=True,
        )
        print(f"高质量图像已保存到: {output_path}")
    else:
        print("请准备内容图和风格图")


def main():
    """主函数"""
    print("=" * 60)
    print("图像风格迁移库 v2.0 - 使用示例")
    print("=" * 60)
    print()
    print("新特性:")
    print("  1. 大图分块处理 - 自动检测大图，使用重叠拼贴减少接缝")
    print("  2. 自适应强度调度 - 低强度时自动保留更多内容纹理")
    print("  3. 宽高比保持 - 使用黑边填充保持原始比例")
    print()
    print("可用示例:")
    print("  1. 基本用法 (启用新特性)")
    print("  2. 使用预训练风格")
    print("  3. 自适应强度调度")
    print("  4. 批量处理 (保持宽高比)")
    print("  5. 大图分块处理")
    print("  6. 自定义参数 (高质量)")
    print()

    example_pretrained_style()


if __name__ == "__main__":
    main()
