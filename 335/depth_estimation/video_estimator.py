import cv2
import numpy as np
import time
from typing import Optional, Tuple, Callable, Dict
from collections import deque

from config.config import VideoConfig, CameraCalibrationConfig, AlignmentConfig, ARConfig
from .midas_model import MidasModel
from .post_processing import DepthPostProcessor
from .temporal_filtering import TemporalFilterPipeline
from .camera_calibration import CameraCalibrator, DepthConverter
from .depth_rgb_alignment import DepthRGBAligner
from .ar_overlay import AROverlay


class VideoDepthEstimator:
    def __init__(
        self,
        model: MidasModel,
        post_processor: DepthPostProcessor,
        config: VideoConfig,
        camera_config: Optional[CameraCalibrationConfig] = None,
        alignment_config: Optional[AlignmentConfig] = None,
        ar_config: Optional[ARConfig] = None
    ):
        self.model = model
        self.post_processor = post_processor
        self.config = config
        self.cap = None
        self.writer = None
        self.running = False
        self.fps_history = deque(maxlen=30)
        self.frame_count = 0
        
        self.temporal_pipeline = TemporalFilterPipeline(
            config.temporal_smoothing,
            config.temporal_hole_filling,
            post_processor.config
        )
        
        if camera_config is None:
            camera_config = CameraCalibrationConfig()
        if alignment_config is None:
            alignment_config = AlignmentConfig()
        if ar_config is None:
            ar_config = ARConfig()
        
        self.camera_calibrator = CameraCalibrator(camera_config)
        self.depth_converter = DepthConverter(self.camera_calibrator)
        self.depth_aligner = DepthRGBAligner(self.camera_calibrator, alignment_config)
        self.ar_overlay = AROverlay(self.camera_calibrator, ar_config)
        
        self._metric_depth_cache = None
        self._mouse_callback_set = False
    
    def _open_capture(self) -> bool:
        source = self.config.source
        if source.isdigit():
            source = int(source)
        
        self.cap = cv2.VideoCapture(source)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video source: {self.config.source}")
        
        if self.config.target_size:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.target_size[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.target_size[1])
        
        return True
    
    def _setup_writer(self, frame_shape: Tuple[int, int]) -> None:
        if not self.config.save_video or not self.config.output_path:
            return
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = self.config.target_fps
        width = frame_shape[1] * 2 if self.config.display_depth else frame_shape[1]
        height = frame_shape[0]
        
        self.writer = cv2.VideoWriter(
            self.config.output_path,
            fourcc,
            fps,
            (width, height)
        )
        
        if not self.writer.isOpened():
            raise RuntimeError(f"Failed to create video writer: {self.config.output_path}")
    
    def _read_frame(self) -> Optional[np.ndarray]:
        if self.cap is None:
            return None
        
        ret, frame = self.cap.read()
        if not ret:
            return None
        
        if self.config.target_size:
            frame = cv2.resize(
                frame,
                self.config.target_size,
                interpolation=cv2.INTER_AREA
            )
        
        return frame
    
    def _estimate_depth(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        raw_depth = self.model.predict(frame)
        processed_depth = self.post_processor.process(raw_depth, frame)
        temporal_depth = self.temporal_pipeline.process(processed_depth, frame)
        return raw_depth, temporal_depth
    
    def _convert_to_metric(self, depth_map: np.ndarray) -> np.ndarray:
        return self.depth_converter.relative_to_metric_depth(
            depth_map,
            method='median'
        )
    
    def _visualize(self, frame: np.ndarray, depth_map: np.ndarray, metric_depth: np.ndarray, fps: float) -> np.ndarray:
        if self.config.display_depth:
            depth_colored = DepthPostProcessor.apply_colormap(
                depth_map,
                self.config.colormap
            )
            
            if depth_colored.shape[:2] != frame.shape[:2]:
                depth_colored = cv2.resize(
                    depth_colored,
                    (frame.shape[1], frame.shape[0])
                )
            
            ar_frame = self.ar_overlay.render(frame, metric_depth)
            ar_frame = self.ar_overlay.render_shadow(ar_frame, metric_depth)
            
            combined = np.hstack((ar_frame, depth_colored))
        else:
            ar_frame = self.ar_overlay.render(frame, metric_depth)
            combined = ar_frame
        
        if self.config.show_fps:
            cv2.putText(
                combined,
                f"FPS: {fps:.1f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
                cv2.LINE_AA
            )
        
        depth_roi = cv2.putText(
            combined,
                "AR Mode - Click to place object",
                (combined.shape[1] // 2 + 10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                1,
                cv2.LINE_AA
            )
        
        return combined
    
    def _write_frame(self, frame: np.ndarray) -> None:
        if self.writer is not None:
            self.writer.write(frame)
    
    def _mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if self._metric_depth_cache is not None:
                display_width = self.config.target_size[0] if self.config.target_size else 640
                
                if x < display_width:
                    self.ar_overlay.place_object_at_pixel(
                        self._metric_depth_cache, x, y)
                    print(f"Object placed at pixel ({x}, {y})")
    
    def run(self, callback: Optional[Callable[[np.ndarray, np.ndarray], None]] = None) -> None:
        self._open_capture()
        
        ret, test_frame = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to read from video source")
        
        self._setup_writer(test_frame.shape[:2])
        self.reset_temporal_filters()
        
        self.running = True
        print("Starting video depth estimation with AR.")
        print("Press 'q' to quit, 's' to save current frame.")
        print("Left-click on the RGB image to place 3D objects.")
        print("Press 'c' to clear all AR objects.")
        
        cv2.namedWindow("Depth Estimation + AR")
        cv2.setMouseCallback("Depth Estimation + AR", self._mouse_callback)
        
        try:
            while self.running:
                start_time = time.time()
                
                frame = self._read_frame()
                if frame is None:
                    print("End of video stream.")
                    break
                
                raw_depth, processed_depth = self._estimate_depth(frame)
                
                metric_depth = self._convert_to_metric(processed_depth)
                self._metric_depth_cache = metric_depth
                
                inference_time = time.time() - start_time
                fps = 1.0 / inference_time if inference_time > 0 else 0
                self.fps_history.append(fps)
                avg_fps = sum(self.fps_history) / len(self.fps_history)
                
                display_frame = self._visualize(frame, processed_depth, metric_depth, avg_fps)
                
                self._write_frame(display_frame)
                
                if callback is not None:
                    callback(frame, processed_depth)
                
                cv2.imshow("Depth Estimation + AR", display_frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("Quitting...")
                    break
                elif key == ord('s'):
                    self._save_current_frame(frame, processed_depth)
                elif key == ord('c'):
                    self.ar_overlay.clear_objects()
                    print("AR objects cleared.")
                
                self.frame_count += 1
                
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
        finally:
            self._cleanup()
    
    def _save_current_frame(self, frame: np.ndarray, depth_map: np.ndarray) -> None:
        import time as time_module
        timestamp = time_module.strftime("%Y%m%d_%H%M%S")
        frame_path = f"frame_{timestamp}.jpg"
        depth_path = f"depth_{timestamp}.png"
        
        cv2.imwrite(frame_path, frame)
        
        depth_colored = DepthPostProcessor.apply_colormap(
            depth_map,
            self.config.colormap
        )
        cv2.imwrite(depth_path, depth_colored)
        
        print(f"Saved frame: {frame_path}, depth map: {depth_path}")
    
    def process_video_file(self, input_path: str, output_path: Optional[str] = None,
                          progress_callback: Optional[Callable[[int, int], None]] = None) -> None:
        temp_source = self.config.source
        self.config.source = input_path
        
        if output_path:
            self.config.output_path = output_path
            self.config.save_video = True
        
        self._open_capture()
        
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        ret, test_frame = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to read video file")
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        self._setup_writer(test_frame.shape[:2])
        self.reset_temporal_filters()
        
        self.running = True
        frame_idx = 0
        
        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                if self.config.target_size:
                    frame = cv2.resize(
                        frame,
                        self.config.target_size,
                        interpolation=cv2.INTER_AREA
                    )
                
                start_time = time.time()
                _, processed_depth = self._estimate_depth(frame)
                metric_depth = self._convert_to_metric(processed_depth)
                inference_time = time.time() - start_time
                self.fps_history.append(1.0 / inference_time)
                
                display_frame = self._visualize(
                    frame,
                    processed_depth,
                    metric_depth,
                    sum(self.fps_history) / len(self.fps_history)
                )
                
                self._write_frame(display_frame)
                
                if progress_callback is not None:
                    progress_callback(frame_idx, total_frames)
                
                frame_idx += 1
                
                if frame_idx % 10 == 0:
                    print(f"Processed {frame_idx}/{total_frames} frames "
                          f"({100 * frame_idx / total_frames:.1f}%)")
                
        finally:
            self._cleanup()
            self.config.source = temp_source
        
        print(f"Video processing complete. Output saved to: {self.config.output_path}")
    
    def get_frame_generator(self):
        self._open_capture()
        self.reset_temporal_filters()
        
        try:
            while True:
                frame = self._read_frame()
                if frame is None:
                    break
                
                start_time = time.time()
                raw_depth, processed_depth = self._estimate_depth(frame)
                metric_depth = self._convert_to_metric(processed_depth)
                fps = 1.0 / (time.time() - start_time)
                
                yield {
                    'frame': frame,
                    'raw_depth': raw_depth,
                    'processed_depth': processed_depth,
                    'metric_depth': metric_depth,
                    'fps': fps
                }
        finally:
            self._cleanup()
    
    def _cleanup(self) -> None:
        self.running = False
        
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        if self.writer is not None:
            self.writer.release()
            self.writer = None
        
        if hasattr(self, 'temporal_pipeline'):
            self.temporal_pipeline.reset()
        
        self.ar_overlay.clear_objects()
        
        cv2.destroyAllWindows()
    
    def get_stats(self) -> dict:
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        stats = {
            "frame_count": self.frame_count,
            "avg_fps": avg_fps,
            "source": self.config.source,
            "target_size": self.config.target_size,
        }
        
        if hasattr(self, 'temporal_pipeline'):
            stats["temporal"] = self.temporal_pipeline.get_stats()
            stats["temporal_smoothing_enabled"] = self.config.temporal_smoothing.apply_temporal_smoothing
            stats["temporal_hole_filling_enabled"] = self.config.temporal_hole_filling.apply_temporal_hole_filling
        
        stats["ar_objects"] = len(self.ar_overlay.objects)
        stats["ar_enabled"] = True
        
        return stats
    
    def reset_temporal_filters(self) -> None:
        if hasattr(self, 'temporal_pipeline'):
            self.temporal_pipeline.reset()
    
    def add_ar_object(self, position_3d: np.ndarray, 
                     object_type: str = 'cube',
                     scale: Optional[float] = None,
                     color: Optional[Tuple[int, int, int]] = None) -> int:
        return self.ar_overlay.add_object(position_3d, object_type, scale, color)
    
    def place_ar_object_at_pixel(self, depth_map: np.ndarray,
                           pixel_x: int, pixel_y: int,
                           object_type: str = 'cube') -> Optional[int]:
        return self.ar_overlay.place_object_at_pixel(depth_map, pixel_x, pixel_y, object_type)
    
    def clear_ar_objects(self):
        self.ar_overlay.clear_objects()
    
    def get_aligned_output(self, rgb_image: np.ndarray, 
                           depth_map: np.ndarray) -> Dict[str, np.ndarray]:
        return self.depth_aligner.align(rgb_image, depth_map)
    
    def get_metric_depth(self, depth_map: np.ndarray) -> np.ndarray:
        return self._convert_to_metric(depth_map)
    
    def get_colored_depth_overlay(self, rgb_image: np.ndarray,
                              depth_map: np.ndarray) -> np.ndarray:
        return self.depth_aligner.generate_depth_overlay(rgb_image, depth_map)
    
    def get_colored_pointcloud(self, rgb_image: np.ndarray,
                           depth_map: np.ndarray) -> Dict:
        return self.depth_aligner.generate_pointcloud_colored(rgb_image, depth_map)
    
    def __del__(self):
        self._cleanup()
