import streamlit as st
import numpy as np
import cv2
from PIL import Image
from depth_estimator import MiDaSDepthEstimator
from crf_optimizer import FastCRFDepthOptimizer
from depth_super_resolution import (
    DepthSuperResolution,
    align_depth_to_rgb,
    create_aligned_colored_depth,
    compute_depth_metrics,
    MetricsAccumulator,
)
from utils import (
    colorize_depth,
    colorize_depth_dynamic,
    enhance_edges,
    overlay_edges_on_depth,
    compute_depth_gradients,
    create_side_by_side,
    format_metrics_display,
)


@st.cache_resource
def load_estimator(model_type):
    return MiDaSDepthEstimator(model_type=model_type)


@st.cache_resource
def load_crf_optimizer(
    iterations,
    bilateral_sxy,
    bilateral_srgb,
    bilateral_compat,
    gaussian_sxy,
    gaussian_compat,
    num_depth_bins,
    downscale,
    use_approx,
    texture_skip_threshold,
):
    return FastCRFDepthOptimizer(
        num_iterations=iterations,
        bilateral_sxy=bilateral_sxy,
        bilateral_srgb=bilateral_srgb,
        bilateral_compat=bilateral_compat,
        gaussian_sxy=gaussian_sxy,
        gaussian_compat=gaussian_compat,
        num_depth_bins=num_depth_bins,
        downscale=downscale,
        use_approx=use_approx,
        texture_skip_threshold=texture_skip_threshold,
    )


def pil_to_cv2(pil_image):
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)


def cv2_to_pil(cv2_image):
    if len(cv2_image.shape) == 2:
        return Image.fromarray(cv2_image)
    return Image.fromarray(cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB))


def main():
    st.set_page_config(page_title="单目深度估计优化", layout="wide", page_icon="🔭")

    st.title("🔭 单目视觉深度估计优化 (v3.0)")
    st.markdown("基于 **MiDaS** + **快速CRF** + **超分辨率** + **RGB对齐** + **实时评估**")

    with st.sidebar:
        st.header("⚙️ 参数配置")

        model_type = st.selectbox(
            "MiDaS 模型",
            ["MiDaS_small", "DPT_Hybrid", "DPT_Large"],
            index=1,
            help="MiDaS_small 最快，DPT_Large 最精确",
        )

        st.subheader("🚀 快速 CRF 优化")
        use_crf = st.checkbox("启用 CRF 边缘优化", value=True)
        use_fast_approx = st.checkbox("快速近似模式 (15fps+)", value=True, help="使用引导滤波近似替代完整CRF推理")
        if use_crf:
            crf_iterations = st.slider("CRF 迭代次数", 1, 10, 3)
            crf_downscale = st.slider("CRF 处理下采样倍数", 1, 4, 2, help="越大越快，但细节可能损失")
            num_depth_bins = st.slider("深度离散化 bin 数", 8, 64, 24, help="越小越快")
            texture_skip_threshold = st.slider("低纹理跳过阈值", 0.001, 0.05, 0.01, step=0.001, help="低于此值的低纹理区域跳过CRF")
            with st.expander("⚙️ 高级 CRF 参数"):
                bilateral_sxy = st.slider("双边空间参数 (sxy)", 10, 200, 60)
                bilateral_srgb = st.slider("双边颜色参数 (srgb)", 1, 50, 10)
                bilateral_compat = st.slider("双边兼容性", 1, 50, 8)
                gaussian_sxy = st.slider("高斯空间参数 (sxy)", 1, 20, 3)
                gaussian_compat = st.slider("高斯兼容性", 1, 20, 3)
        else:
            crf_iterations = 3
            bilateral_sxy = 60
            bilateral_srgb = 10
            bilateral_compat = 8
            gaussian_sxy = 3
            gaussian_compat = 3
            crf_downscale = 2
            use_fast_approx = True
            num_depth_bins = 24
            texture_skip_threshold = 0.01

        st.subheader("🔬 深度超分辨率")
        use_sr = st.checkbox("启用深度超分辨率", value=False, help="低分辨率深度图上采样至高分辨率")
        if use_sr:
            sr_method = st.selectbox(
                "上采样方法",
                ["bilinear_guided", "nearest", "bilinear", "bicubic", "laplacian_pyramid", "edge_preserving"],
                index=0,
                help="bilinear_guided: 双边引导滤波(推荐); laplacian_pyramid: 拉普拉斯金字塔; edge_preserving: 边缘保持",
            )
            sr_scale = st.slider("上采样倍数", 2, 4, 2)
            sr_guided = st.checkbox("使用RGB引导", value=True, help="用RGB图像作为引导保持边缘")
        else:
            sr_method = "bilinear_guided"
            sr_scale = 2
            sr_guided = True

        st.subheader("🎯 RGB-深度对齐")
        align_depth = st.checkbox("启用深度-RGB对齐", value=True, help="确保深度图与RGB图像像素对齐")
        if align_depth:
            alpha_blend = st.slider("RGB混合透明度", 0.0, 0.5, 0.0, help="0=纯深度, 0.5=50%RGB+50%深度")
        else:
            alpha_blend = 0.0

        st.subheader("📊 评估指标")
        show_metrics = st.checkbox("显示评估指标", value=False, help="需要提供真值深度图")
        if show_metrics:
            gt_file = st.file_uploader("上传真值深度图", type=["npy", "png", "jpg"], key="gt_upload")

        st.subheader("🎨 动态彩色化")
        colormap = st.selectbox(
            "深度图配色",
            ["turbo", "magma", "inferno", "plasma", "viridis", "jet"],
            index=0,
        )
        dynamic_color = st.checkbox("动态深度映射", value=True, help="根据深度分布自动调整颜色表")

        st.subheader("🔍 自适应边缘增强")
        show_edges = st.checkbox("叠加边缘", value=False)
        adaptive_edges = st.checkbox("自适应阈值", value=True, help="纹理区弱增强，边缘区强增强")
        edge_method = st.selectbox("边缘检测方法", ["canny", "sobel", "laplacian"], index=0)
        edge_alpha = st.slider("边缘叠加透明度", 0.0, 1.0, 0.3)
        if adaptive_edges:
            texture_threshold = st.slider("纹理区分阈值", 0.1, 0.5, 0.25)
            min_enhancement = st.slider("纹理区最小增强", 0.1, 0.7, 0.3)

        st.subheader("📹 视频处理")
        target_width = st.slider("处理分辨率宽度", 320, 1280, 640, step=64)
        temporal_alpha = st.slider("时序平滑系数", 0.0, 1.0, 0.7, help="值越大越平滑，但延迟越高")

    tab_image, tab_video, tab_about = st.tabs(["🖼️ 图片深度估计", "🎬 视频流处理", "ℹ️ 技术说明"])

    with tab_image:
        st.subheader("上传图片进行深度估计")
        uploaded_file = st.file_uploader("选择图片", type=["jpg", "jpeg", "png", "bmp"], key="image_upload")

        if uploaded_file is not None:
            pil_image = Image.open(uploaded_file).convert("RGB")
            image_bgr = pil_to_cv2(pil_image)

            with st.spinner("正在加载模型并估计深度..."):
                estimator = load_estimator(model_type)
                depth_raw = estimator.estimate(image_bgr)

            depth_colorized_raw = colorize_depth(depth_raw, colormap=colormap)
            if dynamic_color:
                depth_colorized_raw = colorize_depth_dynamic(depth_raw, colormap=colormap, adaptive=True)

            edges = None
            if show_edges:
                if adaptive_edges:
                    edges = enhance_edges(
                        image_bgr,
                        method=edge_method,
                        low_threshold=30,
                        high_threshold=90,
                        adaptive=True,
                        min_enhancement=min_enhancement,
                        texture_threshold=texture_threshold,
                    )
                else:
                    edges = enhance_edges(image_bgr, method=edge_method)

            depth_final = depth_raw.copy()
            if use_crf:
                with st.spinner("快速 CRF 边缘优化中..."):
                    crf_opt = load_crf_optimizer(
                        crf_iterations, bilateral_sxy, bilateral_srgb, bilateral_compat,
                        gaussian_sxy, gaussian_compat, num_depth_bins, crf_downscale,
                        use_fast_approx, texture_skip_threshold,
                    )
                    edge_map = None
                    if edges is not None:
                        edge_map = edges.astype(np.float32) / 255.0
                    depth_final = crf_opt.optimize_with_edge_guidance(image_bgr, depth_raw, edge_map)

            h_orig, w_orig = image_bgr.shape[:2]

            if use_sr:
                with st.spinner("深度超分辨率上采样中..."):
                    sr = DepthSuperResolution(method=sr_method, scale_factor=sr_scale)
                    guidance = image_bgr if sr_guided else None
                    depth_final = sr.upsample(depth_final, guidance, (h_orig, w_orig))

            if align_depth:
                with st.spinner("RGB-深度对齐中..."):
                    depth_final, _ = align_depth_to_rgb(depth_final, image_bgr)
                    if depth_final.shape[:2] != (h_orig, w_orig):
                        depth_final = cv2.resize(depth_final, (w_orig, h_orig), interpolation=cv2.INTER_LINEAR)

            if dynamic_color:
                if align_depth:
                    depth_colorized_final = create_aligned_colored_depth(
                        depth_final, image_bgr, colormap=colormap,
                        dynamic_mapping=True, alpha_blend=alpha_blend,
                    )
                else:
                    depth_colorized_final = colorize_depth_dynamic(depth_final, colormap=colormap, adaptive=True)
            else:
                if align_depth:
                    depth_colorized_final = create_aligned_colored_depth(
                        depth_final, image_bgr, colormap=colormap,
                        dynamic_mapping=False, alpha_blend=alpha_blend,
                    )
                else:
                    depth_colorized_final = colorize_depth(depth_final, colormap=colormap)

            if show_edges and edges is not None:
                depth_colorized_final = overlay_edges_on_depth(
                    depth_colorized_final, edges, alpha=edge_alpha, color=(0, 255, 0)
                )

            metrics = {}
            if show_metrics and gt_file is not None:
                try:
                    if gt_file.name.endswith(".npy"):
                        gt_depth = np.load(gt_file).astype(np.float32)
                    else:
                        gt_pil = Image.open(gt_file)
                        gt_depth = np.array(gt_pil).astype(np.float32)
                        if gt_depth.max() > 1:
                            gt_depth = gt_depth / 255.0

                    if gt_depth.ndim == 3:
                        gt_depth = gt_depth[:, :, 0]

                    gt_depth = cv2.resize(gt_depth, (w_orig, h_orig), interpolation=cv2.INTER_LINEAR)
                    metrics = compute_depth_metrics(depth_final, gt_depth)
                except Exception as e:
                    st.error(f"评估指标计算失败: {e}")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.subheader("原始图像")
                st.image(pil_image, use_container_width=True)

            with col2:
                st.subheader("MiDaS 原始深度")
                st.image(cv2_to_pil(depth_colorized_raw), use_container_width=True)

            with col3:
                label_parts = []
                if use_crf:
                    label_parts.append("FastCRF")
                if use_sr:
                    label_parts.append(f"SR×{sr_scale}")
                if align_depth:
                    label_parts.append("对齐")
                label = " + ".join(label_parts) if label_parts else "MiDaS 深度"
                st.subheader(label)
                st.image(cv2_to_pil(depth_colorized_final), use_container_width=True)

            if show_metrics and metrics:
                st.subheader("📊 实时评估指标")
                col_a, col_b, col_c = st.columns(3)

                with col_a:
                    st.metric("RMSE", f"{metrics.get('rmse', 0):.4f}", help="均方根误差，越小越好")
                    st.metric("MAE", f"{metrics.get('mae', 0):.4f}", help="平均绝对误差，越小越好")

                with col_b:
                    st.metric("δ < 1.25", f"{metrics.get('delta1', 0)*100:.1f}%", help="阈值内像素比例，越大越好")
                    st.metric("δ < 1.25²", f"{metrics.get('delta2', 0)*100:.1f}%", help="δ平方阈值内像素比例")

                with col_c:
                    st.metric("Abs Rel", f"{metrics.get('abs_rel', 0):.4f}", help="绝对相对误差")
                    st.metric("有效像素", f"{metrics.get('valid_pixels', 0)}", help="参与计算的有效像素数")

                with st.expander("📋 详细指标"):
                    st.code(format_metrics_display(metrics), language="text")

            st.subheader("📊 深度图分析")
            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("**原始深度统计**")
                st.write(f"  均值: {depth_raw.mean():.4f}")
                st.write(f"  标准差: {depth_raw.std():.4f}")
                st.write(f"  最小值: {depth_raw.min():.4f}")
                st.write(f"  最大值: {depth_raw.max():.4f}")

                grad_raw = compute_depth_gradients(depth_raw)
                st.write(f"  梯度均值: {grad_raw.mean():.4f}")

            with col_b:
                if use_crf:
                    st.markdown("**FastCRF 优化后统计**")
                    st.write(f"  均值: {depth_final.mean():.4f}")
                    st.write(f"  标准差: {depth_final.std():.4f}")
                    st.write(f"  最小值: {depth_final.min():.4f}")
                    st.write(f"  最大值: {depth_final.max():.4f}")

                    grad_final = compute_depth_gradients(depth_final)
                    st.write(f"  梯度均值: {grad_final.mean():.4f}")

                    diff = np.abs(depth_raw - depth_final)
                    st.write(f"  与原始差异均值: {diff.mean():.6f}")

            if show_edges and edges is not None:
                st.subheader("🔍 边缘检测结果")
                st.image(edges, caption=f"边缘检测 ({edge_method}{', 自适应' if adaptive_edges else ''})", use_container_width=True)

    with tab_video:
        st.subheader("视频流深度估计")

        source = st.radio("视频源", ["上传视频文件", "摄像头 (本地运行)"], index=0)

        if source == "上传视频文件":
            video_file = st.file_uploader("选择视频", type=["mp4", "avi", "mov", "mkv"], key="video_upload")

            if video_file is not None:
                with st.spinner("正在加载模型..."):
                    estimator = load_estimator(model_type)
                    crf_opt = None
                    if use_crf:
                        crf_opt = load_crf_optimizer(
                            crf_iterations, bilateral_sxy, bilateral_srgb, bilateral_compat,
                            gaussian_sxy, gaussian_compat, num_depth_bins, crf_downscale,
                            use_fast_approx, texture_skip_threshold,
                        )

                tfile = f"temp_video_{id(video_file)}.mp4"
                with open(tfile, "wb") as f:
                    f.write(video_file.read())

                cap = cv2.VideoCapture(tfile)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()

                frame_idx = st.slider("选择帧", 0, max(total_frames - 1, 0), 0)

                process_btn = st.button("▶️ 处理该帧")

                if process_btn:
                    cap = cv2.VideoCapture(tfile)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    cap.release()

                    if ret:
                        h, w = frame.shape[:2]
                        if w > target_width:
                            scale = target_width / w
                            frame = cv2.resize(frame, (target_width, int(h * scale)))

                        import time
                        start = time.time()

                        with st.spinner("深度估计中..."):
                            depth_map = estimator.estimate(frame)

                        mid = time.time()

                        if use_crf and crf_opt is not None:
                            with st.spinner("FastCRF 优化中..."):
                                if adaptive_edges:
                                    edge_map_edges = enhance_edges(
                                        frame,
                                        method=edge_method,
                                        low_threshold=30,
                                        high_threshold=90,
                                        adaptive=True,
                                        min_enhancement=min_enhancement,
                                        texture_threshold=texture_threshold,
                                    )
                                else:
                                    edge_map_edges = enhance_edges(frame, method=edge_method)
                                if edge_map_edges is not None:
                                    edge_map_f = edge_map_edges.astype(np.float32) / 255.0
                                else:
                                    edge_map_f = None
                                depth_map = crf_opt.optimize_with_edge_guidance(frame, depth_map, edge_map_f)

                        mid2 = time.time()

                        h_frame, w_frame = frame.shape[:2]
                        if use_sr:
                            with st.spinner("深度超分辨率中..."):
                                sr = DepthSuperResolution(method=sr_method, scale_factor=sr_scale)
                                guidance = frame if sr_guided else None
                                depth_map = sr.upsample(depth_map, guidance, (h_frame, w_frame))

                        if align_depth:
                            with st.spinner("RGB-深度对齐中..."):
                                depth_map, _ = align_depth_to_rgb(depth_map, frame)
                                if depth_map.shape[:2] != (h_frame, w_frame):
                                    depth_map = cv2.resize(depth_map, (w_frame, h_frame), interpolation=cv2.INTER_LINEAR)

                        end = time.time()
                        depth_time = mid - start
                        crf_time = mid2 - mid
                        sr_time = end - mid2
                        total_time = end - start
                        fps = 1.0 / max(total_time, 1e-6)

                        time_info = f"⏱️ 深度: {depth_time*1000:.0f}ms | CRF: {crf_time*1000:.0f}ms"
                        if use_sr:
                            time_info += f" | SR: {sr_time*1000:.0f}ms"
                        time_info += f" | 合计: {total_time*1000:.0f}ms | FPS: {fps:.1f}"
                        st.success(time_info)

                        if dynamic_color:
                            if align_depth:
                                depth_color = create_aligned_colored_depth(
                                    depth_map, frame, colormap=colormap,
                                    dynamic_mapping=True, alpha_blend=alpha_blend,
                                )
                            else:
                                depth_color = colorize_depth_dynamic(depth_map, colormap=colormap, adaptive=True)
                        else:
                            if align_depth:
                                depth_color = create_aligned_colored_depth(
                                    depth_map, frame, colormap=colormap,
                                    dynamic_mapping=False, alpha_blend=alpha_blend,
                                )
                            else:
                                depth_color = colorize_depth(depth_map, colormap=colormap)

                        if show_edges:
                            if adaptive_edges:
                                edges = enhance_edges(
                                    frame,
                                    method=edge_method,
                                    low_threshold=30,
                                    high_threshold=90,
                                    adaptive=True,
                                    min_enhancement=min_enhancement,
                                    texture_threshold=texture_threshold,
                                )
                            else:
                                edges = enhance_edges(frame, method=edge_method)
                            if edges is not None:
                                depth_color = overlay_edges_on_depth(depth_color, edges, alpha=edge_alpha)

                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("原始帧")
                            st.image(cv2_to_pil(frame), use_container_width=True)
                        with col2:
                            label = "深度图 (FastCRF 优化)" if use_crf else "深度图"
                            st.subheader(label)
                            st.image(cv2_to_pil(depth_color), use_container_width=True)

                        comparison = create_side_by_side(frame, depth_color)
                        st.image(cv2_to_pil(comparison), caption="并排对比", use_container_width=True)

        else:
            st.info("📹 摄像头实时处理请在本地运行以下命令：")
            st.code("streamlit run app.py\n\n# 或使用命令行版本:\npython video_processor.py --webcam --model DPT_Hybrid", language="bash")
            st.markdown("""
            **推荐配置 (15fps+)**：
            ```python
            from video_processor import VideoProcessor
            proc = VideoProcessor(
                model_type="DPT_Hybrid",
                use_crf=True,
                use_fast_approx=True,
                adaptive_edges=True,
                dynamic_colorization=True,
                target_width=640,
                crf_downscale=2,
                use_super_resolution=True,
                sr_method="bilinear_guided",
                sr_scale=2,
                align_depth_to_rgb_flag=True,
                alpha_blend=0.0,
            )
            proc.process_webcam(camera_id=0)
            ```
            **命令行启动 (带所有优化)**：
            ```bash
            python video_processor.py --webcam --sr --sr-method bilinear_guided --sr-scale 2 --evaluate
            ```
            """)

    with tab_about:
        st.subheader("🚀 v3.0 功能总览")

        st.markdown("""
        ### 1. 快速 CRF 近似优化 (目标 15fps)

        **核心优化策略**：
        - **下采样处理**：CRF 在 1/2 分辨率下进行，像素数降为 1/4，运算量降为 1/4
        - **深度 bins 减少**：从 64 降至 24，内存占用减少 62.5%
        - **引导滤波近似**：使用快速引导滤波（Guided Filter）替代完整 CRF 均值场推理
          - 复杂度从 O(N) 降为近似 O(1)（盒式滤波）
          - 保持边缘感知平滑特性
        - **低纹理区域跳过**：Laplacian 方差 < 阈值的区域直接跳过 CRF
        - **迭代次数减少**：从 5 降至 3

        **预计性能提升**：
        | 模式 | 640×480 估计 FPS | 说明 |
        |------|----------------|------|
        | 原始 CRF | ~3-5 | 完整均值场推理 |
        | FastCRF (近似) | **~15-20** | 下采样 + 引导滤波 |
        | FastCRF (低纹理跳过) | **~20-25** | 部分帧跳过 |

        ---

        ### 2. 自适应边缘增强

        **算法原理**：
        1. **纹理密度估计**：用滑动窗口计算局部方差（标准差）
        ```
        texture_map = local_std(gray_image, window=15)
        ```
        2. **自适应阈值**：
           - 高纹理区 (texture > 0.25)：降低 Canny 阈值 × 0.3，避免过度检测纹理边缘
           - 低纹理区：正常阈值 × 1.0，保留真实物体边缘
        3. **分类处理**：将图像分为 4 个纹理等级，分别应用不同增强强度

        **效果**：
        - ✅ 草地、地毯等纹理区的虚假边缘被抑制
        - ✅ 物体轮廓边缘被精准检测
        - ✅ 减少深度图在纹理区的错误锐化

        ---

        ### 3. 动态深度彩色化

        **核心改进**：
        - **百分位截断**：去掉深度分布的 1% ~ 99% 极端值，避免离群点压缩动态范围
        - **直方图均衡化**：基于累积分布函数 (CDF) 重新映射深度值
        - **场景自适应**：
          - 若远景和近景比例均衡（各 > 30%）：压缩两端 5%，增强中段对比度
          - 自动检测深度分布，调整拉伸范围

        **效果对比**：
        - 线性映射：深度集中在 0.4-0.6 的场景 → 颜色区分度低
        - 动态映射：同样场景 → 颜色分布覆盖整个色阶，细节清晰

        ---

        ### 4. 🔬 深度超分辨率

        **上采样方法**：
        | 方法 | 速度 | 质量 | 说明 |
        |------|------|------|------|
        | `nearest` | ⭐⭐⭐⭐⭐ | ⭐ | 最近邻插值，最快但锯齿严重 |
        | `bilinear` | ⭐⭐⭐⭐ | ⭐⭐ | 双线性插值，边缘模糊 |
        | `bicubic` | ⭐⭐⭐ | ⭐⭐⭐ | 双三次插值，细节较好 |
        | **`bilinear_guided`** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 双线性 + 引导滤波，**推荐**，保持边缘 |
        | `laplacian_pyramid` | ⭐⭐ | ⭐⭐⭐⭐ | 拉普拉斯金字塔，多尺度融合 |
        | `edge_preserving` | ⭐⭐⭐ | ⭐⭐⭐⭐ | 边缘保持上采样，纹理区弱增强 |

        **引导滤波原理**：
        - 以 RGB 图像作为引导图，在平滑深度同时保持物体边缘
        - 使用盒式滤波实现 O(N) 复杂度，速度快
        - 适合作为轻量级深度超分辨率方案

        ---

        ### 5. 🎯 RGB-深度对齐

        **核心功能**：
        - 支持内参矩阵投影对齐（当提供 intrinsics 时）
        - 默认使用像素级尺寸对齐，保证与 RGB 同分辨率
        - 可选 RGB 混合叠加（alpha blend），直观验证对齐效果
        - 对齐后生成彩色深度图，空间坐标与 RGB 像素一一对应

        **使用场景**：
        - ✅ AR 虚拟物体渲染，需要精确深度与 RGB 对应
        - ✅ 3D 重建，点云与图像配准
        - ✅ 语义分割 + 深度融合

        ---

        ### 6. 📊 深度评估指标

        **支持的指标**：

        | 指标 | 全称 | 说明 | 理想值 |
        |------|------|------|--------|
        | **RMSE** | Root Mean Squared Error | 均方根误差，衡量整体精度 | ↓ 越小越好 |
        | **MAE** | Mean Absolute Error | 平均绝对误差 | ↓ 越小越好 |
        | **Abs Rel** | Absolute Relative | 绝对相对误差 | ↓ 越小越好 |
        | **δ < 1.25** | Threshold Accuracy | 最大误差比 < 1.25 的像素比例 | ↑ 越大越好 |
        | **δ < 1.25²** | Threshold Accuracy | 最大误差比 < 1.5625 的像素比例 | ↑ 越大越好 |
        | **δ < 1.25³** | Threshold Accuracy | 最大误差比 < 1.9531 的像素比例 | ↑ 越大越好 |

        **δ 准确率公式**：
        ```
        max(d_pred / d_gt, d_gt / d_pred) < threshold
        ```

        **实时显示**：
        - 单帧指标即时显示
        - 支持帧间累积平均（MetricsAccumulator）
        - 摄像头模式下 OSD 叠加显示
        """)


if __name__ == "__main__":
    main()
