"""
视频处理模块
支持视频帧提取、帧间一致性损失、视频合成
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from tqdm import tqdm
import numpy as np
from PIL import Image

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    cv2 = None


class TemporalLoss(nn.Module):
    """
    帧间时序一致性损失
    用于视频风格迁移，避免帧间闪烁
    """

    def __init__(self, temporal_weight=1e3, loss_type='l1'):
        """
        初始化时序损失

        Args:
            temporal_weight: 时序损失权重
            loss_type: 损失类型，'l1' 或 'l2'
        """
        super(TemporalLoss, self).__init__()
        self.temporal_weight = temporal_weight
        self.loss_type = loss_type
        self.previous_frame = None

    def set_previous_frame(self, frame):
        """设置前一帧"""
        self.previous_frame = frame.detach()

    def forward(self, current_frame):
        """
        计算时序损失

        Args:
            current_frame: 当前帧张量

        Returns:
            时序损失值
        """
        if self.previous_frame is None:
            return torch.tensor(0.0, device=current_frame.device)

        if self.loss_type == 'l1':
            loss = F.l1_loss(current_frame, self.previous_frame)
        else:
            loss = F.mse_loss(current_frame, self.previous_frame)

        return self.temporal_weight * loss


class OpticalFlowTemporalLoss(nn.Module):
    """
    基于光流的帧间一致性损失
    使用前一帧的光流预测当前帧应该的样子
    """

    def __init__(self, temporal_weight=1e3, flow_method='farneback'):
        """
        初始化光流时序损失

        Args:
            temporal_weight: 时序损失权重
            flow_method: 光流计算方法
        """
        super(OpticalFlowTemporalLoss, self).__init__()
        self.temporal_weight = temporal_weight
        self.flow_method = flow_method
        self.previous_frame = None
        self.previous_original = None

    def set_previous_frames(self, stylized_frame, original_frame):
        """设置前一帧的风格化图像和原始图像"""
        self.previous_frame = stylized_frame.detach()
        self.previous_original = original_frame.detach()

    def _compute_flow(self, prev_original, curr_original):
        """计算光流"""
        if not HAS_CV2:
            return None

        prev_np = prev_original.squeeze(0).cpu().permute(1, 2, 0).numpy()
        curr_np = curr_original.squeeze(0).cpu().permute(1, 2, 0).numpy()

        prev_gray = cv2.cvtColor((prev_np * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        curr_gray = cv2.cvtColor((curr_np * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)

        if self.flow_method == 'farneback':
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, curr_gray, None,
                0.5, 3, 15, 3, 5, 1.2, 0
            )
        else:
            flow = np.zeros((prev_gray.shape[0], prev_gray.shape[1], 2), dtype=np.float32)

        return flow

    def _warp_frame(self, frame, flow):
        """根据光流扭曲帧"""
        if flow is None:
            return frame

        device = frame.device
        flow = torch.from_numpy(flow).float().to(device)

        b, c, h, w = frame.shape
        grid_y, grid_x = torch.meshgrid(
            torch.arange(h, device=device),
            torch.arange(w, device=device),
            indexing='ij'
        )

        grid_x = grid_x.float() + flow[:, :, 0]
        grid_y = grid_y.float() + flow[:, :, 1]

        grid_x = 2.0 * grid_x / (w - 1) - 1.0
        grid_y = 2.0 * grid_y / (h - 1) - 1.0

        grid = torch.stack([grid_x, grid_y], dim=-1).unsqueeze(0)

        warped = F.grid_sample(frame, grid, mode='bilinear', padding_mode='border')
        return warped

    def forward(self, current_frame, current_original):
        """
        计算基于光流的时序损失

        Args:
            current_frame: 当前风格化帧
            current_original: 当前原始帧

        Returns:
            时序损失值
        """
        if self.previous_frame is None or self.previous_original is None:
            return torch.tensor(0.0, device=current_frame.device)

        flow = self._compute_flow(self.previous_original, current_original)
        warped_previous = self._warp_frame(self.previous_frame, flow)

        loss = F.l1_loss(current_frame, warped_previous)
        return self.temporal_weight * loss


def extract_frames(video_path, output_dir=None, max_frames=None, frame_interval=1):
    """
    从视频中提取帧

    Args:
        video_path: 视频路径
        output_dir: 输出目录，None则不保存到磁盘
        max_frames: 最大帧数，None则提取所有帧
        frame_interval: 帧间隔

    Returns:
        frames: 帧列表 [N, 3, H, W]
        fps: 视频帧率
        frame_size: 帧尺寸 (height, width)
    """
    if not HAS_CV2:
        raise ImportError("需要安装 opencv-python: pip install opencv-python")

    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    frame_count = 0
    extracted_count = 0

    with tqdm(total=min(max_frames or total_frames, total_frames // frame_interval),
              desc="提取帧") as pbar:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_tensor = torch.from_numpy(frame_rgb).permute(2, 0, 1).float() / 255.0
                frames.append(frame_tensor.unsqueeze(0))

                if output_dir is not None:
                    frame_pil = Image.fromarray(frame_rgb)
                    frame_pil.save(output_dir / f"frame_{extracted_count:06d}.png")

                extracted_count += 1
                pbar.update(1)

                if max_frames is not None and extracted_count >= max_frames:
                    break

            frame_count += 1

    cap.release()

    if len(frames) > 0:
        frames = torch.cat(frames, dim=0)

    return frames, fps, (height, width)


def frames_to_video(frames, output_path, fps=30.0, use_pbar=True):
    """
    将帧列表合成为视频

    Args:
        frames: 帧列表或张量 [N, 3, H, W]
        output_path: 输出视频路径
        fps: 帧率
        use_pbar: 是否显示进度条
    """
    if not HAS_CV2:
        raise ImportError("需要安装 opencv-python: pip install opencv-python")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(frames, torch.Tensor):
        frames_list = [frames[i] for i in range(frames.shape[0])]
    else:
        frames_list = frames

    if len(frames_list) == 0:
        raise ValueError("帧列表为空")

    first_frame = frames_list[0]
    if first_frame.dim() == 4:
        first_frame = first_frame.squeeze(0)

    height, width = first_frame.shape[1], first_frame.shape[2]

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    if not out.isOpened():
        raise ValueError(f"无法创建视频写入器: {output_path}")

    iterator = tqdm(frames_list, desc="合成视频") if use_pbar else frames_list

    for frame in iterator:
        if frame.dim() == 4:
            frame = frame.squeeze(0)

        frame_np = frame.cpu().permute(1, 2, 0).numpy()
        frame_np = (frame_np * 255).astype(np.uint8)
        frame_bgr = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
        out.write(frame_bgr)

    out.release()
    return output_path


class VideoStylizer:
    """
    视频风格迁移器
    支持帧间时序一致性，避免闪烁
    """

    def __init__(self, stylizer, use_temporal_loss=True, temporal_weight=1e3):
        """
        初始化视频风格迁移器

        Args:
            stylizer: 图像风格迁移器实例
            use_temporal_loss: 是否使用时序损失
            temporal_weight: 时序损失权重
        """
        self.stylizer = stylizer
        self.use_temporal_loss = use_temporal_loss
        self.temporal_weight = temporal_weight

        self.temporal_loss = TemporalLoss(
            temporal_weight=temporal_weight
        ) if use_temporal_loss else None

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

        stylized_frames = []

        if self.temporal_loss is not None:
            self.temporal_loss.previous_frame = None

        iterator = tqdm(range(len(frames)), desc="风格化帧") if verbose else range(len(frames))

        for i in iterator:
            original_frame = frames[i:i+1].to(self.stylizer.device)

            stylized_frame, _, _ = self.stylizer.stylize(
                content_image=original_frame,
                style_image=style_image,
                style_name=style_name,
                verbose=False,
                keep_aspect_ratio=False,
            )

            stylized_frames.append(stylized_frame.cpu())

            if self.temporal_loss is not None:
                self.temporal_loss.set_previous_frame(stylized_frame)

        if verbose:
            print("合成视频...")

        output_path = frames_to_video(
            stylized_frames, output_path, fps=fps, use_pbar=verbose
        )

        if verbose:
            print(f"视频已保存到: {output_path}")

        return output_path
