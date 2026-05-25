"""
KCF and CSRT trackers backed by OpenCV's Tracker API.
"""

from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np

from ..tracker_base import BBox, BaseTracker


def _make_opencv_tracker(kind: str) -> cv2.Tracker:
    """Factory that handles OpenCV version differences."""
    constructors = {
        "KCF": cv2.TrackerKCF_create,
        "CSRT": cv2.TrackerCSRT_create,
    }
    if kind not in constructors:
        raise ValueError(f"Unknown OpenCV tracker kind: {kind}")
    return constructors[kind]()


class _OpenCVSingleTracker(BaseTracker):
    """Thin wrapper around an OpenCV tracker."""

    def __init__(self, kind: str) -> None:
        super().__init__()
        self._kind = kind
        self.name = f"OpenCV-{kind}"
        self._tracker = _make_opencv_tracker(kind)

    def _init(self, frame: np.ndarray, bbox: BBox) -> bool:
        self._validate_bbox(bbox)
        self._tracker = _make_opencv_tracker(self._kind)
        bbox_int = tuple(int(round(v)) for v in bbox)
        result = self._tracker.init(frame, bbox_int)
        # Some OpenCV builds return None on success.
        return result is not False

    def _update(self, frame: np.ndarray) -> Tuple[bool, BBox]:
        ok, bbox = self._tracker.update(frame)
        bbox = tuple(float(v) for v in bbox)  # type: ignore[assignment]
        return bool(ok), bbox  # type: ignore[return-value]

    def _reset(self) -> None:
        self._tracker = _make_opencv_tracker(self._kind)


class KCFTracker(_OpenCVSingleTracker):
    """Kernelized Correlation Filter tracker."""

    def __init__(self) -> None:
        super().__init__("KCF")
        self.name = "KCF"


class CSRTTracker(_OpenCVSingleTracker):
    """Discriminative Correlation Filter with Channel and Spatial Reliability."""

    def __init__(self) -> None:
        super().__init__("CSRT")
        self.name = "CSRT"
