import webrtcvad
import numpy as np
import threading
import queue
import time
from collections import deque
from typing import List, Tuple, Optional, Callable, Any
from dataclasses import dataclass
from config import VADConfig


@dataclass
class AudioSegment:
    audio_bytes: bytes
    timestamp: float
    duration: float
    is_partial: bool = False


class DoubleBufferVAD:
    def __init__(self, config: VADConfig):
        self.config = config
        self.vad = webrtcvad.Vad(config.mode)
        self.sample_rate = config.sample_rate
        self.frame_duration = config.frame_duration
        self.frame_size = int(self.sample_rate * self.frame_duration / 1000)
        
        self.min_silence_frames = int(config.min_silence_duration * 1000 / self.frame_duration)
        self.min_speech_frames = int(config.min_speech_duration * 1000 / self.frame_duration)
        self.padding_frames = int(config.padding_duration * 1000 / self.frame_duration)
        self.max_silence_duration = 5.0
        self.max_silence_frames = int(self.max_silence_duration * 1000 / self.frame_duration)
        
        self.speech_buffer: List[bytes] = []
        self.silence_counter = 0
        self.speech_counter = 0
        self.in_speech = False
        self.padding_buffer: deque = deque(maxlen=self.padding_frames)
        self.last_speech_time = time.time()
        self.context_start_time = time.time()
        
        self.audio_queue: queue.Queue = queue.Queue(maxsize=1000)
        self.segment_queue: queue.Queue = queue.Queue(maxsize=100)
        self.partial_queue: queue.Queue = queue.Queue(maxsize=50)
        
        self.is_running = False
        self.process_thread: Optional[threading.Thread] = None
        self.recognition_thread: Optional[threading.Thread] = None
        
        self.recognition_callback: Optional[Callable[[AudioSegment], Any]] = None
        self.partial_callback: Optional[Callable[[AudioSegment], Any]] = None
        
        self._lock = threading.Lock()
        
    def is_speech(self, audio_frame: bytes) -> bool:
        return self.vad.is_speech(audio_frame, self.sample_rate)
    
    def check_context_reset(self) -> bool:
        current_time = time.time()
        if self.silence_counter >= self.max_silence_frames:
            if current_time - self.last_speech_time >= self.max_silence_duration:
                self._reset_context()
                return True
        return False
    
    def _reset_context(self):
        with self._lock:
            self.speech_buffer = []
            self.silence_counter = 0
            self.speech_counter = 0
            self.in_speech = False
            self.padding_buffer.clear()
            self.context_start_time = time.time()
            print(f"[VAD] 长时间静音检测，上下文已重置")
    
    def process_frame(self, audio_frame: bytes, timestamp: Optional[float] = None) -> Tuple[bool, Optional[AudioSegment]]:
        if timestamp is None:
            timestamp = time.time()
            
        is_speech_frame = self.is_speech(audio_frame)
        self.padding_buffer.append(audio_frame)
        
        self.check_context_reset()
        
        segment = None
        is_complete = False
        
        if is_speech_frame:
            self.last_speech_time = timestamp
            self.silence_counter = 0
            self.speech_counter += 1
            
            if not self.in_speech and self.speech_counter >= self.min_speech_frames:
                self.in_speech = True
                self.speech_buffer = list(self.padding_buffer)
            elif self.in_speech:
                self.speech_buffer.append(audio_frame)
                
                if len(self.speech_buffer) % 50 == 0:
                    partial_audio = b''.join(self.speech_buffer)
                    segment = AudioSegment(
                        audio_bytes=partial_audio,
                        timestamp=self.context_start_time,
                        duration=len(self.speech_buffer) * self.frame_duration / 1000,
                        is_partial=True
                    )
                    try:
                        self.partial_queue.put_nowait(segment)
                    except queue.Full:
                        pass
        else:
            self.speech_counter = 0
            
            if self.in_speech:
                self.silence_counter += 1
                self.speech_buffer.append(audio_frame)
                
                if self.silence_counter >= self.min_silence_frames:
                    self.in_speech = False
                    complete_audio = b''.join(self.speech_buffer[:-self.min_silence_frames + 1])
                    duration = (len(self.speech_buffer) - self.min_silence_frames + 1) * self.frame_duration / 1000
                    
                    segment = AudioSegment(
                        audio_bytes=complete_audio,
                        timestamp=self.context_start_time,
                        duration=duration,
                        is_partial=False
                    )
                    is_complete = True
                    
                    self.speech_buffer = []
                    self.silence_counter = 0
        
        return is_complete, segment
    
    def put_audio_frame(self, audio_frame: bytes):
        try:
            self.audio_queue.put_nowait(audio_frame)
        except queue.Full:
            try:
                self.audio_queue.get_nowait()
                self.audio_queue.put_nowait(audio_frame)
            except queue.Empty:
                pass
    
    def _process_audio_loop(self):
        while self.is_running:
            try:
                frame = self.audio_queue.get(timeout=0.1)
                is_complete, segment = self.process_frame(frame)
                
                if is_complete and segment:
                    try:
                        self.segment_queue.put_nowait(segment)
                    except queue.Full:
                        try:
                            self.segment_queue.get_nowait()
                            self.segment_queue.put_nowait(segment)
                        except queue.Empty:
                            pass
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[VAD] 处理音频帧错误: {e}")
    
    def _recognition_loop(self):
        while self.is_running:
            try:
                segment = self.segment_queue.get(timeout=0.1)
                
                if self.recognition_callback:
                    self.recognition_callback(segment)
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[VAD] 识别循环错误: {e}")
    
    def get_partial_segment(self, timeout: float = 0.1) -> Optional[AudioSegment]:
        try:
            return self.partial_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_complete_segment(self, timeout: float = 0.1) -> Optional[AudioSegment]:
        try:
            return self.segment_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def start(self, recognition_callback: Optional[Callable] = None, partial_callback: Optional[Callable] = None):
        self.is_running = True
        self.recognition_callback = recognition_callback
        self.partial_callback = partial_callback
        
        self.process_thread = threading.Thread(target=self._process_audio_loop, daemon=True)
        self.process_thread.start()
        
        self.recognition_thread = threading.Thread(target=self._recognition_loop, daemon=True)
        self.recognition_thread.start()
        
        print("[VAD] 双缓冲处理已启动")
    
    def stop(self):
        self.is_running = False
        
        if self.process_thread:
            self.process_thread.join(timeout=1.0)
        
        if self.recognition_thread:
            self.recognition_thread.join(timeout=1.0)
        
        self._reset_context()
        print("[VAD] 双缓冲处理已停止")
    
    def reset(self):
        self._reset_context()
    
    @staticmethod
    def float_to_pcm16(audio: np.ndarray) -> bytes:
        audio = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio * 32767).astype(np.int16)
        return audio_int16.tobytes()
    
    @staticmethod
    def pcm16_to_float(audio_bytes: bytes) -> np.ndarray:
        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
        return audio_int16.astype(np.float32) / 32767.0


class AudioSegmenter:
    def __init__(self, config: VADConfig):
        self.vad = DoubleBufferVAD(config)
        self.frame_size = self.vad.frame_size
        
    def segment_audio(self, audio_data: bytes) -> List[AudioSegment]:
        segments = []
        offset = 0
        frame_bytes = self.frame_size * 2
        
        while offset + frame_bytes <= len(audio_data):
            frame = audio_data[offset:offset + frame_bytes]
            is_complete, segment = self.vad.process_frame(frame)
            
            if is_complete and segment:
                segments.append(segment)
            
            offset += frame_bytes
        
        return segments
    
    def reset(self):
        self.vad.reset()
