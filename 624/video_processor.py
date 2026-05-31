import cv2
import numpy as np
from typing import List, Tuple, Dict
import os


class VideoProcessor:
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")
        
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0

    def get_video_info(self) -> Dict:
        return {
            "fps": self.fps,
            "total_frames": self.total_frames,
            "width": self.width,
            "height": self.height,
            "duration": self.duration,
            "resolution": f"{self.width}x{self.height}"
        }

    def extract_frames(self, sample_interval: float = 1.0) -> List[Tuple[int, np.ndarray]]:
        frames = []
        frame_interval = max(1, int(self.fps * sample_interval))
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        frame_count = 0
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append((frame_count, frame_rgb))
            
            frame_count += 1
        
        return frames

    def extract_keyframes(self, num_frames: int = 10) -> List[Tuple[int, np.ndarray]]:
        if self.total_frames <= num_frames:
            return self.extract_frames(sample_interval=1.0)
        
        interval = self.total_frames // num_frames
        frames = []
        
        for i in range(num_frames):
            frame_idx = i * interval
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = self.cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append((frame_idx, frame_rgb))
        
        return frames

    def get_frame_at_timestamp(self, timestamp_sec: float) -> Tuple[int, np.ndarray]:
        frame_idx = int(timestamp_sec * self.fps)
        frame_idx = max(0, min(frame_idx, self.total_frames - 1))
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return (frame_idx, frame_rgb)
        return (frame_idx, None)

    def extract_frames_by_indices(self, indices: List[int]) -> List[Tuple[int, np.ndarray]]:
        frames = []
        for idx in indices:
            idx = max(0, min(idx, self.total_frames - 1))
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = self.cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append((idx, frame_rgb))
        return frames

    def close(self):
        if self.cap is not None:
            self.cap.release()

    def __del__(self):
        self.close()
