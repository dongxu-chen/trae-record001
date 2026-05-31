import os
import numpy as np
import torch
import torch.nn as nn
import cv2
from torchvision.utils import make_grid
from typing import Optional


def slerp(z1: torch.Tensor, z2: torch.Tensor, t: float) -> torch.Tensor:
    z1_norm = z1 / torch.norm(z1, dim=1, keepdim=True)
    z2_norm = z2 / torch.norm(z2, dim=1, keepdim=True)
    omega = torch.acos(torch.clamp((z1_norm * z2_norm).sum(dim=1), -1.0, 1.0))
    sin_omega = torch.sin(omega)
    t = torch.tensor(t, device=z1.device, dtype=torch.float32)

    mask = sin_omega > 1e-6
    res = torch.zeros_like(z1)
    res[mask] = (torch.sin((1.0 - t) * omega[mask]).unsqueeze(1) * z1[mask] +
                 torch.sin(t * omega[mask]).unsqueeze(1) * z2[mask]) / sin_omega[mask].unsqueeze(1)

    res[~mask] = (1.0 - t) * z1[~mask] + t * z2[~mask]
    return res


def lerp(z1: torch.Tensor, z2: torch.Tensor, t: float) -> torch.Tensor:
    return (1.0 - t) * z1 + t * z2


class LatentInterpolationAnimator:
    def __init__(self, config, device: torch.device, output_dir: str = "./animations"):
        self.config = config
        self.device = device
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _tensor_to_cv2(self, img_tensor: torch.Tensor) -> np.ndarray:
        img = (img_tensor + 1.0) / 2.0
        img = img.clamp(0.0, 1.0) * 255.0
        img = img.permute(1, 2, 0).cpu().numpy().astype(np.uint8)
        if img.shape[2] == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return img

    def generate_interpolation_video(
        self,
        generator: nn.Module,
        z1: Optional[torch.Tensor] = None,
        z2: Optional[torch.Tensor] = None,
        num_samples: int = 1,
        num_frames: Optional[int] = None,
        fps: Optional[int] = None,
        output_path: Optional[str] = None,
        use_slerp: bool = True,
        ema_g=None,
    ) -> str:
        if num_frames is None:
            num_frames = self.config.interpolation_frames
        if fps is None:
            fps = self.config.interpolation_fps
        if output_path is None:
            output_path = os.path.join(self.output_dir, "interpolation.mp4")

        g = ema_g.ema if (ema_g is not None) else generator
        g.eval()

        if z1 is None:
            z1 = torch.randn(num_samples, self.config.z_dim, device=self.device)
        if z2 is None:
            z2 = torch.randn(num_samples, self.config.z_dim, device=self.device)

        z1 = z1.to(self.device)
        z2 = z2.to(self.device)

        with torch.no_grad():
            x0 = g(z1)
            size = (x0.shape[3] * 8, x0.shape[2] * 8) if num_samples >= 8 else (x0.shape[3] * num_samples, x0.shape[2])
            size = (size[0] * 8 if num_samples == 64 else size[0], size[1] * 8 if num_samples == 64 else size[1])
            if x0.shape[2] >= 32 and x0.shape[3] >= 32:
                size = (x0.shape[3] * 4, x0.shape[2] * 4) if num_samples == 1 else (x0.shape[3] * 8, x0.shape[2] * 8)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(output_path, fourcc, fps, size)

        interpolation_fn = slerp if use_slerp else lerp

        with torch.no_grad():
            for frame_idx in range(num_frames):
                t = frame_idx / (num_frames - 1)
                z_interp = interpolation_fn(z1, z2, t)
                generated = g(z_interp)

                if generated.shape[1] == 1:
                    generated = generated.repeat(1, 3, 1, 1)

                grid = make_grid(generated, nrow=8 if num_samples >= 8 else num_samples,
                                 normalize=True, value_range=(-1, 1), padding=2)

                frame = self._tensor_to_cv2(grid)
                if frame.shape[:2] != (size[1], size[0]):
                    frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
                video_writer.write(frame)

        video_writer.release()
        g.train()
        return output_path

    def generate_interpolation_gif(
        self,
        generator: nn.Module,
        num_samples: int = 1,
        num_frames: Optional[int] = None,
        fps: Optional[int] = None,
        output_path: Optional[str] = None,
        ema_g=None,
    ) -> str:
        if num_frames is None:
            num_frames = self.config.interpolation_frames
        if fps is None:
            fps = self.config.interpolation_fps
        if output_path is None:
            output_path = os.path.join(self.output_dir, "interpolation.gif")

        g = ema_g.ema if (ema_g is not None) else generator
        g.eval()

        z1 = torch.randn(num_samples, self.config.z_dim, device=self.device)
        z2 = torch.randn(num_samples, self.config.z_dim, device=self.device)

        frames = []
        with torch.no_grad():
            for frame_idx in range(num_frames):
                t = frame_idx / (num_frames - 1)
                z_interp = slerp(z1, z2, t)
                generated = g(z_interp)

                if generated.shape[1] == 1:
                    generated = generated.repeat(1, 3, 1, 1)

                grid = make_grid(generated, nrow=8 if num_samples >= 8 else num_samples,
                                 normalize=True, value_range=(-1, 1), padding=2)
                img = (grid + 1) / 2 * 255
                img = img.clamp(0, 255).permute(1, 2, 0).cpu().numpy().astype(np.uint8)
                frames.append(img)

        g.train()

        from PIL import Image
        pil_frames = [Image.fromarray(frame) for frame in frames]
        pil_frames[0].save(
            output_path,
            save_all=True,
            append_images=pil_frames[1:],
            duration=int(1000 / fps),
            loop=0,
            optimize=False,
        )
        return output_path

    def generate_walkthrough_video(
        self,
        generator: nn.Module,
        num_keypoints: int = 4,
        num_frames_per_segment: Optional[int] = None,
        fps: Optional[int] = None,
        output_path: Optional[str] = None,
        ema_g=None,
    ) -> str:
        if num_frames_per_segment is None:
            num_frames_per_segment = self.config.interpolation_frames // 4
        if fps is None:
            fps = self.config.interpolation_fps
        if output_path is None:
            output_path = os.path.join(self.output_dir, "walkthrough.mp4")

        g = ema_g.ema if (ema_g is not None) else generator
        g.eval()

        keypoints = [torch.randn(1, self.config.z_dim, device=self.device) for _ in range(num_keypoints)]
        keypoints.append(keypoints[0])

        with torch.no_grad():
            x0 = g(keypoints[0])
            size = (x0.shape[3] * 4, x0.shape[2] * 4) if x0.shape[2] >= 32 else (256, 256)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(output_path, fourcc, fps, size)

        with torch.no_grad():
            for k in range(num_keypoints):
                z1 = keypoints[k]
                z2 = keypoints[k + 1]
                for frame_idx in range(num_frames_per_segment):
                    t = frame_idx / (num_frames_per_segment - 1)
                    z_interp = slerp(z1, z2, t)
                    generated = g(z_interp)
                    if generated.shape[1] == 1:
                        generated = generated.repeat(1, 3, 1, 1)
                    grid = make_grid(generated, nrow=1, normalize=True, value_range=(-1, 1), padding=2)
                    frame = self._tensor_to_cv2(grid)
                    if frame.shape[:2] != (size[1], size[0]):
                        frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
                    video_writer.write(frame)

        video_writer.release()
        g.train()
        return output_path
