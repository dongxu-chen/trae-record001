import streamlit as st
import cv2
import numpy as np
import tempfile
import os
from pathlib import Path
import time
from PIL import Image
import json
from typing import List, Dict

from video_processor import create_video_enhancer, VideoEnhancer
from utils import get_video_info, check_dependencies, tensor_to_pil, pil_to_tensor
from quality_metrics import create_quality_evaluator, ComprehensiveQualityResult
from mos_evaluation import MOSRating, MOSResult, CombinedQualityScore
from model_compression import ModelPruner, ModelQuantizer, ModelCompressor, InferenceOptimizer
from config import STREAMLIT_CONFIG, DEVICE

st.set_page_config(
    page_title=STREAMLIT_CONFIG["page_title"],
    page_icon=STREAMLIT_CONFIG["page_icon"],
    layout=STREAMLIT_CONFIG["layout"],
)


@st.cache_resource
def get_video_enhancer(use_patch_processing: bool = False,
                       use_temporal_alignment: bool = True,
                       use_compressed_model: bool = False):
    return create_video_enhancer(
        use_patch_processing=use_patch_processing,
        use_temporal_alignment=use_temporal_alignment,
        use_compressed_model=use_compressed_model
    )


@st.cache_resource
def get_quality_evaluator(use_mos: bool = True):
    return create_quality_evaluator(device=str(DEVICE), metrics=['psnr', 'ssim', 'lpips'], use_mos=use_mos)


def main():
    st.title("🎬 视频插帧超分联合处理系统 v2.0")
    st.markdown("基于 VESPCN 网络 | 2x 帧率提升 + 2x 分辨率提升 | 模型压缩加速 | 综合质量评估")

    with st.sidebar:
        st.header("⚙️ 系统设置")

        st.subheader("处理模式")
        mode = st.radio(
            "选择模式",
            ["视频文件处理", "实时摄像头处理", "单帧图像处理", "模型压缩优化", "质量评估", "MOS主观评分"]
        )

        st.subheader("模型配置")
        use_temporal_alignment = st.checkbox("启用时域校准", value=True,
                                             help="消除错位模糊，提升时序一致性")
        use_compressed_model = st.checkbox("使用压缩模型", value=False,
                                           help="加载压缩优化后的模型以获得更快的推理速度")

        st.subheader("推理优化")
        use_fp16 = st.checkbox("FP16 半精度", value=True, help="使用半精度加速推理")
        use_channels_last = st.checkbox("Channels Last", value=True, help="优化内存格式")
        use_jit = st.checkbox("JIT 编译", value=False, help="使用 TorchScript 编译加速")

        st.subheader("目标性能")
        target_fps = st.slider("目标 FPS", 10.0, 30.0, 15.0, 1.0,
                               help="模型压缩时的目标帧率")

        if mode != "质量评估" and mode != "MOS主观评分":
            use_patch_processing = st.checkbox("使用分块处理 (大视频)", value=False)
            if use_patch_processing:
                patch_size = st.slider("分块大小", 128, 1024, 512, 128)

        st.subheader("系统信息")
        deps = check_dependencies()
        st.info(f"PyTorch: {deps['torch']}\nCUDA: {'可用' if deps['cuda_available'] else '不可用'}\nOpenCV: {deps['opencv']}")

    if mode == "视频文件处理":
        video_file_processing(use_temporal_alignment, use_compressed_model,
                              use_fp16, use_channels_last, use_jit, target_fps)
    elif mode == "实时摄像头处理":
        realtime_processing(use_temporal_alignment, use_compressed_model,
                           use_fp16, use_channels_last, use_jit, target_fps)
    elif mode == "单帧图像处理":
        single_frame_processing(use_temporal_alignment, use_compressed_model,
                               use_fp16, use_channels_last, use_jit)
    elif mode == "模型压缩优化":
        model_compression_page(use_temporal_alignment, target_fps)
    elif mode == "质量评估":
        quality_evaluation()
    elif mode == "MOS主观评分":
        mos_evaluation_page()


def video_file_processing(use_temporal_alignment: bool, use_compressed_model: bool,
                          use_fp16: bool, use_channels_last: bool, use_jit: bool,
                          target_fps: float):
    st.header("📹 视频文件处理")

    uploaded_file = st.file_uploader("上传视频文件", type=['mp4', 'avi', 'mov', 'mkv'])

    if uploaded_file is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(uploaded_file.read())
        tfile.close()

        video_info = get_video_info(tfile.name)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("分辨率", f"{video_info['width']}x{video_info['height']}")
        with col2:
            st.metric("帧率", f"{video_info['fps']:.1f} FPS")
        with col3:
            st.metric("总帧数", video_info['total_frames'])
        with col4:
            st.metric("时长", f"{video_info['duration']:.1f}s")

        max_frames = st.slider("处理帧数限制", 10, video_info['total_frames'],
                               min(100, video_info['total_frames']), 10)

        col1, col2 = st.columns(2)
        with col1:
            enable_quality_metrics = st.checkbox("启用质量评估", value=True)
        with col2:
            auto_optimize = st.checkbox("自动优化推理", value=True)

        if st.button("开始处理", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()

            enhancer = get_video_enhancer(
                use_patch_processing=False,
                use_temporal_alignment=use_temporal_alignment,
                use_compressed_model=use_compressed_model
            )

            if auto_optimize and not use_compressed_model:
                with st.spinner("正在优化推理引擎..."):
                    enhancer.optimize_for_inference(
                        use_half=use_fp16,
                        use_channels_last=use_channels_last,
                        use_jit=use_jit
                    )
                st.success("✅ 推理优化完成!")

            model_info = enhancer.get_model_info()
            with st.expander("📊 模型信息"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("参数量", f"{model_info['num_parameters']/1e6:.2f} M")
                with col2:
                    st.metric("模型大小", f"{model_info['model_size_mb']:.1f} MB")
                with col3:
                    st.metric("目标 FPS", f"{target_fps:.0f}")

            def progress_callback(current, total):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"处理中... {current}/{total} 帧")

            with st.spinner("正在处理视频..."):
                result = enhancer.process_video(
                    tfile.name,
                    max_frames=max_frames,
                    progress_callback=progress_callback,
                    enable_quality_metrics=enable_quality_metrics
                )

            progress_bar.progress(1.0)
            status_text.text("处理完成!")

            st.success("✅ 视频处理完成!")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("输入分辨率", result['input_resolution'])
                st.metric("输入帧率", f"{result['input_fps']:.1f} FPS")
            with col2:
                st.metric("输出分辨率", result['output_resolution'])
                st.metric("输出帧率", f"{result['output_fps']:.1f} FPS")
            with col3:
                avg_fps = 1.0 / result['avg_processing_time']
                fps_met = "✅" if avg_fps >= target_fps else "⚠️"
                st.metric("平均处理 FPS", f"{avg_fps:.1f} {fps_met}")
                st.metric("总处理时间", f"{result['total_processing_time']:.1f}s")

            if 'quality_metrics' in result:
                st.subheader("📊 客观质量指标")
                metrics = result['quality_metrics']
                col1, col2, col3 = st.columns(3)
                with col1:
                    psnr_color = "normal" if metrics.get('psnr', 0) >= 35 else "off"
                    st.metric("PSNR", f"{metrics.get('psnr', 0):.2f} dB",
                              help="峰值信噪比，越高越好")
                with col2:
                    st.metric("SSIM", f"{metrics.get('ssim', 0):.4f}",
                              help="结构相似性，范围 [0,1]，越高越好")
                with col3:
                    st.metric("LPIPS", f"{metrics.get('lpips', 0):.4f}",
                              help="感知相似度，越低越好")

            if 'temporal_metrics' in result:
                st.subheader("⏱️ 时序一致性指标")
                temp_metrics = result['temporal_metrics']
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("时序一致性", f"{temp_metrics.get('temporal_consistency_mean', 0):.4f}")
                with col2:
                    st.metric("时序 PSNR", f"{temp_metrics.get('temporal_psnr_mean', 0):.2f} dB")

            if os.path.exists(result['output_path']):
                with open(result['output_path'], 'rb') as f:
                    video_bytes = f.read()
                st.download_button(
                    label="📥 下载处理后的视频",
                    data=video_bytes,
                    file_name=f"enhanced_{uploaded_file.name}",
                    mime="video/mp4"
                )

        os.unlink(tfile.name)


def realtime_processing(use_temporal_alignment: bool, use_compressed_model: bool,
                       use_fp16: bool, use_channels_last: bool, use_jit: bool,
                       target_fps: float):
    st.header("📷 实时摄像头处理")

    st.warning("实时处理模式将使用默认摄像头 (设备 0)，按 '停止' 按钮退出。")

    enhancer = get_video_enhancer(
        use_patch_processing=False,
        use_temporal_alignment=use_temporal_alignment,
        use_compressed_model=use_compressed_model
    )

    if not use_compressed_model:
        with st.spinner("正在优化推理引擎..."):
            enhancer.optimize_for_inference(
                use_half=use_fp16,
                use_channels_last=use_channels_last,
                use_jit=use_jit
            )

    model_info = enhancer.get_model_info()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("参数量", f"{model_info['num_parameters']/1e6:.2f} M")
    with col2:
        st.metric("目标 FPS", f"{target_fps:.0f}")
    with col3:
        status_placeholder = st.empty()
        status_placeholder.info("⏳ 等待处理...")

    frame_placeholder = st.empty()
    fps_placeholder = st.empty()
    stop_button = st.button("停止处理", type="secondary")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        st.error("无法打开摄像头")
        return

    prev_frame = None
    frame_times = []
    fps_history = []

    while not stop_button:
        ret, frame = cap.read()
        if not ret:
            break

        start_time = time.time()

        if prev_frame is not None:
            _, _, enhanced = enhancer.interpolate_and_enhance(prev_frame, frame)
        else:
            enhanced = enhancer.enhance_frame(frame)

        processing_time = time.time() - start_time
        current_fps = 1.0 / processing_time if processing_time > 0 else 0
        frame_times.append(processing_time)
        fps_history.append(current_fps)

        if len(frame_times) > 30:
            frame_times.pop(0)
        if len(fps_history) > 30:
            fps_history.pop(0)

        avg_fps = np.mean(fps_history)
        fps_met = avg_fps >= target_fps

        if fps_met:
            status_placeholder.success(f"✅ 达到目标 FPS ({target_fps:.0f})")
        else:
            status_placeholder.warning(f"⚠️ 未达到目标 FPS (当前: {avg_fps:.1f}, 目标: {target_fps:.0f})")

        enhanced_rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
        frame_placeholder.image(enhanced_rgb, channels="RGB", use_column_width=True)

        fps_info = f"""
        **实时 FPS**: {current_fps:.1f} | **平均 FPS**: {avg_fps:.1f} | 
        **处理时间**: {np.mean(frame_times)*1000:.1f}ms | 
        **目标 FPS**: {target_fps:.0f} {'✅' if fps_met else '⚠️'}
        """
        fps_placeholder.markdown(fps_info)

        prev_frame = frame

    cap.release()
    st.info("✅ 已停止摄像头处理")

    if fps_history:
        st.subheader("📊 性能统计")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("平均 FPS", f"{np.mean(fps_history):.1f}")
        with col2:
            st.metric("最小 FPS", f"{np.min(fps_history):.1f}")
        with col3:
            st.metric("最大 FPS", f"{np.max(fps_history):.1f}")


def single_frame_processing(use_temporal_alignment: bool, use_compressed_model: bool,
                           use_fp16: bool, use_channels_last: bool, use_jit: bool):
    st.header("🖼️ 单帧图像处理")

    uploaded_image = st.file_uploader("上传图片", type=['png', 'jpg', 'jpeg'])

    if uploaded_image is not None:
        image = Image.open(uploaded_image)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("原图")
            st.image(image, use_column_width=True)
            st.info(f"分辨率: {image.size[0]}x{image.size[1]}")

        enhancer = get_video_enhancer(
            use_patch_processing=False,
            use_temporal_alignment=use_temporal_alignment,
            use_compressed_model=use_compressed_model
        )

        if not use_compressed_model:
            enhancer.optimize_for_inference(
                use_half=use_fp16,
                use_channels_last=use_channels_last,
                use_jit=use_jit
            )

        with st.spinner("处理中..."):
            frame = np.array(image)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            start_time = time.time()
            enhanced = enhancer.enhance_frame(frame)
            processing_time = time.time() - start_time

            enhanced_rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
            enhanced_pil = Image.fromarray(enhanced_rgb)

        with col2:
            st.subheader("增强后")
            st.image(enhanced_pil, use_column_width=True)
            st.success(f"分辨率: {enhanced_pil.size[0]}x{enhanced_pil.size[1]}")
            st.info(f"处理时间: {processing_time*1000:.1f}ms")

        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            enhanced_pil.save(tmp.name)
            with open(tmp.name, 'rb') as f:
                st.download_button(
                    label="📥 下载增强图片",
                    data=f.read(),
                    file_name=f"enhanced_{uploaded_image.name}",
                    mime="image/png"
                )
            os.unlink(tmp.name)

        st.subheader("📊 对比分析")
        show_difference = st.checkbox("显示差异图")
        if show_difference:
            resized_original = image.resize(enhanced_pil.size, Image.BICUBIC)
            diff = np.abs(np.array(enhanced_pil) - np.array(resized_original)).mean(axis=2)
            st.image(diff, caption="差异图", use_column_width=True, clamp=True)


def model_compression_page(use_temporal_alignment: bool, target_fps: float):
    st.header("⚡ 模型压缩与优化")
    st.markdown("通过剪枝和量化技术，在保持质量的同时提升推理速度到目标 FPS")

    enhancer = get_video_enhancer(
        use_patch_processing=False,
        use_temporal_alignment=use_temporal_alignment,
        use_compressed_model=False
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 原始模型信息")
        original_info = enhancer.get_model_info()
        st.metric("参数量", f"{original_info['num_parameters']/1e6:.2f} M")
        st.metric("模型大小", f"{original_info['model_size_mb']:.1f} MB")

    with col2:
        st.subheader("🎯 压缩目标")
        target_fps_val = st.slider("目标 FPS", 10.0, 30.0, target_fps, 1.0)
        max_prune_amount = st.slider("最大剪枝比例", 0.2, 0.8, 0.5, 0.1,
                                     help="最多剪枝的参数比例")
        use_quantization = st.checkbox("启用量化", value=True,
                                       help="使用 INT8 量化进一步加速")

    st.subheader("🔧 压缩配置")
    compression_mode = st.radio(
        "压缩模式",
        ["自动优化 (推荐)", "手动配置"],
        horizontal=True
    )

    if compression_mode == "手动配置":
        col1, col2 = st.columns(2)
        with col1:
            prune_method = st.selectbox("剪枝方法", ["L1 非结构化剪枝", "结构化剪枝"])
            prune_amount = st.slider("剪枝比例", 0.1, max_prune_amount, 0.3, 0.1)
        with col2:
            quant_method = st.selectbox("量化方法", ["动态量化", "静态量化", "QAT 量化"])

    if st.button("开始压缩", type="primary"):
        with st.spinner("正在压缩模型，可能需要几分钟..."):
            if compression_mode == "自动优化":
                compressed_model, result = enhancer.compress_model(
                    target_fps=target_fps_val,
                    use_quantization=use_quantization
                )
            else:
                prune_amount_val = prune_amount if compression_mode == "手动配置" else None
                compressed_model, result = enhancer.compress_model(
                    target_fps=target_fps_val,
                    prune_amount=prune_amount_val,
                    use_quantization=use_quantization
                )

        st.success("✅ 模型压缩完成!")

        st.subheader("📈 压缩结果")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("压缩后 FPS", f"{result.get('final_fps', 0):.1f}",
                      delta=f"{result.get('speedup_ratio', 1.0):.1f}x")
        with col2:
            st.metric("参数压缩率", f"{result.get('prune_ratio', 0)*100:.1f}%")
        with col3:
            fps_met = result.get('target_fps_met', False)
            st.metric("目标达成", "✅ 是" if fps_met else "⚠️ 否")

        with st.expander("详细压缩信息"):
            st.json(result)

        st.subheader("💾 保存压缩模型")
        save_path = st.text_input("保存路径", value="models/compressed_vespcn.pt")
        if st.button("保存模型"):
            enhancer.save_compressed_model(save_path)
            st.success(f"✅ 模型已保存到: {save_path}")

    st.subheader("🧪 性能基准测试")
    if st.button("运行基准测试"):
        with st.spinner("正在运行基准测试..."):
            benchmark_result = enhancer.benchmark_full_pipeline(num_iterations=100)

        st.success("✅ 基准测试完成!")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("平均 FPS", f"{benchmark_result.get('fps', 0):.1f}")
        with col2:
            st.metric("平均延迟", f"{benchmark_result.get('latency_ms', 0):.1f} ms")
        with col3:
            st.metric("显存占用", f"{benchmark_result.get('memory_mb', 0):.1f} MB")

        with st.expander("详细基准测试结果"):
            st.json(benchmark_result)


def quality_evaluation():
    st.header("📊 综合质量评估")
    st.markdown("客观指标 + 主观 MOS 评分的综合质量评估")

    evaluator = get_quality_evaluator(use_mos=True)

    eval_mode = st.radio(
        "评估模式",
        ["单图像对评估", "综合质量报告", "MOS-客观相关性分析"],
        horizontal=True
    )

    if eval_mode == "单图像对评估":
        col1, col2 = st.columns(2)

        with col1:
            uploaded_image1 = st.file_uploader("上传原始图片", type=['png', 'jpg', 'jpeg'], key="img1")
        with col2:
            uploaded_image2 = st.file_uploader("上传对比图片", type=['png', 'jpg', 'jpeg'], key="img2")

        if uploaded_image1 and uploaded_image2:
            img1 = Image.open(uploaded_image1)
            img2 = Image.open(uploaded_image2)

            if img1.size != img2.size:
                st.warning(f"图片尺寸不一致: {img1.size} vs {img2.size}")
                img2 = img2.resize(img1.size, Image.BICUBIC)

            col1, col2 = st.columns(2)
            with col1:
                st.image(img1, caption="原图", use_column_width=True)
            with col2:
                st.image(img2, caption="对比图", use_column_width=True)

            tensor1 = pil_to_tensor(img1, device=str(DEVICE))
            tensor2 = pil_to_tensor(img2, device=str(DEVICE))

            with st.spinner("计算质量指标..."):
                metrics = evaluator.calculate_all(tensor1, tensor2)

            st.subheader("客观质量指标")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("PSNR", f"{metrics.get('psnr', 0):.2f} dB",
                          help="峰值信噪比，越高越好")
            with col2:
                st.metric("SSIM", f"{metrics.get('ssim', 0):.4f}",
                          help="结构相似性，范围 [0,1]，越高越好")
            with col3:
                st.metric("LPIPS", f"{metrics.get('lpips', 0):.4f}",
                          help="感知相似度，越低越好")

    elif eval_mode == "综合质量报告":
        st.subheader("综合质量评估")

        video_id = st.text_input("视频 ID", value="video_001")

        uploaded_ref = st.file_uploader("上传参考视频帧 (可选)", type=['npy', 'pt'], key="ref")
        uploaded_proc = st.file_uploader("上传处理后视频帧 (可选)", type=['npy', 'pt'], key="proc")

        use_custom_weights = st.checkbox("自定义权重")
        weights = None
        if use_custom_weights:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                w_mos = st.slider("MOS 权重", 0.0, 1.0, 0.4, 0.05)
            with col2:
                w_psnr = st.slider("PSNR 权重", 0.0, 1.0, 0.25, 0.05)
            with col3:
                w_ssim = st.slider("SSIM 权重", 0.0, 1.0, 0.25, 0.05)
            with col4:
                w_lpips = st.slider("LPIPS 权重", 0.0, 1.0, 0.1, 0.05)

            total = w_mos + w_psnr + w_ssim + w_lpips
            if abs(total - 1.0) > 0.01:
                st.warning(f"权重总和应为 1.0，当前为 {total:.2f}，将自动归一化")
            weights = {
                'mos': w_mos / total,
                'psnr': w_psnr / total,
                'ssim': w_ssim / total,
                'lpips': w_lpips / total
            }

        if st.button("生成综合评估报告"):
            ref_frames = None
            proc_frames = None

            if uploaded_ref is not None and uploaded_proc is not None:
                try:
                    if uploaded_ref.name.endswith('.npy'):
                        ref_frames = torch.from_numpy(np.load(uploaded_ref))
                        proc_frames = torch.from_numpy(np.load(uploaded_proc))
                    else:
                        ref_frames = torch.load(uploaded_ref, map_location='cpu')
                        proc_frames = torch.load(uploaded_proc, map_location='cpu')
                except Exception as e:
                    st.error(f"加载帧数据失败: {e}")

            with st.spinner("正在生成综合评估报告..."):
                result = evaluator.evaluate_comprehensive(
                    video_id=video_id,
                    reference_frames=ref_frames,
                    processed_frames=proc_frames,
                    calculate_objective=(ref_frames is not None),
                    weights=weights
                )

            st.success("✅ 综合评估完成!")

            if result.combined_score:
                st.subheader("🏆 综合质量评分")
                combined = result.combined_score

                score_col, level_col = st.columns(2)
                with score_col:
                    st.metric("综合得分", f"{combined.combined_score:.2f}/5")
                with level_col:
                    st.info(f"质量等级: **{result.quality_level}**")

                st.subheader("📊 分项得分")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("MOS 评分", f"{combined.mos_score:.2f}")
                with col2:
                    st.metric("PSNR", f"{combined.psnr:.1f} dB")
                with col3:
                    st.metric("SSIM", f"{combined.ssim:.3f}")
                with col4:
                    st.metric("LPIPS", f"{combined.lpips:.3f}")

                with st.expander("权重配置"):
                    st.json(combined.weights)

            if result.objective_metrics:
                st.subheader("📈 客观指标详情")
                st.json(result.objective_metrics)

            if result.mos_result:
                st.subheader("👥 MOS 评分详情")
                mos = result.mos_result
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("MOS 均值", f"{mos.mean_score:.2f} ± {mos.std_score:.2f}")
                with col2:
                    st.metric("95% 置信区间", f"[{mos.confidence_interval[0]:.2f}, {mos.confidence_interval[1]:.2f}]")
                with col3:
                    st.metric("评价人数", mos.num_raters)

            if result.temporal_metrics:
                st.subheader("⏱️ 时序一致性")
                st.json(result.temporal_metrics)

            with st.expander("完整评估报告"):
                st.json(result.to_dict())

            export_format = st.selectbox("导出格式", ["JSON", "CSV"])
            if st.button("导出报告"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{export_format.lower()}') as tmp:
                    if export_format == "JSON":
                        with open(tmp.name, 'w', encoding='utf-8') as f:
                            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
                    else:
                        import csv
                        with open(tmp.name, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow(['指标', '值'])
                            for key, value in result.to_dict().items():
                                if isinstance(value, dict):
                                    for k, v in value.items():
                                        writer.writerow([f"{key}.{k}", v])
                                else:
                                    writer.writerow([key, value])

                    with open(tmp.name, 'rb') as f:
                        st.download_button(
                            label="📥 下载评估报告",
                            data=f.read(),
                            file_name=f"quality_report_{video_id}.{export_format.lower()}",
                            mime=f"application/{export_format.lower()}"
                        )
                    os.unlink(tmp.name)

    elif eval_mode == "MOS-客观相关性分析":
        st.subheader("📊 主观-客观指标相关性分析")
        st.info("分析 MOS 主观评分与客观指标 (PSNR/SSIM/LPIPS) 之间的相关性")

        num_videos = st.number_input("视频数量", min_value=3, max_value=20, value=5)

        video_metrics = {}
        for i in range(num_videos):
            with st.expander(f"视频 {i+1}"):
                vid = f"video_{i+1:03d}"
                col1, col2, col3 = st.columns(3)
                with col1:
                    psnr = st.number_input(f"PSNR (dB)", min_value=0.0, max_value=100.0, value=30.0+i, key=f"psnr_{i}")
                with col2:
                    ssim = st.number_input(f"SSIM", min_value=0.0, max_value=1.0, value=0.8+i*0.02, key=f"ssim_{i}")
                with col3:
                    lpips = st.number_input(f"LPIPS", min_value=0.0, max_value=1.0, value=0.2-i*0.02, key=f"lpips_{i}")

                video_metrics[vid] = {'psnr': psnr, 'ssim': ssim, 'lpips': lpips}

        if st.button("分析相关性"):
            with st.spinner("正在计算相关性..."):
                correlations = evaluator.analyze_objective_mos_correlation(video_metrics)

            if correlations:
                st.success("✅ 相关性分析完成!")

                for metric, corr in correlations.items():
                    st.subheader(f"📈 {metric.upper()} - MOS 相关性")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Pearson 相关系数", f"{corr['pearson_r']:.4f}",
                                  delta="显著" if corr['is_significant'] else "不显著")
                    with col2:
                        st.metric("P-value", f"{corr['pearson_p_value']:.4f}")
                    with col3:
                        st.metric("样本数", corr['num_samples'])

                    st.info(f"Spearman 相关系数: {corr['spearman_r']:.4f} (p={corr['spearman_p_value']:.4f})")

                    if corr['is_significant']:
                        st.success(f"✅ {metric.upper()} 与 MOS 评分存在显著相关性")
                    else:
                        st.warning(f"⚠️ {metric.upper()} 与 MOS 评分相关性不显著")
            else:
                st.warning("请先添加 MOS 评分数据")

    st.markdown("""
    ### 指标说明
    - **PSNR (Peak Signal-to-Noise Ratio)**: 衡量图像质量的客观指标，单位为 dB。通常 >30dB 表示高质量。
    - **SSIM (Structural Similarity Index Measure)**: 衡量图像结构相似性，范围 [0, 1]。越接近 1 表示质量越好。
    - **LPIPS (Learned Perceptual Image Patch Similarity)**: 基于深度学习的感知相似度指标。越低表示感知质量越好。
    - **MOS (Mean Opinion Score)**: 主观平均意见得分，范围 [1, 5]。>4.0 表示优秀，>3.5 表示良好。
    - **综合得分**: 加权融合 MOS (40%)、PSNR (25%)、SSIM (25%)、LPIPS (10%) 的综合质量评分。
    """)


def mos_evaluation_page():
    st.header("👥 MOS 主观评分系统")
    st.markdown("收集、管理和分析视频质量的主观评价数据")

    evaluator = get_quality_evaluator(use_mos=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📝 添加评分", "📊 查看结果", "📁 导入导出", "🔍 异常检测"])

    with tab1:
        st.subheader("添加 MOS 评分")

        col1, col2 = st.columns(2)
        with col1:
            video_id = st.text_input("视频 ID", value="video_001")
            rater_id = st.text_input("评价者 ID", value="rater_001")
        with col2:
            score = st.slider("质量评分 (1-5)", 1.0, 5.0, 3.5, 0.5,
                              help="1=很差, 2=较差, 3=一般, 4=很好, 5=优秀")
            comment = st.text_input("评价备注 (可选)", placeholder="请输入您的评价...")

        if st.button("提交评分", type="primary"):
            try:
                evaluator.add_mos_rating(video_id, rater_id, score, comment)
                st.success(f"✅ 评分已提交! 视频: {video_id}, 评分: {score}")
            except Exception as e:
                st.error(f"提交失败: {e}")

        st.divider()

        st.subheader("批量添加评分")
        batch_data = st.text_area(
            "批量评分数据 (JSON 格式)",
            height=200,
            placeholder='''[
  {"video_id": "video_001", "rater_id": "rater_001", "score": 4.0, "comment": "很好"},
  {"video_id": "video_002", "rater_id": "rater_001", "score": 3.5, "comment": "一般"}
]'''
        )

        if st.button("批量提交"):
            try:
                import json
                ratings_data = json.loads(batch_data)
                ratings_list = [
                    (r['video_id'], r['rater_id'], r['score'], r.get('comment'))
                    for r in ratings_data
                ]
                evaluator.add_mos_ratings_batch(ratings_list)
                st.success(f"✅ 已提交 {len(ratings_list)} 条评分!")
            except Exception as e:
                st.error(f"批量提交失败: {e}")

    with tab2:
        st.subheader("查看 MOS 结果")

        try:
            all_mos = evaluator.get_all_mos_results()

            if all_mos:
                for video_id, result in all_mos.items():
                    with st.expander(f"📊 {video_id}"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("MOS 均值", f"{result.mean_score:.2f} ± {result.std_score:.2f}")
                        with col2:
                            st.metric("95% 置信区间",
                                      f"[{result.confidence_interval[0]:.2f}, {result.confidence_interval[1]:.2f}]")
                        with col3:
                            st.metric("评价人数", result.num_raters)

                        if hasattr(result, 'ratings') and result.ratings:
                            st.subheader("评分分布")
                            scores = [r.score for r in result.ratings]
                            fig = create_score_histogram(scores)
                            st.plotly_chart(fig, use_container_width=True)

                            st.subheader("评分详情")
                            import pandas as pd
                            df = pd.DataFrame([
                                {
                                    '评价者': r.rater_id,
                                    '评分': r.score,
                                    '时间': r.timestamp,
                                    '备注': r.comment or ''
                                }
                                for r in result.ratings
                            ])
                            st.dataframe(df, use_container_width=True)
            else:
                st.info("暂无评分数据，请先添加评分。")

        except Exception as e:
            st.info("暂无评分数据")

        st.divider()

        st.subheader("评价者可靠性分析")
        rater_id = st.text_input("评价者 ID", value="rater_001", key="rater_rel")
        if st.button("分析可靠性"):
            try:
                reliability = evaluator.get_rater_reliability(rater_id)
                st.json(reliability)
            except Exception as e:
                st.warning(f"无法分析: {e}")

    with tab3:
        st.subheader("导入导出评分数据")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("导出")
            export_format = st.selectbox("导出格式", ["json", "csv"], key="export_fmt")
            export_path = st.text_input("导出路径", value=f"mos_ratings.{export_format}")

            if st.button("导出评分"):
                try:
                    evaluator.save_mos_ratings(export_path, export_format)
                    st.success(f"✅ 评分已导出到: {export_path}")

                    with open(export_path, 'rb') as f:
                        st.download_button(
                            label="📥 下载导出文件",
                            data=f.read(),
                            file_name=export_path,
                            mime=f"application/{export_format}"
                        )
                except Exception as e:
                    st.error(f"导出失败: {e}")

        with col2:
            st.subheader("导入")
            import_format = st.selectbox("导入格式", ["json", "csv"], key="import_fmt")
            uploaded_file = st.file_uploader("选择评分文件", type=['json', 'csv'])

            if uploaded_file is not None and st.button("导入评分"):
                try:
                    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{import_format}')
                    tfile.write(uploaded_file.read())
                    tfile.close()

                    evaluator.load_mos_ratings(tfile.name, import_format)
                    os.unlink(tfile.name)
                    st.success("✅ 评分导入成功!")
                except Exception as e:
                    st.error(f"导入失败: {e}")

    with tab4:
        st.subheader("异常评分检测")
        st.info("检测偏离整体评分分布的异常评分，用于数据清洗。")

        video_id = st.text_input("视频 ID", value="video_001", key="outlier_vid")
        threshold = st.slider("异常阈值 (标准差倍数)", 1.0, 4.0, 2.0, 0.5,
                              help="大于此倍数的评分将被视为异常")

        if st.button("检测异常"):
            try:
                outliers = evaluator.detect_mos_outliers(video_id, threshold)

                if outliers:
                    st.warning(f"⚠️ 检测到 {len(outliers)} 条异常评分!")

                    import pandas as pd
                    df = pd.DataFrame([
                        {
                            '评价者': r.rater_id,
                            '评分': r.score,
                            '时间': r.timestamp,
                            '备注': r.comment or ''
                        }
                        for r in outliers
                    ])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.success("✅ 未检测到异常评分")

            except Exception as e:
                st.warning(f"检测失败: {e}")


def create_score_histogram(scores):
    import plotly.graph_objects as go

    fig = go.Figure(data=[go.Histogram(
        x=scores,
        nbinsx=5,
        marker_color='rgb(100, 149, 237)',
        marker_line_color='rgb(8,48,107)',
        marker_line_width=1.5,
        opacity=0.8
    )])

    fig.update_layout(
        title='评分分布',
        xaxis_title='评分',
        yaxis_title='频次',
        bargap=0.1,
        height=300
    )

    fig.update_xaxes(range=[0.5, 5.5], tickvals=[1, 2, 3, 4, 5])

    return fig


if __name__ == "__main__":
    main()
