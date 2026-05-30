import time
import numpy as np
from typing import Dict, List, Optional, Tuple
from collections import deque
from dataclasses import dataclass, field

from config import Config


@dataclass
class FrameMetrics:
    frame_index: int
    num_detections: int = 0
    num_tracks: int = 0
    num_matches: int = 0
    num_false_positives: int = 0
    num_false_negatives: int = 0
    num_id_switches: int = 0
    num_fragmentations: int = 0
    processing_time_ms: float = 0.0


class TrackingMetrics:
    def __init__(
        self,
        window_size: Optional[int] = None,
        gt_source: Optional[str] = None,
    ):
        self.window_size = window_size or Config.METRICS_WINDOW_SIZE

        self.frame_metrics: deque = deque(maxlen=self.window_size)
        self.id_switches: deque = deque(maxlen=self.window_size)
        self.track_id_history: Dict[int, int] = {}
        self.prev_track_ids: Dict[int, int] = {}
        self.gt_source = gt_source
        self.gt_data: Dict[int, List[Dict]] = {}

        self.total_frames = 0
        self.total_detections = 0
        self.total_tracks = 0
        self.total_matches = 0
        self.total_id_switches = 0
        self.total_false_positives = 0
        self.total_false_negatives = 0

        self.fps_history: deque = deque(maxlen=60)
        self.last_frame_time = 0.0
        self.current_fps = 0.0

        self.track_age_map: Dict[int, int] = {}
        self.track_fragmentation: Dict[int, int] = {}

    def update(
        self,
        frame_index: int,
        detections: np.ndarray,
        tracks: List[Dict],
        processing_time_ms: float = 0.0,
    ) -> FrameMetrics:
        current_time = time.time()
        if self.last_frame_time > 0:
            dt = current_time - self.last_frame_time
            if dt > 0:
                instant_fps = 1.0 / dt
                self.fps_history.append(instant_fps)
                self.current_fps = np.mean(list(self.fps_history)) if self.fps_history else 0.0
        self.last_frame_time = current_time

        self.total_frames += 1
        num_detections = len(detections) if detections is not None and len(detections) > 0 else 0
        num_tracks = len(tracks)
        self.total_detections += num_detections
        self.total_tracks += num_tracks

        id_switches = self._detect_id_switches(tracks)
        self.total_id_switches += id_switches

        num_matches = min(num_detections, num_tracks)
        num_fp = max(0, num_tracks - num_matches)
        num_fn = max(0, num_detections - num_matches)
        self.total_matches += num_matches
        self.total_false_positives += num_fp
        self.total_false_negatives += num_fn

        for track in tracks:
            tid = track["id"]
            if tid not in self.track_age_map:
                self.track_age_map[tid] = 0
            self.track_age_map[tid] += 1

            if track.get("time_since_update", 0) > 0:
                self.track_fragmentation[tid] = self.track_fragmentation.get(tid, 0) + 1

        metrics = FrameMetrics(
            frame_index=frame_index,
            num_detections=num_detections,
            num_tracks=num_tracks,
            num_matches=num_matches,
            num_false_positives=num_fp,
            num_false_negatives=num_fn,
            num_id_switches=id_switches,
            processing_time_ms=processing_time_ms,
        )
        self.frame_metrics.append(metrics)

        return metrics

    def _detect_id_switches(self, tracks: List[Dict]) -> int:
        if len(tracks) == 0:
            return 0

        current_map: Dict[int, int] = {}
        for track in tracks:
            tid = track["id"]
            bbox = track["bbox"]
            center = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
            grid_key = (int(center[0] / 50), int(center[1] / 50))
            current_map[grid_key] = tid

        switches = 0
        for grid_key, current_id in current_map.items():
            if grid_key in self.prev_track_ids:
                prev_id = self.prev_track_ids[grid_key]
                if prev_id != current_id and prev_id in self.track_id_history:
                    if self.track_id_history[prev_id] != current_id:
                        switches += 1
                        self.track_id_history[prev_id] = current_id

        for grid_key, tid in current_map.items():
            if tid not in self.track_id_history:
                self.track_id_history[tid] = tid
            self.prev_track_ids[grid_key] = tid

        return switches

    def compute_mota(self) -> float:
        if self.total_detections == 0:
            return 1.0

        fn = self.total_false_negatives
        fp = self.total_false_positives
        idsw = self.total_id_switches
        gt = self.total_detections

        mota = 1.0 - (fn + fp + idsw) / gt
        return max(0.0, mota)

    def compute_motp(self) -> float:
        if len(self.frame_metrics) == 0:
            return 0.0

        recent_metrics = list(self.frame_metrics)
        if self.total_matches == 0:
            return 0.0

        avg_iou_estimate = max(0.0, 1.0 - self.total_false_positives / (self.total_matches + 1e-6))
        return avg_iou_estimate

    def compute_idf1(self) -> float:
        if self.total_detections == 0 and self.total_tracks == 0:
            return 1.0

        idsw = self.total_id_switches
        total_matches = self.total_matches

        idtp = max(0, total_matches - idsw)
        idfn = self.total_false_negatives + idsw
        idfp = self.total_false_positives + idsw

        if idtp == 0:
            return 0.0

        precision = idtp / (idtp + idfp + 1e-6)
        recall = idtp / (idtp + idfn + 1e-6)

        if precision + recall < 1e-6:
            return 0.0

        idf1 = 2 * precision * recall / (precision + recall)
        return idf1

    def compute_precision(self) -> float:
        total_pred = self.total_matches + self.total_false_positives
        if total_pred == 0:
            return 1.0
        return self.total_matches / total_pred

    def compute_recall(self) -> float:
        total_gt = self.total_matches + self.total_false_negatives
        if total_gt == 0:
            return 1.0
        return self.total_matches / total_gt

    def compute_fragmentation_rate(self) -> float:
        if len(self.track_age_map) == 0:
            return 0.0
        total_frag = sum(self.track_fragmentation.values())
        total_age = sum(self.track_age_map.values())
        if total_age == 0:
            return 0.0
        return total_frag / total_age

    def get_dashboard_data(self) -> Dict:
        return {
            "mota": round(self.compute_mota(), 4),
            "motp": round(self.compute_motp(), 4),
            "idf1": round(self.compute_idf1(), 4),
            "precision": round(self.compute_precision(), 4),
            "recall": round(self.compute_recall(), 4),
            "fps": round(self.current_fps, 1),
            "total_frames": self.total_frames,
            "total_detections": self.total_detections,
            "total_tracks": self.total_tracks,
            "total_matches": self.total_matches,
            "total_id_switches": self.total_id_switches,
            "total_false_positives": self.total_false_positives,
            "total_false_negatives": self.total_false_negatives,
            "fragmentation_rate": round(self.compute_fragmentation_rate(), 4),
            "active_tracks": len(self.track_age_map),
        }

    def get_trend_data(self, n: int = 30) -> Dict:
        recent = list(self.frame_metrics)[-n:]
        if len(recent) == 0:
            return {"frames": [], "mota": [], "idf1": [], "fps": []}

        frames = [m.frame_index for m in recent]
        detections_per_frame = [m.num_detections for m in recent]
        tracks_per_frame = [m.num_tracks for m in recent]
        processing_times = [m.processing_time_ms for m in recent]

        return {
            "frames": frames,
            "detections_per_frame": detections_per_frame,
            "tracks_per_frame": tracks_per_frame,
            "processing_times_ms": processing_times,
        }

    def reset(self):
        self.frame_metrics.clear()
        self.id_switches.clear()
        self.track_id_history.clear()
        self.prev_track_ids.clear()
        self.total_frames = 0
        self.total_detections = 0
        self.total_tracks = 0
        self.total_matches = 0
        self.total_id_switches = 0
        self.total_false_positives = 0
        self.total_false_negatives = 0
        self.fps_history.clear()
        self.last_frame_time = 0.0
        self.current_fps = 0.0
        self.track_age_map.clear()
        self.track_fragmentation.clear()


class DashboardRenderer:
    def __init__(self):
        self.panel_width = 280
        self.bg_color = (40, 40, 40)
        self.text_color = (220, 220, 220)
        self.accent_color = (0, 180, 255)
        self.warning_color = (0, 165, 255)
        self.danger_color = (0, 0, 255)
        self.success_color = (0, 200, 0)

    def render(self, frame: np.ndarray, metrics: TrackingMetrics) -> np.ndarray:
        h, w = frame.shape[:2]
        panel = np.full((h, self.panel_width, 3), self.bg_color[0], dtype=np.uint8)
        panel[:, :, 0] = self.bg_color[0]
        panel[:, :, 1] = self.bg_color[1]
        panel[:, :, 2] = self.bg_color[2]

        y = 15
        y = self._draw_title(panel, y, "TRACKING METRICS")

        data = metrics.get_dashboard_data()

        y = self._draw_metric(panel, y, "MOTA", data["mota"], self._score_color(data["mota"]))
        y = self._draw_metric(panel, y, "MOTP", data["motp"], self._score_color(data["motp"]))
        y = self._draw_metric(panel, y, "IDF1", data["idf1"], self._score_color(data["idf1"]))
        y = self._draw_metric(panel, y, "Precision", data["precision"], self._score_color(data["precision"]))
        y = self._draw_metric(panel, y, "Recall", data["recall"], self._score_color(data["recall"]))

        y = self._draw_separator(panel, y)
        y = self._draw_title(panel, y, "PERFORMANCE")

        y = self._draw_metric(panel, y, "FPS", data["fps"], self._fps_color(data["fps"]))
        y = self._draw_metric(panel, y, "Frames", data["total_frames"], self.text_color)
        y = self._draw_metric(panel, y, "Active Tracks", data["active_tracks"], self.text_color)
        y = self._draw_metric(panel, y, "ID Switches", data["total_id_switches"],
                              self.danger_color if data["total_id_switches"] > 5 else self.text_color)
        y = self._draw_metric(panel, y, "False Pos", data["total_false_positives"], self.warning_color)
        y = self._draw_metric(panel, y, "False Neg", data["total_false_negatives"], self.warning_color)
        y = self._draw_metric(panel, y, "Fragment Rate", data["fragmentation_rate"],
                              self.danger_color if data["fragmentation_rate"] > 0.3 else self.text_color)

        y = self._draw_separator(panel, y)
        self._draw_bar_chart(panel, y, metrics)

        combined = np.hstack([panel, frame])
        return combined

    def _draw_title(self, panel: np.ndarray, y: int, text: str) -> int:
        import cv2
        cv2.putText(panel, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.accent_color, 2, cv2.LINE_AA)
        return y + 25

    def _draw_metric(self, panel: np.ndarray, y: int, label: str, value, color) -> int:
        import cv2
        if isinstance(value, float):
            value_str = f"{value:.3f}" if value < 100 else f"{value:.1f}"
        else:
            value_str = str(value)
        cv2.putText(panel, f"{label}:", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.text_color, 1, cv2.LINE_AA)
        cv2.putText(panel, value_str, (150, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
        return y + 22

    def _draw_separator(self, panel: np.ndarray, y: int) -> int:
        import cv2
        cv2.line(panel, (10, y), (self.panel_width - 10, y), (80, 80, 80), 1)
        return y + 10

    def _draw_bar_chart(self, panel: np.ndarray, y: int, metrics: TrackingMetrics):
        import cv2
        trend = metrics.get_trend_data(n=20)
        if len(trend["detections_per_frame"]) == 0:
            return

        cv2.putText(panel, "Detection Trend:", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.text_color, 1, cv2.LINE_AA)
        y += 18

        bars = trend["detections_per_frame"]
        max_val = max(bars) if bars else 1
        if max_val == 0:
            max_val = 1

        bar_width = (self.panel_width - 20) // max(len(bars), 1)
        bar_width = max(bar_width, 4)
        max_bar_height = 60

        for i, val in enumerate(bars):
            bar_height = int((val / max_val) * max_bar_height)
            x = 10 + i * bar_width
            cv2.rectangle(
                panel,
                (x, y + max_bar_height - bar_height),
                (x + bar_width - 1, y + max_bar_height),
                self.accent_color,
                -1,
            )

    def _score_color(self, score: float) -> Tuple[int, int, int]:
        if score >= 0.8:
            return self.success_color
        elif score >= 0.5:
            return self.warning_color
        else:
            return self.danger_color

    def _fps_color(self, fps: float) -> Tuple[int, int, int]:
        if fps >= 25:
            return self.success_color
        elif fps >= 15:
            return self.warning_color
        else:
            return self.danger_color
