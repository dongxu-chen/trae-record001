import cv2
import numpy as np
import mss
import mss.tools
import threading
import time
import os
from typing import Optional, Tuple, Callable
from datetime import datetime
from PIL import Image
import queue

from config import config


class ScreenRecorder:
    def __init__(self, output_dir: Optional[str] = None, fps: int = None):
        self.fps = fps or config.SCREEN_RECORD_FPS
        self.output_dir = output_dir or config.RECORDINGS_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.is_recording = False
        self._recording_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[0]
        
        self._frame_queue: 'queue.Queue[Tuple[float, np.ndarray]]' = queue.Queue()
        self._video_writer: Optional[cv2.VideoWriter] = None
        self._output_path: Optional[str] = None
        
        self._frame_callback: Optional[Callable[[np.ndarray], None]] = None
        self._on_stop_callback: Optional[Callable[[str], None]] = None
    
    def set_frame_callback(self, callback: Callable[[np.ndarray], None]) -> None:
        self._frame_callback = callback
    
    def set_on_stop_callback(self, callback: Callable[[str], None]) -> None:
        self._on_stop_callback = callback
    
    def _get_frame(self) -> Optional[np.ndarray]:
        try:
            img = self.sct.grab(self.monitor)
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            return frame
        except Exception as e:
            print(f"Error capturing screen: {e}")
            return None
    
    def _init_video_writer(self, exam_id: str) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"exam_{exam_id}_{timestamp}.mp4"
        self._output_path = os.path.join(self.output_dir, filename)
        
        width = self.monitor["width"]
        height = self.monitor["height"]
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self._video_writer = cv2.VideoWriter(
            self._output_path, fourcc, self.fps, (width, height)
        )
    
    def _record_loop(self, exam_id: str) -> None:
        self._init_video_writer(exam_id)
        
        frame_interval = 1.0 / self.fps
        last_frame_time = time.time()
        
        while not self._stop_event.is_set():
            current_time = time.time()
            elapsed = current_time - last_frame_time
            
            if elapsed >= frame_interval:
                frame = self._get_frame()
                if frame is not None and self._video_writer is not None:
                    self._video_writer.write(frame)
                    self._frame_queue.put((current_time, frame))
                    
                    if self._frame_callback is not None:
                        try:
                            self._frame_callback(frame)
                        except Exception as e:
                            print(f"Error in frame callback: {e}")
                
                last_frame_time = current_time
            else:
                time.sleep(max(0, frame_interval - elapsed))
        
        if self._video_writer is not None:
            self._video_writer.release()
            self._video_writer = None
        
        if self._on_stop_callback is not None and self._output_path:
            try:
                self._on_stop_callback(self._output_path)
            except Exception as e:
                print(f"Error in stop callback: {e}")
        
        self.is_recording = False
    
    def start(self, exam_id: str = "default") -> bool:
        if self.is_recording:
            return False
        
        self._stop_event.clear()
        self.is_recording = True
        
        self._recording_thread = threading.Thread(
            target=self._record_loop, args=(exam_id,), daemon=True
        )
        self._recording_thread.start()
        
        print(f"Started screen recording for exam {exam_id}")
        return True
    
    def stop(self) -> Optional[str]:
        if not self.is_recording:
            return None
        
        self._stop_event.set()
        
        if self._recording_thread is not None:
            self._recording_thread.join(timeout=5.0)
        
        output_path = self._output_path
        self._output_path = None
        
        print(f"Stopped screen recording. Saved to: {output_path}")
        return output_path
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        if self._frame_queue.empty():
            return None
        
        try:
            while not self._frame_queue.empty():
                timestamp, frame = self._frame_queue.get_nowait()
            return frame
        except queue.Empty:
            return None
    
    def capture_screenshot(self) -> Optional[np.ndarray]:
        return self._get_frame()
    
    def save_screenshot(self, output_path: Optional[str] = None) -> Optional[str]:
        frame = self.capture_screenshot()
        if frame is None:
            return None
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.output_dir, f"screenshot_{timestamp}.png")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cv2.imwrite(output_path, frame)
        return output_path
    
    def get_recordings_list(self) -> list:
        if not os.path.exists(self.output_dir):
            return []
        
        files = []
        for f in os.listdir(self.output_dir):
            if f.endswith('.mp4'):
                filepath = os.path.join(self.output_dir, f)
                stat = os.stat(filepath)
                files.append({
                    'filename': f,
                    'path': filepath,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
        
        files.sort(key=lambda x: x['created'], reverse=True)
        return files
    
    def delete_recording(self, filepath: str) -> bool:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception as e:
            print(f"Error deleting recording: {e}")
            return False
    
    def frame_to_base64(self, frame: np.ndarray) -> Optional[str]:
        try:
            import base64
            _, buffer = cv2.imencode('.jpg', frame)
            return base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            print(f"Error converting frame to base64: {e}")
            return None


class DualRecorder:
    def __init__(self):
        self.screen_recorder = ScreenRecorder()
        self._webcam_writer: Optional[cv2.VideoWriter] = None
        self._webcam_thread: Optional[threading.Thread] = None
        self._webcam_stop_event = threading.Event()
        self._webcam_cap: Optional[cv2.VideoCapture] = None
    
    def start(self, exam_id: str, include_webcam: bool = True) -> bool:
        screen_started = self.screen_recorder.start(exam_id)
        
        if include_webcam:
            self._start_webcam(exam_id)
        
        return screen_started
    
    def _start_webcam(self, exam_id: str) -> None:
        self._webcam_cap = cv2.VideoCapture(0)
        if not self._webcam_cap.isOpened():
            print("Warning: Could not open webcam")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"webcam_{exam_id}_{timestamp}.mp4"
        output_path = os.path.join(config.RECORDINGS_DIR, filename)
        
        fps = int(self._webcam_cap.get(cv2.CAP_PROP_FPS)) or 15
        width = int(self._webcam_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._webcam_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self._webcam_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        self._webcam_stop_event.clear()
        self._webcam_thread = threading.Thread(
            target=self._webcam_loop, daemon=True
        )
        self._webcam_thread.start()
        print(f"Started webcam recording for exam {exam_id}")
    
    def _webcam_loop(self) -> None:
        while not self._webcam_stop_event.is_set():
            if self._webcam_cap is None:
                break
            
            ret, frame = self._webcam_cap.read()
            if ret and self._webcam_writer is not None:
                self._webcam_writer.write(frame)
            time.sleep(0.01)
        
        if self._webcam_writer is not None:
            self._webcam_writer.release()
            self._webcam_writer = None
        
        if self._webcam_cap is not None:
            self._webcam_cap.release()
            self._webcam_cap = None
    
    def stop(self) -> Tuple[Optional[str], Optional[str]]:
        screen_path = self.screen_recorder.stop()
        
        self._webcam_stop_event.set()
        if self._webcam_thread is not None:
            self._webcam_thread.join(timeout=5.0)
        
        return screen_path, None
    
    def get_webcam_frame(self) -> Optional[np.ndarray]:
        if self._webcam_cap is None:
            return None
        
        ret, frame = self._webcam_cap.read()
        return frame if ret else None
