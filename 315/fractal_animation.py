import numpy as np
from typing import Callable, Dict, Any, List, Tuple, Optional
import os
from PIL import Image
import math
import time
import threading


class AnimationCurve:
    """动画曲线生成器"""
    
    @staticmethod
    def linear(t: float) -> float:
        return t
    
    @staticmethod
    def ease_in(t: float) -> float:
        return t * t
    
    @staticmethod
    def ease_out(t: float) -> float:
        return 1 - (1 - t) * (1 - t)
    
    @staticmethod
    def ease_in_out(t: float) -> float:
        if t < 0.5:
            return 2 * t * t
        return 1 - math.pow(-2 * t + 2, 2) / 2
    
    @staticmethod
    def sinusoidal(t: float) -> float:
        return (1 - math.cos(t * math.pi)) / 2
    
    @staticmethod
    def bounce(t: float) -> float:
        n1 = 7.5625
        d1 = 2.75
        
        if t < 1 / d1:
            return n1 * t * t
        elif t < 2 / d1:
            t -= 1.5 / d1
            return n1 * t * t + 0.75
        elif t < 2.5 / d1:
            t -= 2.25 / d1
            return n1 * t * t + 0.9375
        else:
            t -= 2.625 / d1
            return n1 * t * t + 0.984375
    
    @staticmethod
    def elastic(t: float) -> float:
        c4 = (2 * math.pi) / 3
        if t == 0:
            return 0
        elif t == 1:
            return 1
        return -math.pow(2, 10 * t - 10) * math.sin((t * 10 - 10.75) * c4)


class Keyframe:
    """关键帧定义"""
    
    def __init__(self, frame: int, parameters: Dict[str, float],
                 curve: str = 'ease_in_out'):
        self.frame = frame
        self.parameters = parameters.copy()
        self.curve = getattr(AnimationCurve, curve, AnimationCurve.linear)


class AnimationTrack:
    """动画轨道：管理单个参数的动画"""
    
    def __init__(self, param_name: str, keyframes: List[Keyframe]):
        self.param_name = param_name
        self.keyframes = sorted(keyframes, key=lambda k: k.frame)
    
    def get_value(self, frame: int) -> float:
        """获取指定帧的参数值"""
        if len(self.keyframes) == 0:
            return 0.0
        
        if len(self.keyframes) == 1:
            return self.keyframes[0].parameters[self.param_name]
        
        if frame <= self.keyframes[0].frame:
            return self.keyframes[0].parameters[self.param_name]
        
        if frame >= self.keyframes[-1].frame:
            return self.keyframes[-1].parameters[self.param_name]
        
        for i in range(len(self.keyframes) - 1):
            k1 = self.keyframes[i]
            k2 = self.keyframes[i + 1]
            
            if k1.frame <= frame <= k2.frame:
                t = (frame - k1.frame) / (k2.frame - k1.frame)
                t_curvy = k2.curve(t)
                
                v1 = k1.parameters[self.param_name]
                v2 = k2.parameters[self.param_name]
                
                return v1 + (v2 - v1) * t_curvy
        
        return self.keyframes[-1].parameters[self.param_name]


class FractalAnimation:
    """分形动画生成器"""
    
    def __init__(self, renderer: Any, width: int = 800, height: int = 600,
                 fps: int = 30):
        self.renderer = renderer
        self.width = width
        self.height = height
        self.fps = fps
        self.tracks: Dict[str, AnimationTrack] = {}
        self.is_playing = False
        self.current_frame = 0
        self.total_frames = 0
        self._stop_event = threading.Event()
        self._frames_cache: Dict[int, np.ndarray] = {}
    
    def add_track(self, param_name: str, keyframes: List[Keyframe]):
        """添加参数动画轨道"""
        track = AnimationTrack(param_name, keyframes)
        self.tracks[param_name] = track
        
        max_frame = max(kf.frame for kf in keyframes)
        if max_frame > self.total_frames:
            self.total_frames = max_frame
    
    def get_parameters(self, frame: int) -> Dict[str, float]:
        """获取指定帧的所有参数值"""
        params = {}
        for name, track in self.tracks.items():
            params[name] = track.get_value(frame)
        return params
    
    def render_frame(self, frame: int) -> np.ndarray:
        """渲染单帧图像"""
        if frame in self._frames_cache:
            return self._frames_cache[frame]
        
        params = self.get_parameters(frame)
        
        if hasattr(self.renderer, 'update_parameters'):
            self.renderer.update_parameters(params)
        else:
            for key, value in params.items():
                if hasattr(self.renderer, key):
                    setattr(self.renderer, key, value)
        
        if hasattr(self.renderer, 'render'):
            image = self.renderer.render()
        else:
            image = self.renderer()
        
        self._frames_cache[frame] = image
        return image
    
    def play(self, callback: Optional[Callable[[int, np.ndarray], None]] = None,
             start_frame: int = 0, loop: bool = True):
        """播放动画"""
        self.is_playing = True
        self._stop_event.clear()
        self.current_frame = start_frame
        
        frame_duration = 1.0 / self.fps
        
        while self.is_playing and not self._stop_event.is_set():
            start_time = time.perf_counter()
            
            image = self.render_frame(self.current_frame)
            
            if callback is not None:
                callback(self.current_frame, image)
            
            elapsed = time.perf_counter() - start_time
            sleep_time = max(0, frame_duration - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            self.current_frame += 1
            if self.current_frame > self.total_frames:
                if loop:
                    self.current_frame = 0
                else:
                    break
        
        self.is_playing = False
    
    def stop(self):
        """停止动画播放"""
        self._stop_event.set()
        self.is_playing = False
    
    def export_gif(self, output_path: str, start_frame: int = 0,
                   end_frame: Optional[int] = None, loop: int = 0,
                   progress_callback: Optional[Callable[[int, int], None]] = None):
        """
        导出为GIF动画
        
        Args:
            output_path: 输出文件路径
            start_frame: 起始帧
            end_frame: 结束帧
            loop: 循环次数（0表示无限循环）
            progress_callback: 进度回调函数 (current, total)
        """
        if end_frame is None:
            end_frame = self.total_frames
        
        frames = []
        total = end_frame - start_frame + 1
        
        for i, frame in enumerate(range(start_frame, end_frame + 1)):
            image = self.render_frame(frame)
            pil_image = self._to_pil_image(image)
            frames.append(pil_image)
            
            if progress_callback is not None:
                progress_callback(i + 1, total)
        
        if frames:
            frames[0].save(
                output_path,
                save_all=True,
                append_images=frames[1:],
                duration=1000 / self.fps,
                loop=loop
            )
    
    def export_video(self, output_path: str, start_frame: int = 0,
                     end_frame: Optional[int] = None,
                     progress_callback: Optional[Callable[[int, int], None]] = None):
        """
        导出为视频（需要imageio或ffmpeg）
        
        Args:
            output_path: 输出文件路径
            start_frame: 起始帧
            end_frame: 结束帧
            progress_callback: 进度回调函数
        """
        try:
            import imageio
        except ImportError:
            raise ImportError("需要安装imageio库: pip install imageio[ffmpeg]")
        
        if end_frame is None:
            end_frame = self.total_frames
        
        total = end_frame - start_frame + 1
        
        with imageio.get_writer(output_path, fps=self.fps) as writer:
            for i, frame in enumerate(range(start_frame, end_frame + 1)):
                image = self.render_frame(frame)
                if image.shape[-1] == 4:
                    image = image[..., :3]
                image_uint8 = (np.clip(image, 0, 1) * 255).astype(np.uint8)
                writer.append_data(image_uint8)
                
                if progress_callback is not None:
                    progress_callback(i + 1, total)
    
    def clear_cache(self):
        """清空帧缓存"""
        self._frames_cache.clear()
    
    def _to_pil_image(self, image: np.ndarray) -> Image.Image:
        """转换numpy数组为PIL Image"""
        if image.shape[-1] == 4:
            image = image[..., :3]
        image_uint8 = (np.clip(image, 0, 1) * 255).astype(np.uint8)
        return Image.fromarray(image_uint8)


class PresetAnimations:
    """预设动画"""
    
    @staticmethod
    def create_julia_rotation(renderer: Any, cx_start: float = -0.7,
                              cx_end: float = -0.7, cy_start: float = 0.27015,
                              cy_end: float = 0.27015, duration: float = 3.0,
                              fps: int = 30) -> FractalAnimation:
        """创建Julia集参数动画"""
        total_frames = int(duration * fps)
        
        kf_cx_start = Keyframe(0, {'cx': cx_start}, 'ease_in_out')
        kf_cx_end = Keyframe(total_frames, {'cx': cx_end}, 'ease_in_out')
        
        kf_cy_start = Keyframe(0, {'cy': cy_start}, 'sinusoidal')
        kf_cy_end = Keyframe(total_frames, {'cy': cy_end}, 'sinusoidal')
        
        anim = FractalAnimation(renderer, fps=fps)
        anim.add_track('cx', [kf_cx_start, kf_cx_end])
        anim.add_track('cy', [kf_cy_start, kf_cy_end])
        
        return anim
    
    @staticmethod
    def create_zoom_animation(renderer: Any, zoom_factor: float = 10.0,
                              duration: float = 5.0, fps: int = 30) -> FractalAnimation:
        """创建缩放动画"""
        total_frames = int(duration * fps)
        
        if hasattr(renderer, 'zoom_level'):
            kf_start = Keyframe(0, {'zoom_level': 1.0}, 'ease_in')
            kf_end = Keyframe(total_frames, {'zoom_level': zoom_factor}, 'ease_in')
            
            anim = FractalAnimation(renderer, fps=fps)
            anim.add_track('zoom_level', [kf_start, kf_end])
            return anim
        return None
    
    @staticmethod
    def create_mandelbulb_spin(renderer: Any, duration: float = 10.0,
                               fps: int = 30) -> FractalAnimation:
        """创建Mandelbulb旋转动画"""
        total_frames = int(duration * fps)
        
        kf_rx_start = Keyframe(0, {'rotation_x': 0.0}, 'linear')
        kf_rx_end = Keyframe(total_frames, {'rotation_x': math.pi}, 'linear')
        
        kf_ry_start = Keyframe(0, {'rotation_y': 0.0}, 'linear')
        kf_ry_end = Keyframe(total_frames, {'rotation_y': math.pi * 2}, 'linear')
        
        anim = FractalAnimation(renderer, fps=fps)
        anim.add_track('rotation_x', [kf_rx_start, kf_rx_end])
        anim.add_track('rotation_y', [kf_ry_start, kf_ry_end])
        
        return anim
    
    @staticmethod
    def create_iteration_pulse(renderer: Any, min_iter: int = 50,
                               max_iter: int = 500, duration: float = 4.0,
                               fps: int = 30) -> FractalAnimation:
        """创建迭代次数脉冲动画"""
        total_frames = int(duration * fps)
        half_frames = total_frames // 2
        
        kf1 = Keyframe(0, {'max_iter': min_iter}, 'ease_in_out')
        kf2 = Keyframe(half_frames, {'max_iter': max_iter}, 'ease_in_out')
        kf3 = Keyframe(total_frames, {'max_iter': min_iter}, 'ease_in_out')
        
        anim = FractalAnimation(renderer, fps=fps)
        anim.add_track('max_iter', [kf1, kf2, kf3])
        
        return anim
    
    @staticmethod
    def create_color_animation(renderer: Any, duration: float = 6.0,
                               fps: int = 30) -> FractalAnimation:
        """创建颜色偏移动画"""
        total_frames = int(duration * fps)
        
        kf1 = Keyframe(0, {'color_offset': 0.0}, 'linear')
        kf2 = Keyframe(total_frames, {'color_offset': 1.0}, 'linear')
        
        anim = FractalAnimation(renderer, fps=fps)
        anim.add_track('color_offset', [kf1, kf2])
        
        return anim
