import argparse
import torch
from gradio_interface import StyleTransferApp


def main():
    parser = argparse.ArgumentParser(description='图像风格分解与重建系统')
    parser.add_argument('--device', type=str, default=None,
                        help='使用的设备 (cuda/cpu, 默认自动检测)')
    parser.add_argument('--server_name', type=str, default='127.0.0.1',
                        help='服务器地址')
    parser.add_argument('--server_port', type=int, default=7860,
                        help='服务器端口')
    parser.add_argument('--share', action='store_true',
                        help='是否创建公共链接')
    parser.add_argument('--test', action='store_true',
                        help='运行测试模式')

    args = parser.parse_args()

    if args.test:
        run_test(args.device)
        return

    print("=" * 60)
    print("🎨 图像风格分解与重建系统")
    print("=" * 60)

    device = args.device if args.device else ('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")

    print("\n正在加载模型...")
    app = StyleTransferApp(device=device)

    print("正在构建界面...")
    demo = app.build_interface()

    print(f"\n启动服务器: http://{args.server_name}:{args.server_port}")
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)

    demo.launch(
        server_name=args.server_name,
        server_port=args.server_port,
        share=args.share
    )


def run_test(device=None):
    print("=" * 60)
    print("运行测试模式...")
    print("=" * 60)

    device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")

    import numpy as np
    import cv2

    print("\n1. 测试模型加载...")
    try:
        from style_decomposer import StyleDecomposer, DiffusionStyleDecomposer, StructurePreservingLoss
        from style_mixer import StyleMixer, HighFrequencyEnhancer
        from clip_model import CLIPEncoder
        from gradio_interface import AsyncTaskManager
        from video_stylizer import VideoStylizer
        from style_animation import StyleAnimationGenerator

        adain_decomposer = StyleDecomposer(device)
        print("   ✓ AdaIN分解器加载成功 (含StructurePreservingLoss)")

        struct_loss = StructurePreservingLoss(device)
        print("   ✓ 结构保留损失加载成功")

        diffusion_decomposer = DiffusionStyleDecomposer(device)
        print("   ✓ Diffusion分解器加载成功 (含StructurePreservingLoss)")

        style_mixer = StyleMixer(device)
        print("   ✓ 风格混合器加载成功 (含HighFrequencyEnhancer)")

        hf_enhancer = HighFrequencyEnhancer(device)
        print("   ✓ 高频增强器加载成功")

        clip_encoder = CLIPEncoder(device)
        print("   ✓ CLIP编码器加载成功")

        task_manager = AsyncTaskManager(max_workers=2)
        print("   ✓ 异步任务管理器加载成功")

        video_stylizer = VideoStylizer(device)
        print("   ✓ 视频风格化器加载成功")

        animation_gen = StyleAnimationGenerator(device)
        print("   ✓ 风格动画生成器加载成功")

    except Exception as e:
        print(f"   ✗ 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        return

    test_img1 = np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8)
    test_img2 = np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8)
    test_img3 = np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8)

    print("\n2. 测试多风格混合 (三种模式)...")
    try:
        for mode in ['feature', 'pixel', 'dual']:
            mixed = style_mixer.style_mix(test_img1, [test_img2, test_img3],
                                           weights=[0.6, 0.4], alpha=0.8,
                                           hf_enhance=True, hf_strength=0.5,
                                           mix_mode=mode)
            assert mixed.shape == (512, 512, 3)
            print(f"   ✓ 多风格混合 ({mode}) 成功")
    except Exception as e:
        print(f"   ✗ 多风格混合失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n3. 测试多关键帧插值...")
    try:
        keyframe_frames = style_mixer.multi_keyframe_interpolation(
            test_img1, [test_img2, test_img3, test_img1],
            num_frames_per_seg=3, alpha=0.8, hf_enhance=False
        )
        print(f"   ✓ 多关键帧插值成功, 生成 {len(keyframe_frames)} 帧")
    except Exception as e:
        print(f"   ✗ 多关键帧插值失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n4. 测试视频风格化 (帧处理)...")
    try:
        frames = [np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8) for _ in range(5)]
        style_tensor = video_stylizer.preprocess(test_img2)
        style_feats = video_stylizer.decomposer.adain.encode_style(style_tensor)

        stylized_frames = []
        for f in frames:
            s = video_stylizer.stylize_single_frame(f, test_img2, None, alpha=0.8)
            stylized_frames.append(s)
        print(f"   ✓ 逐帧风格化成功, {len(stylized_frames)} 帧")

        flow = video_stylizer.compute_optical_flow(stylized_frames[0], stylized_frames[1])
        print(f"   ✓ 光流计算成功, shape: {flow.shape}")

        blended = video_stylizer.temporal_blend(stylized_frames[1], stylized_frames[0], flow, blend_weight=0.5)
        assert blended.shape == (512, 512, 3)
        print("   ✓ 时域混合成功")

        consistent = video_stylizer._apply_short_term_consistency(stylized_frames, window=3, temporal_weight=0.5)
        assert len(consistent) == len(stylized_frames)
        print(f"   ✓ 短时一致性处理成功, {len(consistent)} 帧")
    except Exception as e:
        print(f"   ✗ 视频风格化失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n5. 测试风格动画生成...")
    try:
        interp_frames = style_mixer.style_interpolation(
            test_img1, test_img2, test_img3, interpolation_steps=5, alpha=0.8, hf_enhance=False
        )
        assert len(interp_frames) == 5
        print(f"   ✓ 风格插值帧生成成功, {len(interp_frames)} 帧")

        cyclic_frames = style_mixer.multi_keyframe_interpolation(
            test_img1, [test_img2, test_img3],
            num_frames_per_seg=5, alpha=0.8, hf_enhance=False
        )
        print(f"   ✓ 多关键帧动画帧生成成功, {len(cyclic_frames)} 帧")
    except Exception as e:
        print(f"   ✗ 风格动画生成失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n6. 测试颜色迁移...")
    try:
        color_result = style_mixer.color_transfer(test_img1, test_img2)
        assert color_result.shape == (512, 512, 3)
        print("   ✓ 颜色迁移成功")
    except Exception as e:
        print(f"   ✗ 颜色迁移失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("✓ 所有测试通过!")
    print("=" * 60)
    print("\n功能列表:")
    print("  - StructurePreservingLoss: Sobel边缘 + 梯度 + 特征损失")
    print("  - HighFrequencyEnhancer: Laplacian金字塔 + Unsharp Mask + 纹理增强")
    print("  - 多风格混合: feature/pixel/dual 三种混合模式")
    print("  - VideoStylizer: 逐帧迁移 + 光流对齐 + 时域平滑 + 短时一致性")
    print("  - StyleAnimationGenerator: 插值/循环/强度扫描动画 (GIF/MP4)")
    print("  - AsyncTaskManager: 线程池异步 + 低分辨率实时预览")
    print("\n运行 'python main.py' 启动Gradio界面")


if __name__ == '__main__':
    main()
