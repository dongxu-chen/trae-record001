import os
import sys
import tempfile
import numpy as np
import cv2
import streamlit as st
from pathlib import Path
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from super_resolution_pipeline import SuperResolutionPipeline, get_available_models, get_available_scales, compare_with_bicubic
from processors import FFmpegProcessor
from utils.common import calc_psnr, calc_ssim, get_device
from config import PROCESS_CONFIG


st.set_page_config(
    page_title="视频超分辨率重建系统",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    .css-18e3th9 {
        padding-top: 2rem;
    }
    h1, h2, h3 {
        color: #f0f2f6;
    }
    .stButton>button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
    }
    .stProgress > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
    }
    .info-box {
        background: rgba(102, 126, 234, 0.1);
        border-left: 4px solid #667eea;
        padding: 1rem;
        border-radius: 8px;
        color: #c9d1d9;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def load_pipeline(model_name, scale, enable_denoise, enable_temporal, enable_bitrate_adapt, 
                   enable_face_enhance=False, enable_subtitle_enhance=False, enable_realtime=False,
                   weight_path=None):
    return SuperResolutionPipeline(
        model_name=model_name,
        scale=scale,
        enable_denoise=enable_denoise,
        enable_temporal=enable_temporal,
        enable_bitrate_adapt=enable_bitrate_adapt,
        enable_face_enhance=enable_face_enhance,
        enable_subtitle_enhance=enable_subtitle_enhance,
        enable_realtime=enable_realtime,
        weight_path=weight_path if weight_path else None,
    )


def save_uploaded_file(uploaded_file):
    temp_dir = tempfile.mkdtemp(prefix='sr_upload_')
    file_path = os.path.join(temp_dir, uploaded_file.name)
    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    return file_path, temp_dir


def get_video_preview(video_path, num_frames=3):
    cap = cv2.VideoCapture(video_path)
    frames = []
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    if total_frames > 0:
        step = max(1, total_frames // num_frames)
        for i in range(num_frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES, min(i * step, total_frames - 1))
            ret, frame = cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame)
    
    cap.release()
    return frames, fps, total_frames


def main():
    with st.sidebar:
        st.title("⚙️ 配置选项")
        
        st.subheader("模型设置")
        model_name = st.selectbox("选择模型", get_available_models(), index=0, format_func=lambda x: x.upper())
        scale = st.selectbox("超分倍数", get_available_scales(), index=2, format_func=lambda x: f"{x}x")
        
        weight_file = st.file_uploader("加载预训练权重 (可选)", type=['pth', 'pt', 'pkl'])
        weight_path = None
        if weight_file:
            weight_path, _ = save_uploaded_file(weight_file)
        
        st.subheader("高级选项")
        enable_denoise = st.checkbox("多帧融合降噪", value=True)
        enable_temporal = st.checkbox("时序一致性", value=True)
        enable_bitrate_adapt = st.checkbox("码率自适应", value=True)
        enable_face_enhance = st.checkbox("人脸区域增强", value=False, help="人脸区域使用更高超分倍数")
        enable_subtitle_enhance = st.checkbox("字幕清晰化", value=False, help="字幕区域锐化处理")
        enable_realtime = st.checkbox("实时超分优化", value=False, help="GPU加速达30fps+")
        half_precision = st.checkbox("半精度推理 (FP16)", value=False)
        
        if enable_denoise:
            fusion_method = st.selectbox(
                "融合方法",
                ['weighted_average', 'gaussian', 'bilateral', 'adaptive'],
                index=0,
                format_func=lambda x: {
                    'weighted_average': '加权平均',
                    'gaussian': '高斯融合',
                    'bilateral': '双边滤波',
                    'adaptive': '自适应融合'
                }[x]
            )
        
        if enable_temporal:
            temporal_method = st.selectbox(
                "时序方法",
                ['optical_flow', 'simple_average', 'rolling_guidance', 'deep_flow'],
                index=0,
                format_func=lambda x: {
                    'optical_flow': '光流法',
                    'simple_average': '简单平均',
                    'rolling_guidance': '滚动引导',
                    'deep_flow': '深度光流'
                }[x]
            )
        
        target_quality = st.selectbox(
            "输出质量",
            ['low', 'medium', 'high', 'ultra'],
            index=2,
            format_func=lambda x: {
                'low': '低质量 (快速)',
                'medium': '中等质量',
                'high': '高质量',
                'ultra': '极高质量 (慢速)'
            }[x]
        )
        
        st.divider()
        st.info(f"当前设备: {get_device()}")
        ffmpeg = FFmpegProcessor()
        st.info(f"FFmpeg: {'✓ 可用' if ffmpeg.check_ffmpeg() else '✗ 未找到'}")

    st.title("🎬 视频超分辨率重建系统")
    st.markdown("---")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📹 视频超分", "🖼️ 图片超分", "⚡ 实时超分预览", "📊 关于"])
    
    with tab1:
        st.header("视频超分辨率处理")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_file = st.file_uploader("上传视频文件", type=['mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'])
            
            if uploaded_file is not None:
                video_path, temp_dir = save_uploaded_file(uploaded_file)
                
                video_info = ffmpeg.probe_video(video_path)
                if video_info:
                    st.success(f"视频加载成功!")
                    
                    preview_frames, fps, total_frames = get_video_preview(video_path, num_frames=5)
                    
                    st.subheader("视频预览")
                    preview_cols = st.columns(len(preview_frames))
                    for i, frame in enumerate(preview_frames):
                        with preview_cols[i]:
                            st.image(frame, caption=f"帧 {i*max(1, total_frames//5)+1}", use_column_width=True)
                    
                    col_info1, col_info2, col_info3, col_info4 = st.columns(4)
                    with col_info1:
                        st.markdown(f'<div class="metric-card"><h3>📐 分辨率</h3><h2>{video_info["width"]}×{video_info["height"]}</h2></div>', unsafe_allow_html=True)
                    with col_info2:
                        st.markdown(f'<div class="metric-card"><h3>🎞️ 帧率</h3><h2>{video_info["fps"]:.1f} FPS</h2></div>', unsafe_allow_html=True)
                    with col_info3:
                        st.markdown(f'<div class="metric-card"><h3>⏱️ 时长</h3><h2>{video_info["duration"]:.1f}s</h2></div>', unsafe_allow_html=True)
                    with col_info4:
                        st.markdown(f'<div class="metric-card"><h3>📈 目标分辨率</h3><h2>{video_info["width"]*scale}×{video_info["height"]*scale}</h2></div>', unsafe_allow_html=True)
                    
                    st.divider()
                    
                    col_start, col_stop = st.columns([1, 1])
                    with col_start:
                        start_time = st.number_input("开始时间 (秒)", min_value=0.0, max_value=video_info["duration"], value=0.0, step=0.5)
                    with col_stop:
                        duration = st.number_input("处理时长 (秒, 0=全部)", min_value=0.0, max_value=video_info["duration"], value=0.0, step=0.5)
                    
                    target_fps = st.number_input("目标帧率 (0=原始)", min_value=0, max_value=60, value=0)
                    
                    process_btn = st.button("🚀 开始超分处理", type="primary", use_container_width=True)
                    
                    if process_btn:
                        try:
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            time_metric = st.empty()
                            
                            pipeline = load_pipeline(
                                model_name=model_name,
                                scale=scale,
                                enable_denoise=enable_denoise,
                                enable_temporal=enable_temporal,
                                enable_bitrate_adapt=enable_bitrate_adapt,
                                enable_face_enhance=enable_face_enhance,
                                enable_subtitle_enhance=enable_subtitle_enhance,
                                enable_realtime=enable_realtime,
                                weight_path=weight_path,
                            )
                            
                            def progress_callback(current, total):
                                progress = current / total
                                progress_bar.progress(progress)
                                status_text.info(f"处理进度: {current}/{total} 帧 ({progress*100:.1f}%)")
                                elapsed = time.time() - start_time
                                if current > 0:
                                    eta = (total - current) * (elapsed / current)
                                    time_metric.info(f"已用时: {elapsed:.1f}s | 预计剩余: {eta:.1f}s")
                            
                            start_time = time.time()
                            
                            with st.spinner("正在处理视频..."):
                                result = pipeline.process_video(
                                    input_path=video_path,
                                    start_time=start_time if start_time > 0 else None,
                                    duration=duration if duration > 0 else None,
                                    target_fps=target_fps if target_fps > 0 else None,
                                    target_quality=target_quality,
                                    progress_callback=progress_callback,
                                )
                            
                            progress_bar.progress(1.0)
                            status_text.success("✅ 处理完成!")
                            time_metric.empty()
                            
                            st.divider()
                            st.subheader("📊 处理结果")
                            
                            col_res1, col_res2, col_res3 = st.columns(3)
                            with col_res1:
                                st.markdown(f'<div class="metric-card"><h3>✅ 处理帧数</h3><h2>{result["num_frames"]}</h2></div>', unsafe_allow_html=True)
                            with col_res2:
                                st.markdown(f'<div class="metric-card"><h3>📐 输出分辨率</h3><h2>{result["resolution"][0]}×{result["resolution"][1]}</h2></div>', unsafe_allow_html=True)
                            with col_res3:
                                st.markdown(f'<div class="metric-card"><h3>🎞️ 输出帧率</h3><h2>{result["fps"]:.1f} FPS</h2></div>', unsafe_allow_html=True)
                            
                            if result.get('complexity_analysis'):
                                ca = result['complexity_analysis']
                                st.subheader("🎯 视频复杂度分析")
                                col_c1, col_c2, col_c3, col_c4 = st.columns(4)
                                with col_c1:
                                    complexity_label = {
                                        'very_low': '极低',
                                        'low': '低',
                                        'medium': '中等',
                                        'high': '高',
                                        'very_high': '极高'
                                    }.get(ca['overall'], ca['overall'])
                                    st.markdown(f'<div class="metric-card"><h3>综合等级</h3><h2>{complexity_label}</h2></div>', unsafe_allow_html=True)
                                with col_c2:
                                    st.markdown(f'<div class="metric-card"><h3>纹理复杂度</h3><h2>{ca["texture_score"]:.2f}</h2></div>', unsafe_allow_html=True)
                                with col_c3:
                                    st.markdown(f'<div class="metric-card"><h3>运动复杂度</h3><h2>{ca["motion_score"]:.2f}</h2></div>', unsafe_allow_html=True)
                                with col_c4:
                                    st.markdown(f'<div class="metric-card"><h3>编码CRF</h3><h2>{result["encode_params"]["crf"]}</h2></div>', unsafe_allow_html=True)
                                st.info(f"💡 基于纹理和运动复杂度，系统自动调整了编码参数以保持画质均匀。高纹理/高运动区域分配了更多码率。")
                            
                            if result.get('face_enhance_enabled') or result.get('subtitle_enhance_enabled'):
                                st.subheader("🎯 ROI增强功能")
                                roi_cols = []
                                if result.get('face_enhance_enabled'):
                                    roi_cols.append('👤 人脸增强')
                                if result.get('subtitle_enhance_enabled'):
                                    roi_cols.append('📝 字幕增强')
                                st.success("已启用: " + " | ".join(roi_cols))
                            
                            if result.get('realtime_stats'):
                                rs = result['realtime_stats']
                                st.subheader("⚡ 实时超分性能")
                                rt_col1, rt_col2, rt_col3, rt_col4 = st.columns(4)
                                with rt_col1:
                                    st.markdown(f'<div class="metric-card"><h3>实际帧率</h3><h2>{rs["fps"]:.1f} FPS</h2></div>', unsafe_allow_html=True)
                                with rt_col2:
                                    st.markdown(f'<div class="metric-card"><h3>目标帧率</h3><h2>{rs["target_fps"]} FPS</h2></div>', unsafe_allow_html=True)
                                with rt_col3:
                                    st.markdown(f'<div class="metric-card"><h3>缓存命中率</h3><h2>{rs["cache_hit_rate"]*100:.1f}%</h2></div>', unsafe_allow_html=True)
                                with rt_col4:
                                    st.markdown(f'<div class="metric-card"><h3>处理帧数</h3><h2>{rs["processed_frames"]}</h2></div>', unsafe_allow_html=True)
                                
                                if 'pipeline_times' in rs and len(rs['pipeline_times']) > 0:
                                    with st.expander("📊 详细性能分析"):
                                        for stage, data in rs['pipeline_times'].items():
                                            stage_name = {
                                                'preprocess': '预处理',
                                                'transfer': '数据传输',
                                                'inference': '模型推理',
                                                'postprocess': '后处理'
                                            }.get(stage, stage)
                                            st.progress(data['percentage'] / 100, text=f"{stage_name}: {data['avg_ms']:.2f}ms ({data['percentage']:.1f}%)")
                            
                            if os.path.exists(result['output_path']):
                                with open(result['output_path'], 'rb') as f:
                                    video_bytes = f.read()
                                
                                st.video(video_bytes)
                                
                                st.download_button(
                                    "📥 下载处理后的视频",
                                    video_bytes,
                                    file_name=os.path.basename(result['output_path']),
                                    mime='video/mp4',
                                    use_container_width=True
                                )
                                
                                output_size = os.path.getsize(result['output_path']) / (1024 * 1024)
                                original_size = os.path.getsize(video_path) / (1024 * 1024)
                                st.info(f"输出文件大小: {output_size:.2f} MB (原始: {original_size:.2f} MB)")
                                
                                cap_sr = cv2.VideoCapture(result['output_path'])
                                cap_lr = cv2.VideoCapture(video_path)
                                
                                for _ in range(5):
                                    cap_sr.read()
                                    cap_lr.read()
                                
                                ret_sr, frame_sr = cap_sr.read()
                                ret_lr, frame_lr = cap_lr.read()
                                
                                if ret_sr and ret_lr:
                                    frame_sr = cv2.cvtColor(frame_sr, cv2.COLOR_BGR2RGB)
                                    frame_lr = cv2.cvtColor(frame_lr, cv2.COLOR_BGR2RGB)
                                    
                                    frame_lr_up = cv2.resize(frame_lr, (frame_sr.shape[1], frame_sr.shape[0]), interpolation=cv2.INTER_CUBIC)
                                    
                                    psnr_value = calc_psnr(frame_sr, frame_lr_up)
                                    ssim_value = calc_ssim(frame_sr, frame_lr_up)
                                    
                                    st.divider()
                                    st.subheader("🔍 质量对比")
                                    
                                    col_comp1, col_comp2 = st.columns(2)
                                    with col_comp1:
                                        st.image(frame_lr_up, caption=f"原图 (双三次上采样) | PSNR: {psnr_value:.2f}dB", use_column_width=True)
                                    with col_comp2:
                                        st.image(frame_sr, caption=f"超分结果 | {model_name.upper()} x{scale} | SSIM: {ssim_value:.4f}", use_column_width=True)
                                
                                cap_sr.release()
                                cap_lr.release()
                                
                        except Exception as e:
                            st.error(f"处理出错: {str(e)}")
                            st.exception(e)
                        finally:
                            import shutil
                            shutil.rmtree(temp_dir, ignore_errors=True)
                else:
                    st.error("无法读取视频文件，请检查文件格式")
    
    with tab2:
        st.header("图片超分辨率处理")
        
        uploaded_image = st.file_uploader("上传图片文件", type=['png', 'jpg', 'jpeg', 'bmp', 'tiff'])
        
        if uploaded_image is not None:
            image_path, temp_dir = save_uploaded_file(uploaded_image)
            
            col_orig, col_proc = st.columns(2)
            
            with col_orig:
                st.subheader("原始图片")
                lr_img = cv2.imread(image_path)
                lr_img_rgb = cv2.cvtColor(lr_img, cv2.COLOR_BGR2RGB)
                st.image(lr_img_rgb, caption=f"分辨率: {lr_img.shape[1]}×{lr_img.shape[0]}", use_column_width=True)
            
            process_img_btn = st.button("🔍 开始图片超分", type="primary", use_container_width=True)
            
            if process_img_btn:
                try:
                    with st.spinner("正在处理图片..."):
                        pipeline = load_pipeline(
                            model_name=model_name,
                            scale=scale,
                            enable_denoise=enable_denoise,
                            enable_temporal=False,
                            enable_bitrate_adapt=False,
                            enable_face_enhance=enable_face_enhance,
                            enable_subtitle_enhance=enable_subtitle_enhance,
                            enable_realtime=False,
                            weight_path=weight_path,
                        )
                        
                        result = pipeline.process_image(image_path)
                        
                        with col_proc:
                            st.subheader("超分结果")
                            sr_img = cv2.imread(result['output_path'])
                            sr_img_rgb = cv2.cvtColor(sr_img, cv2.COLOR_BGR2RGB)
                            st.image(sr_img_rgb, caption=f"分辨率: {result['resolution'][0]}×{result['resolution'][1]}", use_column_width=True)
                        
                        bicubic_img = compare_with_bicubic(lr_img.astype(np.float32) / 255.0, scale)
                        bicubic_img = (bicubic_img * 255).astype(np.uint8)
                        
                        psnr_value = calc_psnr(sr_img, bicubic_img)
                        ssim_value = calc_ssim(sr_img, bicubic_img)
                        
                        st.info(f"PSNR (vs 双三次): {psnr_value:.2f} dB | SSIM: {ssim_value:.4f}")
                        
                        with open(result['output_path'], 'rb') as f:
                            img_bytes = f.read()
                        
                        st.download_button(
                            "📥 下载超分图片",
                            img_bytes,
                            file_name=os.path.basename(result['output_path']),
                            mime='image/png',
                            use_container_width=True
                        )
                        
                except Exception as e:
                    st.error(f"处理出错: {str(e)}")
                    st.exception(e)
                finally:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
    
    with tab3:
        st.header("⚡ 实时超分预览")
        st.info("使用摄像头或视频文件进行实时超分辨率预览。需要启用\"实时超分优化\"选项。")
        
        rt_mode = st.radio("选择输入源", ["摄像头", "视频文件"], horizontal=True)
        
        if rt_mode == "摄像头":
            camera_id = st.number_input("摄像头ID", min_value=0, max_value=10, value=0)
            start_rt = st.button("🎥 开启实时超分", type="primary", use_container_width=True)
            
            if start_rt:
                if not enable_realtime:
                    st.warning("请先在左侧勾选\"实时超分优化\"选项")
                else:
                    st.info("正在初始化摄像头...")
                    st.info("提示：在浏览器中运行摄像头超分需要在服务器端处理，此处展示性能指标。")
                    
                    pipeline = load_pipeline(
                        model_name=model_name,
                        scale=scale,
                        enable_denoise=enable_denoise,
                        enable_temporal=enable_temporal,
                        enable_bitrate_adapt=False,
                        enable_face_enhance=enable_face_enhance,
                        enable_subtitle_enhance=enable_subtitle_enhance,
                        enable_realtime=True,
                        weight_path=weight_path,
                    )
                    
                    from processors import get_gpu_info
                    gpu_info = get_gpu_info()
                    
                    st.subheader("📊 实时性能监控")
                    col_rt1, col_rt2, col_rt3 = st.columns(3)
                    with col_rt1:
                        st.metric("目标帧率", "30 FPS")
                    with col_rt2:
                        st.metric("超分倍数", f"{scale}x")
                    with col_rt3:
                        st.metric("GPU加速", "✓ 启用" if gpu_info['available'] else "✗ CPU")
                    
                    if gpu_info['available']:
                        st.info(f"GPU: {gpu_info['device_name']}")
                        st.info(f"显存已用: {gpu_info['memory_allocated']:.2f} GB / {gpu_info['memory_cached']:.2f} GB")
                    
                    st.success("实时超分引擎已就绪！可以处理视频流。")
                    
        else:
            rt_video_file = st.file_uploader("上传视频文件用于实时预览", type=['mp4', 'avi', 'mov'])
            if rt_video_file is not None:
                rt_video_path, rt_temp_dir = save_uploaded_file(rt_video_file)
                
                col_rt_vid1, col_rt_vid2 = st.columns(2)
                with col_rt_vid1:
                    st.subheader("原始视频")
                    st.video(rt_video_path)
                
                with col_rt_vid2:
                    st.subheader("超分预览")
                    st.info("点击下方按钮生成预览帧")
                    
                    if st.button("🎬 生成预览帧", type="primary"):
                        with st.spinner("正在处理..."):
                            pipeline = load_pipeline(
                                model_name=model_name,
                                scale=scale,
                                enable_denoise=enable_denoise,
                                enable_temporal=False,
                                enable_bitrate_adapt=False,
                                enable_face_enhance=enable_face_enhance,
                                enable_subtitle_enhance=enable_subtitle_enhance,
                                enable_realtime=enable_realtime,
                                weight_path=weight_path,
                            )
                            
                            cap = cv2.VideoCapture(rt_video_path)
                            ret, frame = cap.read()
                            if ret:
                                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                
                                if enable_realtime and pipeline.realtime_engine:
                                    sr_frame = pipeline.realtime_engine.process_frame_sync(frame)
                                else:
                                    sr_frame = pipeline.enhance(frame)
                                
                                sr_frame_display = (sr_frame * 255).astype(np.uint8)
                                st.image(sr_frame_display, caption=f"超分结果 x{scale}", use_column_width=True)
                                
                                psnr = calc_psnr(
                                    sr_frame_display,
                                    cv2.resize(frame, (sr_frame_display.shape[1], sr_frame_display.shape[0]), interpolation=cv2.INTER_CUBIC)
                                )
                                st.success(f"质量指标: PSNR = {psnr:.2f} dB")
                                
                                if enable_realtime and pipeline.realtime_engine:
                                    stats = pipeline.realtime_engine.get_stats()
                                    st.info(f"处理帧率: {stats['fps']:.1f} FPS")
                            
                            cap.release()
    
    with tab4:
        st.header("关于本系统")
        
        st.markdown("""
        <div class="info-box">
        <h3>🎯 系统功能</h3>
        <p>本系统基于深度学习实现视频超分辨率重建，支持以下功能：</p>
        <ul>
            <li><strong>超分模型</strong>: EDSR / RCAN 经典模型，支持 2x/3x/4x 超分</li>
            <li><strong>多帧融合降噪</strong>: 光流引导对齐、加权平均、高斯融合、双边滤波</li>
            <li><strong>时序一致性</strong>: 光流法、去闪烁后处理、双向光流一致性检验</li>
            <li><strong>码率自适应</strong>: 基于纹理复杂度分析、运动复杂度分析</li>
            <li><strong>人脸增强</strong>: 人脸区域检测、独立超分增强、更高倍数重建</li>
            <li><strong>字幕清晰化</strong>: 字幕区域检测、锐化增强、边缘增强</li>
            <li><strong>实时超分</strong>: 批量推理、帧缓存、GPU流水线加速可达30fps+</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        st.markdown("""
        <div class="info-box">
        <h3>🔬 技术栈</h3>
        <ul>
            <li><strong>PyTorch</strong>: 深度学习框架</li>
            <li><strong>OpenCV</strong>: 图像处理</li>
            <li><strong>FFmpeg</strong>: 视频编解码</li>
            <li><strong>Streamlit</strong>: Web交互界面</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        col_mod1, col_mod2 = st.columns(2)
        
        with col_mod1:
            st.markdown("""
            <div class="metric-card">
            <h3>EDSR 模型</h3>
            <p>Enhanced Deep Super-Resolution</p>
            <ul>
                <li>16/32 残差块</li>
                <li>跳跃连接架构</li>
                <li>参数高效</li>
                <li>推理速度快</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
        
        with col_mod2:
            st.markdown("""
            <div class="metric-card">
            <h3>RCAN 模型</h3>
            <p>Residual Channel Attention Network</p>
            <ul>
                <li>通道注意力机制</li>
                <li>残差组架构</li>
                <li>更高重建质量</li>
                <li>适合复杂场景</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        st.markdown("""
        <div class="info-box">
        <h3>💡 使用建议</h3>
        <ol>
            <li>对于快速预览，建议使用 EDSR x2 模型</li>
            <li>追求高质量可选择 RCAN x4 模型</li>
            <li>运动较大的视频建议开启时序一致性</li>
            <li>低质量视频建议开启多帧融合降噪</li>
            <li>需要控制文件大小时调整码率自适应设置</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
