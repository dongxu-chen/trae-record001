import os
import io
import uuid
import json
from typing import List, Optional, Dict, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

import numpy as np
import cv2
from PIL import Image

from schemas import ImageInfo


@dataclass
class VideoFrameInfo:
    frame_index: int
    timestamp: float
    is_keyframe: bool
    image_id: Optional[str] = None


@dataclass
class VideoInfo:
    id: str
    filename: str
    width: int
    height: int
    fps: float
    total_frames: int
    duration: float
    uploaded_at: int
    frames_dir: str


class VideoService:
    _instance = None

    def __init__(self, upload_dir: str = "uploads", videos_dir: str = "videos"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        self.videos_dir = Path(videos_dir)
        self.videos_dir.mkdir(exist_ok=True)
        self.frames_dir = self.videos_dir / "frames"
        self.frames_dir.mkdir(exist_ok=True)
        
        self.videos_meta: Dict[str, dict] = {}
        self.frame_annotations: Dict[str, Dict[int, list]] = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def upload_video(self, file_content: bytes, filename: str) -> VideoInfo:
        video_id = str(uuid.uuid4())
        
        ext = Path(filename).suffix.lower()
        if ext not in ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']:
            ext = '.mp4'
        
        saved_filename = f"{video_id}{ext}"
        filepath = self.videos_dir / saved_filename
        
        with open(filepath, 'wb') as f:
            f.write(file_content)
        
        cap = cv2.VideoCapture(str(filepath))
        if not cap.isOpened():
            os.remove(filepath)
            raise ValueError("Cannot open video file")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0
        
        cap.release()
        
        video_frames_dir = self.frames_dir / video_id
        video_frames_dir.mkdir(exist_ok=True)
        
        video_info = VideoInfo(
            id=video_id,
            filename=filename,
            width=width,
            height=height,
            fps=fps,
            total_frames=total_frames,
            duration=duration,
            uploaded_at=int(datetime.now().timestamp() * 1000),
            frames_dir=str(video_frames_dir)
        )
        
        self.videos_meta[video_id] = {
            'filepath': str(filepath),
            'info': video_info,
            'keyframes': set()
        }
        
        self.frame_annotations[video_id] = {}
        
        return video_info

    def extract_keyframes(
        self,
        video_id: str,
        interval: int = 30,
        max_keyframes: int = 100
    ) -> List[VideoFrameInfo]:
        if video_id not in self.videos_meta:
            raise ValueError("Video not found")
        
        video_meta = self.videos_meta[video_id]
        video_info = video_meta['info']
        filepath = video_meta['filepath']
        
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            raise ValueError("Cannot open video file")
        
        keyframes = []
        frame_idx = 0
        extracted = 0
        
        while extracted < max_keyframes:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if not ret:
                break
            
            timestamp = frame_idx / video_info.fps if video_info.fps > 0 else 0
            
            frame_filename = f"key_{frame_idx:08d}.jpg"
            frame_path = Path(video_info.frames_dir) / frame_filename
            
            cv2.imwrite(str(frame_path), frame)
            
            frame_info = VideoFrameInfo(
                frame_index=frame_idx,
                timestamp=timestamp,
                is_keyframe=True,
                image_id=str(frame_path.stem)
            )
            
            keyframes.append(frame_info)
            video_meta['keyframes'].add(frame_idx)
            
            extracted += 1
            frame_idx += interval
        
        cap.release()
        
        return keyframes

    def extract_single_frame(self, video_id: str, frame_idx: int) -> Optional[VideoFrameInfo]:
        if video_id not in self.videos_meta:
            return None
        
        video_meta = self.videos_meta[video_id]
        video_info = video_meta['info']
        filepath = video_meta['filepath']
        
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            return None
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return None
        
        timestamp = frame_idx / video_info.fps if video_info.fps > 0 else 0
        
        frame_filename = f"frame_{frame_idx:08d}.jpg"
        frame_path = Path(video_info.frames_dir) / frame_filename
        
        cv2.imwrite(str(frame_path), frame)
        
        return VideoFrameInfo(
            frame_index=frame_idx,
            timestamp=timestamp,
            is_keyframe=frame_idx in video_meta['keyframes'],
            image_id=str(frame_path.stem)
        )

    def get_frame_image(self, video_id: str, frame_idx: int) -> Optional[Path]:
        if video_id not in self.videos_meta:
            return None
        
        video_info = self.videos_meta[video_id]['info']
        
        key_frame_path = Path(video_info.frames_dir) / f"key_{frame_idx:08d}.jpg"
        if key_frame_path.exists():
            return key_frame_path
        
        frame_path = Path(video_info.frames_dir) / f"frame_{frame_idx:08d}.jpg"
        if frame_path.exists():
            return frame_path
        
        return None

    def interpolate_annotations(
        self,
        video_id: str,
        start_frame: int,
        end_frame: int,
        start_annotations: list,
        end_annotations: list
    ) -> Dict[int, list]:
        if start_frame >= end_frame:
            return {start_frame: start_annotations}
        
        num_frames = end_frame - start_frame + 1
        interpolated = {}
        
        for i in range(num_frames):
            frame_idx = start_frame + i
            alpha = i / (num_frames - 1) if num_frames > 1 else 0
            
            frame_annotations = []
            for start_ann, end_ann in zip(start_annotations, end_annotations):
                if start_ann.get('type') != end_ann.get('type'):
                    continue
                
                interpolated_ann = self._interpolate_annotation(
                    start_ann, end_ann, alpha
                )
                if interpolated_ann:
                    frame_annotations.append(interpolated_ann)
            
            interpolated[frame_idx] = frame_annotations
        
        return interpolated

    def _interpolate_annotation(
        self,
        start_ann: dict,
        end_ann: dict,
        alpha: float
    ) -> Optional[dict]:
        ann_type = start_ann.get('type')
        
        if ann_type == 'rectangle':
            x = start_ann['x'] + (end_ann['x'] - start_ann['x']) * alpha
            y = start_ann['y'] + (end_ann['y'] - start_ann['y']) * alpha
            w = start_ann['width'] + (end_ann['width'] - start_ann['width']) * alpha
            h = start_ann['height'] + (end_ann['height'] - start_ann['height']) * alpha
            
            return {
                **start_ann,
                'x': x,
                'y': y,
                'width': w,
                'height': h
            }
        
        elif ann_type == 'point':
            sx, sy = start_ann['position']['x'], start_ann['position']['y']
            ex, ey = end_ann['position']['x'], end_ann['position']['y']
            
            return {
                **start_ann,
                'position': {
                    'x': sx + (ex - sx) * alpha,
                    'y': sy + (ey - sy) * alpha
                }
            }
        
        elif ann_type == 'polygon':
            start_points = start_ann.get('points', [])
            end_points = end_ann.get('points', [])
            
            if len(start_points) != len(end_points):
                return start_ann
            
            interpolated_points = []
            for sp, ep in zip(start_points, end_points):
                interpolated_points.append({
                    'x': sp['x'] + (ep['x'] - sp['x']) * alpha,
                    'y': sp['y'] + (ep['y'] - sp['y']) * alpha
                })
            
            return {
                **start_ann,
                'points': interpolated_points
            }
        
        return start_ann

    def set_frame_annotations(self, video_id: str, frame_idx: int, annotations: list):
        if video_id in self.frame_annotations:
            self.frame_annotations[video_id][frame_idx] = annotations

    def get_frame_annotations(self, video_id: str, frame_idx: int) -> list:
        if video_id in self.frame_annotations:
            return self.frame_annotations[video_id].get(frame_idx, [])
        return []

    def get_all_annotations(self, video_id: str) -> Dict[int, list]:
        return self.frame_annotations.get(video_id, {})

    def list_videos(self) -> List[VideoInfo]:
        return [meta['info'] for meta in self.videos_meta.values()]

    def get_video_info(self, video_id: str) -> Optional[VideoInfo]:
        if video_id in self.videos_meta:
            return self.videos_meta[video_id]['info']
        return None

    def delete_video(self, video_id: str) -> bool:
        if video_id not in self.videos_meta:
            return False
        
        video_meta = self.videos_meta[video_id]
        filepath = Path(video_meta['filepath'])
        
        if filepath.exists():
            os.remove(filepath)
        
        frames_dir = Path(video_meta['info'].frames_dir)
        if frames_dir.exists():
            import shutil
            shutil.rmtree(frames_dir)
        
        del self.videos_meta[video_id]
        if video_id in self.frame_annotations:
            del self.frame_annotations[video_id]
        
        return True


video_service = VideoService.get_instance()
