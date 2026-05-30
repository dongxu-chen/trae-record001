import cv2
import time
import numpy as np
import supervision as sv
from typing import Generator, List, Optional, Tuple

from detector import YOLODetector
from tracker import DeepSORT
from anomaly import AnomalyDetector, AnomalyType
from cross_camera import CrossCameraTracker
from metrics import TrackingMetrics, DashboardRenderer
from config import Config


class ColorGenerator:
    def __init__(self, num_colors: int = 100):
        self.colors = {}
        self.num_colors = num_colors

    def get_color(self, track_id: int) -> Tuple[int, int, int]:
        if track_id not in self.colors:
            self.colors[track_id] = self._generate_color(track_id)
        return self.colors[track_id]

    def _generate_color(self, track_id: int) -> Tuple[int, int, int]:
        np.random.seed(track_id)
        color = tuple(np.random.randint(50, 255, 3).tolist())
        return int(color[0]), int(color[1]), int(color[2])


class VideoProcessor:
    def __init__(
        self,
        detector: Optional[YOLODetector] = None,
        tracker: Optional[DeepSORT] = None,
        skip_frame_enable: Optional[bool] = None,
        detect_interval: Optional[int] = None,
        interpolation_enable: Optional[bool] = None,
        anomaly_enable: Optional[bool] = None,
        cross_camera_enable: Optional[bool] = None,
        metrics_enable: Optional[bool] = None,
        camera_id: str = "cam_0",
    ):
        self.detector = detector or YOLODetector()
        self.tracker = tracker or DeepSORT()
        self.color_generator = ColorGenerator()

        self.skip_frame_enable = skip_frame_enable if skip_frame_enable is not None else Config.SKIP_FRAME_ENABLE
        self.detect_interval = detect_interval or Config.DETECT_INTERVAL
        self.interpolation_enable = interpolation_enable if interpolation_enable is not None else Config.MOTION_INTERPOLATION_ENABLE
        self.anomaly_enable = anomaly_enable if anomaly_enable is not None else Config.ANOMALY_ENABLE
        self.cross_camera_enable = cross_camera_enable if cross_camera_enable is not None else Config.CROSS_CAMERA_ENABLE
        self.metrics_enable = metrics_enable if metrics_enable is not None else Config.METRICS_ENABLE
        self.camera_id = camera_id

        self.anomaly_detector = AnomalyDetector()
        self.cross_camera_tracker = CrossCameraTracker()
        self.metrics = TrackingMetrics()
        self.dashboard_renderer = DashboardRenderer()

        self.frame_count = 0
        self.last_detection_frame = -1
        self.last_detected_boxes = None
        self.last_detected_features = None
        self.last_process_time = 0.0

        self.box_annotator = sv.BoxAnnotator(
            thickness=Config.LINE_THICKNESS,
        )
        self.label_annotator = sv.LabelAnnotator(
            text_scale=Config.TEXT_SCALE,
            text_thickness=Config.TEXT_THICKNESS,
        )

    def process_frame(
        self,
        frame: np.ndarray,
        force_detect: bool = False,
    ) -> Tuple[np.ndarray, List[dict]]:
        start_time = time.time()
        self.frame_count += 1
        frame_idx = self.frame_count

        should_detect = force_detect or not self.skip_frame_enable
        if self.skip_frame_enable and not should_detect:
            should_detect = (frame_idx % self.detect_interval == 1)

        features_for_tracks = None
        if should_detect:
            boxes, confidences, class_ids, features = self.detector.detect(frame)
            tracks = self.tracker.update(boxes, confidences, class_ids, features)
            self.last_detection_frame = frame_idx
            self.last_detected_boxes = boxes
            self.last_detected_features = features
            features_for_tracks = features

            for track in tracks:
                track["is_predicted"] = False
                track["time_since_update"] = 0
        else:
            tracks = self.tracker.predict_only()

            if self.interpolation_enable and self.detect_interval > 1:
                frames_since_detect = frame_idx - self.last_detection_frame
                alpha = frames_since_detect / self.detect_interval
                tracks = self.tracker.get_interpolated_tracks(alpha=alpha)

        if self.anomaly_enable:
            tracks = self._detect_anomalies(tracks, frame_idx)

        if self.cross_camera_enable:
            tracks = self.cross_camera_tracker.update(
                self.camera_id, tracks, features_for_tracks
            )

        if self.metrics_enable:
            detections_for_metrics = self.last_detected_boxes if self.last_detected_boxes is not None else np.empty((0, 4))
            process_time_ms = (time.time() - start_time) * 1000
            self.metrics.update(frame_idx, detections_for_metrics, tracks, process_time_ms)
            self.last_process_time = process_time_ms

        annotated_frame = self._annotate_frame(frame, tracks)

        return annotated_frame, tracks

    def _annotate_frame(self, frame: np.ndarray, tracks: List[dict]) -> np.ndarray:
        if len(tracks) == 0:
            return frame.copy()

        annotated_frame = frame.copy()

        if Config.SHOW_TRAILS:
            annotated_frame = self._draw_trails(annotated_frame, tracks)

        predicted_tracks = [t for t in tracks if t.get("is_predicted", False)]
        detected_tracks = [t for t in tracks if not t.get("is_predicted", False)]

        if len(predicted_tracks) > 0:
            self._draw_predicted_boxes(annotated_frame, predicted_tracks)

        if len(detected_tracks) > 0:
            detections = sv.Detections(
                xyxy=np.array([t["bbox"] for t in detected_tracks]),
                class_id=np.array([t["class_id"] for t in detected_tracks], dtype=np.int32),
                confidence=np.array([t["confidence"] for t in detected_tracks], dtype=np.float32),
                tracker_id=np.array([t["id"] for t in detected_tracks], dtype=np.int32),
            )

            labels = [
                f"ID:{t['id']} {self.detector.get_class_name(t['class_id'])}"
                for t in detected_tracks
            ]

            annotated_frame = self.box_annotator.annotate(
                scene=annotated_frame,
                detections=detections,
            )
            annotated_frame = self.label_annotator.annotate(
                scene=annotated_frame,
                detections=detections,
                labels=labels,
            )

        if len(predicted_tracks) > 0:
            for t in predicted_tracks:
                x1, y1, x2, y2 = map(int, t["bbox"])
                color = self.color_generator.get_color(t["id"])
                label = f"ID:{t['id']} (预测)"
                cv2.putText(
                    annotated_frame,
                    label,
                    (x1, max(y1 - 10, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    1,
                    cv2.LINE_AA,
                )

        if self.skip_frame_enable:
            mode_text = f"跳帧模式: 每{self.detect_interval}帧检测"
            cv2.putText(
                annotated_frame,
                mode_text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

        if self.detector.high_res_enable:
            hr_text = "高分辨率分支: 开启"
            cv2.putText(
                annotated_frame,
                hr_text,
                (10, 55),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 165, 0),
                1,
            )

        if self.anomaly_enable:
            anomaly_tracks = [t for t in tracks if t.get("anomalies")]
            for t in anomaly_tracks:
                x1, y1, x2, y2 = map(int, t["bbox"])
                anomalies = t.get("anomalies", [])
                anomaly_labels = [a.value.replace("_", " ").upper() for a in anomalies]
                anomaly_text = " | ".join(anomaly_labels[:2])
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                cv2.putText(
                    annotated_frame,
                    f"! {anomaly_text}",
                    (x1, max(y1 - 30, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )

            if anomaly_tracks:
                cv2.putText(
                    annotated_frame,
                    f"Anomalies: {len(anomaly_tracks)}",
                    (10, 80 if self.detector.high_res_enable else 55),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 255),
                    1,
                )

        for track in tracks:
            gid = track.get("global_id", -1)
            if gid >= 0 and track.get("is_cross_camera", False):
                x1, y1, x2, y2 = map(int, track["bbox"])
                cv2.putText(
                    annotated_frame,
                    f"G:{gid}",
                    (x2 + 5, y1 + 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (255, 200, 0),
                    1,
                    cv2.LINE_AA,
                )

        if self.metrics_enable:
            annotated_frame = self.dashboard_renderer.render(annotated_frame, self.metrics)

        return annotated_frame

    def _draw_predicted_boxes(self, frame: np.ndarray, tracks: List[dict]) -> np.ndarray:
        for track in tracks:
            x1, y1, x2, y2 = map(int, track["bbox"])
            track_id = track["id"]
            color = self.color_generator.get_color(track_id)

            overlay = frame.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 1)
            alpha = 0.5
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

            dash_length = 10
            gap_length = 5
            for x in range(x1, x2, dash_length + gap_length):
                x_end = min(x + dash_length, x2)
                cv2.line(frame, (x, y1), (x_end, y1), color, 1)
                cv2.line(frame, (x, y2), (x_end, y2), color, 1)
            for y in range(y1, y2, dash_length + gap_length):
                y_end = min(y + dash_length, y2)
                cv2.line(frame, (x1, y), (x1, y_end), color, 1)
                cv2.line(frame, (x2, y), (x2, y_end), color, 1)

        return frame

    def _draw_trails(self, frame: np.ndarray, tracks: List[dict]) -> np.ndarray:
        for track in tracks:
            trail = track["trail"]
            if len(trail) < 2:
                continue

            color = self.color_generator.get_color(track["id"])
            is_predicted = track.get("is_predicted", False)

            pts = np.array(trail, np.int32).reshape((-1, 1, 2))

            if is_predicted:
                cv2.polylines(frame, [pts], False, color, thickness=1, lineType=cv2.LINE_AA)
            else:
                cv2.polylines(frame, [pts], False, color, thickness=2, lineType=cv2.LINE_AA)

            for i in range(len(trail) - 1):
                pt1 = (int(trail[i][0]), int(trail[i][1]))
                pt2 = (int(trail[i + 1][0]), int(trail[i + 1][1]))
                alpha = i / len(trail)
                thickness = max(1, int(3 * alpha))
                if is_predicted:
                    thickness = max(1, thickness - 1)
                cv2.line(frame, pt1, pt2, color, thickness, lineType=cv2.LINE_AA)

            if len(trail) > 0:
                last_pt = (int(trail[-1][0]), int(trail[-1][1]))
                cv2.circle(frame, last_pt, 4, color, -1, lineType=cv2.LINE_AA)

        return frame

    def process_video(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        show_progress: bool = True,
    ) -> Generator[Tuple[np.ndarray, List[dict]], None, None]:
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {input_path}")

        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        writer = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        local_frame_count = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                annotated_frame, tracks = self.process_frame(frame)

                if writer:
                    writer.write(annotated_frame)

                yield annotated_frame, tracks

                local_frame_count += 1
                if show_progress and local_frame_count % 10 == 0:
                    detect_count = local_frame_count // self.detect_interval + 1 if self.skip_frame_enable else local_frame_count
                    print(f"处理进度: {local_frame_count}/{total_frames} 帧 ({100*local_frame_count/total_frames:.1f}%) | 检测次数: {detect_count}")

        finally:
            cap.release()
            if writer:
                writer.release()

    def process_webcam(
        self,
        camera_index: int = 0,
        output_path: Optional[str] = None,
    ) -> Generator[Tuple[np.ndarray, List[dict]], None, None]:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            raise ValueError(f"无法打开摄像头: {camera_index}")

        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        writer = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                annotated_frame, tracks = self.process_frame(frame)

                if writer:
                    writer.write(annotated_frame)

                yield annotated_frame, tracks

        finally:
            cap.release()
            if writer:
                writer.release()

    def reset_tracker(self):
        self.tracker.reset()
        self.frame_count = 0
        self.last_detection_frame = -1
        self.last_detected_boxes = None
        self.last_detected_features = None

    def toggle_skip_frame(self) -> bool:
        self.skip_frame_enable = not self.skip_frame_enable
        self.reset_tracker()
        return self.skip_frame_enable

    def set_detect_interval(self, interval: int) -> int:
        interval = max(1, min(interval, 10))
        self.detect_interval = interval
        self.reset_tracker()
        return self.detect_interval

    def toggle_high_resolution(self) -> bool:
        self.detector.high_res_enable = not self.detector.high_res_enable
        return self.detector.high_res_enable

    def _detect_anomalies(self, tracks: List[dict], frame_index: int) -> List[dict]:
        for track in tracks:
            track_id = track["id"]
            bbox = track["bbox"]
            position = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)

            velocity = np.zeros(2)
            for t in self.tracker.tracks:
                if t.id == track_id:
                    velocity = t.velocity.copy()
                    break

            events = self.anomaly_detector.update_track(
                track_id, position, tuple(velocity), frame_index
            )

            if events:
                track["anomalies"] = [e.anomaly_type for e in events]
                track["anomaly_details"] = [e.to_dict() for e in events]
            else:
                track["anomalies"] = []
                track["anomaly_details"] = []

        active_track_ids = {t["id"] for t in tracks}
        all_tracked_ids = set(self.anomaly_detector.track_stats.keys())
        lost_ids = all_tracked_ids - active_track_ids
        for lost_id in lost_ids:
            self.anomaly_detector.remove_track(lost_id)

        return tracks

    def toggle_anomaly(self) -> bool:
        self.anomaly_enable = not self.anomaly_enable
        if not self.anomaly_enable:
            self.anomaly_detector.reset()
        return self.anomaly_enable

    def toggle_cross_camera(self) -> bool:
        self.cross_camera_enable = not self.cross_camera_enable
        if not self.cross_camera_enable:
            self.cross_camera_tracker.reset()
        return self.cross_camera_enable

    def toggle_metrics(self) -> bool:
        self.metrics_enable = not self.metrics_enable
        if not self.metrics_enable:
            self.metrics.reset()
        return self.metrics_enable

    def get_metrics_data(self) -> dict:
        return self.metrics.get_dashboard_data()

    def get_anomaly_events(self, n: int = 20) -> List[dict]:
        return self.anomaly_detector.get_recent_events(n)

    def get_cross_camera_info(self) -> dict:
        transfers = self.cross_camera_tracker.get_transfer_history()
        active_ids = self.cross_camera_tracker.get_active_global_ids()
        identities = {}
        for gid in list(active_ids)[:20]:
            info = self.cross_camera_tracker.get_identity_info(gid)
            if info:
                identities[str(gid)] = info
        return {
            "active_global_ids": len(active_ids),
            "recent_transfers": transfers,
            "identities": identities,
        }
