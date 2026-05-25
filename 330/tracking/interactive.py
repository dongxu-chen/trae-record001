"""
Interactive parameter tuning tool.

Provides a simple OpenCV-based GUI with trackbars for adjusting tracker
parameters in real time while watching the tracking output.

Usage::

    from tracking.interactive import TrackerTuner

    tuner = TrackerTuner(
        video_source=0,
        tracker_type="KCF",
        params={"iou_threshold": (0.1, 0.9, 0.3, 0.01)},
    )
    tuner.run()
"""

from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple

import cv2
import numpy as np

from .tracker_manager import TrackerManager
from .trackers import DeepSORTTracker
from .visualize import TrackVisualizer


# ---------------------------------------------------------------------------
# Parameter specification
# ---------------------------------------------------------------------------
class _ParamSpec:
    """Specification for a single tunable parameter."""

    __slots__ = ("name", "min_val", "max_val", "default", "step", "int_mode")

    def __init__(
        self,
        name: str,
        min_val: float,
        max_val: float,
        default: float,
        step: float = 0.01,
    ) -> None:
        self.name = name
        self.min_val = min_val
        self.max_val = max_val
        self.default = default
        self.step = step
        self.int_mode = step >= 1.0


# ---------------------------------------------------------------------------
# Default parameter sets
# ---------------------------------------------------------------------------
DEFAULT_PARAMS: Dict[str, Dict[str, Tuple[float, float, float, float]]] = {
    "KCF": {
        "iou_threshold": (0.1, 0.9, 0.3, 0.01),
        "max_misses": (1, 100, 15, 1),
        "n_init": (1, 10, 1, 1),
    },
    "CSRT": {
        "iou_threshold": (0.1, 0.9, 0.3, 0.01),
        "max_misses": (1, 100, 15, 1),
        "n_init": (1, 10, 1, 1),
    },
    "SiamRPN": {
        "iou_threshold": (0.1, 0.9, 0.3, 0.01),
        "max_misses": (1, 100, 15, 1),
        "n_init": (1, 10, 1, 1),
    },
    "DeepSORT": {
        "iou_threshold": (0.1, 0.9, 0.3, 0.01),
        "max_iou_distance": (0.1, 0.9, 0.7, 0.01),
        "max_appearance_distance": (0.01, 0.5, 0.2, 0.01),
        "max_age": (1, 100, 30, 1),
        "n_init": (1, 10, 3, 1),
        "lambda_": (0.5, 1.0, 0.98, 0.01),
    },
}


# ---------------------------------------------------------------------------
# Interactive tuner
# ---------------------------------------------------------------------------
class TrackerTuner:
    """
    Interactive GUI for tuning tracker parameters.

    Displays a window with the video and a set of trackbars for each
    parameter.  Changes to trackbars take effect immediately (tracker is
    re-initialised with new parameters on the next frame).

    Parameters
    ----------
    video_source:
        Path to a video file or integer camera index.
    tracker_type:
        One of ``"KCF"``, ``"CSRT"``, ``"SiamRPN"``, ``"DeepSORT"``.
    params:
        ``{param_name: (min, max, default, step)}``.  Falls back to
        :data:`DEFAULT_PARAMS` if ``None``.
    detector:
        Optional callable ``(frame) -> list of (x, y, w, h)`` detections.
        When ``None``, a simple background-subtraction detector is used.
    window_name:
        OpenCV window name.
    """

    def __init__(
        self,
        video_source: str | int,
        tracker_type: str = "KCF",
        params: Optional[Dict[str, Tuple[float, float, float, float]]] = None,
        detector: Optional[Callable[[np.ndarray], list]] = None,
        window_name: str = "Tracker Tuner",
    ) -> None:
        self.video_source = video_source
        self.tracker_type = tracker_type
        self.window_name = window_name
        self.detector = detector or self._default_detector

        param_dict = params or DEFAULT_PARAMS.get(tracker_type, {})
        self._param_specs: Dict[str, _ParamSpec] = {
            name: _ParamSpec(name, *spec) for name, spec in param_dict.items()
        }

        self._values: Dict[str, float] = {
            name: spec.default for name, spec in self._param_specs.items()
        }

        self._visualizer = TrackVisualizer()
        self._tracker = self._build_tracker()
        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=200, varThreshold=25, detectShadows=False
        )

    # ------------------------------------------------------------------
    # OpenCV trackbar helpers (trackbars only support int)
    # ------------------------------------------------------------------
    def _trackbar_max(self, spec: _ParamSpec) -> int:
        return int((spec.max_val - spec.min_val) / spec.step)

    def _trackbar_to_value(self, trackbar_pos: int, spec: _ParamSpec) -> float:
        v = spec.min_val + trackbar_pos * spec.step
        if spec.int_mode:
            return int(round(v))
        return float(round(v, 4))

    def _value_to_trackbar(self, value: float, spec: _ParamSpec) -> int:
        return int((value - spec.min_val) / spec.step)

    def _on_trackbar(self, name: str) -> Callable[[int], None]:
        def _cb(pos: int) -> None:
            spec = self._param_specs[name]
            self._values[name] = self._trackbar_to_value(pos, spec)
        return _cb

    # ------------------------------------------------------------------
    # Tracker construction
    # ------------------------------------------------------------------
    def _build_tracker(self):
        if self.tracker_type == "DeepSORT":
            return DeepSORTTracker(
                iou_threshold=float(self._values.get("iou_threshold", 0.3)),
                max_iou_distance=float(self._values.get("max_iou_distance", 0.7)),
                max_appearance_distance=float(self._values.get("max_appearance_distance", 0.2)),
                max_age=int(self._values.get("max_age", 30)),
                n_init=int(self._values.get("n_init", 3)),
                lambda_=float(self._values.get("lambda_", 0.98)),
                enable_dynamic_thresholds=True,
            )
        return TrackerManager(
            tracker_type=self.tracker_type,
            iou_threshold=float(self._values.get("iou_threshold", 0.3)),
            max_misses=int(self._values.get("max_misses", 15)),
            n_init=int(self._values.get("n_init", 1)),
            enable_kalman=True,
            enable_appearance=True,
            enable_dynamic_thresholds=True,
        )

    # ------------------------------------------------------------------
    # Default detector
    # ------------------------------------------------------------------
    def _default_detector(self, frame: np.ndarray) -> list:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        fg_mask = self._bg_subtractor.apply(gray)
        _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w * h > 500:  # filter tiny blobs
                detections.append((float(x), float(y), float(w), float(h)))
        return detections

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        cap = cv2.VideoCapture(self.video_source)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video source {self.video_source}")

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

        # Create trackbars
        for name, spec in self._param_specs.items():
            max_pos = self._trackbar_max(spec)
            init_pos = self._value_to_trackbar(spec.default, spec)
            cv2.createTrackbar(name, self.window_name, init_pos, max_pos, self._on_trackbar(name))

        frame_id = 0
        paused = False

        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_id += 1

                # Detect
                detections = self.detector(frame)

                # Track
                if self.tracker_type == "DeepSORT":
                    tracks = self._tracker.multi_update(frame, detections)
                else:
                    tracks = self._tracker.update(frame, detections)

                # Draw
                vis_frame = self._visualizer.draw(
                    frame,
                    tracks,
                    info={
                        "Frame": str(frame_id),
                        "Tracks": str(len(tracks)),
                        "Detections": str(len(detections)),
                        "Tracker": self.tracker_type,
                    },
                )
                self._visualizer.update(tracks)

                cv2.imshow(self.window_name, vis_frame)
            else:
                # When paused, still show last frame
                cv2.imshow(self.window_name, vis_frame)  # noqa: F821

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("p"):
                paused = not paused
            elif key == ord("r"):
                # Rebuild tracker with current parameters
                self._tracker = self._build_tracker()
                self._visualizer.reset()
                print("Tracker re-initialised with new parameters:", self._values)

        cap.release()
        cv2.destroyAllWindows()


# ---------------------------------------------------------------------------
# Convenience: one-shot parameter sweep
# ---------------------------------------------------------------------------
def sweep_parameters(
    video_frames,
    ground_truth,
    tracker_type: str,
    param_name: str,
    param_range: list,
    metric: str = "MOTA",
    **fixed_kwargs,
) -> list:
    """
    Evaluate a single parameter over a range of values.

    Returns a list of ``(param_value, score)`` tuples.
    """
    from .evaluate import Evaluator

    results = []
    for val in param_range:
        kwargs = dict(fixed_kwargs)
        kwargs[param_name] = val

        if tracker_type == "DeepSORT":
            tracker = DeepSORTTracker(**kwargs)
        else:
            tracker = TrackerManager(tracker_type=tracker_type, **kwargs)

        evaluator = Evaluator(iou_threshold=0.5)
        for fid, (frame, gt) in enumerate(zip(video_frames, ground_truth)):
            dets = [bbox for _, bbox in gt]
            if tracker_type == "DeepSORT":
                preds = tracker.multi_update(frame, dets)
            else:
                preds = tracker.update(frame, dets)
            evaluator.update(fid, gt, preds)

        m = evaluator.compute()
        results.append((val, m.get(metric, 0.0)))
    return results
