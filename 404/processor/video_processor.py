import cv2
import numpy as np
from typing import Optional, List, Tuple, Dict
import time
from threading import Thread, Lock
from queue import Queue, PriorityQueue
from collections import deque
from dataclasses import dataclass

from detector.yolo_detector import DetectionResult, YOLODetector
from config import (
    VIDEO_STREAM_WIDTH, VIDEO_STREAM_HEIGHT,
    VIDEO_STREAM_FPS, CONF_THRESHOLD
)
from .frame_handler import StreamFrame
from .stream_source import StreamSource
from .temporal_fusion import TemporalFusion, StabilizedResult
from .distance_estimator import SignDistanceEstimator, SignDistanceResult
from .country_adapter import CountryAdapter, AdaptedDetection


@dataclass
class FrameProcessingStats:
    frame_id: int
    timestamp: float
    inference_time: float
    resolution: Tuple[int, int]
    num_detections: int
    skipped: bool = False
    adaptive_mode: str = "normal"


class AdaptiveResolutionController:
    def __init__(
        self,
        base_width: int = VIDEO_STREAM_WIDTH,
        base_height: int = VIDEO_STREAM_HEIGHT,
        target_fps: int = VIDEO_STREAM_FPS,
        min_scale: float = 0.5,
        max_scale: float = 1.0,
        fps_smoothing_window: int = 30,
        adjustment_interval: int = 10
    ):
        self.base_width = base_width
        self.base_height = base_height
        self.target_fps = target_fps
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.fps_smoothing_window = fps_smoothing_window
        self.adjustment_interval = adjustment_interval

        self.current_scale = 1.0
        self.frame_times = deque(maxlen=fps_smoothing_window)
        self.inference_times = deque(maxlen=fps_smoothing_window)
        self.frame_count = 0
        self.last_adjustment_frame = 0
        self.mode_history = deque(maxlen=10)

        self.resolution_steps = [1.0, 0.8, 0.6, 0.5]

    def add_measurement(self, inference_time: float):
        self.inference_times.append(inference_time)
        self.frame_times.append(time.time())
        self.frame_count += 1

    def get_current_fps(self) -> float:
        if len(self.frame_times) < 2:
            return self.target_fps
        elapsed = self.frame_times[-1] - self.frame_times[0]
        if elapsed <= 0:
            return self.target_fps
        return (len(self.frame_times) - 1) / elapsed

    def get_avg_inference_time(self) -> float:
        if not self.inference_times:
            return 0
        return sum(self.inference_times) / len(self.inference_times)

    def get_target_resolution(self) -> Tuple[int, int]:
        if self.frame_count - self.last_adjustment_frame < self.adjustment_interval:
            return self._get_scaled_resolution()

        self.last_adjustment_frame = self.frame_count
        current_fps = self.get_current_fps()
        avg_inference = self.get_avg_inference_time()

        target_inference = 1000.0 / self.target_fps

        if avg_inference > target_inference * 1.2:
            self._decrease_resolution()
        elif avg_inference < target_inference * 0.7 and self.current_scale < self.max_scale:
            self._increase_resolution()

        self.mode_history.append(self._get_mode())
        return self._get_scaled_resolution()

    def _decrease_resolution(self):
        current_idx = self.resolution_steps.index(self.current_scale)
        if current_idx < len(self.resolution_steps) - 1:
            new_scale = self.resolution_steps[current_idx + 1]
            if new_scale >= self.min_scale:
                self.current_scale = new_scale
                print(f"[INFO] Decreased resolution to {self.current_scale:.1f}x to maintain FPS")

    def _increase_resolution(self):
        current_idx = self.resolution_steps.index(self.current_scale)
        if current_idx > 0:
            new_scale = self.resolution_steps[current_idx - 1]
            if new_scale <= self.max_scale:
                self.current_scale = new_scale
                print(f"[INFO] Increased resolution to {self.current_scale:.1f}x")

    def _get_scaled_resolution(self) -> Tuple[int, int]:
        width = int(self.base_width * self.current_scale)
        height = int(self.base_height * self.current_scale)
        return width, height

    def _get_mode(self) -> str:
        if self.current_scale >= 0.9:
            return "high_quality"
        elif self.current_scale >= 0.7:
            return "balanced"
        else:
            return "performance"

    def get_stats(self) -> Dict:
        return {
            "current_scale": self.current_scale,
            "current_fps": round(self.get_current_fps(), 2),
            "avg_inference_time": round(self.get_avg_inference_time(), 2),
            "target_fps": self.target_fps,
            "current_mode": self._get_mode(),
            "resolution": self._get_scaled_resolution()
        }


class PerFrameProcessor:
    def __init__(
        self,
        detector: Optional[YOLODetector] = None,
        conf_threshold: float = CONF_THRESHOLD,
        target_fps: int = VIDEO_STREAM_FPS,
        enable_adaptive_resolution: bool = True
    ):
        self.detector = detector
        self.conf_threshold = conf_threshold
        self.target_fps = target_fps
        self.enable_adaptive_resolution = enable_adaptive_resolution

        self.frame_queue: "Queue[StreamFrame]" = Queue(maxsize=2)
        self.results_queue: "Queue[StreamFrame]" = Queue(maxsize=10)
        self._lock = Lock()
        self._running = False
        self._process_thread: Optional[Thread] = None
        self._frame_count = 0
        self._process_count = 0
        self._skip_count = 0

        self.adaptive_controller = AdaptiveResolutionController(
            target_fps=target_fps
        ) if enable_adaptive_resolution else None

        self.processing_history: List[FrameProcessingStats] = []

    def start(self):
        self._running = True
        self._process_thread = Thread(target=self._processing_loop, daemon=True)
        self._process_thread.start()

    def stop(self):
        self._running = False
        if self._process_thread:
            self._process_thread.join(timeout=2.0)

    def add_frame(self, frame: StreamFrame) -> bool:
        try:
            self.frame_queue.put_nowait(frame)
            return True
        except:
            return False

    def get_result(self, timeout: float = 0.1) -> Optional[StreamFrame]:
        try:
            return self.results_queue.get(timeout=timeout)
        except:
            return None

    def _processing_loop(self):
        while self._running:
            try:
                frame_data = self.frame_queue.get(timeout=0.01)
                self._process_count += 1

                start_time = time.time()

                if self.detector:
                    if self.enable_adaptive_resolution and self.adaptive_controller:
                        target_w, target_h = self.adaptive_controller.get_target_resolution()
                        orig_h, orig_w = frame_data.frame.shape[:2]

                        if (target_w, target_h) != (orig_w, orig_h):
                            processed_frame = cv2.resize(
                                frame_data.frame, (target_w, target_h),
                                interpolation=cv2.INTER_AREA
                            )
                            detections = self.detector.detect(processed_frame, self.conf_threshold)

                            scale_x = orig_w / target_w
                            scale_y = orig_h / target_h
                            for det in detections:
                                det.bbox = [
                                    int(det.bbox[0] * scale_x),
                                    int(det.bbox[1] * scale_y),
                                    int(det.bbox[2] * scale_x),
                                    int(det.bbox[3] * scale_y)
                                ]
                        else:
                            detections = self.detector.detect(frame_data.frame, self.conf_threshold)

                        resolution = (target_w, target_h)
                        mode = self.adaptive_controller._get_mode()
                    else:
                        detections = self.detector.detect(frame_data.frame, self.conf_threshold)
                        resolution = frame_data.frame.shape[:2][::-1]
                        mode = "fixed"

                    annotated = self.detector.draw_detections(frame_data.frame, detections)
                    frame_data.detections = detections
                    frame_data.annotated_frame = annotated

                    inference_time = (time.time() - start_time) * 1000

                    if self.enable_adaptive_resolution and self.adaptive_controller:
                        self.adaptive_controller.add_measurement(inference_time)

                    stats = FrameProcessingStats(
                        frame_id=self._process_count,
                        timestamp=frame_data.timestamp,
                        inference_time=inference_time,
                        resolution=resolution,
                        num_detections=len(detections),
                        skipped=False,
                        adaptive_mode=mode
                    )
                    self.processing_history.append(stats)

                    if len(self.processing_history) > 1000:
                        self.processing_history.pop(0)

                try:
                    self.results_queue.put_nowait(frame_data)
                except:
                    pass

            except:
                continue

    def get_processing_stats(self) -> Dict:
        if self.enable_adaptive_resolution and self.adaptive_controller:
            return self.adaptive_controller.get_stats()
        return {
            "frames_processed": self._process_count,
            "frames_skipped": self._skip_count
        }


class FrameHandler:
    def __init__(
        self,
        detector: Optional[YOLODetector] = None,
        conf_threshold: float = CONF_THRESHOLD
    ):
        self.detector = detector
        self.conf_threshold = conf_threshold

    def process_frame(
        self,
        frame: np.ndarray,
        conf_threshold: Optional[float] = None
    ) -> Tuple[List[DetectionResult], np.ndarray]:
        detections = []
        annotated = frame.copy()

        if self.detector:
            conf = conf_threshold or self.conf_threshold
            detections = self.detector.detect(frame, conf)
            annotated = self.detector.draw_detections(frame, detections)

        return detections, annotated

    def filter_by_confidence(
        self,
        detections: List[DetectionResult],
        min_confidence: float
    ) -> List[DetectionResult]:
        return [d for d in detections if d.confidence >= min_confidence]

    def filter_by_category(
        self,
        detections: List[DetectionResult],
        categories: List[str]
    ) -> List[DetectionResult]:
        return [d for d in detections if d.category in categories]

    def filter_by_class(
        self,
        detections: List[DetectionResult],
        class_names: List[str]
    ) -> List[DetectionResult]:
        return [d for d in detections if d.class_name in class_names]

    def get_statistics(self, detections: List[DetectionResult]) -> dict:
        if not detections:
            return {"total": 0, "by_category": {}, "by_class": {}}

        by_category = {}
        by_class = {}
        for det in detections:
            by_category[det.category] = by_category.get(det.category, 0) + 1
            by_class[det.class_name] = by_class.get(det.class_name, 0) + 1

        return {
            "total": len(detections),
            "by_category": by_category,
            "by_class": by_class,
            "avg_confidence": sum(d.confidence for d in detections) / len(detections)
        }


class VideoProcessor:
    def __init__(
        self,
        detector: Optional[YOLODetector] = None,
        source: int = 0,
        width: int = VIDEO_STREAM_WIDTH,
        height: int = VIDEO_STREAM_HEIGHT,
        fps: int = VIDEO_STREAM_FPS,
        conf_threshold: float = CONF_THRESHOLD,
        display: bool = True,
        enable_adaptive_resolution: bool = True,
        process_every_frame: bool = True,
        enable_temporal_fusion: bool = True,
        enable_distance_estimation: bool = True,
        enable_country_adaptation: bool = True,
        country_code: str = "CN",
        temporal_window_size: int = 5,
        focal_length: float = 800.0,
        camera_height: float = 1.5
    ):
        self.stream_source = StreamSource(source, width, height, fps)
        self.frame_handler = FrameHandler(detector, conf_threshold)
        self.detector = detector
        self.display = display
        self.enable_adaptive_resolution = enable_adaptive_resolution
        self.process_every_frame = process_every_frame
        self.enable_temporal_fusion = enable_temporal_fusion
        self.enable_distance_estimation = enable_distance_estimation
        self.enable_country_adaptation = enable_country_adaptation

        self._running = False
        self._capture_thread: Optional[Thread] = None
        self._display_thread: Optional[Thread] = None
        self._results_queue: "Queue[StreamFrame]" = Queue(maxsize=30)

        self.per_frame_processor = PerFrameProcessor(
            detector=detector,
            conf_threshold=conf_threshold,
            target_fps=fps,
            enable_adaptive_resolution=enable_adaptive_resolution
        ) if detector and process_every_frame else None

        self.temporal_fusion = TemporalFusion(
            window_size=temporal_window_size,
            min_frames_for_stable=3,
            min_hit_ratio=0.6
        ) if enable_temporal_fusion else None

        self.distance_estimator = SignDistanceEstimator(
            focal_length=focal_length,
            image_width=width,
            image_height=height,
            camera_height=camera_height,
            method="hybrid"
        ) if enable_distance_estimation else None

        self.country_adapter = CountryAdapter(
            default_country=country_code
        ) if enable_country_adaptation else None

        self._frames_captured = 0
        self._frames_processed = 0
        self._start_time = 0

        self.temporal_results: List[StabilizedResult] = []
        self.distance_results: List[SignDistanceResult] = []
        self.adapted_detections: List[AdaptedDetection] = []

    def start(self) -> bool:
        if not self.stream_source.open():
            return False

        self._running = True
        self._start_time = time.time()

        if self.per_frame_processor:
            self.per_frame_processor.start()

        self._capture_thread = Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()

        if self.display:
            self._display_thread = Thread(target=self._display_loop, daemon=True)
            self._display_thread.start()

        print(f"[INFO] Video processor started (source: {self.stream_source.source})")
        print(f"[INFO] Per-frame processing: {self.process_every_frame}")
        print(f"[INFO] Adaptive resolution: {self.enable_adaptive_resolution}")
        return True

    def _capture_loop(self):
        while self._running:
            frame_data = self.stream_source.read(timeout=0.01)
            if frame_data is None:
                continue

            self._frames_captured += 1

            if self.per_frame_processor and self.process_every_frame:
                self.per_frame_processor.add_frame(frame_data)

                result = self.per_frame_processor.get_result(timeout=0.001)
                if result:
                    self._frames_processed += 1

                    if result.detections:
                        if self.enable_temporal_fusion and self.temporal_fusion:
                            stabilized = self.temporal_fusion.process(result.detections, result.timestamp)
                            result.detections = [sr.detection for sr in stabilized]
                            self.temporal_results = stabilized

                        if self.enable_distance_estimation and self.distance_estimator and result.detections:
                            distance_results = self.distance_estimator.estimate_batch(
                                result.detections, frame_data.frame.shape
                            )
                            self.distance_results = distance_results

                        if self.enable_country_adaptation and self.country_adapter:
                            adapted = self.country_adapter.batch_adapt(result.detections)
                            self.adapted_detections = adapted

                    if result.detections and self.detector:
                        result.annotated_frame = self._draw_enhanced_annotations(
                            frame_data.frame, result.detections
                        )

                    try:
                        self._results_queue.put_nowait(result)
                    except:
                        pass
            else:
                if self.detector:
                    start = time.time()
                    detections, annotated = self.frame_handler.process_frame(
                        frame_data.frame, self.frame_handler.conf_threshold
                    )
                    frame_data.detections = detections
                    frame_data.annotated_frame = annotated
                    self._frames_processed += 1

                try:
                    self._results_queue.put_nowait(frame_data)
                except:
                    pass

    def _display_loop(self):
        cv2.namedWindow("Traffic Sign Detection", cv2.WINDOW_NORMAL)

        while self._running:
            try:
                result = self._results_queue.get(timeout=0.01)
            except:
                continue

            if result.annotated_frame is not None:
                display_frame = result.annotated_frame.copy()
            else:
                display_frame = result.frame.copy()

            elapsed = time.time() - self._start_time
            if elapsed > 0:
                capture_fps = self._frames_captured / elapsed
                process_fps = self._frames_processed / elapsed

                cv2.putText(
                    display_frame,
                    f"Capture: {capture_fps:.1f} FPS",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
                cv2.putText(
                    display_frame,
                    f"Process: {process_fps:.1f} FPS",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

            if self.per_frame_processor and self.enable_adaptive_resolution:
                stats = self.per_frame_processor.get_processing_stats()
                mode = stats.get("current_mode", "unknown")
                scale = stats.get("current_scale", 1.0)

                mode_color = {
                    "high_quality": (0, 255, 0),
                    "balanced": (0, 255, 255),
                    "performance": (0, 0, 255)
                }.get(mode, (255, 255, 255))

                cv2.putText(
                    display_frame,
                    f"Mode: {mode} ({scale:.1f}x)",
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    mode_color,
                    2
                )

            if result.detections:
                cv2.putText(
                    display_frame,
                    f"Signs: {len(result.detections)}",
                    (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 0),
                    2
                )

            cv2.imshow("Traffic Sign Detection", display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.stop()
                break
            elif key == ord('s'):
                if result.detections:
                    stats_data = self.frame_handler.get_statistics(result.detections)
                    print(f"[INFO] Frame stats: {stats_data}")
            elif key == ord('r'):
                if self.enable_adaptive_resolution and self.per_frame_processor:
                    if self.per_frame_processor.adaptive_controller:
                        self.per_frame_processor.adaptive_controller.current_scale = 1.0
                        print("[INFO] Reset resolution to 1.0x")

        cv2.destroyAllWindows()

    def get_results(self, timeout: float = 0.1) -> Optional[StreamFrame]:
        try:
            return self._results_queue.get(timeout=timeout)
        except:
            return None

    def process_image_file(
        self,
        image_path: str,
        conf_threshold: Optional[float] = None
    ) -> Optional[StreamFrame]:
        frame = cv2.imread(image_path)
        if frame is None:
            print(f"[ERROR] Cannot read image: {image_path}")
            return None

        detections, annotated = self.frame_handler.process_frame(
            frame, conf_threshold
        )

        return StreamFrame(
            frame=frame,
            timestamp=time.time(),
            detections=detections,
            annotated_frame=annotated
        )

    def process_video_file(
        self,
        video_path: str,
        conf_threshold: Optional[float] = None,
        output_path: Optional[str] = None
    ) -> int:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[ERROR] Cannot open video: {video_path}")
            return 0

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        writer = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        frame_count = 0
        all_detections = []
        adaptive_controller = AdaptiveResolutionController(target_fps=fps) if self.enable_adaptive_resolution else None

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            start_time = time.time()

            if self.enable_adaptive_resolution and adaptive_controller and self.detector:
                target_w, target_h = adaptive_controller.get_target_resolution()
                if (target_w, target_h) != (width, height):
                    processed_frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
                    detections = self.detector.detect(processed_frame, conf_threshold)
                    scale_x = width / target_w
                    scale_y = height / target_h
                    for det in detections:
                        det.bbox = [
                            int(det.bbox[0] * scale_x),
                            int(det.bbox[1] * scale_y),
                            int(det.bbox[2] * scale_x),
                            int(det.bbox[3] * scale_y)
                        ]
                else:
                    detections, annotated = self.frame_handler.process_frame(frame, conf_threshold)
            else:
                detections, annotated = self.frame_handler.process_frame(frame, conf_threshold)

            annotated = self.detector.draw_detections(frame, detections) if self.detector else frame

            inference_time = (time.time() - start_time) * 1000
            if adaptive_controller:
                adaptive_controller.add_measurement(inference_time)

            all_detections.extend(detections)
            frame_count += 1

            if writer:
                writer.write(annotated)

            if self.display:
                display_frame = annotated.copy()
                if adaptive_controller:
                    stats = adaptive_controller.get_stats()
                    cv2.putText(
                        display_frame,
                        f"Mode: {stats['current_mode']} ({stats['current_scale']:.1f}x)",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2
                    )
                cv2.imshow("Traffic Sign Detection", display_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            if frame_count % 100 == 0:
                print(f"[INFO] Processed {frame_count}/{total_frames} frames")

        cap.release()
        if writer:
            writer.release()
        cv2.destroyAllWindows()

        print(f"[INFO] Video processing complete. Total frames: {frame_count}")
        stats = self.frame_handler.get_statistics(all_detections)
        print(f"[INFO] Detection statistics: {stats}")

        return frame_count

    def stop(self):
        self._running = False
        if self.per_frame_processor:
            self.per_frame_processor.stop()
        self.stream_source.release()

        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
        if self._display_thread:
            self._display_thread.join(timeout=2.0)

        cv2.destroyAllWindows()

        elapsed = time.time() - self._start_time if self._start_time > 0 else 0
        print(f"[INFO] Video processor stopped")
        print(f"[INFO] Frames captured: {self._frames_captured}")
        print(f"[INFO] Frames processed: {self._frames_processed}")
        if elapsed > 0:
            print(f"[INFO] Average FPS: {self._frames_processed / elapsed:.2f}")

    def _draw_enhanced_annotations(
        self,
        image: np.ndarray,
        detections: List[DetectionResult]
    ) -> np.ndarray:
        output = image.copy()

        colors = {
            "speed_limit": (0, 0, 255),
            "prohibitory": (0, 0, 255),
            "indicative": (0, 255, 0),
            "warning": (0, 255, 255),
            "unknown": (128, 128, 128)
        }

        distance_map = {dr.detection.bbox[1]: dr for dr in self.distance_results}
        temporal_map = {sr.detection.bbox[1]: sr for sr in self.temporal_results}
        adapted_map = {ad.original_class: ad for ad in self.adapted_detections}

        for det in detections:
            x1, y1, x2, y2 = det.bbox

            if det.is_small_target:
                color = (255, 0, 255)
                thickness = 3
            else:
                color = colors.get(det.category, (255, 255, 255))
                thickness = 2

            if self.enable_country_adaptation and self.country_adapter:
                country_color = self.country_adapter.adapt_color(det.category)
                if country_color != (255, 255, 255):
                    color = country_color

            stable_tag = ""
            if y1 in temporal_map:
                sr = temporal_map[y1]
                if sr.is_stable:
                    stable_tag = " [S]"
                    color = (0, 128, 255)

            cv2.rectangle(output, (x1, y1), (x2, y2), color, thickness)

            label_parts = [det.class_name_zh]

            if y1 in distance_map and self.enable_distance_estimation:
                dr = distance_map[y1]
                label_parts.append(f"{dr.distance.distance:.1f}m")

            conf = det.confidence
            label_parts.append(f"{conf:.2f}")

            if det.scale == "high_res":
                label_parts.append("HR")
            if det.is_small_target:
                label_parts.append("S")

            label = " ".join(label_parts) + stable_tag

            (label_w, label_h), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )

            cv2.rectangle(
                output,
                (x1, y1 - label_h - 4),
                (x1 + label_w + 4, y1),
                color,
                -1
            )
            cv2.putText(
                output, label, (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
            )

        return output

    def set_country(self, country_code: str) -> bool:
        if self.country_adapter:
            return self.country_adapter.set_country(country_code)
        return False

    def get_supported_countries(self) -> List[Dict]:
        if self.country_adapter:
            return self.country_adapter.get_supported_countries()
        return []

    def get_current_country(self) -> str:
        if self.country_adapter:
            return self.country_adapter.current_country
        return "CN"

    def get_enhanced_results(self) -> Dict:
        return {
            "temporal": [
                {
                    "track_id": sr.track_id,
                    "smoothed_confidence": sr.smoothed_confidence,
                    "is_stable": sr.is_stable,
                    "frames_seen": sr.frames_seen,
                    "detection": sr.detection.to_dict()
                }
                for sr in self.temporal_results
            ],
            "distances": [
                {
                    "distance": dr.distance.distance,
                    "unit": dr.distance.unit,
                    "confidence": dr.distance.confidence,
                    "method": dr.distance.method,
                    "class_name": dr.distance.class_name
                }
                for dr in self.distance_results
            ],
            "adapted": [
                {
                    "original_class": ad.original_class,
                    "adapted_class": ad.adapted_class,
                    "country_code": ad.country_code,
                    "local_name": ad.local_name
                }
                for ad in self.adapted_detections
            ]
        }

    def get_info(self) -> dict:
        info = {
            "stream": self.stream_source.get_info(),
            "detector_available": self.detector is not None,
            "conf_threshold": self.frame_handler.conf_threshold,
            "running": self._running,
            "per_frame_processing": self.process_every_frame,
            "adaptive_resolution": self.enable_adaptive_resolution,
            "temporal_fusion": self.enable_temporal_fusion,
            "distance_estimation": self.enable_distance_estimation,
            "country_adaptation": self.enable_country_adaptation,
            "current_country": self.get_current_country(),
            "frames_captured": self._frames_captured,
            "frames_processed": self._frames_processed
        }

        if self.per_frame_processor:
            info["processing_stats"] = self.per_frame_processor.get_processing_stats()

        if self.temporal_fusion:
            info["temporal_stats"] = self.temporal_fusion.get_tracking_stats()

        return info
