import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal


class VideoExporter:
    def __init__(self, gl_widget, output_path):
        self.gl_widget = gl_widget
        self.output_path = output_path
        
        self.width = gl_widget.width()
        self.height = gl_widget.height()
        
        if self.width % 2 != 0:
            self.width -= 1
        if self.height % 2 != 0:
            self.height -= 1
    
    def export_animation(self, duration=5.0, fps=30, callback=None):
        total_frames = int(duration * fps)
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        if self.output_path.endswith('.avi'):
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
        
        writer = cv2.VideoWriter(
            self.output_path, fourcc, fps,
            (self.width, self.height)
        )
        
        if not writer.isOpened():
            raise RuntimeError('无法创建视频写入器')
        
        original_time = self.gl_widget.animation_time
        original_playing = self.gl_widget.is_playing
        self.gl_widget.is_playing = False
        
        try:
            for i in range(total_frames):
                time = original_time + (i / fps)
                self.gl_widget.animation_time = time
                self.gl_widget._update_mesh()
                self.gl_widget.paintGL()
                
                frame = self.gl_widget.get_framebuffer()
                
                if frame.shape[1] != self.width or frame.shape[0] != self.height:
                    frame = cv2.resize(frame, (self.width, self.height))
                
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                writer.write(frame_bgr)
                
                if callback is not None:
                    callback(i + 1, total_frames)
        
        finally:
            writer.release()
            self.gl_widget.animation_time = original_time
            self.gl_widget.is_playing = original_playing
