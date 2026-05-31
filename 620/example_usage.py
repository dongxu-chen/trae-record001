#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from super_resolution_pipeline import SuperResolutionPipeline


def example_video_processing():
    print("示例1: 视频超分处理")
    print("-" * 50)
    
    input_video = "input_video.mp4"
    
    if not os.path.exists(input_video):
        print(f"注意: 示例视频 {input_video} 不存在")
        print("请修改为实际的视频路径，或使用Web界面上传视频")
        print()
        return
    
    pipeline = SuperResolutionPipeline(
        model_name='edsr',
        scale=4,
        enable_denoise=True,
        enable_temporal=True,
        enable_bitrate_adapt=True,
    )
    
    result = pipeline.process_video(
        input_path=input_video,
        target_quality='high',
    )
    
    print(f"处理完成! 输出: {result['output_path']}")
    print(f"分辨率: {result['original_resolution']} -> {result['resolution']}")
    print()


def example_image_processing():
    print("示例2: 图片超分处理")
    print("-" * 50)
    
    input_image = "input_image.jpg"
    
    if not os.path.exists(input_image):
        print(f"注意: 示例图片 {input_image} 不存在")
        print("请修改为实际的图片路径")
        print()
        return
    
    pipeline = SuperResolutionPipeline(
        model_name='rcan',
        scale=4,
        enable_denoise=True,
        enable_temporal=False,
        enable_bitrate_adapt=False,
    )
    
    result = pipeline.process_image(input_image)
    
    print(f"处理完成! 输出: {result['output_path']}")
    print(f"分辨率: {result['original_resolution']} -> {result['resolution']}")
    print()


def example_cli_usage():
    print("命令行使用示例:")
    print("-" * 50)
    print()
    print("# 基本视频处理 (EDSR x4)")
    print("python cli.py -i input.mp4 -o output.mp4")
    print()
    print("# 使用RCAN模型，2倍超分")
    print("python cli.py -i input.mp4 -m rcan -s 2")
    print()
    print("# 高质量输出，禁用降噪")
    print("python cli.py -i input.mp4 --quality ultra --no-denoise")
    print()
    print("# 处理图片")
    print("python cli.py -i input.jpg --image-mode")
    print()
    print("# 处理视频片段 (从第10秒开始，处理30秒)")
    print("python cli.py -i input.mp4 --start-time 10 --duration 30")
    print()
    print("# 使用半精度推理加速")
    print("python cli.py -i input.mp4 --half")
    print()


def example_custom_pipeline():
    print("示例3: 自定义处理管线")
    print("-" * 50)
    
    import cv2
    import numpy as np
    
    pipeline = SuperResolutionPipeline(
        model_name='edsr',
        scale=2,
        enable_denoise=True,
        enable_temporal=True,
    )
    
    print("Pipeline初始化完成")
    print(f"模型: EDSR x2")
    print(f"设备: {pipeline.device}")
    print(f"降噪: 开启")
    print(f"时序一致性: 开启")
    print()


if __name__ == '__main__':
    print("=" * 60)
    print("          视频超分辨率重建系统 - 使用示例")
    print("=" * 60)
    print()
    
    example_video_processing()
    example_image_processing()
    example_cli_usage()
    example_custom_pipeline()
    
    print("=" * 60)
    print("启动Web界面请运行: streamlit run app.py")
    print("或直接双击: start.bat")
    print("=" * 60)
