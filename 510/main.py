#!/usr/bin/env python
import argparse
import sys
import json
from pathlib import Path

from video_processor import create_video_enhancer, RealTimeProcessor
from utils import check_dependencies
from quality_metrics import create_quality_evaluator


def print_banner():
    banner = """
==============================================================
  Video Interpolation + SR System v3.0 (VESPCN)
  2x Frame Rate + 2x Resolution | End-to-End Training | Mobile
==============================================================
    """
    print(banner)


def check_system():
    print("🔍 检查系统依赖...")
    deps = check_dependencies()

    print(f"  ✓ PyTorch: {deps['torch']}")
    print(f"  ✓ CUDA: {'可用 (' + deps['cuda_version'] + ')' if deps['cuda_available'] else '不可用 (将使用CPU)'}")
    print(f"  ✓ OpenCV: {deps['opencv']}")
    print(f"  ✓ FFmpeg: {'已安装' if deps['ffmpeg'] else '未安装 (部分功能可能受限)'}")
    print()


def process_video(args):
    print(f"🎬 处理视频: {args.input}")

    if not Path(args.input).exists():
        print(f"❌ 错误: 输入文件不存在: {args.input}")
        sys.exit(1)

    enhancer = create_video_enhancer(
        weights_path=args.weights,
        use_patch_processing=args.patch_processing,
        use_temporal_alignment=not args.disable_temporal_alignment,
        use_compressed_model=args.use_compressed
    )

    if args.auto_optimize and not args.use_compressed:
        print("⚡ 自动优化推理引擎...")
        enhancer.optimize_for_inference(
            use_half=not args.disable_fp16,
            use_channels_last=not args.disable_channels_last,
            use_jit=args.use_jit
        )

    print(f"  分辨率提升: {enhancer.scale_factor}x")
    print(f"  帧率提升: {enhancer.frame_rate_multiplier}x")
    print(f"  使用设备: {enhancer.device}")
    print(f"  时域校准: {'启用' if enhancer.use_temporal_alignment else '禁用'}")
    print(f"  目标 FPS: {args.target_fps}")
    print()

    result = enhancer.process_video(
        input_path=args.input,
        output_path=args.output,
        max_frames=args.max_frames,
        enable_quality_metrics=args.quality_metrics
    )

    print("\n✅ 处理完成!")
    print(f"  输出文件: {result['output_path']}")
    print(f"  输入帧数: {result['input_frames']}")
    print(f"  输出帧数: {result['output_frames']}")
    print(f"  输入分辨率: {result['input_resolution']}")
    print(f"  输出分辨率: {result['output_resolution']}")
    print(f"  输入帧率: {result['input_fps']:.1f} FPS")
    print(f"  输出帧率: {result['output_fps']:.1f} FPS")

    avg_fps = 1.0 / result['avg_processing_time']
    fps_met = "✅" if avg_fps >= args.target_fps else "⚠️"
    print(f"  平均处理 FPS: {avg_fps:.1f} {fps_met} (目标: {args.target_fps})")
    print(f"  总处理时间: {result['total_processing_time']:.1f}s")

    if 'quality_metrics' in result:
        print("\n📊 客观质量指标:")
        for metric, value in result['quality_metrics'].items():
            print(f"  {metric.upper()}: {value:.4f}")

    if 'temporal_metrics' in result:
        print("\n⏱️  时序一致性指标:")
        for metric, value in result['temporal_metrics'].items():
            print(f"  {metric}: {value:.4f}")


def compress_model(args):
    print("⚡ 模型压缩与优化")
    print()

    enhancer = create_video_enhancer(
        weights_path=args.weights,
        use_temporal_alignment=not args.disable_temporal_alignment,
        use_compressed_model=False
    )

    original_info = enhancer.get_model_info()
    print(f"📊 原始模型信息:")
    print(f"  参数量: {original_info['num_parameters']/1e6:.2f} M")
    print(f"  模型大小: {original_info['model_size_mb']:.1f} MB")
    print()

    print(f"🎯 压缩目标:")
    print(f"  目标 FPS: {args.target_fps}")
    print(f"  最大剪枝比例: {args.max_prune_amount}")
    print(f"  启用量化: {'是' if not args.disable_quantization else '否'}")
    print()

    if args.prune_amount is not None:
        print(f"🔧 手动配置压缩:")
        print(f"  剪枝比例: {args.prune_amount}")
    else:
        print(f"🔧 自动优化模式: 自动寻找达到目标 FPS 的最佳配置")
    print()

    print("⏳ 正在压缩模型，可能需要几分钟...")
    compressed_model, result = enhancer.compress_model(
        target_fps=args.target_fps,
        prune_amount=args.prune_amount,
        use_quantization=not args.disable_quantization
    )

    print("\n✅ 模型压缩完成!")
    print(f"\n📈 压缩结果:")
    print(f"  压缩后 FPS: {result.get('final_fps', 0):.1f} (提升 {result.get('speedup_ratio', 1.0):.1f}x)")
    print(f"  参数压缩率: {result.get('prune_ratio', 0)*100:.1f}%")
    fps_met = result.get('target_fps_met', False)
    print(f"  目标达成: {'✅ 是' if fps_met else '⚠️ 否'}")

    if args.output:
        enhancer.save_compressed_model(args.output)
        print(f"\n💾 压缩模型已保存到: {args.output}")

    if args.verbose:
        print(f"\n📋 详细压缩信息:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.benchmark_after:
        print(f"\n🧪 运行基准测试...")
        benchmark_result = enhancer.benchmark_full_pipeline(num_iterations=args.benchmark_runs)
        print(f"  平均 FPS: {benchmark_result.get('fps', 0):.1f}")
        print(f"  平均延迟: {benchmark_result.get('latency_ms', 0):.1f} ms")
        print(f"  显存占用: {benchmark_result.get('memory_mb', 0):.1f} MB")


def benchmark(args):
    print("⚡ 运行性能基准测试...")

    if args.input and not Path(args.input).exists():
        print(f"❌ 错误: 测试文件不存在: {args.input}")
        sys.exit(1)

    enhancer = create_video_enhancer(
        weights_path=args.weights,
        use_temporal_alignment=not args.disable_temporal_alignment,
        use_compressed_model=args.use_compressed
    )

    if args.auto_optimize and not args.use_compressed:
        print("⚡ 自动优化推理引擎...")
        enhancer.optimize_for_inference(
            use_half=not args.disable_fp16,
            use_channels_last=not args.disable_channels_last,
            use_jit=args.use_jit
        )

    if args.input:
        result = enhancer.benchmark(args.input, num_runs=args.runs)
    else:
        result = enhancer.benchmark_full_pipeline(num_iterations=args.runs)

    print("\n📊 基准测试结果:")
    print(f"  设备: {result.get('device', str(enhancer.device))}")
    if 'resolution' in result:
        print(f"  分辨率: {result['resolution']}")
    print(f"  平均 FPS: {result.get('fps', 0):.1f}")
    print(f"  平均延迟: {result.get('avg_time_ms', result.get('latency_ms', 0)):.1f} ms")
    if 'std_time_ms' in result:
        print(f"  标准差: {result['std_time_ms']:.1f} ms")
    if 'memory_mb' in result:
        print(f"  显存占用: {result['memory_mb']:.1f} MB")
    if 'fps' in result:
        fps_met = result['fps'] >= args.target_fps
        print(f"  目标 FPS {args.target_fps} 达成: {'✅' if fps_met else '⚠️'}")


def evaluate_quality(args):
    print("📊 综合质量评估")
    print()

    evaluator = create_quality_evaluator(use_mos=not args.disable_mos)

    if args.mode == "comprehensive":
        print(f"🎯 综合质量评估模式")
        print(f"  视频 ID: {args.video_id}")

        ref_frames = None
        proc_frames = None

        if args.reference and args.processed:
            import torch
            import numpy as np

            print(f"  参考帧: {args.reference}")
            print(f"  处理后帧: {args.processed}")

            if args.reference.endswith('.npy'):
                ref_frames = torch.from_numpy(np.load(args.reference))
                proc_frames = torch.from_numpy(np.load(args.processed))
            else:
                ref_frames = torch.load(args.reference, map_location='cpu')
                proc_frames = torch.load(args.processed, map_location='cpu')

        weights = None
        if args.weights_config:
            try:
                weights = json.loads(args.weights_config)
                print(f"  自定义权重: {weights}")
            except:
                print(f"⚠️  权重解析失败，使用默认权重")

        print("\n⏳ 正在生成评估报告...")
        result = evaluator.evaluate_comprehensive(
            video_id=args.video_id,
            reference_frames=ref_frames,
            processed_frames=proc_frames,
            calculate_objective=(ref_frames is not None),
            weights=weights
        )

        print("\n🏆 综合评估结果:")
        if result.combined_score:
            print(f"  综合得分: {result.combined_score.combined_score:.2f}/5")
            print(f"  质量等级: {result.quality_level}")
            print(f"  MOS: {result.combined_score.mos_score:.2f}")
            print(f"  PSNR: {result.combined_score.psnr:.1f} dB")
            print(f"  SSIM: {result.combined_score.ssim:.3f}")
            print(f"  LPIPS: {result.combined_score.lpips:.3f}")
            print(f"  权重配置: {json.dumps(result.combined_score.weights, ensure_ascii=False)}")

        if result.objective_metrics:
            print(f"\n📈 客观指标:")
            for k, v in result.objective_metrics.items():
                print(f"  {k.upper()}: {v:.4f}")

        if result.mos_result:
            print(f"\n👥 MOS 详情:")
            print(f"  均值: {result.mos_result.mean_score:.2f} ± {result.mos_result.std_score:.2f}")
            print(f"  95% CI: [{result.mos_result.confidence_interval[0]:.2f}, {result.mos_result.confidence_interval[1]:.2f}]")
            print(f"  评价人数: {result.mos_result.num_raters}")

        if result.temporal_metrics:
            print(f"\n⏱️  时序一致性:")
            for k, v in result.temporal_metrics.items():
                print(f"  {k}: {v:.4f}")

        if args.output:
            evaluator.export_evaluation_report({args.video_id: result}, args.output)
            print(f"\n💾 评估报告已保存到: {args.output}")

    elif args.mode == "correlation":
        print(f"📊 主观-客观相关性分析")
        print(f"  配置文件: {args.metrics_config}")

        if not Path(args.metrics_config).exists():
            print(f"❌ 错误: 配置文件不存在: {args.metrics_config}")
            sys.exit(1)

        with open(args.metrics_config, 'r', encoding='utf-8') as f:
            video_metrics = json.load(f)

        print(f"  分析 {len(video_metrics)} 个视频...")
        correlations = evaluator.analyze_objective_mos_correlation(video_metrics)

        if correlations:
            print(f"\n✅ 相关性分析完成:")
            for metric, corr in correlations.items():
                print(f"\n  {metric.upper()}:")
                print(f"    Pearson r: {corr['pearson_r']:.4f} (p={corr['pearson_p_value']:.4f})")
                print(f"    Spearman r: {corr['spearman_r']:.4f} (p={corr['spearman_p_value']:.4f})")
                print(f"    显著性: {'✅ 是' if corr['is_significant'] else '⚠️ 否'}")
        else:
            print(f"\n⚠️  请先添加 MOS 评分数据")


def mos_management(args):
    print("👥 MOS 评分管理")
    print()

    evaluator = create_quality_evaluator(use_mos=True)

    if args.subcommand == "add":
        print(f"➕ 添加评分:")
        print(f"  视频 ID: {args.video_id}")
        print(f"  评价者 ID: {args.rater_id}")
        print(f"  评分: {args.score}")
        if args.comment:
            print(f"  备注: {args.comment}")

        evaluator.add_mos_rating(args.video_id, args.rater_id, args.score, args.comment)
        print(f"\n✅ 评分已添加!")

    elif args.subcommand == "view":
        print(f"👁️  查看评分结果:")
        try:
            all_mos = evaluator.get_all_mos_results()

            if all_mos:
                for video_id, result in all_mos.items():
                    if args.video_id and video_id != args.video_id:
                        continue
                    print(f"\n  {video_id}:")
                    print(f"    MOS: {result.mean_score:.2f} ± {result.std_score:.2f}")
                    print(f"    95% CI: [{result.confidence_interval[0]:.2f}, {result.confidence_interval[1]:.2f}]")
                    print(f"    评价人数: {result.num_raters}")
            else:
                print("  暂无评分数据")
        except Exception as e:
            print(f"  暂无评分数据")

    elif args.subcommand == "export":
        print(f"📤 导出评分:")
        print(f"  格式: {args.format}")
        print(f"  路径: {args.output}")

        evaluator.save_mos_ratings(args.output, args.format)
        print(f"\n✅ 评分已导出到: {args.output}")

    elif args.subcommand == "import":
        print(f"📥 导入评分:")
        print(f"  格式: {args.format}")
        print(f"  路径: {args.input}")

        if not Path(args.input).exists():
            print(f"❌ 错误: 文件不存在: {args.input}")
            sys.exit(1)

        evaluator.load_mos_ratings(args.input, args.format)
        print(f"\n✅ 评分已导入!")

    elif args.subcommand == "outlier":
        print(f"🔍 异常检测:")
        print(f"  视频 ID: {args.video_id}")
        print(f"  阈值: {args.threshold}σ")

        outliers = evaluator.detect_mos_outliers(args.video_id, args.threshold)

        if outliers:
            print(f"\n⚠️  检测到 {len(outliers)} 条异常评分:")
            for i, r in enumerate(outliers, 1):
                print(f"  {i}. 评价者: {r.rater_id}, 评分: {r.score}, 时间: {r.timestamp}")
                if r.comment:
                    print(f"     备注: {r.comment}")
        else:
            print(f"\n✅ 未检测到异常评分")


def realtime_camera(args):
    print("📷 启动实时摄像头处理...")
    print("  按 'q' 键退出")
    print()

    enhancer = create_video_enhancer(
        weights_path=args.weights,
        use_patch_processing=False,
        use_temporal_alignment=not args.disable_temporal_alignment,
        use_compressed_model=args.use_compressed
    )

    if args.auto_optimize and not args.use_compressed:
        print("⚡ 自动优化推理引擎...")
        enhancer.optimize_for_inference(
            use_half=not args.disable_fp16,
            use_channels_last=not args.disable_channels_last,
            use_jit=args.use_jit
        )
        print()

    processor = RealTimeProcessor(enhancer, source=args.camera_id, target_fps=args.target_fps)

    try:
        processor.start()
    except KeyboardInterrupt:
        print("\n⏹️  已停止处理")


def run_webui(args):
    print("🌐 启动 Streamlit Web 界面...")
    print("  访问 http://localhost:8501")
    print()

    import subprocess
    cmd = [sys.executable, "-m", "streamlit", "run", "app.py"]
    subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(
        description="视频插帧超分联合处理系统 v2.0 - 使用 VESPCN 网络实现 2x2 倍增强",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 视频处理命令
    video_parser = subparsers.add_parser("video", help="处理视频文件")
    video_parser.add_argument("-i", "--input", required=True, help="输入视频路径")
    video_parser.add_argument("-o", "--output", help="输出视频路径")
    video_parser.add_argument("-w", "--weights", help="模型权重文件路径")
    video_parser.add_argument("--max-frames", type=int, help="最大处理帧数")
    video_parser.add_argument("--patch-processing", action="store_true", help="使用分块处理大视频")
    video_parser.add_argument("--quality-metrics", action="store_true", help="计算质量指标")
    video_parser.add_argument("--disable-temporal-alignment", action="store_true", help="禁用时域校准")
    video_parser.add_argument("--use-compressed", action="store_true", help="使用压缩模型")
    video_parser.add_argument("--auto-optimize", action="store_true", default=True, help="自动优化推理")
    video_parser.add_argument("--disable-fp16", action="store_true", help="禁用 FP16 半精度")
    video_parser.add_argument("--disable-channels-last", action="store_true", help="禁用 Channels Last")
    video_parser.add_argument("--use-jit", action="store_true", help="启用 JIT 编译")
    video_parser.add_argument("--target-fps", type=float, default=15.0, help="目标 FPS (默认: 15)")

    # 摄像头处理命令
    camera_parser = subparsers.add_parser("camera", help="实时摄像头处理")
    camera_parser.add_argument("-w", "--weights", help="模型权重文件路径")
    camera_parser.add_argument("--camera-id", type=int, default=0, help="摄像头设备ID")
    camera_parser.add_argument("--disable-temporal-alignment", action="store_true", help="禁用时域校准")
    camera_parser.add_argument("--use-compressed", action="store_true", help="使用压缩模型")
    camera_parser.add_argument("--auto-optimize", action="store_true", default=True, help="自动优化推理")
    camera_parser.add_argument("--disable-fp16", action="store_true", help="禁用 FP16 半精度")
    camera_parser.add_argument("--disable-channels-last", action="store_true", help="禁用 Channels Last")
    camera_parser.add_argument("--use-jit", action="store_true", help="启用 JIT 编译")
    camera_parser.add_argument("--target-fps", type=float, default=15.0, help="目标 FPS (默认: 15)")

    # 模型压缩命令
    compress_parser = subparsers.add_parser("compress", help="模型压缩与优化")
    compress_parser.add_argument("-w", "--weights", help="模型权重文件路径")
    compress_parser.add_argument("-o", "--output", help="压缩模型输出路径")
    compress_parser.add_argument("--prune-amount", type=float, help="手动指定剪枝比例 (0-1)")
    compress_parser.add_argument("--max-prune-amount", type=float, default=0.5, help="最大剪枝比例 (默认: 0.5)")
    compress_parser.add_argument("--disable-quantization", action="store_true", help="禁用 INT8 量化")
    compress_parser.add_argument("--disable-temporal-alignment", action="store_true", help="禁用时域校准")
    compress_parser.add_argument("--target-fps", type=float, default=15.0, help="目标 FPS (默认: 15)")
    compress_parser.add_argument("--benchmark-after", action="store_true", help="压缩后运行基准测试")
    compress_parser.add_argument("--benchmark-runs", type=int, default=100, help="基准测试次数")
    compress_parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")

    # 基准测试命令
    bench_parser = subparsers.add_parser("benchmark", help="性能基准测试")
    bench_parser.add_argument("-i", "--input", help="测试视频/图片路径 (可选)")
    bench_parser.add_argument("-w", "--weights", help="模型权重文件路径")
    bench_parser.add_argument("--runs", type=int, default=100, help="测试次数")
    bench_parser.add_argument("--disable-temporal-alignment", action="store_true", help="禁用时域校准")
    bench_parser.add_argument("--use-compressed", action="store_true", help="使用压缩模型")
    bench_parser.add_argument("--auto-optimize", action="store_true", default=True, help="自动优化推理")
    bench_parser.add_argument("--disable-fp16", action="store_true", help="禁用 FP16 半精度")
    bench_parser.add_argument("--disable-channels-last", action="store_true", help="禁用 Channels Last")
    bench_parser.add_argument("--use-jit", action="store_true", help="启用 JIT 编译")
    bench_parser.add_argument("--target-fps", type=float, default=15.0, help="目标 FPS (默认: 15)")

    # 质量评估命令
    eval_parser = subparsers.add_parser("evaluate", help="质量评估")
    eval_subparsers = eval_parser.add_subparsers(dest="mode", required=True)

    # 综合评估
    comp_parser = eval_subparsers.add_parser("comprehensive", help="综合质量评估")
    comp_parser.add_argument("--video-id", required=True, help="视频 ID")
    comp_parser.add_argument("--reference", help="参考帧文件 (.npy 或 .pt)")
    comp_parser.add_argument("--processed", help="处理后帧文件 (.npy 或 .pt)")
    comp_parser.add_argument("--weights-config", help='自定义权重 JSON, 例如: {"mos":0.5, "psnr":0.25, "ssim":0.2, "lpips":0.05}')
    comp_parser.add_argument("--disable-mos", action="store_true", help="禁用 MOS 评估")
    comp_parser.add_argument("-o", "--output", help="评估报告输出路径 (.json)")

    # 相关性分析
    corr_parser = eval_subparsers.add_parser("correlation", help="主观-客观相关性分析")
    corr_parser.add_argument("--metrics-config", required=True, help="视频客观指标配置文件 (.json)")
    corr_parser.add_argument("--disable-mos", action="store_true", help="禁用 MOS 评估")

    # MOS 管理命令
    mos_parser = subparsers.add_parser("mos", help="MOS 评分管理")
    mos_subparsers = mos_parser.add_subparsers(dest="subcommand", required=True)

    # 添加评分
    add_parser = mos_subparsers.add_parser("add", help="添加评分")
    add_parser.add_argument("--video-id", required=True, help="视频 ID")
    add_parser.add_argument("--rater-id", required=True, help="评价者 ID")
    add_parser.add_argument("--score", type=float, required=True, help="评分 (1-5)")
    add_parser.add_argument("--comment", help="评价备注")

    # 查看评分
    view_parser = mos_subparsers.add_parser("view", help="查看评分")
    view_parser.add_argument("--video-id", help="指定视频 ID (可选)")

    # 导出评分
    export_parser = mos_subparsers.add_parser("export", help="导出评分")
    export_parser.add_argument("-o", "--output", required=True, help="输出文件路径")
    export_parser.add_argument("--format", choices=["json", "csv"], default="json", help="导出格式")

    # 导入评分
    import_parser = mos_subparsers.add_parser("import", help="导入评分")
    import_parser.add_argument("-i", "--input", required=True, help="输入文件路径")
    import_parser.add_argument("--format", choices=["json", "csv"], default="json", help="导入格式")

    # 异常检测
    outlier_parser = mos_subparsers.add_parser("outlier", help="异常评分检测")
    outlier_parser.add_argument("--video-id", required=True, help="视频 ID")
    outlier_parser.add_argument("--threshold", type=float, default=2.0, help="异常阈值 (标准差倍数)")

    # Web UI 命令
    web_parser = subparsers.add_parser("webui", help="启动 Web 界面")

    # 训练命令
    train_parser = subparsers.add_parser("train", help="端到端训练")
    train_parser.add_argument("--train-dir", required=True, help="训练帧目录")
    train_parser.add_argument("--val-dir", help="验证帧目录")
    train_parser.add_argument("--epochs", type=int, default=100, help="训练轮数")
    train_parser.add_argument("--batch-size", type=int, default=4, help="批量大小")
    train_parser.add_argument("--lr", type=float, default=1e-4, help="学习率")
    train_parser.add_argument("--interp-weight", type=float, default=0.5, help="插帧损失权重")
    train_parser.add_argument("--sr-weight", type=float, default=0.5, help="超分损失权重")
    train_parser.add_argument("--temporal-weight", type=float, default=0.1, help="时域一致性权重")
    train_parser.add_argument("--flow-weight", type=float, default=0.05, help="光流平滑权重")
    train_parser.add_argument("--quality-weight", type=float, default=0.5, help="质量-尺度平衡权重")
    train_parser.add_argument("--patch-size", type=int, default=64, help="训练裁剪尺寸")
    train_parser.add_argument("--output-dir", default="checkpoints", help="模型保存目录")
    train_parser.add_argument("--scale-factor", type=int, default=2, help="超分倍数")
    train_parser.add_argument("--resume", help="恢复训练的检查点路径")

    # 移动端部署命令
    deploy_parser = subparsers.add_parser("deploy", help="移动端部署")
    deploy_parser.add_argument("-w", "--weights", help="模型权重文件路径")
    deploy_parser.add_argument("-o", "--output-dir", default="mobile_deploy", help="输出目录")
    deploy_parser.add_argument("--format", choices=["onnx", "torchscript", "tflite"], default="onnx", help="导出格式")
    deploy_parser.add_argument("--device", choices=["android", "ios"], default="android", help="目标设备")
    deploy_parser.add_argument("--resolution", type=str, default="480,640", help="输入分辨率 (H,W)")
    deploy_parser.add_argument("--lightweight", action="store_true", help="使用轻量级模型")
    deploy_parser.add_argument("--scale-factor", type=int, default=2, help="超分倍数")
    deploy_parser.add_argument("--benchmark", action="store_true", help="导出后运行基准测试")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    print_banner()
    check_system()

    if args.command == "video":
        process_video(args)
    elif args.command == "camera":
        realtime_camera(args)
    elif args.command == "compress":
        compress_model(args)
    elif args.command == "benchmark":
        benchmark(args)
    elif args.command == "evaluate":
        evaluate_quality(args)
    elif args.command == "mos":
        mos_management(args)
    elif args.command == "webui":
        run_webui(args)
    elif args.command == "train":
        train_model(args)
    elif args.command == "deploy":
        deploy_mobile(args)


def train_model(args):
    print(f"Training: {args.train_dir}")
    from training import create_trainer

    config = {
        'lr': args.lr,
        'epochs': args.epochs,
        'batch_size': args.batch_size,
        'interp_weight': args.interp_weight,
        'sr_weight': args.sr_weight,
        'temporal_weight': args.temporal_weight,
        'flow_weight': args.flow_weight,
        'quality_weight': args.quality_weight,
        'patch_size': args.patch_size,
        'checkpoint_dir': args.output_dir,
    }

    trainer = create_trainer(
        train_dir=args.train_dir,
        val_dir=args.val_dir,
        config=config,
        scale_factor=args.scale_factor
    )

    if args.resume:
        trainer.load_checkpoint(args.resume)

    trainer.train()

    final_path = Path(args.output_dir) / "final_model.pth"
    trainer.save_checkpoint(str(final_path))
    print(f"Model saved to: {final_path}")


def deploy_mobile(args):
    print(f"Deploying for {args.device} ({args.format})")

    res_parts = args.resolution.split(",")
    resolution = (int(res_parts[0]), int(res_parts[1]))

    enhancer = create_video_enhancer(
        weights_path=args.weights,
        use_lightweight=args.lightweight,
        scale_factor=args.scale_factor
    )

    result = enhancer.deploy_to_mobile(
        output_dir=args.output_dir,
        model_format=args.format,
        target_device=args.device,
        input_resolution=resolution
    )

    print("Deployment results:")
    for k, v in result.items():
        if k != 'config':
            print(f"  {k}: {v}")

    if args.benchmark and 'onnx_path' in result:
        try:
            from mobile_deploy import MobileModelConverter
            converter = MobileModelConverter(enhancer.model, device=str(enhancer.device))
            bench = converter.benchmark_onnx(result['onnx_path'], (1, 3, resolution[0], resolution[1]))
            print(f"\nONNX Benchmark:")
            print(f"  Avg latency: {bench['avg_time_ms']:.1f} ms")
            print(f"  FPS: {bench['fps']:.1f}")
        except Exception as e:
            print(f"Benchmark failed: {e}")


if __name__ == "__main__":
    main()
