import streamlit as st
import cv2
import numpy as np
from PIL import Image
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import time

from underwater_enhancer import UnderwaterImageEnhancer, WhiteBalancer, DarkChannelPrior, ContrastEnhancer, AdaptiveParameterEstimator
from video_enhancer import VideoProcessor, FrameComparator
from quality_evaluator import NoReferenceEvaluator, FullReferenceEvaluator, QualityMetrics

st.set_page_config(
    page_title="水下图像增强系统",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🌊 水下图像增强系统")
st.markdown("---")


def load_image(image_file):
    image = Image.open(image_file)
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def pil_to_opencv(pil_img):
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def opencv_to_pil(cv_img):
    return Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))


def plot_histograms(original, enhanced):
    fig, axes = plt.subplots(2, 3, figsize=(12, 6))
    
    for idx, (img, title_prefix) in enumerate([(original, "Original"), (enhanced, "Enhanced")]):
        colors = ('b', 'g', 'r')
        for i, color in enumerate(colors):
            hist = cv2.calcHist([img], [i], None, [256], [0, 256])
            axes[idx, i].plot(hist, color=color)
            axes[idx, i].set_title(f'{title_prefix} - {color.upper()}')
            axes[idx, i].set_xlim([0, 256])
    
    plt.tight_layout()
    return fig


def create_radar_chart(metrics_orig, metrics_enh):
    categories = ['Contrast', 'Sharpness', 'Color', 'Brightness', 'Edge Density']
    
    values_orig = [
        metrics_orig['contrast'],
        metrics_orig['sharpness'],
        metrics_orig['color_fidelity'],
        metrics_orig['brightness'],
        min(metrics_orig['edge_density'] / 10, 1.0)
    ]
    
    values_enh = [
        metrics_enh['contrast'],
        metrics_enh['sharpness'],
        metrics_enh['color_fidelity'],
        metrics_enh['brightness'],
        min(metrics_enh['edge_density'] / 10, 1.0)
    ]
    
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, polar=True)
    
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    values_orig += values_orig[:1]
    values_enh += values_enh[:1]
    angles += angles[:1]
    
    ax.plot(angles, values_orig, 'o-', linewidth=2, label='Original', color='#ff7f0e')
    ax.fill(angles, values_orig, alpha=0.25, color='#ff7f0e')
    
    ax.plot(angles, values_enh, 'o-', linewidth=2, label='Enhanced', color='#1f77b4')
    ax.fill(angles, values_enh, alpha=0.25, color='#1f77b4')
    
    ax.set_thetagrids(np.degrees(angles[:-1]), categories)
    ax.set_ylim(0, 1)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    ax.set_title('Image Quality Metrics Comparison', pad=20)
    
    return fig


with st.sidebar:
    st.header("⚙️ 参数设置")
    
    mode = st.selectbox(
        "工作模式",
        ["图像增强", "视频增强", "实时摄像头", "质量评估"],
        index=0
    )
    
    st.subheader("增强参数")
    use_adaptive = st.checkbox("自适应参数", value=True, help="根据图像自动调节参数")
    
    if not use_adaptive:
        red_boost = st.slider("红色通道增强", 0.8, 2.0, 1.3, 0.1)
        blue_scale = st.slider("蓝色通道抑制", 0.7, 1.2, 0.9, 0.1)
        omega = st.slider("去雾强度 (omega)", 0.7, 1.0, 0.95, 0.05)
        gamma = st.slider("Gamma校正", 0.5, 2.0, 1.0, 0.1)
        clahe_clip = st.slider("CLAHE对比度限制", 1.0, 4.0, 2.0, 0.5)
        sharpen_strength = st.slider("锐化强度", 0.0, 2.0, 0.5, 0.1)
        patch_size = st.slider("暗通道窗口大小", 5, 31, 15, 2)
    else:
        st.info("参数将根据输入图像自动调节")
    
    st.subheader("显示选项")
    show_steps = st.checkbox("显示处理步骤", value=False)
    show_histogram = st.checkbox("显示直方图", value=True)
    show_metrics = st.checkbox("显示质量评估", value=True)


if mode == "图像增强":
    st.header("📷 图像增强")
    
    uploaded_file = st.file_uploader("上传水下图像", type=['jpg', 'jpeg', 'png', 'bmp'])
    
    if uploaded_file is not None:
        original_img = load_image(uploaded_file)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("原始图像")
            st.image(opencv_to_pil(original_img), use_column_width=True)
        
        with st.spinner("正在增强图像..."):
            if use_adaptive:
                enhancer = UnderwaterImageEnhancer(use_adaptive=True)
            else:
                enhancer = UnderwaterImageEnhancer(
                    use_adaptive=False,
                    red_boost=red_boost,
                    blue_scale=blue_scale,
                    omega=omega,
                    gamma=gamma,
                    clahe_clip=clahe_clip,
                    sharpen_strength=sharpen_strength,
                    patch_size=patch_size
                )
            
            start_time = time.time()
            enhanced_img, info = enhancer.enhance(original_img)
            process_time = time.time() - start_time
        
        with col2:
            st.subheader("增强后图像")
            st.image(opencv_to_pil(enhanced_img), use_column_width=True)
            
            buf = io.BytesIO()
            pil_enhanced = opencv_to_pil(enhanced_img)
            pil_enhanced.save(buf, format="PNG")
            st.download_button(
                label="下载增强图像",
                data=buf.getvalue(),
                file_name="enhanced_image.png",
                mime="image/png"
            )
        
        st.success(f"处理完成！耗时: {process_time:.3f} 秒")
        
        if show_steps and info.get('adaptive_params'):
            with st.expander("📊 自适应参数详情"):
                params = info['adaptive_params']
                st.write(f"- 🌫️ 雾化程度: {params['haze_level']:.3f}")
                st.write(f"- ☀️ 亮度水平: {params['brightness']:.3f}")
                st.write(f"- 🎨 对比度: {params['contrast']:.3f}")
                st.write(f"- 🔴 红色增强: {params['red_boost']:.2f}")
                st.write(f"- 🔵 蓝色抑制: {params['blue_scale']:.2f}")
                st.write(f"- ⚡ Gamma值: {params['gamma']:.2f}")
                st.write(f"- 🌫️ 去雾强度: {params['omega']:.2f}")
        
        if show_histogram:
            st.subheader("📈 直方图对比")
            fig = plot_histograms(original_img, enhanced_img)
            st.pyplot(fig)
        
        if show_metrics:
            st.subheader("📊 质量评估")
            
            metrics = NoReferenceEvaluator.compare(original_img, enhanced_img)
            
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric("总体质量", 
                         f"{metrics['enhanced']['overall_quality']:.3f}", 
                         f"{metrics['improvement']['overall_quality']:+.3f}")
            with col_m2:
                st.metric("对比度", 
                         f"{metrics['enhanced']['contrast']:.3f}", 
                         f"{metrics['improvement']['contrast']:+.3f}")
            with col_m3:
                st.metric("锐度", 
                         f"{metrics['enhanced']['sharpness']:.3f}", 
                         f"{metrics['improvement']['sharpness']:+.3f}")
            with col_m4:
                st.metric("色彩保真度", 
                         f"{metrics['enhanced']['color_fidelity']:.3f}", 
                         f"{metrics['improvement']['color_fidelity']:+.3f}")
            
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                radar_fig = create_radar_chart(metrics['original'], metrics['enhanced'])
                st.pyplot(radar_fig)
            with col_r2:
                st.subheader("详细指标")
                st.json({
                    '原始图像': {k: round(v, 4) for k, v in metrics['original'].items()},
                    '增强图像': {k: round(v, 4) for k, v in metrics['enhanced'].items()},
                    '提升幅度': {k: round(v, 4) for k, v in metrics['improvement'].items()}
                })


elif mode == "视频增强":
    st.header("🎬 视频增强")
    
    uploaded_video = st.file_uploader("上传视频文件", type=['mp4', 'avi', 'mov', 'mkv'])
    
    if uploaded_video is not None:
        tfile = io.BytesIO(uploaded_video.read())
        
        temp_input = "temp_input.mp4"
        temp_output = "temp_output.mp4"
        
        with open(temp_input, "wb") as f:
            f.write(tfile.getvalue())
        
        st.video(temp_input)
        
        if st.button("开始增强视频"):
            with st.spinner("正在处理视频..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def progress_callback(progress, current, total):
                    progress_bar.progress(progress)
                    status_text.text(f"处理中: {current}/{total} 帧 ({progress*100:.1f}%)")
                
                processor = VideoProcessor(use_adaptive=use_adaptive)
                result = processor.process_video_file(
                    temp_input, 
                    temp_output,
                    progress_callback=progress_callback
                )
                
                st.success(f"视频处理完成！耗时: {result['total_time']:.2f} 秒")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("处理帧数", result['total_frames'])
                col2.metric("处理帧率", f"{result['processing_fps']:.1f} FPS")
                col3.metric("视频分辨率", f"{result['resolution'][0]}x{result['resolution'][1]}")
                
                st.subheader("增强后视频")
                st.video(temp_output)


elif mode == "实时摄像头":
    st.header("📹 实时摄像头增强")
    
    st.info("点击下方按钮开始实时摄像头增强")
    st.warning("注意：实时模式下，请确保摄像头可用。按 'q' 键退出，按 's' 键保存截图。")
    
    if st.button("启动摄像头"):
        st.info("摄像头正在启动... 请查看弹出窗口")
        
        from video_enhancer import RealTimeEnhancer
        rt_enhancer = RealTimeEnhancer(use_adaptive=use_adaptive, downscale_factor=0.5)
        rt_enhancer.run_camera()
        
        st.success("摄像头会话已结束")


elif mode == "质量评估":
    st.header("📊 质量评估工具")
    
    st.subheader("无参考质量评估")
    
    col1, col2 = st.columns(2)
    
    with col1:
        file1 = st.file_uploader("上传图像 1", type=['jpg', 'jpeg', 'png'], key="img1")
    
    with col2:
        file2 = st.file_uploader("上传图像 2 (可选)", type=['jpg', 'jpeg', 'png'], key="img2")
    
    if file1 is not None:
        img1 = load_image(file1)
        
        metrics1 = NoReferenceEvaluator.evaluate(img1)
        
        st.subheader("图像 1 质量指标")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("总体质量", f"{metrics1['overall_quality']:.3f}")
        c2.metric("对比度", f"{metrics1['contrast']:.3f}")
        c3.metric("锐度", f"{metrics1['sharpness']:.3f}")
        c4.metric("色彩", f"{metrics1['color_fidelity']:.3f}")
        
        st.image(opencv_to_pil(img1), caption="图像 1", use_column_width=True)
        
        if file2 is not None:
            img2 = load_image(file2)
            metrics2 = NoReferenceEvaluator.evaluate(img2)
            
            st.subheader("图像 2 质量指标")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("总体质量", f"{metrics2['overall_quality']:.3f}", 
                     f"{metrics2['overall_quality'] - metrics1['overall_quality']:+.3f}")
            c2.metric("对比度", f"{metrics2['contrast']:.3f}",
                     f"{metrics2['contrast'] - metrics1['contrast']:+.3f}")
            c3.metric("锐度", f"{metrics2['sharpness']:.3f}",
                     f"{metrics2['sharpness'] - metrics1['sharpness']:+.3f}")
            c4.metric("色彩", f"{metrics2['color_fidelity']:.3f}",
                     f"{metrics2['color_fidelity'] - metrics1['color_fidelity']:+.3f}")
            
            st.image(opencv_to_pil(img2), caption="图像 2", use_column_width=True)
            
            if st.button("计算全参考指标 (PSNR/SSIM)"):
                psnr = QualityMetrics.psnr(img1, img2)
                ssim = QualityMetrics.ssim(img1, img2)
                
                col_p, col_s = st.columns(2)
                col_p.metric("PSNR (峰值信噪比)", f"{psnr:.2f} dB")
                col_s.metric("SSIM (结构相似性)", f"{ssim:.4f}")


st.markdown("---")
st.subheader("📖 算法说明")

with st.expander("查看算法详情"):
    st.markdown("""
    **水下图像增强算法流程：**
    
    1. **色彩校正** - 针对水下图像的蓝绿色偏进行红通道增强和蓝通道抑制
    2. **灰度世界白平衡** - 自动调整各通道均值实现白平衡
    3. **暗通道先验去雾** - 基于暗通道先验理论去除水下雾化效应
    4. **CLAHE对比度增强** - 限制对比度自适应直方图均衡化
    5. **Gamma校正** - 调整图像亮度
    6. **图像锐化** - 增强图像细节边缘
    
    **参数自适应功能：**
    - 自动检测雾化程度、亮度、对比度
    - 根据图像特性动态调整增强参数
    
    **质量评估指标：**
    - 无参考：对比度、锐度、色彩保真度、边缘密度
    - 全参考：PSNR、SSIM、MSE
    """)
