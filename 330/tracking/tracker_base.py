"""
Abstract base class for single-object trackers.
"""

from __future__ import annotations

import abc
from typing import Any, Dict, Optional, Tuple

import numpy as np


BBox = Tuple[float, float, float, float]  # (x, y, w, h) top-left origin


class BaseTracker(abc.ABC):
    """
    Interface for a single-object tracker.

    All concrete trackers must implement :meth:`init` and :meth:`update`.
    Coordinates follow the OpenCV convention: ``(x, y, w, h)`` with the origin
    at the top-left corner of the image.
    """

    name: str = "BaseTracker"

    def __init__(self) -> None:
        self._initialized: bool = False
        self._bbox: Optional[BBox] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def bbox(self) -> Optional[BBox]:
        return self._bbox

    def init(self, frame: np.ndarray, bbox: BBox) -> bool:
        """Initialize the tracker on *frame* with the given *bbox*."""
        ok = self._init(frame, bbox)
        if ok:
            self._initialized = True
            self._bbox = tuple(float(v) for v in bbox)  # type: ignore[assignment]
        return ok

    def update(self, frame: np.ndarray) -> Tuple[bool, BBox]:
        """
        Advance the tracker to the next *frame*.

        Returns
        -------
        (ok, bbox)
            ``ok`` is ``False`` when the tracker has lost the target.
        """
        if not self._initialized:
            return False, (0.0, 0.0, 0.0, 0.0)
        ok, bbox = self._update(frame)
        if ok:
            self._bbox = tuple(float(v) for v in bbox)  # type: ignore[assignment]
        return ok, self._bbox  # type: ignore[return-value]

    def reset(self) -> None:
        """Clear internal state so the tracker can be re-initialized."""
        self._initialized = False
        self._bbox = None
        self._reset()

    def state_dict(self) -> Dict[str, Any]:
        """Return a serialisable snapshot of the tracker state."""
        return {
            "name": self.name,
            "initialized": self._initialized,
            "bbox": self._bbox,
        }

    # ------------------------------------------------------------------
    # Hooks for subclasses
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def _init(self, frame: np.ndarray, bbox: BBox) -> bool: ...

    @abc.abstractmethod
    def _update(self, frame: np.ndarray) -> Tuple[bool, BBox]: ...

    def _reset(self) -> None:  # pragma: no cover - trivial hook
        pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_bbox(bbox: BBox) -> None:
        if len(bbox) != 4:
            raise ValueError(f"bbox must have length 4, got {len(bbox)}")
        x, y, w, h = bbox
        if w <= 0 or h <= 0:
            raise ValueError(f"bbox width/height must be positive, got {(w, h)}")
