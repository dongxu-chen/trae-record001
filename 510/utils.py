import os
import cv2
import numpy as np
import torch
from pathlib import Path
from typing import List, Tuple, Optional, Union
from PIL import Image
import subprocess
import shutil


def check_dependencies() -> dict:
    deps = {
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
        "opencv": cv2.__version__,
        "ffmpeg": None,
    }

    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            deps["ffmpeg"] = result.stdout.split("\n")[0]
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    return deps


def frame_to_tensor(frame: np.ndarray, device: str = "cuda",
                   normalize: bool = True) -> torch.Tensor:
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(frame_rgb).float().permute(2, 0, 1).unsqueeze(0)

    if normalize:
        tensor = tensor / 255.0

    return tensor.to(device)


def tensor_to_frame(tensor: torch.Tensor, denormalize: bool = True) -> np.ndarray:
    if tensor.is_cuda:
        tensor = tensor.cpu()

    tensor = tensor.squeeze(0).permute(1, 2, 0)

    if denormalize:
        tensor = tensor * 255.0

    tensor = torch.clamp(tensor, 0, 255)
    frame_rgb = tensor.numpy().astype(np.uint8)
    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    return frame_bgr


def pil_to_tensor(pil_image: Image.Image, device: str = "cuda",
                 normalize: bool = True) -> torch.Tensor:
    array = np.array(pil_image)
    tensor = torch.from_numpy(array).float().permute(2, 0, 1).unsqueeze(0)

    if normalize:
        tensor = tensor / 255.0

    return tensor.to(device)


def tensor_to_pil(tensor: torch.Tensor, denormalize: bool = True) -> Image.Image:
    if tensor.is_cuda:
        tensor = tensor.cpu()

    tensor = tensor.squeeze(0).permute(1, 2, 0)

    if denormalize:
        tensor = tensor * 255.0

    tensor = torch.clamp(tensor, 0, 255)
    array = tensor.numpy().astype(np.uint8)
    return Image.fromarray(array)


def save_frame(frame: np.ndarray, output_path: str):
    cv2.imwrite(output_path, frame)


def load_frame(frame_path: str) -> np.ndarray:
    return cv2.imread(frame_path)


def get_video_info(video_path: str) -> dict:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")

    info = {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "duration": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / cap.get(cv2.CAP_PROP_FPS)
        if cap.get(cv2.CAP_PROP_FPS) > 0 else 0,
    }

    cap.release()
    return info


def extract_frames(video_path: str, output_dir: str,
                   max_frames: Optional[int] = None) -> List[str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")

    frame_paths = []
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret or (max_frames and frame_count >= max_frames):
            break

        frame_path = str(output_path / f"frame_{frame_count:06d}.png")
        cv2.imwrite(frame_path, frame)
        frame_paths.append(frame_path)
        frame_count += 1

    cap.release()
    return frame_paths


def frames_to_video(frame_paths: List[str], output_path: str,
                    fps: float = 30.0, codec: str = "libx264",
                    crf: int = 20, use_ffmpeg: bool = True):
    if len(frame_paths) == 0:
        raise ValueError("No frames to process")

    if use_ffmpeg:
        first_frame = cv2.imread(frame_paths[0])
        height, width = first_frame.shape[:2]

        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-framerate", str(fps),
            "-i", str(Path(frame_paths[0]).parent / "frame_%06d.png"),
            "-c:v", codec,
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            output_path
        ]

        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
    else:
        first_frame = cv2.imread(frame_paths[0])
        height, width = first_frame.shape[:2]

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        for frame_path in frame_paths:
            frame = cv2.imread(frame_path)
            out.write(frame)

        out.release()


def clean_temp_dir(temp_dir: str):
    temp_path = Path(temp_dir)
    if temp_path.exists():
        shutil.rmtree(temp_path)
    temp_path.mkdir(parents=True, exist_ok=True)


def create_padding_mask(height: int, width: int,
                        patch_size: int, device: str = "cuda") -> torch.Tensor:
    pad_h = (patch_size - height % patch_size) % patch_size
    pad_w = (patch_size - width % patch_size) % patch_size

    return torch.nn.functional.pad(
        torch.zeros(1, 3, height, width, device=device),
        (0, pad_w, 0, pad_h),
        mode='reflect'
    )


def process_in_patches(model: torch.nn.Module, tensor: torch.Tensor,
                       patch_size: int = 256, overlap: int = 32) -> torch.Tensor:
    B, C, H, W = tensor.shape
    device = tensor.device

    pad_h = (patch_size - H % patch_size) % patch_size if H % patch_size != 0 else 0
    pad_w = (patch_size - W % patch_size) % patch_size if W % patch_size != 0 else 0

    tensor_padded = torch.nn.functional.pad(tensor, (0, pad_w, 0, pad_h), mode='reflect')
    _, _, H_pad, W_pad = tensor_padded.shape

    output = torch.zeros(B, C, H_pad * model.scale_factor, W_pad * model.scale_factor, device=device)
    weight = torch.zeros_like(output)

    step = patch_size - overlap
    scale = model.scale_factor

    for i in range(0, H_pad - patch_size + 1, step):
        for j in range(0, W_pad - patch_size + 1, step):
            patch = tensor_padded[:, :, i:i + patch_size, j:j + patch_size]

            with torch.no_grad():
                output_patch = model.process_single_frame(patch)

            out_i = i * scale
            out_j = j * scale
            out_size = patch_size * scale

            output[:, :, out_i:out_i + out_size, out_j:out_j + out_size] += output_patch
            weight[:, :, out_i:out_i + out_size, out_j:out_j + out_size] += 1

    output = output / weight.clamp(min=1)
    output = output[:, :, :H * scale, :W * scale]

    return output


class VideoReader:
    def __init__(self, video_path: str):
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")

    def __iter__(self):
        return self

    def __next__(self) -> np.ndarray:
        ret, frame = self.cap.read()
        if not ret:
            self.cap.release()
            raise StopIteration
        return frame

    def read_frame(self) -> Tuple[bool, np.ndarray]:
        return self.cap.read()

    def get_info(self) -> dict:
        return {
            "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": self.cap.get(cv2.CAP_PROP_FPS),
            "total_frames": int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        }

    def set_frame_position(self, pos: int):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, pos)

    def release(self):
        self.cap.release()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class VideoWriter:
    def __init__(self, output_path: str, fps: float, width: int, height: int,
                 codec: str = 'mp4v'):
        fourcc = cv2.VideoWriter_fourcc(*codec)
        self.writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    def write_frame(self, frame: np.ndarray):
        self.writer.write(frame)

    def write_batch(self, frames: List[np.ndarray]):
        for frame in frames:
            self.writer.write(frame)

    def release(self):
        self.writer.release()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class AverageMeter:
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val: float, n: int = 1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


class Timer:
    def __init__(self):
        self.start_time = None
        self.elapsed_time = 0

    def start(self):
        import time
        self.start_time = time.time()

    def stop(self) -> float:
        import time
        if self.start_time is not None:
            self.elapsed_time = time.time() - self.start_time
            self.start_time = None
        return self.elapsed_time

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


if __name__ == "__main__":
    deps = check_dependencies()
    print("Dependencies:")
    for key, value in deps.items():
        print(f"  {key}: {value}")
