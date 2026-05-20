import os
import subprocess
import json
from typing import List, Dict, Optional, Tuple
from config.config import FFMPEG_PATH, FFPROBE_PATH, FRAMES_DIR, FRAME_INTERVAL, MAX_FRAMES_PER_VIDEO
from models import FrameModel


class FrameExtractor:
    def __init__(self, video_path: str, video_id: int):
        self.video_path = video_path
        self.video_id = video_id
        self.video_info = None
        self.frames: List[Dict] = []
        self.scene_changes: List[float] = []
        self.output_dir = os.path.join(FRAMES_DIR, str(video_id))
        os.makedirs(self.output_dir, exist_ok=True)

    def get_video_info(self) -> Dict:
        cmd = [
            FFPROBE_PATH,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            self.video_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                video_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), None)
                
                if video_stream:
                    duration = float(data.get('format', {}).get('duration', 0))
                    width = int(video_stream.get('width', 0))
                    height = int(video_stream.get('height', 0))
                    bit_rate = int(data.get('format', {}).get('bit_rate', 0))
                    
                    self.video_info = {
                        'duration': duration,
                        'width': width,
                        'height': height,
                        'bit_rate': bit_rate,
                        'codec': video_stream.get('codec_name', ''),
                        'fps': self._parse_fps(video_stream.get('r_frame_rate', '0/0'))
                    }
                    return self.video_info
        except Exception as e:
            raise RuntimeError(f"Failed to get video info: {str(e)}")
        
        raise RuntimeError("Failed to get video info")

    def _parse_fps(self, fps_str: str) -> float:
        try:
            num, den = map(int, fps_str.split('/'))
            return num / den if den != 0 else 0.0
        except:
            return 0.0

    def detect_scene_changes(self, threshold: float = 0.3) -> List[float]:
        cmd = [
            FFMPEG_PATH,
            '-i', self.video_path,
            '-vf', f'select=\'gt(scene,{threshold})\',showinfo',
            '-f', 'null',
            '-'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            output = result.stderr
            
            import re
            timestamps = []
            pattern = r'pts_time:(\d+\.\d+)'
            matches = re.findall(pattern, output)
            
            for match in matches:
                timestamps.append(float(match))
            
            self.scene_changes = sorted(set(timestamps))
            return self.scene_changes
            
        except Exception as e:
            print(f"Scene detection warning: {e}")
            return []

    def _calculate_dynamic_intervals(self, base_interval: float, scene_changes: List[float],
                                    min_interval: float = 0.5, max_interval: float = 5.0,
                                    scene_window: float = 2.0) -> List[Tuple[float, float]]:
        duration = self.video_info['duration']
        intervals = []
        current_time = 0.0
        
        while current_time < duration:
            next_scene = None
            for scene_time in scene_changes:
                if scene_time > current_time:
                    next_scene = scene_time
                    break
            
            if next_scene and (next_scene - current_time) <= scene_window:
                interval = max(min_interval, base_interval / 2)
            else:
                interval = min(max_interval, base_interval)
            
            intervals.append((current_time, interval))
            current_time += interval
        
        return intervals

    def extract_frames_dynamic(self, base_interval: float = None, min_interval: float = 0.5,
                              max_interval: float = 5.0, scene_threshold: float = 0.3,
                              scene_window: float = 2.0) -> List[Dict]:
        if not self.video_info:
            self.get_video_info()

        base_interval = base_interval or FRAME_INTERVAL
        duration = self.video_info['duration']
        
        if duration <= 0:
            raise RuntimeError("Invalid video duration")

        print("检测场景切换中...")
        scene_changes = self.detect_scene_changes(threshold=scene_threshold)
        print(f"检测到 {len(scene_changes)} 个场景切换点")

        intervals = self._calculate_dynamic_intervals(
            base_interval=base_interval,
            scene_changes=scene_changes,
            min_interval=min_interval,
            max_interval=max_interval,
            scene_window=scene_window
        )

        if len(intervals) > MAX_FRAMES_PER_VIDEO:
            print(f"帧数过多，限制为 {MAX_FRAMES_PER_VIDEO} 帧")
            intervals = intervals[:MAX_FRAMES_PER_VIDEO]

        select_expr = self._build_select_expression(intervals)
        
        pattern = os.path.join(self.output_dir, f'frame_{self.video_id}_%06d.jpg')
        
        cmd = [
            FFMPEG_PATH,
            '-i', self.video_path,
            '-vf', f"select='{select_expr}'",
            '-vsync', 'vfr',
            '-q:v', '2',
            pattern,
            '-y'
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=300)
        except subprocess.TimeoutExpired:
            raise RuntimeError("Frame extraction timed out")
        except Exception as e:
            raise RuntimeError(f"Frame extraction failed: {str(e)}")

        self._collect_dynamic_frames(intervals)
        return self.frames

    def _build_select_expression(self, intervals: List[Tuple[float, float]]) -> str:
        conditions = []
        for i, (timestamp, _) in enumerate(intervals):
            if i == 0:
                conditions.append(f"gte(t,{timestamp})")
            else:
                prev_timestamp = intervals[i-1][0]
                conditions.append(f"gte(t,{timestamp})*lt(t,{prev_timestamp})")
        
        return '+'.join(conditions)

    def _collect_dynamic_frames(self, intervals: List[Tuple[float, float]]):
        self.frames = []
        frame_files = sorted([f for f in os.listdir(self.output_dir) if f.startswith('frame_') and f.endswith('.jpg')])

        for idx, filename in enumerate(frame_files):
            if idx >= len(intervals):
                break
                
            filepath = os.path.join(self.output_dir, filename)
            timestamp = intervals[idx][0]
            interval_used = intervals[idx][1]
            
            try:
                file_size = os.path.getsize(filepath)
            except:
                file_size = 0

            is_near_scene = False
            for scene_time in self.scene_changes:
                if abs(timestamp - scene_time) <= 2.0:
                    is_near_scene = True
                    break

            frame_info = {
                'frame_number': idx + 1,
                'timestamp': timestamp,
                'interval_used': interval_used,
                'is_near_scene': is_near_scene,
                'image_path': filepath,
                'width': self.video_info.get('width'),
                'height': self.video_info.get('height'),
                'file_size': file_size
            }

            try:
                FrameModel.create(
                    video_id=self.video_id,
                    frame_number=frame_info['frame_number'],
                    timestamp=frame_info['timestamp'],
                    image_path=frame_info['image_path'],
                    width=frame_info['width'],
                    height=frame_info['height'],
                    file_size=frame_info['file_size']
                )
            except Exception as e:
                print(f"Warning: Failed to save frame info to DB: {e}")

            self.frames.append(frame_info)

    def extract_frames(self, interval: float = None) -> List[Dict]:
        return self.extract_frames_dynamic(base_interval=interval)

    def extract_keyframes(self) -> List[Dict]:
        pattern = os.path.join(self.output_dir, f'keyframe_{self.video_id}_%06d.jpg')
        
        cmd = [
            FFMPEG_PATH,
            '-i', self.video_path,
            '-vf', "select='eq(pict_type,PICT_TYPE_I)'",
            '-vsync', 'vfr',
            '-q:v', '2',
            pattern,
            '-y'
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=300)
        except Exception as e:
            raise RuntimeError(f"Keyframe extraction failed: {str(e)}")

        self._collect_keyframes()
        return self.frames

    def _collect_keyframes(self):
        self.frames = []
        frame_files = sorted([f for f in os.listdir(self.output_dir) if f.startswith('keyframe_') and f.endswith('.jpg')])
        
        timestamps = self._get_keyframe_timestamps()

        for idx, filename in enumerate(frame_files):
            filepath = os.path.join(self.output_dir, filename)
            timestamp = timestamps[idx] if idx < len(timestamps) else idx * 2.0

            try:
                file_size = os.path.getsize(filepath)
            except:
                file_size = 0

            frame_info = {
                'frame_number': idx + 1,
                'timestamp': timestamp,
                'image_path': filepath,
                'width': self.video_info.get('width') if self.video_info else None,
                'height': self.video_info.get('height') if self.video_info else None,
                'file_size': file_size
            }
            self.frames.append(frame_info)

    def _get_keyframe_timestamps(self) -> List[float]:
        cmd = [
            FFPROBE_PATH,
            '-v', 'quiet',
            '-select_streams', 'v:0',
            '-show_entries', 'frame=pkt_pts_time,pict_type',
            '-of', 'json',
            self.video_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                timestamps = []
                for frame in data.get('frames', []):
                    if frame.get('pict_type') == 'I':
                        try:
                            timestamps.append(float(frame.get('pkt_pts_time', 0)))
                        except:
                            pass
                return timestamps
        except:
            pass
        return []

    def get_scene_summary(self) -> Dict:
        return {
            'total_scene_changes': len(self.scene_changes),
            'scene_timestamps': self.scene_changes[:100],
            'avg_scene_duration': (
                self.video_info['duration'] / (len(self.scene_changes) + 1)
                if self.video_info and len(self.scene_changes) > 0
                else 0
            )
        }

    def cleanup(self):
        for frame_file in os.listdir(self.output_dir):
            try:
                os.remove(os.path.join(self.output_dir, frame_file))
            except:
                pass
        try:
            os.rmdir(self.output_dir)
        except:
            pass
