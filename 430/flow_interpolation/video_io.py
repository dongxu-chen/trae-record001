import os
import subprocess
import numpy as np
import cv2
import torch
from typing import Tuple, Optional, List, Iterator
from dataclasses import dataclass


@dataclass
class VideoInfo:
    path: str
    width: int
    height: int
    fps: float
    frame_count: int
    duration: float
    codec: str = ''


def get_video_info(video_path: str) -> VideoInfo:
    if not os.path.exists(video_path):
        raise FileNotFoundError(f'Video file not found: {video_path}')
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f'Cannot open video file: {video_path}')
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps > 0 else 0
    
    cap.release()
    
    return VideoInfo(
        path=video_path,
        width=width,
        height=height,
        fps=fps,
        frame_count=frame_count,
        duration=duration
    )


def check_ffmpeg_available() -> bool:
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      capture_output=True, 
                      timeout=5,
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, TimeoutError):
        return False


def frame_to_tensor(frame: np.ndarray, device: str = 'cuda') -> torch.Tensor:
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(frame_rgb).permute(2, 0, 1).float()
    tensor = tensor.unsqueeze(0).to(device)
    return tensor


def tensor_to_frame(tensor: torch.Tensor) -> np.ndarray:
    tensor = tensor.squeeze(0).cpu().clamp(0, 255).byte()
    frame_rgb = tensor.permute(1, 2, 0).numpy()
    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    return frame_bgr


class VideoReader:
    def __init__(self, video_path: str, use_ffmpeg: bool = False):
        self.video_path = video_path
        self.use_ffmpeg = use_ffmpeg and check_ffmpeg_available()
        self.cap = None
        self.info = None
        self._open()
    
    def _open(self):
        self.info = get_video_info(self.video_path)
        if not self.use_ffmpeg:
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                raise ValueError(f'Cannot open video file: {self.video_path}')
    
    def read_frame(self) -> Optional[np.ndarray]:
        if self.use_ffmpeg:
            return self._read_frame_ffmpeg()
        else:
            if self.cap is None:
                return None
            ret, frame = self.cap.read()
            return frame if ret else None
    
    def _read_frame_ffmpeg(self) -> Optional[np.ndarray]:
        raise NotImplementedError('FFmpeg frame reading not implemented yet')
    
    def get_info(self) -> VideoInfo:
        return self.info
    
    def close(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
    
    def __iter__(self) -> Iterator[np.ndarray]:
        return self
    
    def __next__(self) -> np.ndarray:
        frame = self.read_frame()
        if frame is None:
            self.close()
            raise StopIteration
        return frame
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class VideoWriter:
    def __init__(self, output_path: str, width: int, height: int, fps: float,
                 codec: str = 'libx264', pixel_format: str = 'yuv420p',
                 use_ffmpeg: bool = False, crf: int = 18, preset: str = 'medium'):
        self.output_path = output_path
        self.width = width
        self.height = height
        self.fps = fps
        self.codec = codec
        self.pixel_format = pixel_format
        self.use_ffmpeg = use_ffmpeg and check_ffmpeg_available()
        self.crf = crf
        self.preset = preset
        self.writer = None
        self.ffmpeg_process = None
        self._open()
    
    def _open(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.output_path)), exist_ok=True)
        
        if self.use_ffmpeg:
            self._open_ffmpeg()
        else:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.writer = cv2.VideoWriter(
                self.output_path, fourcc, self.fps,
                (self.width, self.height)
            )
            if not self.writer.isOpened():
                raise ValueError(f'Cannot open video writer for: {self.output_path}')
    
    def _open_ffmpeg(self):
        ffmpeg_cmd = [
            'ffmpeg',
            '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{self.width}x{self.height}',
            '-pix_fmt', 'bgr24',
            '-r', str(self.fps),
            '-i', '-',
            '-c:v', self.codec,
            '-pix_fmt', self.pixel_format,
            '-crf', str(self.crf),
            '-preset', self.preset,
            self.output_path
        ]
        
        self.ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    
    def write_frame(self, frame: np.ndarray):
        if frame.shape[0] != self.height or frame.shape[1] != self.width:
            frame = cv2.resize(frame, (self.width, self.height))
        
        if self.use_ffmpeg and self.ffmpeg_process is not None:
            self.ffmpeg_process.stdin.write(frame.tobytes())
        elif self.writer is not None:
            self.writer.write(frame)
    
    def write_tensor(self, tensor: torch.Tensor):
        frame = tensor_to_frame(tensor)
        self.write_frame(frame)
    
    def close(self):
        if self.ffmpeg_process is not None:
            self.ffmpeg_process.stdin.close()
            self.ffmpeg_process.wait()
            self.ffmpeg_process = None
        
        if self.writer is not None:
            self.writer.release()
            self.writer = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def read_frames(video_path: str, start_frame: int = 0, 
               num_frames: Optional[int] = None) -> List[np.ndarray]:
    frames = []
    with VideoReader(video_path) as reader:
        for i, frame in enumerate(reader):
            if i < start_frame:
                continue
            if num_frames is not None and i >= start_frame + num_frames:
                break
            frames.append(frame)
    return frames


def extract_frames_to_folder(video_path: str, output_folder: str,
                            start_frame: int = 0, 
                            num_frames: Optional[int] = None,
                            image_format: str = 'png'):
    os.makedirs(output_folder, exist_ok=True)
    
    with VideoReader(video_path) as reader:
        count = 0
        for i, frame in enumerate(reader):
            if i < start_frame:
                continue
            if num_frames is not None and count >= num_frames:
                break
            
            output_path = os.path.join(output_folder, f'frame_{count:06d}.{image_format}')
            cv2.imwrite(output_path, frame)
            count += 1


def create_video_from_frames(frame_folder: str, output_path: str, fps: float,
                            image_format: str = 'png',
                            use_ffmpeg: bool = False,
                            codec: str = 'libx264',
                            crf: int = 18,
                            preset: str = 'medium'):
    frame_files = sorted([
        f for f in os.listdir(frame_folder) 
        if f.endswith(f'.{image_format}')
    ])
    
    if not frame_files:
        raise ValueError(f'No frames found in {frame_folder}')
    
    first_frame = cv2.imread(os.path.join(frame_folder, frame_files[0]))
    height, width = first_frame.shape[:2]
    
    with VideoWriter(output_path, width, height, fps, 
                    codec=codec, use_ffmpeg=use_ffmpeg,
                    crf=crf, preset=preset) as writer:
        for frame_file in frame_files:
            frame = cv2.imread(os.path.join(frame_folder, frame_file))
            writer.write_frame(frame)
