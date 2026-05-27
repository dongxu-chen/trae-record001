"""
图像风格迁移库 v3.0 - 新功能示例
演示: 视频风格迁移、任意风格即时迁移、风格插值
"""

import sys
sys.path.insert(0, "..")

from style_transfer import Stylizer, list_available_styles
from style_transfer.utils import show_images
from pathlib import Path


def example_video_stylization():
    """
    示例1: 视频风格迁移
    使用时序损失保持帧间稳定，避免闪烁
    """
    print("=" * 60)
    print("示例1: 视频风格迁移 (帧间稳定避免闪烁)")
    print("=" * 60)

    stylizer = Stylizer(
        image_size=512,
        num_steps=300,
        keep_aspect_ratio=True,
    )

    video_path = "path/to/input.mp4"
    output_path = "output/stylized_video.mp4"

    if Path(video_path).exists():
        print("风格化视频...")
        stylizer.stylize_video(
            video_path=video_path,
            output_path=output_path,
            style_name="starry_night",
            max_frames=100,
            frame_interval=1,
            use_temporal_loss=True,
            temporal_weight=1e3,
        )
        print(f"视频已保存到: {output_path}")
    else:
        print("请准备视频文件:", video_path)
        print()
        print("使用方法:")
        print("  stylizer.stylize_video(")
        print("      video_path='input.mp4',")
        print("      output_path='output.mp4',")
        print("      style_name='starry_night',")
        print("      use_temporal_loss=True,  # 启用帧间稳定")
        print("      temporal_weight=1e3,     # 时序损失权重")
        print("  )")


def example_instant_style_transfer():
    """
    示例2: 任意风格即时迁移
    输入任意风格图即可迁移，无需重新训练
    风格特征会被缓存，多次使用同一风格时速度更快
    """
    print("\n" + "=" * 60)
    print("示例2: 任意风格即时迁移 (无需重新训练)")
    print("=" * 60)

    stylizer = Stylizer(
        image_size=512,
        num_steps=500,
        keep_aspect_ratio=True,
    )

    content_path = "path/to/content.jpg"
    custom_style_path = "path/to/my_style.jpg"
    output_path = "output/custom_style.png"

    if Path(content_path).exists() and Path(custom_style_path).exists():
        print("使用自定义风格图像进行迁移...")
        print("注意: 风格特征会被缓存，下次使用同一风格时更快")

        stylizer.stylize_and_save(
            content_image=content_path,
            style_image=custom_style_path,
            output_path=output_path,
            keep_original_size=True,
        )
        print(f"风格化图像已保存到: {output_path}")

        print("\n使用另一张风格图:")
        another_style = "path/to/another_style.jpg"
        if Path(another_style).exists():
            stylizer.stylize_and_save(
                content_image=content_path,
                style_image=another_style,
                output_path="output/another_style.png",
            )
            print("已生成第二张风格化图像")
    else:
        print("请准备内容图和自定义风格图")
        print()
        print("使用方法:")
        print("  stylizer.stylize_and_save(")
        print("      content_image='content.jpg',")
        print("      style_image='my_style.jpg',  # 任意风格图")
        print("      output_path='output.png',")
        print("      keep_original_size=True,")
        print("  )")


def example_style_interpolation():
    """
    示例3: 风格插值
    在两个或多个风格之间创建平滑过渡效果
    """
    print("\n" + "=" * 60)
    print("示例3: 风格插值 (双风格平滑过渡)")
    print("=" * 60)

    stylizer = Stylizer(
        image_size=512,
        num_steps=300,
        use_multi_style=True,
        num_styles=2,
    )

    content_path = "path/to/content.jpg"
    style1_path = "path/to/style1.jpg"
    style2_path = "path/to/style2.jpg"
    output_dir = Path("output/interpolation")

    if Path(content_path).exists() and Path(style1_path).exists() and Path(style2_path).exists():
        print("创建风格插值序列...")
        print("在两个风格之间生成30帧平滑过渡")

        results = stylizer.stylize_interpolation(
            content_image=content_path,
            style_images=[style1_path, style2_path],
            num_frames=30,
            output_dir=str(output_dir),
            output_prefix="interp",
        )

        print(f"已生成 {len(results)} 帧插值图像")
        print(f"保存在: {output_dir}")

        print("\n创建插值视频:")
        video_path = "output/style_transition.mp4"
        stylizer.create_style_transition_video(
            content_image=content_path,
            style_images=[style1_path, style2_path],
            output_path=video_path,
            num_frames=60,
            fps=15,
        )
        print(f"过渡视频已保存到: {video_path}")
    else:
        print("请准备内容图和两个风格图")
        print()
        print("使用方法:")
        print("  stylizer = Stylizer(use_multi_style=True, num_styles=2)")
        print()
        print("  # 生成插值帧序列")
        print("  results = stylizer.stylize_interpolation(")
        print("      content_image='content.jpg',")
        print("      style_images=['style1.jpg', 'style2.jpg'],")
        print("      num_frames=30,")
        print("      output_dir='output/interp',")
        print("  )")
        print()
        print("  # 直接创建过渡视频")
        print("  stylizer.create_style_transition_video(")
        print("      content_image='content.jpg',")
        print("      style_images=['style1.jpg', 'style2.jpg'],")
        print("      output_path='transition.mp4',")
        print("      num_frames=60,")
        print("      fps=15,")
        print("  )")


def example_multi_style_interpolation():
    """
    示例4: 多风格插值
    在3个或更多风格之间创建平滑过渡
    """
    print("\n" + "=" * 60)
    print("示例4: 多风格插值 (3个以上风格)")
    print("=" * 60)

    stylizer = Stylizer(
        image_size=512,
        num_steps=300,
        use_multi_style=True,
        num_styles=3,
    )

    content_path = "path/to/content.jpg"
    style_paths = [
        "path/to/style1.jpg",
        "path/to/style2.jpg",
        "path/to/style3.jpg",
    ]
    output_dir = Path("output/multi_interp")

    if Path(content_path).exists() and all(Path(p).exists() for p in style_paths):
        print("在3个风格之间创建平滑过渡...")

        results = stylizer.stylize_interpolation(
            content_image=content_path,
            style_images=style_paths,
            num_frames=60,
            output_dir=str(output_dir),
        )

        print(f"已生成 {len(results)} 帧插值图像")

        video_path = "output/multi_style_transition.mp4"
        stylizer.create_style_transition_video(
            content_image=content_path,
            style_images=style_paths,
            output_path=video_path,
            num_frames=90,
            fps=15,
        )
        print(f"多风格过渡视频已保存到: {video_path}")
    else:
        print("请准备内容图和3个风格图")


def example_style_cache():
    """
    示例5: 风格缓存机制
    演示如何利用缓存提高重复使用同一风格的效率
    """
    print("\n" + "=" * 60)
    print("示例5: 风格缓存机制 (提高效率)")
    print("=" * 60)

    stylizer = Stylizer(
        image_size=512,
        num_steps=300,
    )

    content_images = [
        "path/to/content1.jpg",
        "path/to/content2.jpg",
        "path/to/content3.jpg",
    ]

    print("对多张内容图使用同一风格:")
    print("  第1张: 提取并缓存风格特征")
    print("  第2张: 直接使用缓存的特征")
    print("  第3张: 直接使用缓存的特征")
    print()
    print("这可以显著提高处理多张图像的效率")

    style_path = "path/to/style.jpg"
    if Path(style_path).exists():
        output_paths = []
        for i, content_path in enumerate(content_images):
            if Path(content_path).exists():
                output_path = f"output/stylized_{i}.png"
                stylizer.stylize_and_save(
                    content_image=content_path,
                    style_image=style_path,
                    output_path=output_path,
                )
                output_paths.append(output_path)

        print(f"已处理 {len(output_paths)} 张图像")
        print("可以清除缓存以释放内存:")
        print("  stylizer.clear_style_cache()")
    else:
        print("请准备风格图和多张内容图")


def main():
    """主函数"""
    print("=" * 60)
    print("图像风格迁移库 v3.0 - 新功能示例")
    print("=" * 60)
    print()
    print("新功能:")
    print("  1. 视频风格迁移 - 帧间稳定避免闪烁")
    print("  2. 任意风格即时迁移 - 输入任意风格图，无需重新训练")
    print("  3. 风格插值 - 双风格/多风格平滑过渡")
    print()
    print("依赖:")
    print("  - opencv-python (视频处理): pip install opencv-python")
    print()

    example_instant_style_transfer()

    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
