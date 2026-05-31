import os
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from tqdm import tqdm

from config import Config, TrainingConfig
from preprocessor import ImagePreprocessor, ContourExtractor, CharacterDataset
from contour_smoother import GlyphOptimizer
from font_generator import FontCreator, BaseFontGenerator
from font_model import SimpleFontGenerator, FontVAE, FontTrainer, ContourDataset
from stroke_analyzer import StrokeDecomposer, StructureConstraint, StrokeBasedGenerator
from font_style_transfer import FontStyleTransfer, FontStyle
from font_blender import FontBlender, FontMixer, BlendMode
from font_preview import FontPreviewer, PreviewConfig
from torch.utils.data import DataLoader


class VectorFontGenerator:
    def __init__(self, font_name: str = "MyHandwriting",
                 use_structure_constraint: bool = True,
                 use_iterative_fitting: bool = True,
                 preserve_corners: bool = True):
        self.font_name = font_name
        self.use_structure_constraint = use_structure_constraint
        self.use_iterative_fitting = use_iterative_fitting
        self.preserve_corners = preserve_corners
        
        self.preprocessor = ImagePreprocessor()
        self.contour_extractor = ContourExtractor()
        self.glyph_optimizer = GlyphOptimizer()
        self.base_generator = BaseFontGenerator()
        self.style_generator = SimpleFontGenerator()
        
        if use_structure_constraint:
            self.stroke_decomposer = StrokeDecomposer()
            self.structure_constraint = StructureConstraint()
            self.stroke_generator = StrokeBasedGenerator()
        
        self.style_transfer = FontStyleTransfer()
        self.font_blender = FontBlender()
        self.font_mixer = FontMixer()
        self.font_previewer = FontPreviewer()
        
        self.dataset = CharacterDataset()
        self.font_creator = None
        self.structure_reports = {}
        self.style_variations = {}
        self.blended_fonts = {}
        self.current_glyphs = {}
        
        TrainingConfig.ensure_dirs()
    
    def load_sample_images(self, samples_dir: str) -> int:
        if not os.path.exists(samples_dir):
            print(f"目录不存在: {samples_dir}")
            return 0
        
        success_count = 0
        
        for filename in tqdm(os.listdir(samples_dir), desc="加载样本"):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                char = os.path.splitext(filename)[0]
                if len(char) != 1:
                    continue
                
                filepath = os.path.join(samples_dir, filename)
                image = cv2.imread(filepath)
                
                if image is not None:
                    if self.add_sample_char(char, image):
                        success_count += 1
        
        print(f"成功加载 {success_count} 个样本字符")
        return success_count
    
    def add_sample_char(self, char: str, image: np.ndarray) -> bool:
        try:
            binary = self.preprocessor.preprocess(image)
            contour = self.contour_extractor.extract_contour(binary)
            points = self.contour_extractor.sample_contour_points(contour)
            
            if points is not None:
                if self.use_structure_constraint:
                    report = self.analyze_character_structure(char, binary)
                    self.structure_reports[char] = report
                    
                    if hasattr(self, 'stroke_generator'):
                        self.stroke_generator.learn_stroke_templates(char, binary)
                
                normalized_points = self.contour_extractor.normalize_contour(points)
                self.dataset.add_character(char, binary, normalized_points)
                return True
        except Exception as e:
            print(f"处理字符 '{char}' 时出错: {e}")
        
        return False
    
    def analyze_character_structure(self, char: str, binary_image: np.ndarray) -> dict:
        if not hasattr(self, 'stroke_generator'):
            return {}
        
        report = self.stroke_generator.get_structure_report(char, binary_image)
        
        if not report['valid']:
            print(f"字符 '{char}' 结构警告: {report['issues']}")
        
        return report
    
    def learn_style(self, use_vae: bool = False) -> bool:
        chars, points_list = self.dataset.get_training_data()
        
        if len(chars) < 3:
            print("样本字符不足，至少需要3个字符")
            return False
        
        print(f"开始学习风格，基于 {len(chars)} 个字符...")
        
        if self.use_structure_constraint:
            print("正在分析笔画结构...")
            for char in chars:
                if char not in self.structure_reports:
                    char_data = self.dataset.get_character(char)
                    if char_data and char_data['image'] is not None:
                        self.analyze_character_structure(char, char_data['image'])
        
        char_points_dict = {}
        for char, points in zip(chars, points_list):
            char_points_dict[char] = points
        
        if use_vae:
            return self._learn_style_vae(points_list)
        else:
            return self.style_generator.learn_style(char_points_dict)
    
    def _learn_style_vae(self, points_list: List[np.ndarray]) -> bool:
        try:
            dataset = ContourDataset(points_list)
            dataloader = DataLoader(dataset, batch_size=TrainingConfig.BATCH_SIZE, shuffle=True)
            
            model = FontVAE(latent_dim=TrainingConfig.LATENT_DIM)
            trainer = FontTrainer(model)
            
            print("训练VAE模型...")
            trainer.train(dataloader, epochs=min(50, TrainingConfig.EPOCHS))
            
            model_path = os.path.join(TrainingConfig.MODEL_DIR, f"{self.font_name}_vae.pth")
            trainer.save_model(model_path)
            print(f"模型已保存到: {model_path}")
            
            self.vae_model = model
            self.vae_trainer = trainer
            
            return True
        except Exception as e:
            print(f"VAE训练失败: {e}")
            return False
    
    def generate_glyphs(self, target_chars: List[str], 
                       style_strength: float = 0.5,
                       use_structure_constraint: bool = None,
                       use_iterative_fitting: bool = None,
                       preserve_corners: bool = None) -> Dict[str, np.ndarray]:
        if use_structure_constraint is None:
            use_structure_constraint = self.use_structure_constraint
        if use_iterative_fitting is None:
            use_iterative_fitting = self.use_iterative_fitting
        if preserve_corners is None:
            preserve_corners = self.preserve_corners
        
        generated = {}
        generation_stats = {'total': 0, 'structure_applied': 0, 'corners_detected': 0}
        
        print(f"开始生成 {len(target_chars)} 个字形...")
        if use_structure_constraint:
            print("  - 启用笔画结构约束")
        if use_iterative_fitting:
            print("  - 启用迭代优化拟合")
        if preserve_corners:
            print("  - 启用尖角保持")
        
        for char in tqdm(target_chars, desc="生成字形"):
            generation_stats['total'] += 1
            
            char_data = self.dataset.get_character(char)
            
            if char_data and char_data['points'] is not None:
                base_points = char_data['points']
            else:
                base_points = self.base_generator.generate_base_char(char)
            
            if base_points is not None:
                if hasattr(self.style_generator, 'mean_style'):
                    generated_points = base_points * (1 - style_strength) + self.style_generator.mean_style * style_strength
                else:
                    generated_points = base_points
                
                if use_structure_constraint and hasattr(self, 'structure_constraint'):
                    reference_char = self._find_reference_char(char)
                    if reference_char and reference_char in self.structure_reports:
                        structure = self.stroke_decomposer.analyze_image(
                            self.dataset.get_character(reference_char)['image']
                        )
                        generated_points = self.structure_constraint.apply_constraints(
                            generated_points, structure
                        )
                        
                        if hasattr(self, 'stroke_generator'):
                            generated_points = self.stroke_generator.generate_with_structure(
                                generated_points, reference_char
                            )
                        generation_stats['structure_applied'] += 1
                
                optimized = self.glyph_optimizer.optimize_glyph(
                    generated_points,
                    use_corner_preservation=preserve_corners,
                    use_iterative_fitting=use_iterative_fitting
                )
                
                if optimized:
                    if optimized.get('corners'):
                        generation_stats['corners_detected'] += 1
                    generated[char] = optimized['smoothed_points']
        
        print(f"成功生成 {len(generated)} 个字形")
        print(f"  - 应用结构约束: {generation_stats['structure_applied']}")
        print(f"  - 检测到拐点: {generation_stats['corners_detected']}")
        
        return generated
    
    def _find_reference_char(self, char: str) -> Optional[str]:
        available = list(self.structure_reports.keys())
        if not available:
            return None
        
        if char in available:
            return char
        
        if char.isalpha() and char.islower():
            upper_char = char.upper()
            if upper_char in available:
                return upper_char
        elif char.isalpha() and char.isupper():
            lower_char = char.lower()
            if lower_char in available:
                return lower_char
        
        return available[0]
    
    def create_font_file(self, glyphs: Dict[str, np.ndarray], output_dir: str, 
                        file_format: str = 'ttf') -> Optional[str]:
        if not glyphs:
            print("没有字形数据")
            return None
        
        print(f"创建 {file_format.upper()} 字体文件...")
        
        self.font_creator = FontCreator(font_name=self.font_name)
        success_count = self.font_creator.add_characters_from_dict(glyphs)
        
        print(f"成功添加 {success_count} 个字符到字体")
        
        output_path = self.font_creator.create_font(output_dir, file_format=file_format)
        
        print(f"字体文件已保存到: {output_path}")
        return output_path
    
    def generate_from_samples(self, samples_dir: str, target_chars: List[str],
                             output_dir: str, file_format: str = 'ttf',
                             style_strength: float = 0.5) -> Optional[str]:
        self.load_sample_images(samples_dir)
        
        if not self.learn_style():
            print("风格学习失败")
            return None
        
        glyphs = self.generate_glyphs(target_chars, style_strength)
        
        return self.create_font_file(glyphs, output_dir, file_format)
    
    def get_available_samples(self) -> List[str]:
        return self.dataset.get_available_chars()
    
    def get_sample_count(self) -> int:
        return len(self.dataset.get_available_chars())
    
    def get_structure_report(self, char: str) -> Optional[dict]:
        return self.structure_reports.get(char)
    
    def get_all_structure_reports(self) -> Dict[str, dict]:
        return self.structure_reports
    
    def apply_style_transfer(self, glyphs: Dict[str, np.ndarray],
                            style: str, **kwargs) -> Dict[str, np.ndarray]:
        print(f"应用风格转换: {style}")
        styled = self.style_transfer.transfer_batch(glyphs, style, **kwargs)
        self.style_variations[style] = styled
        print(f"成功转换 {len(styled)} 个字形")
        return styled
    
    def get_available_styles(self) -> List[str]:
        return self.style_transfer.get_available_styles()
    
    def create_style_variations(self, glyphs: Dict[str, np.ndarray],
                               styles: Optional[List[str]] = None) -> Dict[str, Dict[str, np.ndarray]]:
        if styles is None:
            styles = self.get_available_styles()
        
        variations = {}
        for style in tqdm(styles, desc="生成风格变体"):
            variations[style] = self.apply_style_transfer(glyphs, style)
        
        self.style_variations = variations
        return variations
    
    def blend_two_fonts(self, font1_glyphs: Dict[str, np.ndarray],
                       font2_glyphs: Dict[str, np.ndarray],
                       ratio: float = 0.5,
                       mode: str = 'linear',
                       output_name: Optional[str] = None) -> Dict[str, np.ndarray]:
        print(f"混合字体: 比例={ratio:.2f}, 模式={mode}")
        
        blend_results = self.font_blender.blend_batch(
            font1_glyphs, font2_glyphs, ratio, mode
        )
        
        blended = {char: r.points for char, r in blend_results.items()}
        
        if output_name is None:
            output_name = f"blend_{ratio:.2f}_{mode}"
        
        self.blended_fonts[output_name] = blended
        
        avg_error = np.mean([r.metrics.get('error_to_font1', 0) + r.metrics.get('error_to_font2', 0) 
                            for r in blend_results.values()]) / 2
        
        print(f"成功混合 {len(blended)} 个字符，平均误差: {avg_error:.2f}")
        
        return blended
    
    def get_available_blend_modes(self) -> List[str]:
        return self.font_blender.get_available_modes()
    
    def create_blend_sequence(self, font1_glyphs: Dict[str, np.ndarray],
                             font2_glyphs: Dict[str, np.ndarray],
                             char: str, num_steps: int = 10,
                             mode: str = 'linear') -> List[np.ndarray]:
        p1 = font1_glyphs.get(char)
        p2 = font2_glyphs.get(char)
        
        if p1 is None or p2 is None:
            return []
        
        sequence = self.font_blender.create_blend_sequence(p1, p2, num_steps, mode, char)
        return [r.points for r in sequence]
    
    def blend_multiple_fonts(self, font_ratios: Dict[str, float],
                            mode: str = 'linear',
                            output_name: Optional[str] = None) -> Optional[Dict[str, np.ndarray]]:
        print(f"混合 {len(font_ratios)} 个字体")
        
        self.font_mixer._fonts = {}
        for name, glyphs in font_ratios.items():
            if isinstance(glyphs, dict):
                self.font_mixer.add_font(name, glyphs)
        
        ratios = {name: 1.0 for name in font_ratios.keys()}
        
        result = self.font_mixer.mix_many_fonts(ratios, mode, output_name)
        
        if result and output_name:
            self.blended_fonts[output_name] = result
        
        return result
    
    def set_preview_glyphs(self, glyphs: Dict[str, np.ndarray]):
        self.current_glyphs = glyphs
        self.font_previewer.set_glyphs(glyphs)
    
    def preview_text(self, text: str, font_size: int = 48,
                    **kwargs) -> np.ndarray:
        if not self.current_glyphs:
            print("请先设置预览字形")
            return np.zeros((200, 400, 3), dtype=np.uint8)
        
        result = self.font_previewer.preview_text(text, font_size=font_size, **kwargs)
        return result.image
    
    def preview_glyph(self, char: str, font_size: int = 120,
                     **kwargs) -> Optional[np.ndarray]:
        if not self.current_glyphs:
            print("请先设置预览字形")
            return None
        
        result = self.font_previewer.preview_glyph(char, font_size=font_size, **kwargs)
        return result.image if result else None
    
    def preview_grid(self, chars: Optional[List[str]] = None,
                    font_size: int = 32, cols: int = 10,
                    **kwargs) -> np.ndarray:
        if not self.current_glyphs:
            print("请先设置预览字形")
            return np.zeros((400, 600, 3), dtype=np.uint8)
        
        result = self.font_previewer.preview_grid(chars, font_size=font_size, cols=cols, **kwargs)
        return result.image
    
    def preview_comparison(self, text: str,
                          other_fonts: Dict[str, Dict[str, np.ndarray]],
                          font_size: int = 36, **kwargs) -> np.ndarray:
        if not self.current_glyphs:
            print("请先设置预览字形")
            return np.zeros((400, 600, 3), dtype=np.uint8)
        
        result = self.font_previewer.preview_comparison(text, other_fonts, font_size=font_size, **kwargs)
        return result.image
    
    def analyze_coverage(self, text: str) -> Dict:
        if not self.current_glyphs:
            return {}
        return self.font_previewer.analyze_glyph_coverage(text)
    
    def test_kerning(self) -> Dict[str, float]:
        if not self.current_glyphs:
            return {}
        return self.font_previewer.test_kerning()
    
    def save_preview_image(self, image: np.ndarray, output_path: str):
        self.font_previewer.export_preview(
            type('PreviewResult', (), {'image': image})(), output_path
        )
        print(f"预览图已保存到: {output_path}")


def demo_enhanced_features():
    print("=" * 60)
    print("矢量字体生成器 - 增强功能演示")
    print("=" * 60)
    
    generator = VectorFontGenerator(
        font_name="EnhancedFont",
        use_structure_constraint=True,
        use_iterative_fitting=True,
        preserve_corners=True
    )
    
    samples_dir = TrainingConfig.SAMPLES_DIR
    output_dir = TrainingConfig.OUTPUT_DIR
    
    print(f"\n样本目录: {samples_dir}")
    print(f"输出目录: {output_dir}")
    
    if not os.path.exists(samples_dir):
        os.makedirs(samples_dir)
        print(f"\n⚠️  样本目录为空，请将手写字符图片放入: {samples_dir}")
        print("   图片文件名应为字符本身 (例如: 'a.png', 'B.jpg', '中.png')")
        return
    
    sample_count = generator.load_sample_images(samples_dir)
    
    if sample_count < 3:
        print(f"\n⚠️  样本数量不足 ({sample_count})，请至少提供3个样本字符")
        return
    
    print("\n" + "=" * 60)
    print("笔画结构分析报告")
    print("=" * 60)
    
    reports = generator.get_all_structure_reports()
    for char, report in reports.items():
        print(f"\n字符: {char}")
        print(f"  笔画数: {report.get('stroke_count', 0)}")
        print(f"  宽高比: {report.get('aspect_ratio', 1.0):.2f}")
        print(f"  结构有效: {report.get('valid', False)}")
        if not report.get('valid', True):
            print(f"  问题: {report.get('issues', [])}")
        if 'strokes' in report:
            stroke_types = [s['type'] for s in report['strokes']]
            print(f"  笔画类型: {', '.join(stroke_types)}")
    
    generator.learn_style()
    
    target_chars = list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    
    glyphs = generator.generate_glyphs(
        target_chars, 
        style_strength=0.5,
        use_structure_constraint=True,
        use_iterative_fitting=True,
        preserve_corners=True
    )
    
    output_path = generator.create_font_file(glyphs, output_dir, file_format='ttf')
    
    if output_path:
        print(f"\n✅ 字体生成完成!")
        print(f"   文件路径: {output_path}")
        print("\n增强功能已启用:")
        print("   ✅ 中文笔画分解监督 - 保持结构完整")
        print("   ✅ 迭代优化拟合 - 最小化拟合误差")
        print("   ✅ 拐点检测保持 - 尖角处保持锐利")


def run_web_app():
    os.system("streamlit run app.py")


def demo_style_transfer():
    print("=" * 60)
    print("字体风格迁移演示")
    print("=" * 60)
    
    generator = VectorFontGenerator(font_name="StyleDemo")
    
    samples_dir = TrainingConfig.SAMPLES_DIR
    
    if not os.path.exists(samples_dir) or len(os.listdir(samples_dir)) == 0:
        print("\n⚠️  请先添加样本字符到:", samples_dir)
        return
    
    sample_count = generator.load_sample_images(samples_dir)
    
    if sample_count < 3:
        print(f"\n⚠️  样本数量不足 ({sample_count})")
        return
    
    generator.learn_style()
    
    target_chars = list("ABCDEFabcdef012345")
    glyphs = generator.generate_glyphs(target_chars, style_strength=0.5)
    
    print("\n可用风格:", ", ".join(generator.get_available_styles()))
    
    bold_glyphs = generator.apply_style_transfer(glyphs, 'bold')
    italic_glyphs = generator.apply_style_transfer(glyphs, 'italic')
    handwriting_glyphs = generator.apply_style_transfer(glyphs, 'handwriting')
    
    print("\n✅ 风格迁移完成!")
    print(f"   - 原始: {len(glyphs)} 字")
    print(f"   - 粗体: {len(bold_glyphs)} 字")
    print(f"   - 斜体: {len(italic_glyphs)} 字")
    print(f"   - 手写体: {len(handwriting_glyphs)} 字")
    
    generator.set_preview_glyphs(bold_glyphs)
    preview_img = generator.preview_text("ABCDEF 012345", font_size=48)
    preview_path = os.path.join(TrainingConfig.OUTPUT_DIR, "style_preview.png")
    generator.save_preview_image(preview_img, preview_path)


def demo_font_blending():
    print("=" * 60)
    print("字体混合演示")
    print("=" * 60)
    
    generator = VectorFontGenerator(font_name="BlendDemo")
    
    samples_dir = TrainingConfig.SAMPLES_DIR
    
    if not os.path.exists(samples_dir) or len(os.listdir(samples_dir)) == 0:
        print("\n⚠️  请先添加样本字符到:", samples_dir)
        return
    
    sample_count = generator.load_sample_images(samples_dir)
    
    if sample_count < 3:
        print(f"\n⚠️  样本数量不足 ({sample_count})")
        return
    
    generator.learn_style()
    
    target_chars = list("ABCDEFabcdef012345")
    base_glyphs = generator.generate_glyphs(target_chars, style_strength=0.3)
    bold_glyphs = generator.apply_style_transfer(base_glyphs, 'bold')
    
    print("\n可用混合模式:", ", ".join(generator.get_available_blend_modes()))
    
    blended_50 = generator.blend_two_fonts(
        base_glyphs, bold_glyphs,
        ratio=0.5, mode='linear',
        output_name='normal_to_bold_50'
    )
    
    blended_25 = generator.blend_two_fonts(
        base_glyphs, bold_glyphs,
        ratio=0.25, mode='ease_in_out',
        output_name='normal_to_bold_25'
    )
    
    print("\n✅ 字体混合完成!")
    print(f"   - 50%混合: {len(blended_50)} 字")
    print(f"   - 25%混合: {len(blended_25)} 字")
    
    char = 'A'
    sequence = generator.create_blend_sequence(base_glyphs, bold_glyphs, char, num_steps=5)
    print(f"\n字符 '{char}' 渐变序列 ({len(sequence)} 帧)")


def demo_preview():
    print("=" * 60)
    print("字体预览与测试演示")
    print("=" * 60)
    
    generator = VectorFontGenerator(font_name="PreviewDemo")
    
    samples_dir = TrainingConfig.SAMPLES_DIR
    
    if not os.path.exists(samples_dir) or len(os.listdir(samples_dir)) == 0:
        print("\n⚠️  请先添加样本字符到:", samples_dir)
        return
    
    sample_count = generator.load_sample_images(samples_dir)
    
    if sample_count < 3:
        print(f"\n⚠️  样本数量不足 ({sample_count})")
        return
    
    generator.learn_style()
    
    target_chars = list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    glyphs = generator.generate_glyphs(target_chars, style_strength=0.5)
    
    generator.set_preview_glyphs(glyphs)
    
    test_text = "The quick brown fox jumps over the lazy dog 1234567890"
    
    coverage = generator.analyze_coverage(test_text)
    print(f"\n文本覆盖率: {coverage['coverage_percent']:.1f}%")
    print(f"缺失字符: {coverage['missing_chars']}")
    
    text_preview = generator.preview_text(test_text, font_size=48)
    text_path = os.path.join(TrainingConfig.OUTPUT_DIR, "text_preview.png")
    generator.save_preview_image(text_preview, text_path)
    
    grid_preview = generator.preview_grid(cols=13, font_size=24)
    grid_path = os.path.join(TrainingConfig.OUTPUT_DIR, "grid_preview.png")
    generator.save_preview_image(grid_preview, grid_path)
    
    kerning = generator.test_kerning()
    print("\n字距测试:")
    for pair, spacing in list(kerning.items())[:5]:
        print(f"  {pair}: {spacing:.1f}px")
    
    print("\n✅ 预览演示完成!")
    print(f"   文本预览: {text_path}")
    print(f"   网格预览: {grid_path}")


def demo_all_new_features():
    print("=" * 60)
    print("所有新功能综合演示")
    print("=" * 60)
    
    generator = VectorFontGenerator(
        font_name="AllFeaturesDemo",
        use_structure_constraint=True,
        use_iterative_fitting=True,
        preserve_corners=True
    )
    
    samples_dir = TrainingConfig.SAMPLES_DIR
    
    if not os.path.exists(samples_dir) or len(os.listdir(samples_dir)) == 0:
        print("\n⚠️  请先添加样本字符到:", samples_dir)
        return
    
    sample_count = generator.load_sample_images(samples_dir)
    
    if sample_count < 3:
        print(f"\n⚠️  样本数量不足 ({sample_count})")
        return
    
    generator.learn_style()
    
    target_chars = list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    glyphs = generator.generate_glyphs(target_chars, style_strength=0.5)
    
    print("\n" + "=" * 60)
    print("1. 风格迁移")
    print("=" * 60)
    styles = ['bold', 'italic', 'condensed']
    for style in styles:
        styled = generator.apply_style_transfer(glyphs, style)
        print(f"  ✅ {style}: {len(styled)} 字")
    
    print("\n" + "=" * 60)
    print("2. 字体混合")
    print("=" * 60)
    if 'bold' in generator.style_variations:
        blended = generator.blend_two_fonts(
            glyphs, generator.style_variations['bold'],
            ratio=0.5, mode='ease_in_out'
        )
        print(f"  ✅ 50%混合: {len(blended)} 字")
    
    print("\n" + "=" * 60)
    print("3. 预览测试")
    print("=" * 60)
    generator.set_preview_glyphs(glyphs)
    coverage = generator.analyze_coverage("Hello World 123")
    print(f"  ✅ 覆盖率: {coverage['coverage_percent']:.1f}%")
    
    output_path = generator.create_font_file(glyphs, TrainingConfig.OUTPUT_DIR, 'ttf')
    
    print("\n" + "=" * 60)
    print("所有功能演示完成!")
    print("=" * 60)
    print(f"字体文件: {output_path}")
    print(f"风格变体: {len(generator.style_variations)} 种")
    print(f"混合字体: {len(generator.blended_fonts)} 种")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'demo':
            demo_basic_usage()
        elif sys.argv[1] == 'demo-enhanced':
            demo_enhanced_features()
        elif sys.argv[1] == 'demo-style':
            demo_style_transfer()
        elif sys.argv[1] == 'demo-blend':
            demo_font_blending()
        elif sys.argv[1] == 'demo-preview':
            demo_preview()
        elif sys.argv[1] == 'demo-all':
            demo_all_new_features()
        elif sys.argv[1] == 'list-styles':
            generator = VectorFontGenerator()
            print("可用风格:", ", ".join(generator.get_available_styles()))
            print("混合模式:", ", ".join(generator.get_available_blend_modes()))
    else:
        print("启动Web界面...")
        run_web_app()


def demo_basic_usage():
    print("=" * 50)
    print("矢量字体生成器 - 基本使用演示")
    print("=" * 50)
    
    generator = VectorFontGenerator(font_name="DemoFont")
    
    samples_dir = TrainingConfig.SAMPLES_DIR
    output_dir = TrainingConfig.OUTPUT_DIR
    
    print(f"\n样本目录: {samples_dir}")
    print(f"输出目录: {output_dir}")
    
    if not os.path.exists(samples_dir):
        os.makedirs(samples_dir)
        print(f"\n⚠️  样本目录为空，请将手写字符图片放入: {samples_dir}")
        print("   图片文件名应为字符本身 (例如: 'a.png', 'B.jpg', '中.png')")
        return
    
    sample_count = generator.load_sample_images(samples_dir)
    
    if sample_count < 3:
        print(f"\n⚠️  样本数量不足 ({sample_count})，请至少提供3个样本字符")
        return
    
    generator.learn_style()
    
    target_chars = list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    
    glyphs = generator.generate_glyphs(target_chars, style_strength=0.5)
    
    output_path = generator.create_font_file(glyphs, output_dir, file_format='ttf')
    
    if output_path:
        print(f"\n✅ 字体生成完成!")
        print(f"   文件路径: {output_path}")
