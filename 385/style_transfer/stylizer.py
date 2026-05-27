"""
风格迁移主类
整合VGG19特征提取、感知损失和优化过程
支持分块处理大图、自适应强度调度、宽高比保持
支持视频风格迁移、风格插值、任意风格即时迁移
"""

import torch
import torch.optim as optim
from pathlib import Path
from tqdm import tqdm
import numpy as np

from .vgg import VGG19Extractor
from .losses import PerceptualLoss, TemporalLoss
from .utils import (
    load_image, save_image, tensor_to_pil,
    extract_patches, merge_patches
)
from .styles import get_style_config, PRETRAINED_STYLES
from .video import extract_frames, frames_to_video


class Stylizer:
    """
    图像风格迁移器

    支持:
    - 自定义内容图和风格图
    - 多种预训练风格
    - 风格强度可调
    - 批量处理
    - 大图分块处理（重叠拼贴减少接缝）
    - 自适应强度调度（低强度保留更多纹理）
    - 宽高比保持（黑边填充）
    - 视频风格迁移（帧间稳定避免闪烁）
    - 任意风格即时迁移（无需重新训练）
    - 风格插值（双风格平滑过渡）
    """

    def __init__(
        self,
        device=None,
        image_size=512,
        content_weight=1.0,
        style_weight=1e4,
        tv_weight=1e-6,
        num_steps=500,
        learning_rate=0.03,
        use_patch_processing=True,
        patch_size=512,
        patch_overlap=128,
        use_adaptive_scheduling=True,
        warmup_steps=100,
        content_preservation_factor=0.5,
        keep_aspect_ratio=True,
        use_multi_style=False,
        num_styles=2,
    ):
        """
        初始化风格迁移器

        Args:
            device: 计算设备，None则自动选择
            image_size: 输出图像大小
            content_weight: 内容损失权重
            style_weight: 风格损失权重
            tv_weight: 总变差损失权重
            num_steps: 优化步数
            learning_rate: 学习率
            use_patch_processing: 是否使用分块处理大图
            patch_size: 分块大小
            patch_overlap: 分块重叠大小
            use_adaptive_scheduling: 是否使用自适应强度调度
            warmup_steps: 预热步数
            content_preservation_factor: 内容保留因子
            keep_aspect_ratio: 是否保持宽高比
            use_multi_style: 是否启用多风格插值
            num_styles: 风格数量（用于插值）
        """
        if device is None:
            self.device = torch.device(
                "cuda" if torch.cuda.is_available() else "cpu"
            )
        else:
            self.device = torch.device(device)

        self.image_size = image_size
        self.content_weight = content_weight
        self.style_weight = style_weight
        self.tv_weight = tv_weight
        self.num_steps = num_steps
        self.learning_rate = learning_rate

        self.use_patch_processing = use_patch_processing
        self.patch_size = patch_size
        self.patch_overlap = patch_overlap
        self.keep_aspect_ratio = keep_aspect_ratio
        self.use_multi_style = use_multi_style
        self.num_styles = num_styles

        self.extractor = VGG19Extractor().to(self.device)
        self.perceptual_loss = PerceptualLoss(
            content_weight=content_weight,
            style_weight=style_weight,
            tv_weight=tv_weight,
            use_adaptive_scheduling=use_adaptive_scheduling,
            warmup_steps=warmup_steps,
            content_preservation_factor=content_preservation_factor,
            use_multi_style=use_multi_style,
            num_styles=num_styles,
        ).to(self.device)

        self._style_intensity = 1.0

        self.cached_style_features = {}

    @property
    def style_intensity(self):
        """风格强度 (style_weight / content_weight)"""
        return self._style_intensity

    @style_intensity.setter
    def style_intensity(self, value):
        """设置风格强度"""
        self._style_intensity = max(0.01, value)
        self.style_weight = self.content_weight * self._style_intensity
        self.perceptual_loss.style_weight = self.style_weight
        self.perceptual_loss.target_intensity = self._style_intensity
        if self.perceptual_loss.scheduler is not None:
            self.perceptual_loss.scheduler.target_intensity = self._style_intensity

    def set_style_strength(self, strength):
        """
        设置风格强度

        Args:
            strength: 风格强度值，范围建议 0.1 ~ 100
        """
        self.style_intensity = strength

    def _get_style_features(self, style_image, style_name=None):
        """
        获取风格特征，支持缓存
        实现任意风格即时迁移的核心：只需提取一次风格特征
        """
        cache_key = None

        if style_name is not None:
            cache_key = style_name
        elif isinstance(style_image, (str, Path)):
            cache_key = str(style_image)

        if cache_key and cache_key in self.cached_style_features:
            return self.cached_style_features[cache_key]

        if style_name is not None:
            style_config = get_style_config(style_name)
            self.style_weight = style_config.get(
                "style_weight", self.style_weight
            )
            self.perceptual_loss.style_weight = self.style_weight

            style_path = Path(__file__).parent.parent / "models" / f"{style_name}.jpg"
            if style_path.exists():
                result = load_image(
                    str(style_path), self.image_size, self.device,
                    keep_aspect_ratio=False
                )
                style_img, _, _ = result
            else:
                raise FileNotFoundError(
                    f"风格图像不存在: {style_path}\n"
                    f"请将风格图片放入 models/ 目录"
                )
        elif isinstance(style_image, (str, Path)):
            result = load_image(
                style_image, self.image_size, self.device,
                keep_aspect_ratio=False
            )
            style_img, _, _ = result
        elif isinstance(style_image, torch.Tensor):
            style_img = style_image.to(self.device)
        else:
            raise TypeError("style_image 必须是路径或张量")

        with torch.no_grad():
            style_features = self.extractor.get_style_features(style_img)

        if cache_key:
            self.cached_style_features[cache_key] = style_features

        return style_features

    def _initialize_generated(self, content_img):
        """初始化生成图像"""
        generated = content_img.clone().detach().to(self.device)
        generated.requires_grad_(True)
        return generated

    def _process_single(
        self, content_img, style_features, num_steps, learning_rate,
        verbose, previous_frame=None
    ):
        """处理单张图像或单个块"""
        with torch.no_grad():
            content_features = self.extractor.get_content_features(content_img)

        self.perceptual_loss.set_content_target(content_features)

        if self.use_multi_style and isinstance(style_features, list):
            self.perceptual_loss.set_multi_style_targets(style_features)
        else:
            self.perceptual_loss.set_style_target(style_features)

        self.perceptual_loss.set_training_steps(num_steps)

        if previous_frame is not None:
            self.perceptual_loss.set_previous_frame(previous_frame)
        else:
            self.perceptual_loss.reset_temporal()

        generated = self._initialize_generated(content_img)

        optimizer = optim.LBFGS(
            [generated],
            lr=learning_rate,
            max_iter=num_steps,
            tolerance_grad=1e-7,
            tolerance_change=1e-10,
        )

        iteration = [0]

        if verbose:
            pbar = tqdm(total=num_steps, desc="风格迁移")

        def closure():
            self.perceptual_loss.update_step(iteration[0])

            with torch.no_grad():
                generated.clamp_(0, 1)

            optimizer.zero_grad()

            generated_features = self.extractor.get_all_features(generated)

            loss = self.perceptual_loss(generated_features, generated)

            loss.backward()

            iteration[0] += 1

            if verbose and iteration[0] % 10 == 0:
                pbar.update(10)
                pbar.set_postfix({"loss": f"{loss.item():.4f}"})

            return loss

        optimizer.step(closure)

        if verbose:
            pbar.close()

        with torch.no_grad():
            generated.clamp_(0, 1)

        return generated.detach()

    def _should_use_patches(self, image_tensor):
        """判断是否需要使用分块处理"""
        if not self.use_patch_processing:
            return False

        _, _, height, width = image_tensor.shape
        return height > self.patch_size or width > self.patch_size

    def stylize(
        self,
        content_image,
        style_image=None,
        style_name=None,
        num_steps=None,
        content_weight=None,
        style_weight=None,
        tv_weight=None,
        learning_rate=None,
        verbose=True,
        keep_aspect_ratio=None,
        previous_frame=None,
        interpolation_weights=None,
    ):
        """
        执行风格迁移

        Args:
            content_image: 内容图像路径或张量
            style_image: 风格图像路径或张量（与style_name二选一）
            style_name: 预训练风格名称（与style_image二选一）
            num_steps: 优化步数，None则使用默认值
            content_weight: 内容损失权重
            style_weight: 风格损失权重
            tv_weight: 总变差损失权重
            learning_rate: 学习率
            verbose: 是否显示进度条
            keep_aspect_ratio: 是否保持宽高比，None则使用设置
            previous_frame: 前一帧（用于视频时序一致性）
            interpolation_weights: 风格插值权重 [w1, w2, ...]

        Returns:
            风格化后的图像张量 [1, 3, H, W]
        """
        if style_image is None and style_name is None and not self.use_multi_style:
            raise ValueError("必须指定 style_image 或 style_name 其中之一")

        if content_weight is not None:
            self.content_weight = content_weight
            self.perceptual_loss.content_weight = content_weight
        if style_weight is not None:
            self.style_weight = style_weight
            self.perceptual_loss.style_weight = style_weight
        if tv_weight is not None:
            self.tv_weight = tv_weight
            self.perceptual_loss.tv_weight = tv_weight
        if num_steps is None:
            num_steps = self.num_steps
        if learning_rate is None:
            learning_rate = self.learning_rate
        if keep_aspect_ratio is None:
            keep_aspect_ratio = self.keep_aspect_ratio

        if interpolation_weights is not None:
            self.perceptual_loss.set_interpolation_weights(interpolation_weights)

        padding_info = None
        original_size = None

        if isinstance(content_image, (str, Path)):
            result = load_image(
                content_image, self.image_size, self.device,
                keep_aspect_ratio=keep_aspect_ratio
            )
            content_img, padding_info, original_size = result
        elif isinstance(content_image, torch.Tensor):
            content_img = content_image.to(self.device)
        else:
            raise TypeError("content_image 必须是路径或张量")

        if self.use_multi_style and isinstance(style_image, list):
            style_features_list = []
            for s_img in style_image:
                sf = self._get_style_features(s_img)
                style_features_list.append(sf)
            style_features = style_features_list
        else:
            style_features = self._get_style_features(style_image, style_name)

        use_patches = self._should_use_patches(content_img)

        if use_patches:
            if verbose:
                print(f"检测到大图，使用分块处理 (块大小: {self.patch_size}, 重叠: {self.patch_overlap})")

            patches, positions, original_size_img = extract_patches(
                content_img, self.patch_size, self.patch_overlap
            )

            if verbose:
                print(f"分割为 {len(patches)} 个块")

            processed_patches = []
            for i, patch in enumerate(patches):
                if verbose:
                    print(f"处理块 {i + 1}/{len(patches)}...")

                patch = patch.unsqueeze(0)
                processed = self._process_single(
                    patch, style_features, num_steps, learning_rate,
                    verbose=False, previous_frame=None
                )
                processed_patches.append(processed.squeeze(0))

            generated = merge_patches(
                processed_patches, positions, original_size_img,
                self.patch_overlap, self.device
            )
        else:
            generated = self._process_single(
                content_img, style_features, num_steps, learning_rate,
                verbose, previous_frame=previous_frame
            )

        return generated, padding_info, original_size

    def stylize_and_save(
        self,
        content_image,
        output_path,
        style_image=None,
        style_name=None,
        keep_original_size=False,
        **kwargs,
    ):
        """
        执行风格迁移并保存结果

        Args:
            content_image: 内容图像路径
            output_path: 输出路径
            style_image: 风格图像路径
            style_name: 预训练风格名称
            keep_original_size: 是否保持原始尺寸
            **kwargs: 其他参数传递给 stylize

        Returns:
            保存的文件路径
        """
        generated, padding_info, original_size = self.stylize(
            content_image=content_image,
            style_image=style_image,
            style_name=style_name,
            **kwargs,
        )

        save_kwargs = {}
        if keep_original_size:
            save_kwargs['padding'] = padding_info
            save_kwargs['original_size'] = original_size

        save_image(generated, output_path, **save_kwargs)
        return output_path

    def stylize_batch(
        self,
        content_images,
        output_dir,
        style_image=None,
        style_name=None,
        output_prefix="stylized",
        verbose=True,
        keep_aspect_ratio=None,
        keep_original_size=True,
        **kwargs,
    ):
        """
        批量处理图像

        Args:
            content_images: 内容图像路径列表
            output_dir: 输出目录
            style_image: 风格图像路径
            style_name: 预训练风格名称
            output_prefix: 输出文件名前缀
            verbose: 是否显示进度
            keep_aspect_ratio: 是否保持宽高比
            keep_original_size: 是否保持原始尺寸
            **kwargs: 其他参数传递给 stylize

        Returns:
            输出文件路径列表
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_paths = []

        if verbose:
            iterator = tqdm(
                content_images,
                desc="批量处理",
                unit="img"
            )
        else:
            iterator = content_images

        for idx, content_image in enumerate(iterator):
            if isinstance(content_image, (str, Path)):
                content_image = Path(content_image)
                output_filename = f"{output_prefix}_{idx:04d}.png"
            else:
                output_filename = f"{output_prefix}_{idx:04d}.png"

            output_path = output_dir / output_filename

            try:
                self.stylize_and_save(
                    content_image=str(content_image),
                    output_path=str(output_path),
                    style_image=style_image,
                    style_name=style_name,
                    verbose=False,
                    keep_aspect_ratio=keep_aspect_ratio,
                    keep_original_size=keep_original_size,
                    **kwargs,
                )
                output_paths.append(str(output_path))

                if verbose:
                    iterator.set_postfix({
                        "processed": f"{idx + 1}/{len(content_images)}"
                    })

            except Exception as e:
                print(f"处理 {content_image} 时出错: {e}")

        return output_paths

    def stylize_with_different_strengths(
        self,
        content_image,
        style_image=None,
        style_name=None,
        strengths=None,
        output_dir=None,
        verbose=True,
        **kwargs,
    ):
        """
        使用不同风格强度进行风格迁移

        Args:
            content_image: 内容图像路径
            style_image: 风格图像路径
            style_name: 预训练风格名称
            strengths: 风格强度列表，默认 [1, 5, 10, 50, 100]
            output_dir: 输出目录
            verbose: 是否显示进度
            **kwargs: 其他参数

        Returns:
            结果字典 {强度: 图像张量}
        """
        if strengths is None:
            strengths = [1, 5, 10, 50, 100]

        results = {}

        for strength in strengths:
            if verbose:
                print(f"\n处理强度: {strength}")

            self.style_intensity = strength

            generated, _, _ = self.stylize(
                content_image=content_image,
                style_image=style_image,
                style_name=style_name,
                verbose=verbose,
                **kwargs,
            )

            results[strength] = generated

            if output_dir is not None:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"strength_{strength}.png"
                save_image(generated, str(output_path))

        return results

    def stylize_video(
        self,
        video_path,
        output_path,
        style_image=None,
        style_name=None,
        max_frames=None,
        frame_interval=1,
        temp_dir=None,
        verbose=True,
        use_temporal_loss=True,
        temporal_weight=1e3,
    ):
        """
        风格化整个视频

        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径
            style_image: 风格图像路径
            style_name: 预训练风格名称
            max_frames: 最大处理帧数
            frame_interval: 帧间隔
            temp_dir: 临时目录，用于存储中间帧
            verbose: 是否显示进度
            use_temporal_loss: 是否使用时序损失避免闪烁
            temporal_weight: 时序损失权重

        Returns:
            输出视频路径
        """
        if verbose:
            print(f"提取视频帧: {video_path}")

        frames, fps, frame_size = extract_frames(
            video_path, output_dir=temp_dir,
            max_frames=max_frames, frame_interval=frame_interval
        )

        if verbose:
            print(f"提取到 {len(frames)} 帧，帧率: {fps}fps，尺寸: {frame_size}")
            print("开始风格化帧...")

        if use_temporal_loss:
            self.perceptual_loss.temporal_loss.temporal_weight = temporal_weight
        else:
            self.perceptual_loss.temporal_loss.temporal_weight = 0.0

        stylized_frames = []
        previous_frame = None

        iterator = tqdm(range(len(frames)), desc="风格化帧") if verbose else range(len(frames))

        for i in iterator:
            original_frame = frames[i:i+1].to(self.device)

            stylized_frame, _, _ = self.stylize(
                content_image=original_frame,
                style_image=style_image,
                style_name=style_name,
                verbose=False,
                keep_aspect_ratio=False,
                previous_frame=previous_frame if use_temporal_loss else None,
            )

            stylized_frames.append(stylized_frame.cpu())

            if use_temporal_loss:
                previous_frame = stylized_frame

        if verbose:
            print("合成视频...")

        output_path = frames_to_video(
            stylized_frames, output_path, fps=fps, use_pbar=verbose
        )

        if verbose:
            print(f"视频已保存到: {output_path}")

        return output_path

    def stylize_interpolation(
        self,
        content_image,
        style_images,
        num_frames=30,
        output_dir=None,
        output_prefix="interp",
        verbose=True,
        **kwargs,
    ):
        """
        在多个风格之间进行平滑插值

        Args:
            content_image: 内容图像路径
            style_images: 风格图像列表 [style1, style2, ...]
            num_frames: 插值帧数
            output_dir: 输出目录
            output_prefix: 输出文件名前缀
            verbose: 是否显示进度
            **kwargs: 其他参数传递给 stylize

        Returns:
            结果字典 {插值权重: 图像张量}
        """
        if not self.use_multi_style:
            raise ValueError("请在初始化时设置 use_multi_style=True")

        if len(style_images) < 2:
            raise ValueError("至少需要2个风格图像进行插值")

        if isinstance(content_image, (str, Path)):
            result = load_image(
                content_image, self.image_size, self.device,
                keep_aspect_ratio=self.keep_aspect_ratio
            )
            content_img, _, _ = result
        elif isinstance(content_image, torch.Tensor):
            content_img = content_image.to(self.device)
        else:
            raise TypeError("content_image 必须是路径或张量")

        style_features_list = []
        for style_img in style_images:
            sf = self._get_style_features(style_img)
            style_features_list.append(sf)

        self.perceptual_loss.set_multi_style_targets(style_features_list)

        num_styles = len(style_images)
        results = {}

        iterator = tqdm(range(num_frames), desc="风格插值") if verbose else range(num_frames)

        for i in iterator:
            alpha = i / (num_frames - 1)

            if num_styles == 2:
                weights = [1 - alpha, alpha]
            else:
                weights = []
                for j in range(num_styles):
                    t = alpha * (num_styles - 1) - j
                    if t < 0:
                        w = 1.0 + t
                    elif t < 1:
                        w = 1.0 - t
                    else:
                        w = 0.0
                    weights.append(max(0, w))

                total = sum(weights)
                weights = [w / total for w in weights]

            self.perceptual_loss.set_interpolation_weights(weights)

            generated, _, _ = self.stylize(
                content_image=content_img,
                verbose=False,
                **kwargs,
            )

            results[tuple(weights)] = generated

            if output_dir is not None:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{output_prefix}_{i:04d}.png"
                save_image(generated, str(output_path))

        return results

    def create_style_transition_video(
        self,
        content_image,
        style_images,
        output_path,
        num_frames=60,
        fps=30,
        **kwargs,
    ):
        """
        创建风格过渡视频

        Args:
            content_image: 内容图像
            style_images: 风格图像列表
            output_path: 输出视频路径
            num_frames: 过渡帧数
            fps: 帧率
            **kwargs: 其他参数

        Returns:
            输出视频路径
        """
        if not self.use_multi_style:
            raise ValueError("请在初始化时设置 use_multi_style=True")

        results = self.stylize_interpolation(
            content_image=content_image,
            style_images=style_images,
            num_frames=num_frames,
            verbose=True,
            **kwargs,
        )

        frames = list(results.values())
        output_path = frames_to_video(frames, output_path, fps=fps)

        return output_path

    def clear_style_cache(self):
        """清除风格特征缓存"""
        self.cached_style_features = {}

    def to(self, device):
        """移动到指定设备"""
        self.device = torch.device(device)
        self.extractor = self.extractor.to(self.device)
        self.perceptual_loss = self.perceptual_loss.to(self.device)
        return self
