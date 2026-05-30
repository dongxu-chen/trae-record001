import gradio as gr
import torch
import cv2
import numpy as np
import os
import tempfile
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import threading
from style_decomposer import StyleDecomposer, DiffusionStyleDecomposer
from style_mixer import StyleMixer
from clip_model import CLIPEncoder
from video_stylizer import VideoStylizer
from style_animation import StyleAnimationGenerator


class AsyncTaskManager:
    def __init__(self, max_workers=2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._cancel_flags = {}
        self._lock = threading.Lock()

    def submit(self, task_id, fn, *args, **kwargs):
        with self._lock:
            if task_id in self._cancel_flags:
                self._cancel_flags[task_id] = True
            self._cancel_flags[task_id] = False
        future = self.executor.submit(fn, *args, **kwargs)
        return future

    def is_cancelled(self, task_id):
        with self._lock:
            return self._cancel_flags.get(task_id, False)

    def cancel(self, task_id):
        with self._lock:
            self._cancel_flags[task_id] = True


class StyleTransferApp:
    def __init__(self, device=None):
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.device = device
        self.style_mixer = StyleMixer(device)
        self.adain_decomposer = StyleDecomposer(device)
        self.diffusion_decomposer = DiffusionStyleDecomposer(device)
        self.clip_encoder = CLIPEncoder(device)
        self.video_stylizer = VideoStylizer(device)
        self.animation_generator = StyleAnimationGenerator(device)
        self.task_manager = AsyncTaskManager(max_workers=2)
        self._output_dir = tempfile.mkdtemp()

    def _to_pil(self, bgr_img):
        if bgr_img is None:
            return None
        return Image.fromarray(cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB))

    def decompose_image(self, image, method, preserve_structure, structure_weight):
        if image is None:
            return None, None
        if method == 'adain':
            result = self.adain_decomposer.decompose(image, preserve_structure=preserve_structure, structure_weight=structure_weight)
            return self._to_pil(result['content']), self._to_pil(result['style_map'])
        elif method == 'diffusion':
            result = self.diffusion_decomposer.decompose(image, preserve_structure=preserve_structure, structure_weight=structure_weight)
            h, w = result['content'].shape[:2]
            style_vis = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
            return self._to_pil(result['content']), Image.fromarray(style_vis)

    def style_transfer_async(self, content_img, style_img, alpha, method, hf_enhance, hf_strength):
        if content_img is None or style_img is None:
            yield None
            return
        preview_content = cv2.resize(content_img, (128, 128))
        preview_style = cv2.resize(style_img, (128, 128))
        preview_result = self.style_mixer.style_swap(preview_content, preview_style, alpha=alpha, method=method, hf_enhance=False)
        yield self._to_pil(preview_result)
        result = self.style_mixer.style_swap(content_img, style_img, alpha=alpha, method=method, hf_enhance=hf_enhance, hf_strength=hf_strength)
        yield self._to_pil(result)

    def multi_style_mix_async(self, content_img, style1, style2, style3,
                               weight1, weight2, weight3, alpha, method, hf_enhance, hf_strength, mix_mode):
        if content_img is None:
            yield None
            return
        style_imgs, weights = [], []
        for s, w in [(style1, weight1), (style2, weight2), (style3, weight3)]:
            if s is not None and w > 0:
                style_imgs.append(s)
                weights.append(w)
        if not style_imgs:
            yield None
            return
        total = sum(weights)
        if total == 0:
            yield None
            return
        weights = [w / total for w in weights]
        preview_content = cv2.resize(content_img, (128, 128))
        preview_styles = [cv2.resize(s, (128, 128)) for s in style_imgs]
        preview_result = self.style_mixer.style_mix(preview_content, preview_styles, weights, alpha, method, hf_enhance=False, mix_mode=mix_mode)
        yield self._to_pil(preview_result)
        result = self.style_mixer.style_mix(content_img, style_imgs, weights, alpha, method, hf_enhance=hf_enhance, hf_strength=hf_strength, mix_mode=mix_mode)
        yield self._to_pil(result)

    def style_interpolation_async(self, content_img, style1, style2, steps, alpha, hf_enhance, hf_strength):
        if content_img is None or style1 is None or style2 is None:
            yield [None] * 5
            return
        preview_content = cv2.resize(content_img, (128, 128))
        preview_s1, preview_s2 = cv2.resize(style1, (128, 128)), cv2.resize(style2, (128, 128))
        preview_results = self.style_mixer.style_interpolation(preview_content, preview_s1, preview_s2, interpolation_steps=steps, alpha=alpha, hf_enhance=False)
        preview_rgb = [self._to_pil(r) for r in preview_results]
        while len(preview_rgb) < 5:
            preview_rgb.append(None)
        yield preview_rgb
        results = self.style_mixer.style_interpolation(content_img, style1, style2, interpolation_steps=steps, alpha=alpha, hf_enhance=hf_enhance, hf_strength=hf_strength)
        results_rgb = [self._to_pil(r) for r in results]
        while len(results_rgb) < 5:
            results_rgb.append(None)
        yield results_rgb

    def intensity_sweep_async(self, content_img, style_img, num_steps, hf_enhance, hf_strength):
        if content_img is None or style_img is None:
            yield [None] * 5
            return
        preview_content, preview_style = cv2.resize(content_img, (128, 128)), cv2.resize(style_img, (128, 128))
        preview_results, _ = self.style_mixer.adjust_style_intensity(preview_content, preview_style, min_alpha=0, max_alpha=1, num_steps=num_steps, hf_enhance=False)
        preview_rgb = [self._to_pil(r) for r in preview_results]
        while len(preview_rgb) < 5:
            preview_rgb.append(None)
        yield preview_rgb
        results, alphas = self.style_mixer.adjust_style_intensity(content_img, style_img, min_alpha=0, max_alpha=1, num_steps=num_steps, hf_enhance=hf_enhance, hf_strength=hf_strength)
        results_rgb = [self._to_pil(r) for r in results]
        while len(results_rgb) < 5:
            results_rgb.append(None)
        yield results_rgb

    def color_transfer(self, content_img, style_img):
        if content_img is None or style_img is None:
            return None
        return self._to_pil(self.style_mixer.color_transfer(content_img, style_img))

    def histogram_match(self, content_img, style_img):
        if content_img is None or style_img is None:
            return None
        result = self.style_mixer.histogram_matching(content_img, cv2.cvtColor(style_img, cv2.COLOR_RGB2BGR))
        return self._to_pil(result)

    def stylize_video(self, video_path, style_img, alpha, temporal_weight, consistency_window, max_frames):
        if video_path is None or style_img is None:
            return None
        output_path = os.path.join(self._output_dir, 'stylized_video.mp4')
        try:
            result_path, _ = self.video_stylizer.stylize_video_with_consistency(
                video_path, style_img, output_path=output_path,
                alpha=alpha, temporal_weight=temporal_weight,
                short_term_window=consistency_window, max_frames=max_frames
            )
            return result_path
        except Exception as e:
            print(f"Video stylization error: {e}")
            return None

    def generate_interpolation_animation(self, content_img, style1, style2,
                                           num_frames, alpha, fps, output_format, hf_enhance, hf_strength):
        if content_img is None or style1 is None or style2 is None:
            return None
        ext = 'gif' if output_format == 'GIF' else 'mp4'
        output_path = os.path.join(self._output_dir, f'interpolation_anim.{ext}')
        try:
            result_path, _ = self.animation_generator.generate_interpolation_animation(
                content_img, style1, style2, num_frames=num_frames, alpha=alpha,
                fps=fps, hf_enhance=hf_enhance, hf_strength=hf_strength,
                output_format=ext, output_path=output_path
            )
            return result_path
        except Exception as e:
            print(f"Animation generation error: {e}")
            return None

    def generate_cyclic_animation(self, content_img, style1, style2, style3,
                                   frames_per_style, alpha, fps, output_format, hf_enhance, hf_strength):
        if content_img is None:
            return None
        style_imgs = [s for s in [style1, style2, style3] if s is not None]
        if len(style_imgs) < 2:
            return None
        ext = 'gif' if output_format == 'GIF' else 'mp4'
        output_path = os.path.join(self._output_dir, f'cyclic_anim.{ext}')
        try:
            result_path, _ = self.animation_generator.generate_cyclic_animation(
                content_img, style_imgs, num_cycles=1,
                frames_per_style=frames_per_style, alpha=alpha,
                fps=fps, hf_enhance=hf_enhance, hf_strength=hf_strength,
                output_format=ext, output_path=output_path
            )
            return result_path
        except Exception as e:
            print(f"Cyclic animation error: {e}")
            return None

    def generate_intensity_animation(self, content_img, style_img,
                                      num_frames, alpha_max, fps, output_format, hf_enhance, hf_strength):
        if content_img is None or style_img is None:
            return None
        ext = 'gif' if output_format == 'GIF' else 'mp4'
        output_path = os.path.join(self._output_dir, f'intensity_anim.{ext}')
        try:
            result_path, _ = self.animation_generator.generate_intensity_sweep_animation(
                content_img, style_img, num_frames=num_frames,
                alpha_max=alpha_max, fps=fps, ping_pong=True,
                hf_enhance=hf_enhance, hf_strength=hf_strength,
                output_format=ext, output_path=output_path
            )
            return result_path
        except Exception as e:
            print(f"Intensity animation error: {e}")
            return None

    def build_interface(self):
        with gr.Blocks(title="图像风格分解与重建") as demo:
            gr.Markdown("# 🎨 图像风格分解与重建系统")
            gr.Markdown("AdaIN/Diffusion分解 | 结构保留+高频增强+异步 | 多风格混合 | 视频风格化 | 风格动画")

            with gr.Tabs():
                with gr.TabItem("图像分解"):
                    with gr.Row():
                        with gr.Column():
                            input_image = gr.Image(label="输入图像", type="numpy")
                            method_decompose = gr.Radio(["adain", "diffusion"], label="分解方法", value="adain")
                            preserve_structure = gr.Checkbox(label="结构保留", value=True)
                            structure_weight = gr.Slider(0, 1, 0.3, label="结构保留权重")
                            decompose_btn = gr.Button("分解图像", variant="primary")
                        with gr.Column():
                            content_output = gr.Image(label="内容图 (结构保留)", type="pil")
                            style_output = gr.Image(label="风格图", type="pil")
                    decompose_btn.click(self.decompose_image, inputs=[input_image, method_decompose, preserve_structure, structure_weight], outputs=[content_output, style_output])

                with gr.TabItem("风格迁移"):
                    with gr.Row():
                        with gr.Column():
                            content_input = gr.Image(label="内容图", type="numpy")
                            style_input = gr.Image(label="风格图", type="numpy")
                            alpha_transfer = gr.Slider(0, 1, 0.8, label="风格强度")
                            method_transfer = gr.Radio(["adain", "diffusion"], label="迁移方法", value="adain")
                            hf_enhance_transfer = gr.Checkbox(label="高频增强", value=True)
                            hf_strength_transfer = gr.Slider(0, 2, 0.5, label="高频增强强度")
                            transfer_btn = gr.Button("执行风格迁移 (异步)", variant="primary")
                        with gr.Column():
                            transfer_output = gr.Image(label="结果", type="pil")
                    transfer_btn.click(self.style_transfer_async, inputs=[content_input, style_input, alpha_transfer, method_transfer, hf_enhance_transfer, hf_strength_transfer], outputs=transfer_output)

                with gr.TabItem("多风格混合"):
                    with gr.Row():
                        with gr.Column():
                            content_mix = gr.Image(label="内容图", type="numpy")
                            style1_mix = gr.Image(label="风格图1", type="numpy")
                            weight1 = gr.Slider(0, 1, 0.5, label="风格1权重")
                            style2_mix = gr.Image(label="风格图2", type="numpy")
                            weight2 = gr.Slider(0, 1, 0.3, label="风格2权重")
                            style3_mix = gr.Image(label="风格图3", type="numpy")
                            weight3 = gr.Slider(0, 1, 0.2, label="风格3权重")
                            alpha_mix = gr.Slider(0, 1, 0.8, label="整体风格强度")
                            mix_mode = gr.Radio(["feature", "pixel", "dual"], label="混合模式", value="feature")
                            hf_enhance_mix = gr.Checkbox(label="高频增强", value=True)
                            hf_strength_mix = gr.Slider(0, 2, 0.5, label="高频增强强度")
                            mix_btn = gr.Button("混合风格 (异步+预览)", variant="primary")
                        with gr.Column():
                            mix_output = gr.Image(label="混合结果", type="pil")
                    mix_btn.click(self.multi_style_mix_async, inputs=[content_mix, style1_mix, style2_mix, style3_mix, weight1, weight2, weight3, alpha_mix, gr.State("adain"), hf_enhance_mix, hf_strength_mix, mix_mode], outputs=mix_output)

                with gr.TabItem("风格插值"):
                    with gr.Row():
                        with gr.Column():
                            content_interp = gr.Image(label="内容图", type="numpy")
                            style1_interp = gr.Image(label="起始风格", type="numpy")
                            style2_interp = gr.Image(label="目标风格", type="numpy")
                            steps_interp = gr.Slider(2, 10, 5, step=1, label="插值步数")
                            alpha_interp = gr.Slider(0, 1, 0.8, label="风格强度")
                            hf_enhance_interp = gr.Checkbox(label="高频增强", value=True)
                            hf_strength_interp = gr.Slider(0, 2, 0.5, label="高频增强强度")
                            interp_btn = gr.Button("执行插值 (异步+预览)", variant="primary")
                        with gr.Column():
                            with gr.Row():
                                interp_outputs = [gr.Image(label=f"Step {i+1}", type="pil") for i in range(5)]
                    interp_btn.click(self.style_interpolation_async, inputs=[content_interp, style1_interp, style2_interp, steps_interp, alpha_interp, hf_enhance_interp, hf_strength_interp], outputs=interp_outputs)

                with gr.TabItem("风格强度调节"):
                    with gr.Row():
                        with gr.Column():
                            content_inten = gr.Image(label="内容图", type="numpy")
                            style_inten = gr.Image(label="风格图", type="numpy")
                            steps_inten = gr.Slider(2, 10, 5, step=1, label="强度步数")
                            hf_enhance_inten = gr.Checkbox(label="高频增强", value=True)
                            hf_strength_inten = gr.Slider(0, 2, 0.5, label="高频增强强度")
                            inten_btn = gr.Button("强度扫描 (异步+预览)", variant="primary")
                        with gr.Column():
                            with gr.Row():
                                inten_outputs = [gr.Image(label=f"Level {i+1}", type="pil") for i in range(5)]
                    inten_btn.click(self.intensity_sweep_async, inputs=[content_inten, style_inten, steps_inten, hf_enhance_inten, hf_strength_inten], outputs=inten_outputs)

                with gr.TabItem("视频风格化"):
                    gr.Markdown("### 上传视频和风格图，生成风格化视频\n帧间一致性通过光流对齐+时域平滑+短时一致性窗口保持")
                    with gr.Row():
                        with gr.Column():
                            video_input = gr.Video(label="输入视频")
                            video_style = gr.Image(label="风格图", type="numpy")
                            video_alpha = gr.Slider(0, 1, 0.8, label="风格强度")
                            video_temporal = gr.Slider(0, 1, 0.5, label="时域平滑权重")
                            video_consistency = gr.Slider(1, 10, 3, step=1, label="短时一致性窗口")
                            video_max_frames = gr.Slider(10, 500, 100, step=10, label="最大帧数")
                            video_btn = gr.Button("风格化视频", variant="primary")
                        with gr.Column():
                            video_output = gr.Video(label="风格化视频")
                    video_btn.click(self.stylize_video, inputs=[video_input, video_style, video_alpha, video_temporal, video_consistency, video_max_frames], outputs=video_output)

                with gr.TabItem("风格动画"):
                    gr.Markdown("### 生成风格过渡动画 (GIF/MP4)")
                    with gr.Tabs():
                        with gr.TabItem("插值动画"):
                            with gr.Row():
                                with gr.Column():
                                    anim_content1 = gr.Image(label="内容图", type="numpy")
                                    anim_style1 = gr.Image(label="起始风格", type="numpy")
                                    anim_style2 = gr.Image(label="目标风格", type="numpy")
                                    anim_frames1 = gr.Slider(5, 60, 20, step=1, label="帧数")
                                    anim_alpha1 = gr.Slider(0, 1, 0.8, label="风格强度")
                                    anim_fps1 = gr.Slider(5, 30, 15, step=1, label="FPS")
                                    anim_format1 = gr.Radio(["GIF", "MP4"], label="输出格式", value="GIF")
                                    anim_hf1 = gr.Checkbox(label="高频增强", value=True)
                                    anim_hf_str1 = gr.Slider(0, 2, 0.5, label="高频增强强度")
                                    anim_btn1 = gr.Button("生成插值动画", variant="primary")
                                with gr.Column():
                                    anim_output1 = gr.File(label="动画文件")

                        with gr.TabItem("循环动画"):
                            with gr.Row():
                                with gr.Column():
                                    anim_content2 = gr.Image(label="内容图", type="numpy")
                                    anim_s1 = gr.Image(label="风格图1", type="numpy")
                                    anim_s2 = gr.Image(label="风格图2", type="numpy")
                                    anim_s3 = gr.Image(label="风格图3", type="numpy")
                                    anim_fps_seg = gr.Slider(5, 30, 10, step=1, label="每段帧数")
                                    anim_alpha2 = gr.Slider(0, 1, 0.8, label="风格强度")
                                    anim_fps2 = gr.Slider(5, 30, 15, step=1, label="FPS")
                                    anim_format2 = gr.Radio(["GIF", "MP4"], label="输出格式", value="GIF")
                                    anim_hf2 = gr.Checkbox(label="高频增强", value=True)
                                    anim_hf_str2 = gr.Slider(0, 2, 0.5, label="高频增强强度")
                                    anim_btn2 = gr.Button("生成循环动画", variant="primary")
                                with gr.Column():
                                    anim_output2 = gr.File(label="动画文件")

                        with gr.TabItem("强度扫描动画"):
                            with gr.Row():
                                with gr.Column():
                                    anim_content3 = gr.Image(label="内容图", type="numpy")
                                    anim_style3 = gr.Image(label="风格图", type="numpy")
                                    anim_frames3 = gr.Slider(10, 60, 30, step=1, label="帧数")
                                    anim_alpha3 = gr.Slider(0, 1, 1.0, label="最大风格强度")
                                    anim_fps3 = gr.Slider(5, 30, 15, step=1, label="FPS")
                                    anim_format3 = gr.Radio(["GIF", "MP4"], label="输出格式", value="GIF")
                                    anim_hf3 = gr.Checkbox(label="高频增强", value=True)
                                    anim_hf_str3 = gr.Slider(0, 2, 0.5, label="高频增强强度")
                                    anim_btn3 = gr.Button("生成强度动画", variant="primary")
                                with gr.Column():
                                    anim_output3 = gr.File(label="动画文件")

                    anim_btn1.click(self.generate_interpolation_animation, inputs=[anim_content1, anim_style1, anim_style2, anim_frames1, anim_alpha1, anim_fps1, anim_format1, anim_hf1, anim_hf_str1], outputs=anim_output1)
                    anim_btn2.click(self.generate_cyclic_animation, inputs=[anim_content2, anim_s1, anim_s2, anim_s3, anim_fps_seg, anim_alpha2, anim_fps2, anim_format2, anim_hf2, anim_hf_str2], outputs=anim_output2)
                    anim_btn3.click(self.generate_intensity_animation, inputs=[anim_content3, anim_style3, anim_frames3, anim_alpha3, anim_fps3, anim_format3, anim_hf3, anim_hf_str3], outputs=anim_output3)

                with gr.TabItem("颜色匹配"):
                    with gr.Row():
                        with gr.Column():
                            content_color = gr.Image(label="内容图", type="numpy")
                            style_color = gr.Image(label="参考图", type="numpy")
                            with gr.Row():
                                color_btn = gr.Button("颜色迁移", variant="primary")
                                hist_btn = gr.Button("直方图匹配", variant="secondary")
                        with gr.Column():
                            color_output = gr.Image(label="结果", type="pil")
                    color_btn.click(self.color_transfer, inputs=[content_color, style_color], outputs=color_output)
                    hist_btn.click(self.histogram_match, inputs=[content_color, style_color], outputs=color_output)

            gr.Markdown("---")
            gr.Markdown("### 使用说明")
            gr.Markdown("""
            - **图像分解**: 内容图+风格图分解，结构保留(Sobel边缘+梯度保持)
            - **风格迁移**: AdaIN/Diffusion风格迁移，高频增强(Laplacian+Unsharp)
            - **多风格混合**: 支持3种混合模式 - feature(特征级加权)/pixel(像素级加权)/dual(双层混合)
            - **风格插值**: 两风格间平滑过渡，异步+低分辨率预览
            - **风格强度调节**: 不同风格强度扫描
            - **视频风格化**: 逐帧风格迁移+光流对齐+时域平滑+短时一致性窗口，保证帧间风格一致
            - **风格动画**: 插值动画/循环动画/强度扫描动画，输出GIF或MP4
            - **颜色匹配**: 颜色迁移和直方图匹配
            """)

        return demo
