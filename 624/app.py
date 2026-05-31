import streamlit as st
import cv2
import numpy as np
from PIL import Image
import tempfile
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io

from video_processor import VideoProcessor
from face_analyzer import FaceAnalyzer
from motion_analyzer import MotionAnalyzer, FrameScorer
from overlay_engine import OverlayEngine
from ab_tester import ThumbnailABTester
from ctr_predictor import CTRPredictor
from cover_scheduler import CoverScheduler, CoverVariant, ScheduleConfig
from competitor_analyzer import CompetitorAnalyzer

st.set_page_config(
    page_title="视频封面智能推荐工具",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

sns.set_style("whitegrid")


def initialize_session_state():
    if 'video_processor' not in st.session_state:
        st.session_state.video_processor = None
    if 'frames' not in st.session_state:
        st.session_state.frames = []
    if 'frame_scores' not in st.session_state:
        st.session_state.frame_scores = []
    if 'top_frames' not in st.session_state:
        st.session_state.top_frames = []
    if 'face_analyzer' not in st.session_state:
        st.session_state.face_analyzer = FaceAnalyzer()
    if 'motion_analyzer' not in st.session_state:
        st.session_state.motion_analyzer = MotionAnalyzer()
    if 'frame_scorer' not in st.session_state:
        st.session_state.frame_scorer = FrameScorer()
    if 'overlay_engine' not in st.session_state:
        st.session_state.overlay_engine = OverlayEngine()
    if 'ab_tester' not in st.session_state:
        st.session_state.ab_tester = ThumbnailABTester()
    if 'selected_frame' not in st.session_state:
        st.session_state.selected_frame = None
    if 'video_info' not in st.session_state:
        st.session_state.video_info = {}
    if 'video_style' not in st.session_state:
        st.session_state.video_style = None
    if 'style_analysis' not in st.session_state:
        st.session_state.style_analysis = None
    if 'ctr_predictor' not in st.session_state:
        st.session_state.ctr_predictor = CTRPredictor()
    if 'cover_scheduler' not in st.session_state:
        st.session_state.cover_scheduler = CoverScheduler()
    if 'competitor_analyzer' not in st.session_state:
        st.session_state.competitor_analyzer = CompetitorAnalyzer(
            st.session_state.get('ctr_predictor', CTRPredictor())
        )
    if 'ctr_predictions' not in st.session_state:
        st.session_state.ctr_predictions = []


initialize_session_state()


def analyze_video(video_path, sample_interval=1.0):
    video_proc = VideoProcessor(video_path)
    st.session_state.video_processor = video_proc
    st.session_state.video_info = video_proc.get_video_info()
    
    frames = video_proc.extract_frames(sample_interval=sample_interval)
    st.session_state.frames = frames
    
    frame_scores = []
    progress_bar = st.progress(0)
    
    for i, (frame_idx, frame) in enumerate(frames):
        face_analysis = st.session_state.face_analyzer.analyze_frame(frame)
        
        prev_frame = frames[i-1][1] if i > 0 else None
        motion_analysis = st.session_state.motion_analyzer.analyze_frame_motion(frame, prev_frame)
        
        color_vibrancy = st.session_state.motion_analyzer.analyze_color_vibrancy(frame)
        color_harmony = st.session_state.motion_analyzer.analyze_color_harmony(frame)
        contrast_analysis = st.session_state.motion_analyzer.analyze_contrast(frame)
        composition_analysis = st.session_state.motion_analyzer.analyze_composition(frame)
        
        quality_analysis = {
            "color_analysis": {
                **color_vibrancy,
                **color_harmony,
                **contrast_analysis
            },
            "composition_analysis": composition_analysis,
            "quality_score": (
                color_vibrancy["vibrancy_score"] * 0.4 +
                composition_analysis["composition_score"] * 0.4 +
                contrast_analysis["contrast_score"] * 0.2
            )
        }
        
        aesthetics_analysis = st.session_state.frame_scorer.calculate_aesthetics_score(frame, quality_analysis)
        
        score = st.session_state.frame_scorer.score_frame(
            frame, face_analysis, motion_analysis, quality_analysis, aesthetics_analysis
        )
        
        frame_scores.append((frame_idx, score, face_analysis, motion_analysis, quality_analysis, aesthetics_analysis))
        
        progress_bar.progress((i + 1) / len(frames))
    
    st.session_state.frame_scores = frame_scores
    
    if len(frames) > 0:
        detect_video_style(frames[:min(5, len(frames))])
    
    top_k = min(10, len(frames))
    st.session_state.top_frames = st.session_state.frame_scorer.rank_frames(
        [(idx, score) for idx, score, _, _, _, _ in frame_scores], top_k=top_k
    )
    
    return video_proc, frames, frame_scores


def detect_video_style(sample_frames):
    if not sample_frames:
        st.session_state.video_style = "default"
        st.session_state.style_analysis = None
        return
    
    style_scores = {}
    
    for _, frame in sample_frames:
        color_vibrancy = st.session_state.motion_analyzer.analyze_color_vibrancy(frame)
        composition = st.session_state.motion_analyzer.analyze_composition(frame)
        style_analysis = st.session_state.motion_analyzer.detect_video_style(frame, color_vibrancy, composition)
        
        for style_name, style_value in style_analysis["styles"].items():
            if style_name not in style_scores:
                style_scores[style_name] = []
            style_scores[style_name].append(style_value)
    
    avg_style_scores = {k: np.mean(v) for k, v in style_scores.items()}
    
    main_style = max(avg_style_scores.keys(), key=lambda k: avg_style_scores[k])
    
    st.session_state.video_style = main_style
    st.session_state.style_analysis = {
        "styles": avg_style_scores,
        "main_style": main_style,
        "dominant_color": style_analysis.get("dominant_color", [128, 128, 128]),
        "palette": style_analysis.get("palette", [])
    }


def plot_score_distribution():
    if not st.session_state.frame_scores:
        return None
    
    scores = [s[1]["total_score"] for s in st.session_state.frame_scores]
    frame_indices = [s[0] for s in st.session_state.frame_scores]
    
    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.hist(scores, bins=20, edgecolor='black', alpha=0.7)
    ax1.set_title('总分分布')
    ax1.set_xlabel('分数')
    ax1.set_ylabel('帧数')
    
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(frame_indices, scores, marker='o', markersize=3, linewidth=1)
    ax2.set_title('帧分数趋势')
    ax2.set_xlabel('帧索引')
    ax2.set_ylabel('总分')
    
    ax3 = fig.add_subplot(gs[0, 2])
    if st.session_state.style_analysis and st.session_state.style_analysis["styles"]:
        styles = st.session_state.style_analysis["styles"]
        style_names = list(styles.keys())
        style_values = list(styles.values())
        colors = plt.cm.Set3(np.linspace(0, 1, len(style_names)))
        ax3.bar(style_names, style_values, color=colors)
        ax3.set_title('视频风格分析')
        ax3.set_ylabel('分数')
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    face_scores = [s[1]["face_score"] for s in st.session_state.frame_scores]
    color_scores = [s[1].get("color_score", 0) for s in st.session_state.frame_scores]
    composition_scores = [s[1].get("composition_score", 0) for s in st.session_state.frame_scores]
    motion_scores = [s[1]["motion_score"] for s in st.session_state.frame_scores]
    expression_scores = [s[1]["expression_score"] for s in st.session_state.frame_scores]
    aesthetics_scores = [s[1].get("aesthetics_score", 0) for s in st.session_state.frame_scores]
    
    x = np.arange(len(scores))
    ax4 = fig.add_subplot(gs[1, :])
    ax4.stackplot(x, face_scores, color_scores, composition_scores, 
                  motion_scores, expression_scores,
                  labels=['人脸', '颜色', '构图', '动作', '表情'], alpha=0.7)
    ax4.set_title('多维度分数分布')
    ax4.set_xlabel('帧索引')
    ax4.legend(loc='upper left')
    
    ax5 = fig.add_subplot(gs[2, 0])
    score_data = {
        '人脸': face_scores,
        '颜色': color_scores,
        '构图': composition_scores,
        '动作': motion_scores,
        '表情': expression_scores,
        '美观度': aesthetics_scores
    }
    bp = ax5.boxplot([v for v in score_data.values()], patch_artist=True)
    colors = plt.cm.Set2(np.linspace(0, 1, len(score_data)))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax5.set_xticklabels(list(score_data.keys()), rotation=45, ha='right')
    ax5.set_title('各维度分数箱线图')
    
    ax6 = fig.add_subplot(gs[2, 1])
    avg_scores = [np.mean(v) for v in score_data.values()]
    ax6.pie(avg_scores, labels=score_data.keys(), autopct='%1.1f%%', 
            colors=colors, startangle=90)
    ax6.set_title('各维度平均占比')
    
    if st.session_state.style_analysis and st.session_state.style_analysis.get("palette"):
        ax7 = fig.add_subplot(gs[2, 2])
        palette = st.session_state.style_analysis["palette"][:5]
        for i, color_info in enumerate(palette):
            color_rgb = tuple(c / 255 for c in color_info["color"])
            ax7.add_patch(plt.Rectangle((i * 0.2, 0), 0.18, 1, color=color_rgb))
        ax7.set_xlim(0, 1)
        ax7.set_ylim(0, 1)
        ax7.set_title('主色调')
        ax7.axis('off')
    
    plt.tight_layout()
    return fig


def main():
    st.title("🎬 视频封面智能推荐工具")
    st.markdown("---")
    
    page = st.sidebar.selectbox(
        "功能导航",
        ["视频分析", "封面设计", "CTR预测", "A/B测试", "自动发布", "竞品对比", "结果导出"]
    )
    
    if page == "视频分析":
        show_video_analysis_page()
    elif page == "封面设计":
        show_cover_design_page()
    elif page == "CTR预测":
        show_ctr_prediction_page()
    elif page == "A/B测试":
        show_ab_test_page()
    elif page == "自动发布":
        show_auto_publish_page()
    elif page == "竞品对比":
        show_competitor_page()
    elif page == "结果导出":
        show_export_page()


def show_video_analysis_page():
    st.header("📹 视频分析")
    
    uploaded_file = st.file_uploader("上传视频文件", type=["mp4", "avi", "mov", "mkv"])
    
    if uploaded_file is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.write(uploaded_file.read())
        video_path = tfile.name
        tfile.close()
        
        col1, col2 = st.columns(2)
        with col1:
            sample_interval = st.slider("采样间隔（秒）", 0.5, 5.0, 1.0, 0.5)
        with col2:
            if st.button("开始分析", type="primary"):
                with st.spinner("正在分析视频..."):
                    analyze_video(video_path, sample_interval)
                st.success("分析完成！")
        
        if st.session_state.video_info:
            st.subheader("视频信息")
            info = st.session_state.video_info
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("分辨率", info["resolution"])
            col2.metric("帧率", f"{info['fps']:.1f} fps")
            col3.metric("总帧数", info["total_frames"])
            col4.metric("时长", f"{info['duration']:.1f} 秒")
        
        if st.session_state.video_style and st.session_state.style_analysis:
            st.subheader("🎨 视频风格分析")
            style_desc = st.session_state.overlay_engine.get_style_description(st.session_state.video_style)
            st.success(style_desc)
            
            style_cols = st.columns(3)
            with style_cols[0]:
                st.metric("主要风格", st.session_state.video_style)
            with style_cols[1]:
                style_scores = st.session_state.style_analysis["styles"]
                top_styles = sorted(style_scores.items(), key=lambda x: x[1], reverse=True)[:3]
                st.write("次要风格:")
                for s, v in top_styles[1:]:
                    st.markdown(f"- {s}: {v:.2f}")
            with style_cols[2]:
                if st.session_state.style_analysis.get("palette"):
                    st.write("主色调:")
                    palette = st.session_state.style_analysis["palette"][:3]
                    color_cols = st.columns(3)
                    for i, color_info in enumerate(palette):
                        hex_color = color_info["hex"]
                        color_cols[i].markdown(
                            f'<div style="background-color:{hex_color};width:40px;height:40px;border-radius:5px;"></div>',
                            unsafe_allow_html=True
                        )
                        color_cols[i].write(hex_color)
        
        if st.session_state.top_frames:
            st.subheader("🏆 最佳候选帧")
            
            top_indices = [idx for idx, _ in st.session_state.top_frames]
            top_frames_data = []
            for idx, score in st.session_state.top_frames:
                for fs in st.session_state.frame_scores:
                    if fs[0] == idx:
                        top_frames_data.append((idx, fs[1], fs[2], fs[3], fs[4]))
                        break
            
            cols = st.columns(5)
            for i, (frame_idx, score, face_analysis, motion_analysis, quality_analysis) in enumerate(top_frames_data[:10]):
                col = cols[i % 5]
                frame_data = None
                for idx, f in st.session_state.frames:
                    if idx == frame_idx:
                        frame_data = f
                        break
                
                if frame_data is not None:
                    col.image(frame_data, caption=f"帧 {frame_idx}", use_column_width=True)
                    col.markdown(f"**总分: {score['total_score']:.3f}**")
                    col.markdown(f"人脸: {score['face_score']:.2f} | 动作: {score['motion_score']:.2f}")
                    col.markdown(f"质量: {score['quality_score']:.2f} | 表情: {score['expression_score']:.2f}")
                    if col.button(f"选择此帧", key=f"select_{i}"):
                        st.session_state.selected_frame = (frame_idx, frame_data)
            
            st.subheader("📊 分数统计")
            fig = plot_score_distribution()
            if fig:
                st.pyplot(fig)
            
            st.subheader("📋 详细评分表")
            scores_df = pd.DataFrame([
                {
                    "帧索引": fs[0],
                    "总分": fs[1]["total_score"],
                    "人脸分": fs[1]["face_score"],
                    "颜色分": fs[1].get("color_score", 0),
                    "构图分": fs[1].get("composition_score", 0),
                    "美观度": fs[1].get("aesthetics_score", 0),
                    "动作分": fs[1]["motion_score"],
                    "表情分": fs[1]["expression_score"],
                    "检测人脸数": fs[2].get("num_faces", 0),
                    "主要表情": fs[2].get("main_expression", "N/A")
                }
                for fs in st.session_state.frame_scores
            ])
            st.dataframe(scores_df.sort_values("总分", ascending=False), height=400)
        
        try:
            os.unlink(video_path)
        except:
            pass
    else:
        st.info("👆 请上传一个视频文件开始分析")


def show_cover_design_page():
    st.header("🎨 封面设计")
    
    if st.session_state.selected_frame is None:
        if st.session_state.top_frames:
            st.info("请先在视频分析页面选择一帧，或从下方候选帧中选择")
            
            top_indices = [idx for idx, _ in st.session_state.top_frames[:5]]
            cols = st.columns(5)
            for i, (idx, _) in enumerate(st.session_state.top_frames[:5]):
                col = cols[i]
                for f_idx, frame_data in st.session_state.frames:
                    if f_idx == idx:
                        col.image(frame_data, caption=f"帧 {idx}", use_column_width=True)
                        if col.button(f"选择帧 {idx}", key=f"choose_{idx}"):
                            st.session_state.selected_frame = (idx, frame_data)
                        break
        else:
            st.warning("请先在视频分析页面上传并分析视频")
        return
    
    frame_idx, frame = st.session_state.selected_frame
    st.image(frame, caption=f"当前选择: 帧 {frame_idx}", use_column_width=True)
    
    if st.session_state.video_style:
        style_desc = st.session_state.overlay_engine.get_style_description(st.session_state.video_style)
        st.info(f"🎯 检测到视频风格: {style_desc}")
        
        use_auto_style = st.checkbox("使用视频风格自动推荐字体", value=True)
        
        if use_auto_style:
            recommendations = st.session_state.overlay_engine.recommend_font_by_style(st.session_state.video_style)
            st.success(f"已根据{st.session_state.video_style}风格自动推荐配置")
    else:
        use_auto_style = False
        recommendations = None
    
    st.subheader("标题叠加设置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        title = st.text_input("主标题", "精彩内容抢先看")
        subtitle = st.text_input("副标题", "")
        
        if use_auto_style and recommendations:
            position_options = recommendations["recommended_positions"]
            position = st.selectbox("标题位置", position_options, index=0)
            style_options = recommendations["recommended_styles"]
            style = st.selectbox("预设样式", style_options, index=0)
        else:
            position = st.selectbox(
                "标题位置",
                ["top", "center", "bottom", "top_left", "top_right", "bottom_left", "bottom_right"],
                index=2
            )
            style = st.selectbox("预设样式", ["modern", "minimal", "bold", "clean"], index=0)
    
    with col2:
        if use_auto_style and recommendations:
            font_options = recommendations["recommended_fonts"]
            font_family = st.selectbox("字体", font_options, index=0)
            size_options = recommendations["recommended_font_sizes"]
            font_size = st.selectbox("字体大小", size_options, index=0)
            
            color_options = recommendations["recommended_text_colors"]
            color_hex_options = ["#{:02x}{:02x}{:02x}".format(*c) for c in color_options]
            text_color = st.selectbox("文字颜色", color_hex_options, index=0,
                                     format_func=lambda x: x)
            
            bg_options = recommendations["recommended_bg_colors"]
            if bg_options[0] is not None:
                bg_option = st.checkbox("显示背景", value=True)
                bg_hex_options = ["#{:02x}{:02x}{:02x}".format(*c[:3]) for c in bg_options if c]
                bg_color = st.selectbox("背景颜色", bg_hex_options, index=0,
                                       format_func=lambda x: x)
                bg_alpha = bg_options[0][3] if len(bg_options[0]) > 3 else 180
            else:
                bg_option = st.checkbox("显示背景", value=False)
                bg_color = "#000000"
                bg_alpha = 180
        else:
            font_size = st.slider("字体大小", 20, 100, 48)
            font_family = st.selectbox(
                "字体",
                ["default", "arial", "arial_bold", "impact", "calibri", "verdana"],
                index=2
            )
            text_color = st.color_picker("文字颜色", "#FFFFFF")
            
            bg_option = st.checkbox("显示背景", value=True)
            if bg_option:
                bg_color = st.color_picker("背景颜色", "#000000")
                bg_alpha = st.slider("背景透明度", 0, 255, 180)
            else:
                bg_color = None
                bg_alpha = 0
    
    if st.button("生成预览", type="primary"):
        text_color_rgb = tuple(int(text_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        if bg_option and bg_color:
            bg_rgb = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            bg_rgba = bg_rgb + (bg_alpha,)
        else:
            bg_rgba = None
        
        result = st.session_state.overlay_engine.add_text_overlay(
            frame,
            title=title,
            subtitle=subtitle,
            position=position,
            font_size=int(font_size) if isinstance(font_size, int) else font_size,
            font_family=font_family,
            text_color=text_color_rgb,
            bg_color=bg_rgba
        )
        
        st.subheader("📸 预览效果")
        st.image(result, caption="设计预览", use_column_width=True)
        
        result_pil = Image.fromarray(result)
        buf = io.BytesIO()
        result_pil.save(buf, format="PNG")
        btn = st.download_button(
            label="下载封面",
            data=buf.getvalue(),
            file_name=f"cover_frame_{frame_idx}.png",
            mime="image/png"
        )
    
    if use_auto_style and recommendations:
        st.subheader("🎯 风格自动推荐预览")
        style_variations = st.session_state.overlay_engine.generate_style_based_thumbnails(
            frame, title, st.session_state.video_style, num_variations=3
        )
        var_cols = st.columns(len(style_variations))
        for i, (var_name, var_result) in enumerate(style_variations):
            var_cols[i].image(var_result, caption=var_name, use_column_width=True)
            
            result_pil = Image.fromarray(var_result)
            buf = io.BytesIO()
            result_pil.save(buf, format="PNG")
            var_cols[i].download_button(
                label=f"下载{var_name}",
                data=buf.getvalue(),
                file_name=f"cover_{var_name}_{frame_idx}.png",
                mime="image/png",
                key=f"dl_var_{i}"
            )
    else:
        st.subheader("🎯 样式模板快速预览")
        template_cols = st.columns(4)
        templates = ["modern", "minimal", "bold", "clean"]
        
        for i, template_style in enumerate(templates):
            template_result = st.session_state.overlay_engine.create_thumbnail_template(
                frame, title, template_style
            )
            template_cols[i].image(template_result, caption=f"{template_style}样式", use_column_width=True)


def show_ctr_prediction_page():
    st.header("📈 封面点击率预测")
    
    if not st.session_state.top_frames:
        st.warning("请先在视频分析页面上传并分析视频")
        return
    
    st.subheader("🎯 CTR预测模型")
    
    col1, col2 = st.columns(2)
    with col1:
        video_category = st.selectbox(
            "视频类别",
            ["entertainment", "education", "gaming", "music", "tech", "lifestyle", "food", "travel"],
            format_func=lambda x: {
                "entertainment": "娱乐", "education": "教育", "gaming": "游戏",
                "music": "音乐", "tech": "科技", "lifestyle": "生活",
                "food": "美食", "travel": "旅行",
            }.get(x, x)
        )
    with col2:
        video_style = st.session_state.video_style or "default"
        st.info(f"当前视频风格: **{video_style}**")
    
    if st.button("预测所有候选帧CTR", type="primary"):
        with st.spinner("正在预测点击率..."):
            frames_with_analysis = []
            for fs in st.session_state.frame_scores:
                frame_idx = fs[0]
                frame_data = None
                for idx, f in st.session_state.frames:
                    if idx == frame_idx:
                        frame_data = f
                        break
                
                if frame_data is not None:
                    frames_with_analysis.append(
                        (frame_idx, frame_data, fs[2], fs[4], fs[4])
                    )
            
            ctr_results = st.session_state.ctr_predictor.rank_frames_by_ctr(
                frames_with_analysis, video_style, video_category
            )
            st.session_state.ctr_predictions = ctr_results
        
        st.success("CTR预测完成！")
    
    if st.session_state.ctr_predictions:
        st.subheader("🏆 CTR预测排名")
        
        ctr_df = pd.DataFrame([
            {
                "排名": r["rank"],
                "帧索引": r["frame_index"],
                "预测CTR": f"{r['predicted_ctr']*100:.2f}%",
                "CTR值": r["predicted_ctr"],
                "置信度": f"{r['confidence']*100:.0f}%",
            }
            for r in st.session_state.ctr_predictions
        ])
        st.dataframe(ctr_df, hide_index=True, height=400)
        
        st.subheader("📊 CTR预测可视化")
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        ranks = [r["rank"] for r in st.session_state.ctr_predictions]
        ctrs = [r["predicted_ctr"] * 100 for r in st.session_state.ctr_predictions]
        frame_labels = [f"帧{r['frame_index']}" for r in st.session_state.ctr_predictions]
        
        colors = plt.cm.RdYlGn(np.linspace(0.2, 0.9, len(ctrs)))
        sorted_indices = sorted(range(len(ctrs)), key=lambda i: ctrs[i], reverse=True)
        bar_colors = [''] * len(ctrs)
        for rank, idx in enumerate(sorted_indices):
            bar_colors[idx] = colors[rank]
        
        axes[0].barh(frame_labels, ctrs, color=bar_colors)
        axes[0].set_xlabel("预测CTR (%)")
        axes[0].set_title("各帧预测点击率")
        for i, v in enumerate(ctrs):
            axes[0].text(v + 0.05, i, f"{v:.2f}%", va='center')
        
        best = st.session_state.ctr_predictions[0]
        factors = best["top_factors"]
        factor_names = [f[0] for f in factors]
        factor_contribs = [f[1]["contribution"] for f in factors]
        
        axes[1].pie(factor_contribs, labels=factor_names, autopct='%1.1f%%', startangle=90)
        axes[1].set_title(f"TOP1封面(帧{best['frame_index']})关键因素")
        
        plt.tight_layout()
        st.pyplot(fig)
        
        st.subheader("📋 最佳封面推荐")
        best = st.session_state.ctr_predictions[0]
        
        best_frame_data = None
        for idx, f in st.session_state.frames:
            if idx == best["frame_index"]:
                best_frame_data = f
                break
        
        if best_frame_data is not None:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(best_frame_data, caption=f"🏆 推荐封面 (帧{best['frame_index']})", use_column_width=True)
            with col2:
                st.metric("预测CTR", best["ctr_percentage"])
                st.metric("置信度", f"{best['confidence']*100:.0f}%")
                
                st.markdown("**🔑 关键优势因素:**")
                for fname, finfo in best["top_factors"]:
                    st.markdown(f"- {fname}: {finfo['value']:.3f} (贡献: {finfo['contribution']:.3f})")
                
                st.markdown("**⚠️ 改进空间:**")
                for fname, finfo in best["weak_factors"]:
                    st.markdown(f"- {fname}: {finfo['value']:.3f}")
                
                suggestions = st.session_state.ctr_predictor.generate_improvement_suggestions(
                    {"weak_factors": best["weak_factors"]}
                )
                if suggestions:
                    st.markdown("**💡 改进建议:**")
                    for s in suggestions:
                        st.markdown(s)
        
        st.subheader("📊 所有封面CTR对比")
        top_n = min(5, len(st.session_state.ctr_predictions))
        cols = st.columns(top_n)
        for i, pred in enumerate(st.session_state.ctr_predictions[:top_n]):
            frame_data = None
            for idx, f in st.session_state.frames:
                if idx == pred["frame_index"]:
                    frame_data = f
                    break
            if frame_data is not None:
                with cols[i]:
                    medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i] if i < 5 else f"#{i+1}"
                    st.image(frame_data, caption=f"{medal} 帧{pred['frame_index']}", use_column_width=True)
                    st.metric("预测CTR", pred["ctr_percentage"])
    
    st.subheader("📝 历史数据反馈")
    st.markdown("上传实际CTR数据可以优化预测模型")
    
    feedback_frame = st.selectbox(
        "选择帧",
        [fs[0] for fs in st.session_state.frame_scores],
        key="ctr_feedback_frame"
    )
    actual_ctr = st.number_input("实际CTR (0-1)", 0.0, 1.0, 0.05, 0.01, key="actual_ctr_input")
    
    if st.button("提交反馈"):
        frame_data = None
        face_analysis = None
        quality_analysis = None
        composition_analysis = None
        
        for fs in st.session_state.frame_scores:
            if fs[0] == feedback_frame:
                face_analysis = fs[2]
                quality_analysis = fs[4]
                composition_analysis = fs[4]
                break
        
        for idx, f in st.session_state.frames:
            if idx == feedback_frame:
                frame_data = f
                break
        
        if frame_data is not None:
            st.session_state.ctr_predictor.add_historical_data(
                frame_data, actual_ctr, face_analysis, quality_analysis,
                composition_analysis, video_style, video_category
            )
            st.success(f"已提交反馈！历史数据量: {len(st.session_state.ctr_predictor.historical_data)}")


def show_auto_publish_page():
    st.header("🚀 封面自动发布")
    
    if not st.session_state.top_frames:
        st.warning("请先在视频分析页面上传并分析视频")
        return
    
    st.subheader("📅 创建发布计划")
    
    col1, col2 = st.columns(2)
    with col1:
        schedule_id = st.text_input("计划ID", "schedule_001")
        interval_hours = st.slider("轮换间隔(小时)", 1, 72, 24)
        max_rotations = st.slider("最大轮换次数", 1, 50, 10)
    with col2:
        auto_switch = st.checkbox("自动切换到最优封面", value=True)
        min_impressions = st.number_input("最小曝光量(切换前)", 100, 10000, 500, 100)
        warmup_hours = st.slider("预热时间(小时)", 0.5, 24.0, 2.0, 0.5)
    
    num_cover_variants = st.slider("封面变体数量", 2, 6, 3)
    
    if st.button("创建发布计划", type="primary"):
        variants = []
        for i, (idx, score) in enumerate(st.session_state.top_frames[:num_cover_variants]):
            frame_data = None
            for f_idx, f in st.session_state.frames:
                if f_idx == idx:
                    frame_data = f
                    break
            
            predicted_ctr = 0.05
            if st.session_state.ctr_predictions:
                for pred in st.session_state.ctr_predictions:
                    if pred["frame_index"] == idx:
                        predicted_ctr = pred["predicted_ctr"]
                        break
            
            variant = CoverVariant(
                variant_id=f"variant_{i}",
                frame_index=idx,
                image_data=frame_data,
                predicted_ctr=predicted_ctr,
            )
            variants.append(variant)
        
        config = ScheduleConfig(
            test_id=schedule_id,
            interval_hours=interval_hours,
            max_rotations=max_rotations,
            auto_switch_threshold=0.02 if auto_switch else 1.0,
            min_impressions_before_switch=min_impressions,
            warmup_hours=warmup_hours,
        )
        
        result = st.session_state.cover_scheduler.create_schedule(schedule_id, variants, config)
        st.success(f"发布计划创建成功！初始封面: {result['initial_variant']}")
    
    st.subheader("📋 计划管理")
    
    existing_schedules = list(st.session_state.cover_scheduler.schedules.keys())
    if existing_schedules:
        manage_id = st.selectbox("选择计划", existing_schedules, key="manage_schedule")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("▶️ 启动", key="start_schedule"):
                result = st.session_state.cover_scheduler.start_schedule(manage_id)
                if "error" not in result:
                    st.success(f"计划 {manage_id} 已启动")
                else:
                    st.error(result["error"])
        with col2:
            if st.button("⏸️ 暂停", key="pause_schedule"):
                result = st.session_state.cover_scheduler.pause_schedule(manage_id)
                if "error" not in result:
                    st.success(f"计划 {manage_id} 已暂停")
        with col3:
            if st.button("▶️ 恢复", key="resume_schedule"):
                result = st.session_state.cover_scheduler.resume_schedule(manage_id)
                if "error" not in result:
                    st.success(f"计划 {manage_id} 已恢复")
        with col4:
            if st.button("⏹️ 停止", key="stop_schedule"):
                result = st.session_state.cover_scheduler.stop_schedule(manage_id)
                if "error" not in result:
                    st.success(f"计划 {manage_id} 已停止")
        
        status = st.session_state.cover_scheduler.get_schedule_status(manage_id)
        if "error" not in status:
            st.subheader("📊 计划状态")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("状态", status["status"])
            col2.metric("轮换次数", f"{status['rotation_count']}/{status['max_rotations']}")
            col3.metric("轮换间隔", f"{status['interval_hours']}小时")
            
            if status.get("current_variant"):
                cv = status["current_variant"]
                st.info(f"当前封面: **{cv['variant_id']}** | 预测CTR: {cv['predicted_ctr']:.4f} | 实际CTR: {cv['actual_ctr']:.4f}")
            
            all_variants = status.get("all_variants", [])
            if all_variants:
                var_df = pd.DataFrame(all_variants)
                st.dataframe(var_df, hide_index=True)
    else:
        st.info("暂无发布计划，请先创建")
    
    st.subheader("🧪 模拟发布效果")
    
    sim_cols = st.columns(3)
    with sim_cols[0]:
        sim_id = st.text_input("计划ID（模拟）", "schedule_001", key="sim_schedule_id")
    with sim_cols[1]:
        sim_hours = st.number_input("模拟时长(小时)", 24, 720, 168, 24)
    with sim_cols[2]:
        sim_impressions = st.number_input("每小时曝光量", 50, 1000, 100, 50)
    
    if st.button("运行模拟", type="primary"):
        with st.spinner("正在模拟发布效果..."):
            variants = []
            for i, (idx, score) in enumerate(st.session_state.top_frames[:3]):
                frame_data = None
                for f_idx, f in st.session_state.frames:
                    if f_idx == idx:
                        frame_data = f
                        break
                
                predicted_ctr = 0.05 + np.random.random() * 0.05
                if st.session_state.ctr_predictions:
                    for pred in st.session_state.ctr_predictions:
                        if pred["frame_index"] == idx:
                            predicted_ctr = pred["predicted_ctr"]
                            break
                
                variant = CoverVariant(
                    variant_id=f"variant_{i}",
                    frame_index=idx,
                    image_data=frame_data,
                    predicted_ctr=predicted_ctr,
                )
                variants.append(variant)
            
            config = ScheduleConfig(
                test_id=sim_id,
                interval_hours=interval_hours,
                max_rotations=max_rotations,
                auto_switch_threshold=0.02,
                min_impressions_before_switch=min_impressions,
            )
            st.session_state.cover_scheduler.create_schedule(sim_id, variants, config)
            
            sim_result = st.session_state.cover_scheduler.simulate_performance(
                sim_id, sim_hours, sim_impressions
            )
        
        if "error" not in sim_result:
            st.success("模拟完成！")
            
            winner = sim_result["winner"]
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("模拟时长", f"{sim_result['simulated_hours']}小时")
            col2.metric("轮换次数", sim_result["rotation_count"])
            col3.metric("优胜封面", winner["variant_id"])
            col4.metric("实际CTR", f"{winner['actual_ctr']*100:.2f}%")
            
            st.subheader("📈 CTR趋势")
            snapshots = sim_result.get("snapshots", [])
            if snapshots:
                fig, ax = plt.subplots(figsize=(12, 5))
                
                variant_ids = set()
                for snap in snapshots:
                    for vid in snap.get("variants", {}):
                        variant_ids.add(vid)
                
                for vid in sorted(variant_ids):
                    hours = []
                    ctrs = []
                    for snap in snapshots:
                        if vid in snap.get("variants", {}):
                            hours.append(snap["hour"])
                            ctrs.append(snap["variants"][vid]["actual_ctr"] * 100)
                    if hours:
                        ax.plot(hours, ctrs, marker='o', markersize=2, label=vid, linewidth=1.5)
                
                ax.set_xlabel("时间(小时)")
                ax.set_ylabel("CTR (%)")
                ax.set_title("封面CTR随时间变化趋势")
                ax.legend()
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
                st.pyplot(fig)
            
            st.subheader("📊 最终排名")
            ranking_df = pd.DataFrame(sim_result["final_ranking"])
            st.dataframe(ranking_df, hide_index=True)


def show_competitor_page():
    st.header("⚔️ 竞品封面对比")
    
    if not st.session_state.top_frames:
        st.warning("请先在视频分析页面上传并分析视频")
        return
    
    st.subheader("🖼️ 设置我方封面")
    
    our_frame_idx = st.selectbox(
        "选择我方封面帧",
        [idx for idx, _ in st.session_state.top_frames],
        key="our_cover_select"
    )
    
    our_frame_data = None
    our_face_analysis = None
    our_quality_analysis = None
    our_comp_analysis = None
    
    for idx, f in st.session_state.frames:
        if idx == our_frame_idx:
            our_frame_data = f
            break
    
    for fs in st.session_state.frame_scores:
        if fs[0] == our_frame_idx:
            our_face_analysis = fs[2]
            our_quality_analysis = fs[4]
            our_comp_analysis = fs[4]
            break
    
    if our_frame_data is not None:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(our_frame_data, caption="我方封面", use_column_width=True)
        with col2:
            video_category = st.selectbox(
                "视频类别",
                ["entertainment", "education", "gaming", "music", "tech", "lifestyle", "food", "default"],
                format_func=lambda x: {
                    "entertainment": "娱乐", "education": "教育", "gaming": "游戏",
                    "music": "音乐", "tech": "科技", "lifestyle": "生活",
                    "food": "美食", "default": "通用",
                }.get(x, x),
                key="comp_category"
            )
            
            if st.button("设置我方封面"):
                pred = st.session_state.competitor_analyzer.add_our_cover(
                    our_frame_data, "我方封面", category=video_category,
                    video_style=st.session_state.video_style,
                    face_analysis=our_face_analysis,
                    quality_analysis=our_quality_analysis,
                    composition_analysis=our_comp_analysis,
                )
                st.success(f"我方封面已设置！预测CTR: {pred['ctr_percentage']}")
    
    st.subheader("🔍 添加竞品封面")
    
    comp_files = st.file_uploader(
        "上传竞品封面图片",
        type=["png", "jpg", "jpeg", "bmp", "webp"],
        accept_multiple_files=True,
        key="competitor_uploader"
    )
    
    if comp_files:
        for comp_file in comp_files:
            comp_image = Image.open(comp_file).convert("RGB")
            comp_array = np.array(comp_image)
            
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image(comp_array, caption=comp_file.name, use_column_width=True)
            with col2:
                comp_name = st.text_input("竞品名称", comp_file.name.split('.')[0], key=f"comp_name_{comp_file.name}")
                comp_source = st.text_input("来源", "", key=f"comp_source_{comp_file.name}")
                
                if st.button(f"添加竞品", key=f"add_comp_{comp_file.name}"):
                    pred = st.session_state.competitor_analyzer.add_competitor(
                        comp_array, comp_name, comp_source, category=video_category,
                        video_style=st.session_state.video_style,
                    )
                    st.success(f"竞品 {comp_name} 已添加！预测CTR: {pred['ctr_percentage']}")
    
    if st.session_state.competitor_analyzer.competitors:
        st.subheader("📋 已添加的竞品")
        for i, comp in enumerate(st.session_state.competitor_analyzer.competitors):
            col1, col2 = st.columns([1, 4])
            with col1:
                if comp.image is not None:
                    st.image(comp.image, caption=comp.name, use_column_width=True)
            with col2:
                if comp.ctr_prediction:
                    st.metric("预测CTR", comp.ctr_prediction["ctr_percentage"])
        
        if st.button("🗑️ 清除所有竞品"):
            st.session_state.competitor_analyzer.clear_competitors()
            st.success("已清除所有竞品")
    
    st.subheader("📊 竞品对比分析")
    
    if st.session_state.competitor_analyzer.our_cover and st.session_state.competitor_analyzer.competitors:
        if st.button("开始对比分析", type="primary"):
            with st.spinner("正在分析对比..."):
                result = st.session_state.competitor_analyzer.compare_all(video_category)
            
            if "error" not in result:
                st.success("对比分析完成！")
                
                our = result["our_cover"]
                col1, col2, col3 = st.columns(3)
                col1.metric("我方预测CTR", our["ctr_percentage"])
                col2.metric("CTR排名", f"#{result['ctr_rank']} / {result['total_compared']}")
                
                vs_avg = result["our_vs_avg_percent"]
                col3.metric(
                    "vs 竞品平均",
                    f"{vs_avg:+.1f}%",
                    delta=f"{'领先' if vs_avg > 0 else '落后'}",
                    delta_color="normal" if vs_avg > 0 else "inverse",
                )
                
                st.subheader("🏆 CTR对比排行")
                all_covers = [{"name": our["name"], "ctr": our["predicted_ctr"], "type": "我方"}]
                for c in result["competitors"]:
                    all_covers.append({"name": c["name"], "ctr": c["predicted_ctr"], "type": "竞品"})
                
                all_covers.sort(key=lambda x: x["ctr"], reverse=True)
                
                fig, ax = plt.subplots(figsize=(10, 5))
                names = [c["name"] for c in all_covers]
                ctrs = [c["ctr"] * 100 for c in all_covers]
                colors = ['#ff6b6b' if c["type"] == "我方" else '#4ecdc4' for c in all_covers]
                
                bars = ax.barh(names, ctrs, color=colors)
                ax.set_xlabel("预测CTR (%)")
                ax.set_title("封面CTR对比排行")
                for i, v in enumerate(ctrs):
                    ax.text(v + 0.02, i, f"{v:.2f}%", va='center')
                plt.tight_layout()
                st.pyplot(fig)
                
                if result.get("strengths"):
                    st.subheader("✅ 我方优势")
                    for s in result["strengths"]:
                        st.markdown(f"- {s}")
                
                if result.get("weaknesses"):
                    st.subheader("⚠️ 需要改进")
                    for w in result["weaknesses"]:
                        st.markdown(f"- {w}")
                
                if result.get("suggestions"):
                    st.subheader("💡 竞争建议")
                    for s in result["suggestions"]:
                        st.markdown(s)
                
                if result.get("benchmark_comparison"):
                    st.subheader("📏 行业基准对比")
                    bench = result["benchmark_comparison"]
                    
                    bench_data = []
                    for metric, info in bench.items():
                        metric_labels = {
                            "ctr_vs_avg": "CTR vs 行业平均",
                            "ctr_vs_top": "CTR vs 行业TOP",
                            "saturation_vs_avg": "饱和度 vs 行业平均",
                            "face_vs_avg": "人脸元素 vs 行业平均",
                        }
                        bench_data.append({
                            "指标": metric_labels.get(metric, metric),
                            "我方": f"{info['our']:.4f}",
                            "基准": f"{info['benchmark']:.4f}",
                            "差异": f"{info['diff_pct']:+.1f}%",
                            "状态": "✅ 超越" if info["status"] == "above" else "❌ 低于",
                        })
                    
                    st.dataframe(pd.DataFrame(bench_data), hide_index=True)
                
                if result.get("radar_data"):
                    st.subheader("🕸️ 多维雷达图")
                    radar = result["radar_data"]
                    
                    labels = radar["labels"]
                    num_vars = len(labels)
                    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
                    angles += angles[:1]
                    
                    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
                    
                    for ds in radar["datasets"]:
                        values = ds["data"] + ds["data"][:1]
                        ax.plot(angles, values, 'o-', linewidth=2, label=ds["name"])
                        ax.fill(angles, values, alpha=0.15)
                    
                    ax.set_xticks(angles[:-1])
                    ax.set_xticklabels(labels)
                    ax.set_ylim(0, 1)
                    ax.set_title("封面特征多维度对比")
                    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
                    plt.tight_layout()
                    st.pyplot(fig)
    else:
        st.info("请先设置我方封面并添加至少一个竞品封面")


def show_ab_test_page():
    st.header("📊 A/B测试")
    
    if not st.session_state.top_frames:
        st.warning("请先在视频分析页面上传并分析视频")
        return
    
    st.subheader("创建测试")
    
    col1, col2 = st.columns(2)
    
    with col1:
        test_id = st.text_input("测试ID", "test_001")
        num_frames = st.slider("测试帧数", 2, 5, 3)
        num_titles = st.slider("标题变体数", 1, 5, 2)
    
    with col2:
        base_title = st.text_input("基础标题", "精彩内容")
        use_style_variations = st.checkbox("使用样式变体", value=True)
    
    titles = [base_title]
    if num_titles > 1:
        variations = st.session_state.overlay_engine.generate_title_variations(base_title)
        titles = variations[:num_titles]
        st.write("标题变体:")
        for t in titles:
            st.markdown(f"- {t}")
    
    styles = ["modern", "bold", "clean"] if use_style_variations else ["modern"]
    
    if st.button("创建A/B测试", type="primary"):
        test_frames = []
        for idx, _ in st.session_state.top_frames[:num_frames]:
            for f_idx, frame_data in st.session_state.frames:
                if f_idx == idx:
                    test_frames.append((idx, frame_data))
                    break
        
        st.session_state.ab_tester.create_test(test_id, test_frames, titles, styles)
        st.success(f"测试创建成功！共 {num_frames * len(titles) * len(styles)} 个变体")
    
    st.subheader("运行模拟测试")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        simulate_test_id = st.text_input("测试ID（模拟）", "test_001")
    with col2:
        num_users = st.number_input("模拟用户数", 100, 100000, 1000, 100)
    with col3:
        use_user_hash = st.checkbox("使用用户ID哈希分流", value=True, 
                                  help="同一用户始终分配到同一变体，保证测试一致性")
    
    col_salt = st.columns(1)
    with col_salt[0]:
        salt = st.text_input("分流盐值（可选）", "", 
                           help="用于改变分流结果，同一用户不同盐值分配到不同变体")
    
    if st.button("运行模拟", type="primary"):
        with st.spinner("正在模拟测试..."):
            if use_user_hash:
                results = st.session_state.ab_tester.simulate_test_with_user_hash(
                    simulate_test_id, num_users, salt
                )
            else:
                results = st.session_state.ab_tester.simulate_test(
                    simulate_test_id, num_users, use_user_hash=False
                )
        
        if results:
            st.success("模拟完成！")
            
            st.subheader("🏆 测试结果")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("总用户数", results.get("num_users", results.get("total_impressions", 0)))
            col2.metric("分流方式", "用户ID哈希" if use_user_hash else "随机分配")
            col3.metric("优胜变体", results["winner"])
            
            winner_data = results["winner_data"]
            col4.metric(
                "点击率提升",
                f"{winner_data['significance'].get('uplift_percent', 0):.1f}%"
            )
            
            if use_user_hash and "variant_distribution" in results:
                st.subheader("� 变体分布（用户ID哈希）")
                dist_df = pd.DataFrame([
                    {"变体ID": k, "用户数": v, "占比": f"{v/num_users*100:.1f}%"}
                    for k, v in results["variant_distribution"].items()
                ])
                st.dataframe(dist_df, hide_index=True)
                
                fig, ax = plt.subplots(figsize=(10, 4))
                variant_names = list(results["variant_distribution"].keys())
                variant_counts = list(results["variant_distribution"].values())
                ax.pie(variant_counts, labels=variant_names, autopct='%1.1f%%', startangle=90)
                ax.set_title("各变体用户分布")
                st.pyplot(fig)
            
            st.subheader("� 各变体表现")
            summary = st.session_state.ab_tester.get_test_summary(simulate_test_id)
            
            results_df = pd.DataFrame(summary["all_results"])
            st.dataframe(
                results_df.sort_values("ctr", ascending=False),
                column_config={
                    "ctr": st.column_config.NumberColumn("点击率", format="%.4f"),
                    "conversion_rate": st.column_config.NumberColumn("转化率", format="%.4f"),
                },
                height=400
            )
            
            st.subheader("📊 可视化结果")
            fig, ax = plt.subplots(figsize=(12, 6))
            
            variant_ids = [r["variant_id"] for r in summary["all_results"]]
            ctr_values = [r["ctr"] for r in summary["all_results"]]
            
            colors = ['#ff6b6b' if r["is_control"] else '#4ecdc4' for r in summary["all_results"]]
            
            bars = ax.bar(variant_ids, ctr_values, color=colors)
            ax.set_xlabel("变体ID")
            ax.set_ylabel("点击率 (CTR)")
            ax.set_title("各变体点击率对比")
            plt.xticks(rotation=45, ha='right')
            
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.,
                    height,
                    f'{height:.4f}',
                    ha='center',
                    va='bottom'
                )
            
            plt.tight_layout()
            st.pyplot(fig)
    
    st.subheader("🔍 用户分流查询")
    
    col_q1, col_q2 = st.columns(2)
    with col_q1:
        query_test_id = st.text_input("测试ID（查询）", "test_001")
    with col_q2:
        query_user_id = st.text_input("用户ID", "user_123")
    
    if st.button("查询用户分配"):
        assignment = st.session_state.ab_tester.get_user_variant(query_test_id, query_user_id, salt)
        if assignment:
            st.info(f"""
            用户 **{query_user_id}** 分配结果:
            - 变体ID: **{assignment['variant_id']}**
            - 是否为对照组: {'是' if assignment['is_control'] else '否'}
            - 哈希值: `{assignment['hash_value']}`
            """)
        else:
            st.warning("未找到测试或变体")
    
    st.subheader("✅ 一致性验证")
    
    verify_test_id = st.text_input("测试ID（验证）", "test_001")
    num_verify = st.slider("验证用户数", 10, 1000, 100)
    
    if st.button("验证一致性"):
        verify_result = st.session_state.ab_tester.verify_user_consistency(verify_test_id, num_verify)
        if verify_result["consistent"]:
            st.success(f"✅ 一致性验证通过！{verify_result['num_checks']} 个用户全部一致")
        else:
            st.error(f"""
            ❌ 发现不一致！
            - 检查用户数: {verify_result['num_checks']}
            - 不一致用户数: {verify_result['inconsistent_count']}
            """)
            if verify_result["inconsistent_users"]:
                st.write("不一致用户示例:", verify_result["inconsistent_users"])


def show_export_page():
    st.header("💾 结果导出")
    
    if not st.session_state.frame_scores:
        st.warning("请先在视频分析页面上传并分析视频")
        return
    
    if st.session_state.video_style:
        st.info(f"🎨 视频风格: {st.session_state.video_style}")
        style_desc = st.session_state.overlay_engine.get_style_description(st.session_state.video_style)
        st.write(style_desc)
    
    st.subheader("分析数据导出")
    
    ctr_lookup = {}
    if st.session_state.ctr_predictions:
        for pred in st.session_state.ctr_predictions:
            ctr_lookup[pred["frame_index"]] = pred["predicted_ctr"]
    
    scores_df = pd.DataFrame([
        {
            "帧索引": fs[0],
            "时间戳(秒)": fs[0] / st.session_state.video_info.get("fps", 30),
            "总分": fs[1]["total_score"],
            "人脸分": fs[1]["face_score"],
            "颜色分": fs[1].get("color_score", 0),
            "构图分": fs[1].get("composition_score", 0),
            "美观度": fs[1].get("aesthetics_score", 0),
            "动作分": fs[1]["motion_score"],
            "表情分": fs[1]["expression_score"],
            "预测CTR": ctr_lookup.get(fs[0], 0),
            "检测人脸数": fs[2].get("num_faces", 0),
            "主要表情": fs[2].get("main_expression", "N/A"),
            "动作强度": fs[3].get("motion_score", 0)
        }
        for fs in st.session_state.frame_scores
    ])
    
    csv = scores_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📄 下载评分数据 (CSV)",
        data=csv,
        file_name="frame_scores.csv",
        mime="text/csv"
    )
    
    st.dataframe(scores_df.sort_values("总分", ascending=False), height=300)
    
    st.subheader("TOP封面导出")
    
    top_count = st.slider("导出TOP帧数", 1, 10, 3)
    
    top_indices = [idx for idx, _ in st.session_state.top_frames[:top_count]]
    
    export_cols = st.columns(top_count)
    
    for i, frame_idx in enumerate(top_indices):
        frame_data = None
        for idx, f in st.session_state.frames:
            if idx == frame_idx:
                frame_data = f
                break
        
        if frame_data is not None:
            export_cols[i].image(frame_data, caption=f"TOP{i+1} 帧{frame_idx}", use_column_width=True)
            
            result_pil = Image.fromarray(frame_data)
            buf = io.BytesIO()
            result_pil.save(buf, format="PNG")
            export_cols[i].download_button(
                label=f"下载TOP{i+1}",
                data=buf.getvalue(),
                file_name=f"top{i+1}_frame_{frame_idx}.png",
                mime="image/png",
                key=f"download_top_{i}"
            )
    
    st.subheader("📊 分析报告")
    
    if st.session_state.frame_scores:
        scores = [s[1]["total_score"] for s in st.session_state.frame_scores]
        face_scores = [s[1]["face_score"] for s in st.session_state.frame_scores]
        
        report = f"""
# 视频封面分析报告

## 视频基本信息
- 分辨率: {st.session_state.video_info.get("resolution", "N/A")}
- 帧率: {st.session_state.video_info.get("fps", 0):.1f} fps
- 总帧数: {st.session_state.video_info.get("total_frames", 0)}
- 时长: {st.session_state.video_info.get("duration", 0):.1f} 秒

## 分析统计
- 采样帧数: {len(st.session_state.frame_scores)}
- 平均总分: {np.mean(scores):.3f}
- 最高总分: {np.max(scores):.3f}
- 平均人脸分: {np.mean(face_scores):.3f}

## TOP 3 推荐帧
"""
        for i in range(min(3, len(top_indices))):
            idx = top_indices[i]
            for fs in st.session_state.frame_scores:
                if fs[0] == idx:
                    report += f"{i+1}. 帧 {idx} - 总分: {fs[1]['total_score']:.3f}\n"
                    break
        
        st.download_button(
            label="📝 下载分析报告 (Markdown)",
            data=report.encode('utf-8'),
            file_name="analysis_report.md",
            mime="text/markdown"
        )


if __name__ == "__main__":
    main()
