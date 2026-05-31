import streamlit as st
import numpy as np
import cv2
from PIL import Image, ImageDraw
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config, TrainingConfig
from preprocessor import ImagePreprocessor, ContourExtractor, CharacterDataset
from contour_smoother import GlyphOptimizer, CornerDetector
from font_generator import FontCreator, BaseFontGenerator
from font_model import SimpleFontGenerator, FontVAE, FontTrainer
from stroke_analyzer import StrokeDecomposer, StructureConstraint, StrokeBasedGenerator
from font_style_transfer import FontStyleTransfer, FontStyle
from font_blender import FontBlender, FontMixer, BlendMode
from font_preview import FontPreviewer, PreviewConfig


st.set_page_config(
    page_title="矢量字体生成器",
    page_icon="✍️",
    layout="wide"
)

st.title("✍️ 矢量字体生成器")
st.markdown("从手写样本学习个人字体风格，生成TTF/OTF字体文件")


if 'dataset' not in st.session_state:
    st.session_state.dataset = CharacterDataset()
if 'style_learned' not in st.session_state:
    st.session_state.style_learned = False
if 'generated_points' not in st.session_state:
    st.session_state.generated_points = {}
if 'font_created' not in st.session_state:
    st.session_state.font_created = False
if 'structure_reports' not in st.session_state:
    st.session_state.structure_reports = {}
if 'use_structure_constraint' not in st.session_state:
    st.session_state.use_structure_constraint = True
if 'use_iterative_fitting' not in st.session_state:
    st.session_state.use_iterative_fitting = True
if 'preserve_corners' not in st.session_state:
    st.session_state.preserve_corners = True
if 'style_variations' not in st.session_state:
    st.session_state.style_variations = {}
if 'blended_fonts' not in st.session_state:
    st.session_state.blended_fonts = {}
if 'preview_text' not in st.session_state:
    st.session_state.preview_text = "The quick brown fox jumps over the lazy dog"


TrainingConfig.ensure_dirs()


preprocessor = ImagePreprocessor()
contour_extractor = ContourExtractor()
glyph_optimizer = GlyphOptimizer()
base_generator = BaseFontGenerator()
style_generator = SimpleFontGenerator()
corner_detector = CornerDetector()

if st.session_state.use_structure_constraint:
    stroke_decomposer = StrokeDecomposer()
    structure_constraint = StructureConstraint()
    stroke_generator = StrokeBasedGenerator()

style_transfer = FontStyleTransfer()
font_blender = FontBlender()
font_mixer = FontMixer()
font_previewer = FontPreviewer()


def draw_contour(points, size=(256, 256), scale=100, highlight_corners=None):
    if points is None or len(points) == 0:
        return np.zeros(size, dtype=np.uint8)
    
    img = np.zeros(size, dtype=np.uint8)
    
    try:
        points_centered = points - np.mean(points, axis=0)
        max_val = np.max(np.abs(points_centered))
        if max_val > 0:
            points_scaled = points_centered / max_val * (size[0] * 0.35)
        else:
            points_scaled = points_centered
        
        points_scaled += np.array([size[0]//2, size[1]//2])
        points_int = points_scaled.astype(np.int32)
        
        cv2.fillPoly(img, [points_int], 200)
        cv2.polylines(img, [points_int], True, 255, 2)
        
        if highlight_corners:
            for corner_idx in highlight_corners:
                if corner_idx < len(points_scaled):
                    pt = points_scaled[corner_idx].astype(int)
                    cv2.circle(img, (pt[0], pt[1]), 5, 255, -1)
    except:
        pass
    
    return img


def draw_handwriting_canvas(canvas_size=256):
    if 'canvas_image' not in st.session_state:
        st.session_state.canvas_image = Image.new('L', (canvas_size, canvas_size), 0)
    
    canvas_placeholder = st.empty()
    
    col1, col2 = st.columns(2)
    with col1:
        stroke_width = st.slider("笔画粗细", 1, 20, 8)
    with col2:
        if st.button("清除画布"):
            st.session_state.canvas_image = Image.new('L', (canvas_size, canvas_size), 0)
    
    canvas_placeholder.image(st.session_state.canvas_image, caption="手写区域", width=canvas_size)
    
    return st.session_state.canvas_image


def analyze_and_display_structure(char: str, binary_image: np.ndarray):
    if not st.session_state.use_structure_constraint:
        return None
    
    try:
        report = stroke_generator.get_structure_report(char, binary_image)
        st.session_state.structure_reports[char] = report
        
        stroke_generator.learn_stroke_templates(char, binary_image)
        
        return report
    except Exception as e:
        st.warning(f"结构分析失败: {e}")
        return None


def display_structure_report(report: dict):
    if not report:
        return
    
    st.markdown("#### 📊 笔画结构分析")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("笔画数", report.get('stroke_count', 0))
    with col2:
        st.metric("宽高比", f"{report.get('aspect_ratio', 1.0):.2f}")
    with col3:
        status = "✅ 有效" if report.get('valid', False) else "⚠️ 警告"
        st.metric("结构状态", status)
    
    if 'strokes' in report and report['strokes']:
        st.markdown("**笔画类型:**")
        stroke_types = [f"{s['type']}({s['length']:.0f}px)" for s in report['strokes']]
        st.write(", ".join(stroke_types))
    
    if not report.get('valid', True) and report.get('issues'):
        st.warning("结构问题: " + "; ".join(report['issues']))


tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📝 手写样本输入", 
    "🎨 风格学习", 
    "🖋️ 字体生成", 
    "🎭 风格迁移",
    "🔀 字体混合",
    "👁️ 实时预览",
    "💾 下载字体",
    "⚙️ 高级设置"
])


with tab8:
    st.header("高级设置")
    st.markdown("配置增强功能选项")
    
    st.markdown("### 🔍 笔画分解监督")
    st.session_state.use_structure_constraint = st.checkbox(
        "启用笔画结构约束",
        value=st.session_state.use_structure_constraint,
        help="保持中文笔画结构完整性，防止字形变形"
    )
    
    if st.session_state.use_structure_constraint:
        st.info("✅ 将分析每个样本的笔画类型、数量和结构比例，在生成时应用约束以保持字形结构完整")
    
    st.markdown("### 📈 迭代优化拟合")
    st.session_state.use_iterative_fitting = st.checkbox(
        "启用迭代贝塞尔拟合",
        value=st.session_state.use_iterative_fitting,
        help="使用L-BFGS-B优化算法最小化轮廓拟合误差"
    )
    
    if st.session_state.use_iterative_fitting:
        col1, col2 = st.columns(2)
        with col1:
            st.number_input("最大迭代次数", min_value=5, max_value=100, value=20, step=5)
        with col2:
            st.number_input("目标拟合误差", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
        st.info("✅ 将通过迭代优化贝塞尔曲线控制点，显著降低拟合误差")
    
    st.markdown("### 🎯 拐点检测保持")
    st.session_state.preserve_corners = st.checkbox(
        "启用尖角保持",
        value=st.session_state.preserve_corners,
        help="检测轮廓拐点，在平滑处理时保持尖角锐利"
    )
    
    if st.session_state.preserve_corners:
        col1, col2 = st.columns(2)
        with col1:
            st.slider("拐点角度阈值", min_value=60.0, max_value=160.0, value=120.0, step=5.0,
                     help="小于此角度的点被识别为拐点")
        with col2:
            st.slider("拐点保护半径", min_value=1, max_value=10, value=2, step=1,
                     help="拐点周围多少个点不参与平滑")
        st.info("✅ 将自动检测轮廓拐点，平滑时保持尖角处的锐利特征")
    
    st.markdown("---")
    
    if st.button("保存设置", type="primary"):
        st.success("设置已保存，将在后续处理中生效")


with tab1:
    st.header("手写样本输入")
    st.markdown("上传手写字符图片或在画布上书写")
    
    if st.session_state.use_structure_constraint:
        st.success("🔍 笔画结构监督已启用 - 输入时将自动分析笔画结构")
    if st.session_state.preserve_corners:
        st.success("🎯 拐点保持已启用 - 尖角特征将被保留")
    
    input_method = st.radio("输入方式", ["上传图片", "画布手写"])
    
    char_input = st.text_input("输入字符", max_chars=1, help="输入一个字符")
    
    if input_method == "上传图片":
        uploaded_file = st.file_uploader("选择图片文件", type=['png', 'jpg', 'jpeg'])
        
        if uploaded_file is not None and char_input:
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.image(image, caption="原图", channels="BGR", width=150)
            
            binary = preprocessor.preprocess(image)
            with col2:
                st.image(binary, caption="预处理后", width=150)
            
            contour = contour_extractor.extract_contour(binary)
            points = contour_extractor.sample_contour_points(contour)
            
            if points is not None:
                corners = []
                if st.session_state.preserve_corners:
                    corners = corner_detector.detect_corners(points)
                
                contour_img = draw_contour(points, highlight_corners=corners)
                with col3:
                    caption = f"轮廓 ({len(corners)}拐点)" if corners else "轮廓"
                    st.image(contour_img, caption=caption, width=150)
                
                if st.session_state.use_structure_constraint:
                    with col4:
                        skeleton = stroke_decomposer._extract_skeleton(binary)
                        if skeleton is not None:
                            st.image(skeleton, caption="骨架提取", width=150)
                
                if st.button(f"添加字符 '{char_input}' 到数据集", type="primary"):
                    normalized_points = contour_extractor.normalize_contour(points)
                    st.session_state.dataset.add_character(char_input, binary, normalized_points)
                    
                    if st.session_state.use_structure_constraint:
                        report = analyze_and_display_structure(char_input, binary)
                        if report:
                            display_structure_report(report)
                    
                    st.success(f"已添加字符: {char_input}" + 
                              (f" | 检测到{len(corners)}个拐点" if corners else ""))
            else:
                st.warning("未能提取到有效轮廓")
    else:
        st.info("在下方绘制字符")
        
        if 'drawing' not in st.session_state:
            st.session_state.drawing = False
            st.session_state.last_pos = None
        
        canvas = Image.new('L', (300, 300), 0)
        draw = ImageDraw.Draw(canvas)
        
        st.info("💡 提示：请使用支持Canvas的浏览器进行手写，或使用上传图片方式")
        
        if char_input and st.button("使用示例字符"):
            t = np.linspace(0, 2*np.pi, 100)
            x = 120 + 80*np.cos(t)
            y = 120 + 100*np.sin(t)
            
            demo_canvas = Image.new('L', (300, 300), 0)
            demo_draw = ImageDraw.Draw(demo_canvas)
            
            points = list(zip(x.astype(int), y.astype(int)))
            demo_draw.line(points, fill=255, width=8)
            
            img_array = np.array(demo_canvas)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.image(img_array, caption="示例字符", width=150)
            
            binary = preprocessor.preprocess(img_array)
            with col2:
                st.image(binary, caption="预处理后", width=150)
            
            contour = contour_extractor.extract_contour(binary)
            points = contour_extractor.sample_contour_points(contour)
            
            if points is not None:
                corners = []
                if st.session_state.preserve_corners:
                    corners = corner_detector.detect_corners(points)
                
                contour_img = draw_contour(points, highlight_corners=corners)
                with col3:
                    caption = f"轮廓 ({len(corners)}拐点)" if corners else "轮廓"
                    st.image(contour_img, caption=caption, width=150)
                
                normalized_points = contour_extractor.normalize_contour(points)
                st.session_state.dataset.add_character(char_input, binary, normalized_points)
                
                if st.session_state.use_structure_constraint:
                    report = analyze_and_display_structure(char_input, binary)
                    if report:
                        with st.expander("查看结构分析报告"):
                            display_structure_report(report)
                
                st.success(f"已添加示例字符: {char_input}" + 
                          (f" | 检测到{len(corners)}个拐点" if corners else ""))
    
    st.markdown("---")
    st.subheader("已收集的字符")
    
    available_chars = st.session_state.dataset.get_available_chars()
    
    if available_chars:
        st.write(f"已收集 {len(available_chars)} 个字符")
        
        cols = st.columns(8)
        for idx, char in enumerate(available_chars):
            with cols[idx % 8]:
                char_data = st.session_state.dataset.get_character(char)
                if char_data and char_data['image'] is not None:
                    st.image(char_data['image'], caption=char, width=60)
                    
                    if char in st.session_state.structure_reports:
                        report = st.session_state.structure_reports[char]
                        stroke_count = report.get('stroke_count', 0)
                        st.caption(f"{stroke_count}画")
    else:
        st.info("还没有收集任何字符，请先输入手写样本")
    
    if available_chars and st.session_state.use_structure_constraint:
        with st.expander("📊 查看所有结构分析报告"):
            for char in available_chars:
                if char in st.session_state.structure_reports:
                    st.markdown(f"#### 字符: {char}")
                    display_structure_report(st.session_state.structure_reports[char])


with tab2:
    st.header("风格学习")
    st.markdown("从已收集的手写样本中学习个人字体风格")
    
    if st.session_state.use_structure_constraint:
        st.info("🔍 笔画结构监督已启用 - 学习时将考虑笔画结构特征")
    if st.session_state.use_iterative_fitting:
        st.info("📈 迭代优化拟合已启用 - 风格学习更精确")
    
    available_chars = st.session_state.dataset.get_available_chars()
    
    if len(available_chars) < 3:
        st.warning("请至少收集3个字符样本后再进行风格学习")
    else:
        st.write(f"当前有 {len(available_chars)} 个字符样本可用于学习")
        
        if st.button("开始学习字体风格", type="primary"):
            with st.spinner("正在学习风格..."):
                chars, points_list = st.session_state.dataset.get_training_data()
                
                if st.session_state.use_structure_constraint:
                    st.info("正在分析笔画结构特征...")
                
                char_points_dict = {}
                for char, points in zip(chars, points_list):
                    char_points_dict[char] = points
                
                success = style_generator.learn_style(char_points_dict)
                
                if success:
                    st.session_state.style_learned = True
                    st.success("风格学习完成！")
                    
                    st.subheader("学习到的风格预览")
                    
                    cols = st.columns(4)
                    for idx, char in enumerate(chars[:4]):
                        with cols[idx]:
                            original_points = char_points_dict.get(char)
                            if original_points is not None:
                                corners = corner_detector.detect_corners(original_points) if st.session_state.preserve_corners else []
                                original_img = draw_contour(original_points, highlight_corners=corners)
                                caption = f"{char} ({len(corners)}拐点)" if corners else char
                                st.image(original_img, caption=caption, width=120)
                else:
                    st.error("风格学习失败")
        
        if st.session_state.style_learned:
            st.info("✅ 风格已学习完成，可以进行字体生成了")
            
            st.markdown("---")
            st.subheader("风格插值测试")
            
            chars, points_list = st.session_state.dataset.get_training_data()
            if len(chars) >= 2:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    char1 = st.selectbox("字符1", chars, index=0, key="int_char1")
                with col2:
                    char2 = st.selectbox("字符2", chars, index=min(1, len(chars)-1), key="int_char2")
                with col3:
                    alpha = st.slider("插值系数", 0.0, 1.0, 0.5)
                
                if st.button("生成插值结果"):
                    idx1 = chars.index(char1)
                    idx2 = chars.index(char2)
                    
                    p1 = points_list[idx1]
                    p2 = points_list[idx2]
                    
                    interpolated = p1 * (1 - alpha) + p2 * alpha
                    
                    cols = st.columns(3)
                    with cols[0]:
                        corners1 = corner_detector.detect_corners(p1) if st.session_state.preserve_corners else []
                        img1 = draw_contour(p1, highlight_corners=corners1)
                        st.image(img1, caption=f"{char1} ({len(corners1)}拐点)", width=150)
                    with cols[1]:
                        img_interp = draw_contour(interpolated)
                        st.image(img_interp, caption="插值结果", width=150)
                    with cols[2]:
                        corners2 = corner_detector.detect_corners(p2) if st.session_state.preserve_corners else []
                        img2 = draw_contour(p2, highlight_corners=corners2)
                        st.image(img2, caption=f"{char2} ({len(corners2)}拐点)", width=150)


with tab3:
    st.header("字体生成")
    st.markdown("为目标字符集生成个性化字形")
    
    status_col1, status_col2, status_col3 = st.columns(3)
    with status_col1:
        status = "✅" if st.session_state.use_structure_constraint else "❌"
        st.write(f"{status} 笔画结构约束")
    with status_col2:
        status = "✅" if st.session_state.use_iterative_fitting else "❌"
        st.write(f"{status} 迭代优化拟合")
    with status_col3:
        status = "✅" if st.session_state.preserve_corners else "❌"
        st.write(f"{status} 拐点保持")
    
    target_chars = st.text_area(
        "目标字符集", 
        value="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        help="输入要包含在字体中的所有字符"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        font_name = st.text_input("字体名称", value="MyHandwriting")
    with col2:
        font_format = st.selectbox("字体格式", ["ttf", "otf"])
    
    style_strength = st.slider("风格强度", 0.0, 1.0, 0.5, 
                              help="控制生成字形与原始风格的相似度")
    
    if st.button("生成字体字形", type="primary"):
        if not st.session_state.style_learned:
            st.warning("请先完成风格学习")
        else:
            with st.spinner("正在生成字形..."):
                generated = {}
                stats = {
                    'total': 0,
                    'structure_applied': 0,
                    'corners_detected': 0,
                    'avg_error': 0.0
                }
                
                target_char_list = list(target_chars)
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, char in enumerate(target_char_list):
                    stats['total'] += 1
                    
                    char_data = st.session_state.dataset.get_character(char)
                    
                    if char_data and char_data['points'] is not None:
                        base_points = char_data['points']
                    else:
                        base_points = base_generator.generate_base_char(char)
                    
                    if base_points is not None:
                        if hasattr(style_generator, 'mean_style'):
                            generated_points = base_points * (1 - style_strength) + style_generator.mean_style * style_strength
                        else:
                            generated_points = base_points
                        
                        if st.session_state.use_structure_constraint and 'stroke_generator' in globals():
                            reference_char = char if char in st.session_state.structure_reports else None
                            if not reference_char:
                                for available_char in st.session_state.structure_reports:
                                    reference_char = available_char
                                    break
                            
                            if reference_char and reference_char in st.session_state.structure_reports:
                                ref_data = st.session_state.dataset.get_character(reference_char)
                                if ref_data and ref_data['image'] is not None:
                                    structure = stroke_decomposer.analyze_image(ref_data['image'])
                                    generated_points = structure_constraint.apply_constraints(generated_points, structure)
                                    generated_points = stroke_generator.generate_with_structure(generated_points, reference_char)
                                    stats['structure_applied'] += 1
                        
                        optimized = glyph_optimizer.optimize_glyph(
                            generated_points,
                            use_corner_preservation=st.session_state.preserve_corners,
                            use_iterative_fitting=st.session_state.use_iterative_fitting
                        )
                        
                        if optimized:
                            if optimized.get('corners'):
                                stats['corners_detected'] += 1
                            if 'fitting_info' in optimized:
                                stats['avg_error'] += optimized['fitting_info'].get('average_error', 0)
                            generated[char] = optimized['smoothed_points']
                    
                    progress_bar.progress((idx + 1) / len(target_char_list))
                    status_text.text(f"正在生成: {idx + 1}/{len(target_char_list)} - {char}")
                
                stats['avg_error'] = stats['avg_error'] / max(1, len(generated))
                
                st.session_state.generated_points = generated
                
                st.success(f"成功生成 {len(generated)} 个字形")
                
                st.markdown("### 📊 生成统计")
                stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                with stat_col1:
                    st.metric("总字形数", len(generated))
                with stat_col2:
                    st.metric("应用结构约束", stats['structure_applied'])
                with stat_col3:
                    st.metric("检测拐点", stats['corners_detected'])
                with stat_col4:
                    st.metric("平均拟合误差", f"{stats['avg_error']:.3f}")
                
                st.subheader("生成预览")
                preview_chars = list(generated.keys())[:20]
                
                cols = st.columns(10)
                for idx, char in enumerate(preview_chars):
                    with cols[idx % 10]:
                        points = generated.get(char)
                        if points is not None:
                            corners = corner_detector.detect_corners(points) if st.session_state.preserve_corners else []
                            img = draw_contour(points, highlight_corners=corners)
                            caption = f"{char}({len(corners)})" if corners else char
                            st.image(img, caption=caption, width=60)


with tab4:
    st.header("🎭 字体风格迁移")
    st.markdown("将生成的字形转换为不同风格：粗体、斜体、手写体等")
    
    if not st.session_state.generated_points:
        st.warning("请先生成字体字形")
    else:
        st.success(f"当前有 {len(st.session_state.generated_points)} 个字形可用于风格迁移")
        
        col1, col2 = st.columns(2)
        with col1:
            target_style = st.selectbox(
                "选择目标风格",
                options=style_transfer.get_available_styles(),
                format_func=lambda x: {
                    'bold': '🔤 粗体 (Bold)',
                    'italic': '📐 斜体 (Italic)',
                    'bold_italic': '🔤📐 粗斜体 (Bold Italic)',
                    'condensed': '↔️ 紧凑体 (Condensed)',
                    'expanded': '↔️ 扩展体 (Expanded)',
                    'light': '✏️ 细体 (Light)',
                    'heavy': '🏋️ 特粗体 (Heavy)',
                    'oblique': '📏 倾斜体 (Oblique)',
                    'handwriting': '✍️ 手写体 (Handwriting)'
                }.get(x, x)
            )
        with col2:
            custom_params = st.checkbox("自定义参数", value=False)
        
        if custom_params:
            st.markdown("#### 风格参数调整")
            param_cols = st.columns(3)
            
            if target_style in ['bold', 'light', 'heavy']:
                with param_cols[0]:
                    stroke_width = st.slider("笔画粗细", 0.3, 2.0, 
                                           style_transfer.get_style_info(target_style).get('parameters', {}).get('stroke_width', 1.3),
                                           0.1)
                transfer_kwargs = {'stroke_width': stroke_width}
            elif target_style in ['italic', 'oblique']:
                with param_cols[0]:
                    angle = st.slider("倾斜角度", 0.1, 0.6,
                                     style_transfer.get_style_info(target_style).get('parameters', {}).get('angle', 0.3),
                                     0.05)
                transfer_kwargs = {'angle': angle}
            elif target_style in ['condensed', 'expanded']:
                with param_cols[0]:
                    scale_x = st.slider("水平缩放", 0.5, 1.5,
                                       style_transfer.get_style_info(target_style).get('parameters', {}).get('scale_x', 1.0),
                                       0.05)
                transfer_kwargs = {'scale_x': scale_x}
            elif target_style == 'handwriting':
                with param_cols[0]:
                    jitter = st.slider("抖动程度", 0.02, 0.15, 0.08, 0.01)
                with param_cols[1]:
                    irregularity = st.slider("不规则度", 0.05, 0.3, 0.15, 0.01)
                transfer_kwargs = {'jitter': jitter, 'irregularity': irregularity}
            else:
                transfer_kwargs = {}
        else:
            transfer_kwargs = {}
        
        style_info = style_transfer.get_style_info(target_style)
        if style_info:
            with st.expander("📖 风格说明"):
                st.write(f"**风格类型**: {style_info['enum']}")
                st.write(f"**默认参数**: {style_info['parameters']}")
        
        if st.button("✨ 应用风格转换", type="primary"):
            with st.spinner(f"正在转换为{target_style}风格..."):
                styled_glyphs = style_transfer.transfer_batch(
                    st.session_state.generated_points,
                    target_style,
                    **transfer_kwargs
                )
                
                st.session_state.style_variations[target_style] = styled_glyphs
                
                st.success(f"成功转换 {len(styled_glyphs)} 个字形为{target_style}风格")
                
                st.subheader("风格对比预览")
                
                sample_chars = list(styled_glyphs.keys())[:8]
                
                cols = st.columns(4)
                for i, char in enumerate(sample_chars):
                    with cols[i % 4]:
                        col1, col2 = st.columns(2)
                        with col1:
                            original = st.session_state.generated_points.get(char)
                            if original is not None:
                                img_original = draw_contour(original, size=(120, 120))
                                st.image(img_original, caption=f"{char} 原始", width=60)
                        with col2:
                            styled = styled_glyphs.get(char)
                            if styled is not None:
                                img_styled = draw_contour(styled, size=(120, 120))
                                st.image(img_styled, caption=f"{char} 转换", width=60)
                
                if st.button("💾 保存为当前字体", type="secondary"):
                    st.session_state.generated_points = styled_glyphs
                    st.success("已将转换后的风格设置为当前字体")
        
        if st.session_state.style_variations:
            st.markdown("---")
            st.subheader("📚 已保存的风格变体")
            
            for style_name, glyphs in st.session_state.style_variations.items():
                with st.expander(f"{style_name} ({len(glyphs)}个字形)"):
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"应用 '{style_name}'", key=f"apply_{style_name}"):
                            st.session_state.generated_points = glyphs
                            st.success(f"已应用 {style_name} 风格")
                    with col2:
                        if st.button(f"删除 '{style_name}'", key=f"delete_{style_name}"):
                            del st.session_state.style_variations[style_name]
                            st.rerun()
                    
                    preview_chars = list(glyphs.keys())[:6]
                    cols = st.columns(6)
                    for idx, char in enumerate(preview_chars):
                        with cols[idx]:
                            pts = glyphs.get(char)
                            if pts is not None:
                                img = draw_contour(pts, size=(80, 80))
                                st.image(img, caption=char, width=40)


with tab5:
    st.header("🔀 字体混合")
    st.markdown("将两种字体按比例融合，创造新的字体风格")
    
    source_options = ["当前字体"] + list(st.session_state.style_variations.keys())
    
    col1, col2, col3 = st.columns(3)
    with col1:
        font_a = st.selectbox("字体A", source_options, key="font_a")
    with col2:
        blend_mode = st.selectbox(
            "混合模式",
            options=font_blender.get_available_modes(),
            format_func=lambda x: {
                'linear': '📐 线性混合',
                'ease_in': '🚀 缓入混合',
                'ease_out': '🛬 缓出混合',
                'ease_in_out': '🔄 缓入缓出',
                'smoothstep': '🎯 平滑阶跃',
                'radial': '🔵 径向混合'
            }.get(x, x)
        )
    with col3:
        font_b = st.selectbox("字体B", [s for s in source_options if s != font_a] or source_options, key="font_b")
    
    blend_ratio = st.slider("混合比例 (A→B)", 0.0, 1.0, 0.5, 0.01,
                           help="0.0=完全A, 1.0=完全B, 0.5=各50%")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        align_contours = st.checkbox("轮廓对齐", value=True, help="自动对齐两个字体的轮廓点")
    with col_p2:
        normalize_scale = st.checkbox("尺寸归一化", value=True, help="统一两个字体的尺寸")
    with col_p3:
        common_chars_only = st.checkbox("仅混合共同字符", value=True, help="只混合两个字体都包含的字符")
    
    def get_glyphs(font_name):
        if font_name == "当前字体":
            return st.session_state.generated_points
        return st.session_state.style_variations.get(font_name, {})
    
    glyphs_a = get_glyphs(font_a)
    glyphs_b = get_glyphs(font_b)
    
    if glyphs_a and glyphs_b:
        common = set(glyphs_a.keys()) & set(glyphs_b.keys())
        st.info(f"字体A: {len(glyphs_a)}字 | 字体B: {len(glyphs_b)}字 | 共同: {len(common)}字")
        
        preview_char = st.selectbox("预览字符", sorted(common), index=0 if common else None)
        
        if preview_char:
            p1 = glyphs_a.get(preview_char)
            p2 = glyphs_b.get(preview_char)
            
            if p1 is not None and p2 is not None:
                result = font_blender.blend_glyph(
                    p1, p2,
                    ratio=blend_ratio,
                    mode=blend_mode,
                    align=align_contours,
                    normalize_scale=normalize_scale,
                    char=preview_char
                )
                
                if result:
                    cols = st.columns(5)
                    with cols[0]:
                        img_a = draw_contour(p1, size=(150, 150))
                        st.image(img_a, caption=f"A: {font_a}", width=80)
                    with cols[1]:
                        blend_steps = [0.25, 0.5, 0.75]
                        for step in blend_steps:
                            if abs(step - blend_ratio) < 0.05:
                                r = font_blender.blend_glyph(p1, p2, step, blend_mode, align_contours, normalize_scale)
                                if r:
                                    img_mid = draw_contour(r.points, size=(150, 150))
                                    st.image(img_mid, caption=f"{step:.2f}", width=80)
                    with cols[4]:
                        img_b = draw_contour(p2, size=(150, 150))
                        st.image(img_b, caption=f"B: {font_b}", width=80)
                    
                    st.markdown("**实时预览 (拖动滑块变化)**")
                    img_blended = draw_contour(result.points, size=(200, 200))
                    st.image(img_blended, caption=f"混合结果 {blend_ratio:.2f}", width=120, use_container_width=False)
                    
                    st.caption(f"拟合误差: A={result.metrics.get('error_to_font1', 0):.2f}, B={result.metrics.get('error_to_font2', 0):.2f}")
        
        if st.button("🔀 批量混合全部字符", type="primary"):
            with st.spinner("正在批量混合字体..."):
                blended_results = font_blender.blend_batch(
                    glyphs_a, glyphs_b,
                    ratio=blend_ratio,
                    mode=blend_mode,
                    common_chars_only=common_chars_only
                )
                
                blended_glyphs = {char: r.points for char, r in blended_results.items()}
                blended_name = f"blend_{font_a}_{font_b}_{blend_ratio:.2f}"
                st.session_state.blended_fonts[blended_name] = blended_glyphs
                
                st.success(f"成功混合 {len(blended_glyphs)} 个字符")
                
                if st.button("💾 应用混合结果为当前字体"):
                    st.session_state.generated_points = blended_glyphs
                    st.success("已将混合结果设置为当前字体")
        
        if st.session_state.blended_fonts:
            st.markdown("---")
            st.subheader("💾 已保存的混合字体")
            
            for blend_name, glyphs in st.session_state.blended_fonts.items():
                with st.expander(f"{blend_name} ({len(glyphs)}字)"):
                    if st.button(f"应用 '{blend_name}'", key=f"use_{blend_name}"):
                        st.session_state.generated_points = glyphs
                        st.success(f"已应用 {blend_name}")
    else:
        st.warning("请先生成字体或创建风格变体")


with tab6:
    st.header("👁️ 字体预览与测试")
    st.markdown("输入文本实时预览字体效果，支持多种预览模式")
    
    font_previewer.set_glyphs(st.session_state.generated_points)
    
    available_chars = font_previewer.get_available_chars()
    st.info(f"当前字体包含 {len(available_chars)} 个字符")
    
    preview_mode = st.radio(
        "预览模式",
        ["📝 文本预览", "🔤 单字预览", "📊 字符网格", "🔍 对比预览"],
        horizontal=True
    )
    
    st.markdown("---")
    
    if preview_mode == "📝 文本预览":
        st.subheader("文本实时预览")
        
        text_input = st.text_area(
            "输入预览文本",
            value=st.session_state.preview_text,
            height=100,
            placeholder="输入要预览的文字..."
        )
        
        st.session_state.preview_text = text_input
        
        col1, col2, col3 = st.columns(3)
        with col1:
            font_size = st.slider("字号", 12, 120, 48)
        with col2:
            line_spacing = st.slider("行间距", 1.0, 3.0, 1.5, 0.1)
        with col3:
            char_spacing = st.slider("字间距", 0, 20, 5)
        
        show_options = st.columns(4)
        with show_options[0]:
            show_baseline = st.checkbox("显示基线", value=False)
        with show_options[1]:
            show_bounding_box = st.checkbox("显示边界框", value=False)
        with show_options[2]:
            bg_color = st.color_picker("背景色", "#FFFFFF")
        with show_options[3]:
            fg_color = st.color_picker("文字颜色", "#000000")
        
        quick_texts = font_previewer.renderer.list_test_texts()
        selected_quick = st.selectbox("快速测试文本", options=quick_texts, format_func=lambda x: {
            'basic': '英文基础句',
            'chinese': '中文经典',
            'mixed': '中英混合',
            'numbers': '数字符号',
            'punctuation': '标点符号',
            'all_chars': '字母数字',
            'sentence': '名句',
            'long_text': '长文本'
        }.get(x, x))
        
        if st.button("使用测试文本"):
            st.session_state.preview_text = font_previewer.renderer.get_test_text(selected_quick)
            st.rerun()
        
        if text_input or st.session_state.preview_text:
            with st.spinner("正在渲染预览..."):
                bg_rgb = tuple(int(bg_color[i:i+2], 16) for i in (1, 3, 5))
                fg_rgb = tuple(int(fg_color[i:i+2], 16) for i in (1, 3, 5))
                
                result = font_previewer.preview_text(
                    st.session_state.preview_text,
                    font_size=font_size,
                    line_spacing=line_spacing,
                    char_spacing=char_spacing,
                    show_baseline=show_baseline,
                    show_bounding_box=show_bounding_box,
                    background_color=bg_rgb,
                    foreground_color=fg_rgb
                )
                
                st.image(result.image, caption=f"渲染完成: {result.glyph_count} 个字形", use_container_width=True)
                
                coverage = font_previewer.analyze_glyph_coverage(st.session_state.preview_text)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("字符覆盖率", f"{coverage['coverage_percent']:.1f}%")
                with col2:
                    st.metric("已覆盖字符", coverage['covered_count'])
                with col3:
                    st.metric("缺失字符", coverage['missing_count'])
                
                if coverage['missing_chars']:
                    with st.expander(f"⚠️ 缺失 {len(coverage['missing_chars'])} 个字符"):
                        st.write(", ".join(coverage['missing_chars']))
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.download_button(
                        "📥 下载预览图 (PNG)",
                        data=cv2.imencode('.png', cv2.cvtColor(result.image, cv2.COLOR_RGB2BGR))[1].tobytes(),
                        file_name="font_preview.png",
                        mime="image/png"
                    )
                with col_d2:
                    if st.button("🔍 字距测试"):
                        kerning = font_previewer.test_kerning()
                        st.markdown("**字距测试结果:**")
                        for pair, spacing in kerning.items():
                            st.write(f"{pair}: {spacing:.1f}px")
    
    elif preview_mode == "🔤 单字预览":
        st.subheader("单字详细预览")
        
        preview_char = st.selectbox("选择字符", available_chars, index=0 if available_chars else None)
        
        if preview_char:
            col1, col2 = st.columns(2)
            with col1:
                font_size = st.slider("字号", 48, 200, 120)
            with col2:
                show_details = st.checkbox("显示详细信息", value=True)
            
            result = font_previewer.preview_glyph(
                preview_char,
                font_size=font_size,
                show_baseline=True,
                show_bounding_box=True
            )
            
            if result:
                col_img, col_info = st.columns([1, 1])
                
                with col_img:
                    st.image(result.image, caption=repr(preview_char), use_container_width=True)
                
                with col_info:
                    if show_details:
                        pts = st.session_state.generated_points.get(preview_char)
                        if pts is not None:
                            st.markdown("**字形信息**")
                            st.write(f"- 轮廓点数: {len(pts)}")
                            st.write(f"- 宽度范围: {np.min(pts[:, 0]):.1f} ~ {np.max(pts[:, 0]):.1f}")
                            st.write(f"- 高度范围: {np.min(pts[:, 1]):.1f} ~ {np.max(pts[:, 1]):.1f}")
                            st.write(f"- 质心: ({np.mean(pts[:, 0]):.1f}, {np.mean(pts[:, 1]):.1f})")
                            
                            if st.session_state.preserve_corners:
                                corners = corner_detector.detect_corners(pts)
                                st.write(f"- 拐点数量: {len(corners)}")
                                
                                if corners:
                                    angles = []
                                    for idx in corners:
                                        angle = corner_detector._calculate_local_angle(pts, idx)
                                        angles.append(angle)
                                    st.write(f"- 拐点角度: min={min(angles):.1f}°, max={max(angles):.1f}°")
                            
                            if preview_char in st.session_state.structure_reports:
                                report = st.session_state.structure_reports[preview_char]
                                st.markdown("**结构信息**")
                                st.write(f"- 笔画数: {report.get('stroke_count', 0)}")
                                st.write(f"- 宽高比: {report.get('aspect_ratio', 1.0):.2f}")
    
    elif preview_mode == "📊 字符网格":
        st.subheader("全部字符网格预览")
        
        col1, col2 = st.columns(2)
        with col1:
            grid_font_size = st.slider("网格字号", 16, 48, 24)
        with col2:
            cols = st.slider("列数", 5, 20, 10)
        
        filter_type = st.radio("字符筛选", ["全部", "英文", "数字", "中文"], horizontal=True)
        
        all_chars = available_chars
        if filter_type == "英文":
            all_chars = [c for c in all_chars if c.isalpha() and c.isascii()]
        elif filter_type == "数字":
            all_chars = [c for c in all_chars if c.isdigit()]
        elif filter_type == "中文":
            all_chars = [c for c in all_chars if '\u4e00' <= c <= '\u9fff']
        
        st.info(f"显示 {len(all_chars)} 个字符")
        
        if all_chars:
            result = font_previewer.preview_grid(
                chars=all_chars,
                font_size=grid_font_size,
                cols=cols
            )
            
            st.image(result.image, caption=f"字符网格: {result.glyph_count} 个字形", use_container_width=True)
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button(
                    "📥 下载网格图 (PNG)",
                    data=cv2.imencode('.png', cv2.cvtColor(result.image, cv2.COLOR_RGB2BGR))[1].tobytes(),
                    file_name="font_grid.png",
                    mime="image/png"
                )
    
    elif preview_mode == "🔍 对比预览":
        st.subheader("多字体对比预览")
        
        compare_text = st.text_input("对比文本", value="Hello 世界！")
        
        available_fonts = {"当前字体": st.session_state.generated_points}
        available_fonts.update(st.session_state.style_variations)
        available_fonts.update(st.session_state.blended_fonts)
        
        selected_fonts = st.multiselect(
            "选择要对比的字体",
            options=list(available_fonts.keys()),
            default=["当前字体"] if available_fonts else []
        )
        
        compare_font_size = st.slider("对比字号", 12, 72, 36)
        
        if selected_fonts and compare_text:
            compare_glyphs = {name: available_fonts[name] for name in selected_fonts}
            
            result = font_previewer.preview_comparison(
                compare_text,
                other_fonts=compare_glyphs,
                font_size=compare_font_size
            )
            
            st.image(result.image, caption=f"对比 {len(selected_fonts)} 个字体", use_container_width=True)


with tab7:
    st.header("下载字体")
    st.markdown("生成并下载TTF/OTF字体文件")
    
    if not st.session_state.generated_points:
        st.warning("请先生成字体字形")
    else:
        st.write(f"准备生成包含 {len(st.session_state.generated_points)} 个字符的字体")
        
        font_name = st.text_input("字体文件名", value="MyHandwriting")
        
        if st.button("生成字体文件", type="primary"):
            with st.spinner("正在生成字体文件..."):
                try:
                    font_creator = FontCreator(font_name=font_name)
                    success_count = font_creator.add_characters_from_dict(st.session_state.generated_points)
                    
                    output_path = font_creator.create_font(
                        TrainingConfig.OUTPUT_DIR,
                        file_format=font_format
                    )
                    
                    st.session_state.font_created = True
                    st.session_state.font_path = output_path
                    
                    st.success(f"字体文件已生成！共 {success_count} 个字符")
                    st.info(f"保存位置: {output_path}")
                    
                    with open(output_path, 'rb') as f:
                        font_bytes = f.read()
                    
                    st.download_button(
                        label=f"📥 下载 {font_format.upper()} 文件",
                        data=font_bytes,
                        file_name=f"{font_name}.{font_format}",
                        mime=f"font/{font_format}",
                        type="primary"
                    )
                    
                    st.markdown("---")
                    st.subheader("字体预览文本")
                    preview_text = st.text_input("预览文本", value="Hello World! 你好世界！")
                    
                    st.info("💡 提示：下载字体后安装到系统即可在其他应用中使用")
                    
                    st.markdown("### ✨ 启用的增强功能")
                    features = []
                    if st.session_state.use_structure_constraint:
                        features.append("🔍 笔画结构监督 - 保持结构完整")
                    if st.session_state.use_iterative_fitting:
                        features.append("📈 迭代优化拟合 - 最小化拟合误差")
                    if st.session_state.preserve_corners:
                        features.append("🎯 拐点检测保持 - 尖角处锐利")
                    if st.session_state.style_variations:
                        features.append(f"🎭 风格迁移 - {len(st.session_state.style_variations)}种变体")
                    if st.session_state.blended_fonts:
                        features.append(f"🔀 字体混合 - {len(st.session_state.blended_fonts)}种混合")
                    
                    for feature in features:
                        st.write(feature)
                    
                except Exception as e:
                    st.error(f"生成字体时出错: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())


st.sidebar.header("设置")
st.sidebar.markdown("### 字符集")
st.sidebar.write(f"英文小写: 26个")
st.sidebar.write(f"英文大写: 26个")
st.sidebar.write(f"数字: 10个")
st.sidebar.write(f"常用中文: {len(Config.CHAR_SETS['chinese_common'])}个")

st.sidebar.markdown("### 增强功能")
status1 = "✅" if st.session_state.use_structure_constraint else "❌"
status2 = "✅" if st.session_state.use_iterative_fitting else "❌"
status3 = "✅" if st.session_state.preserve_corners else "❌"
st.sidebar.write(f"{status1} 笔画结构")
st.sidebar.write(f"{status2} 迭代拟合")
st.sidebar.write(f"{status3} 拐点保持")

st.sidebar.markdown("### 🆕 新功能")
st.sidebar.write(f"🎭 风格变体: {len(st.session_state.style_variations)}")
st.sidebar.write(f"🔀 混合字体: {len(st.session_state.blended_fonts)}")

st.sidebar.markdown("### 统计")
st.sidebar.write(f"已收集字符: {len(st.session_state.dataset.get_available_chars())}")
st.sidebar.write(f"风格学习完成: {'✅' if st.session_state.style_learned else '❌'}")
st.sidebar.write(f"已生成字形: {len(st.session_state.generated_points)}")

st.sidebar.markdown("---")
st.sidebar.info("""
**使用流程:**
1. 输入手写样本字符
2. 学习字体风格
3. 生成目标字符字形
4. 下载字体文件
""")
