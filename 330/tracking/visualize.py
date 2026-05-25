"""
Tracking visualization utilities.

Draws bounding boxes, IDs, trajectories, zones and events onto frames
using OpenCV.  Provides both a stateless drawing helper and a
stateful :class:`TrackVisualizer` that accumulates history to draw
trajectories.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from .events import EventType, TrackingEvent, TripLine, Zone


# ---------------------------------------------------------------------------
# Default palette — distinct colours for track IDs
# ---------------------------------------------------------------------------
_DEFAULT_PALETTE = [
    (255, 80, 80),    # blue
    (80, 255, 80),    # green
    (80, 80, 255),    # red
    (255, 200, 80),   # cyan
    (80, 220, 255),   # orange
    (200, 80, 255),   # purple
    (255, 80, 200),   # magenta
    (200, 200, 80),   # teal
]


def _color_for_id(track_id: int) -> Tuple[int, int, int]:
    return _DEFAULT_PALETTE[track_id % len(_DEFAULT_PALETTE)]


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def draw_bboxes(
    frame: np.ndarray,
    tracks: Sequence[Tuple[int, Tuple[float, float, float, float]]],
    show_id: bool = True,
    thickness: int = 2,
    font_scale: float = 0.5,
) -> np.ndarray:
    """
    Draw coloured bounding boxes with optional track IDs.

    Parameters
    ----------
    frame:
        BGR image (modified in-place and returned).
    tracks:
        ``[(track_id, (x, y, w, h)), ...]``.
    """
    for tid, bbox in tracks:
        x, y, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        color = _color_for_id(tid)
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
        if show_id:
            label = f"ID {tid}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
            cv2.rectangle(frame, (x, y - th - 6), (x + tw + 4, y), color, -1)
            cv2.putText(frame, label, (x + 2, y - 4), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1, cv2.LINE_AA)
    return frame


def draw_trajectories(
    frame: np.ndarray,
    history: Dict[int, Deque[Tuple[float, float]]],
    max_points: int = 50,
    thickness: int = 2,
) -> np.ndarray:
    """
    Draw trailing trajectory lines for every track.

    Parameters
    ----------
    history:
        ``{track_id: deque[(cx, cy), ...]}``.
    """
    for tid, pts in history.items():
        if len(pts) < 2:
            continue
        color = _color_for_id(tid)
        pts_list = [(int(p[0]), int(p[1])) for p in pts]
        for i in range(1, len(pts_list)):
            alpha = i / max(max_points, 1)
            c = tuple(int(v * alpha) for v in color)
            cv2.line(frame, pts_list[i - 1], pts_list[i], c, thickness, cv2.LINE_AA)
    return frame


def draw_zones(
    frame: np.ndarray,
    zones: Sequence[Zone],
    thickness: int = 2,
    color: Tuple[int, int, int] = (0, 255, 255),
) -> np.ndarray:
    for z in zones:
        cv2.rectangle(frame, (int(z.x1), int(z.y1)), (int(z.x2), int(z.y2)), color, thickness)
        cv2.putText(frame, z.zone_id, (int(z.x1) + 4, int(z.y1) + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
    return frame


def draw_trip_lines(
    frame: np.ndarray,
    lines: Sequence[TripLine],
    thickness: int = 2,
    color: Tuple[int, int, int] = (255, 255, 0),
) -> np.ndarray:
    for line in lines:
        cv2.line(frame, (int(line.x1), int(line.y1)), (int(line.x2), int(line.y2)), color, thickness, cv2.LINE_AA)
        cv2.putText(frame, line.line_id, (int((line.x1 + line.x2) / 2), int((line.y1 + line.y2) / 2)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
    return frame


def draw_events(
    frame: np.ndarray,
    events: Sequence[TrackingEvent],
    max_events: int = 5,
    origin: Tuple[int, int] = (10, 30),
) -> np.ndarray:
    """Draw recent event log at a corner of the frame."""
    if not events:
        return frame
    x, y = origin
    recent = list(events)[-max_events:]
    h = len(recent) * 18 + 10
    overlay = frame.copy()
    cv2.rectangle(overlay, (x - 4, y - 18), (x + 500, y + h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    for i, e in enumerate(recent):
        cv2.putText(
            frame,
            str(e),
            (x, y + i * 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (200, 200, 200),
            1,
            cv2.LINE_AA,
        )
    return frame


def draw_info_overlay(
    frame: np.ndarray,
    info: Dict[str, str],
    origin: Tuple[int, int] = (10, 30),
) -> np.ndarray:
    """Draw a dictionary of key-value pairs as a semi-transparent panel."""
    if not info:
        return frame
    x, y = origin
    h = len(info) * 18 + 10
    overlay = frame.copy()
    cv2.rectangle(overlay, (x - 4, y - 18), (x + 500, y + h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    for i, (k, v) in enumerate(info.items()):
        cv2.putText(
            frame,
            f"{k}: {v}",
            (x, y + i * 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
    return frame


# ---------------------------------------------------------------------------
# Stateful visualizer
# ---------------------------------------------------------------------------
class TrackVisualizer:
    """
    Stateful visualizer that accumulates per-track history and can draw
    trajectories, zones, events and info overlays on each frame.

    Parameters
    ----------
    max_history:
        Maximum number of centre-points to retain per track.
    """

    def __init__(
        self,
        max_history: int = 50,
        zones: Optional[Sequence[Zone]] = None,
        trip_lines: Optional[Sequence[TripLine]] = None,
    ) -> None:
        self.max_history = max_history
        self._history: Dict[int, Deque[Tuple[float, float]]] = defaultdict(
            lambda: deque(maxlen=max_history)
        )
        self._events: List[TrackingEvent] = []
        self.zones = list(zones) if zones else []
        self.trip_lines = list(trip_lines) if trip_lines else []

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------
    def update(
        self,
        tracks: Sequence[Tuple[int, Tuple[float, float, float, float]]],
        events: Optional[Sequence[TrackingEvent]] = None,
    ) -> None:
        """Update internal history with a new frame of tracks."""
        current_ids: set[int] = set()
        for tid, bbox in tracks:
            cx = bbox[0] + bbox[2] / 2.0
            cy = bbox[1] + bbox[3] / 2.0
            self._history[tid].append((cx, cy))
            current_ids.add(tid)
        # Drop history for tracks that disappeared
        stale = [tid for tid in self._history if tid not in current_ids]
        for tid in stale:
            del self._history[tid]
        if events:
            self._events.extend(events)

    def reset(self) -> None:
        self._history.clear()
        self._events.clear()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(
        self,
        frame: np.ndarray,
        tracks: Sequence[Tuple[int, Tuple[float, float, float, float]]],
        show_trajectories: bool = True,
        show_zones: bool = True,
        show_events: bool = True,
        info: Optional[Dict[str, str]] = None,
    ) -> np.ndarray:
        """
        Render everything onto a frame and return it.
        """
        out = frame.copy()

        if show_zones:
            draw_zones(out, self.zones)
            draw_trip_lines(out, self.trip_lines)

        if show_trajectories:
            draw_trajectories(out, self._history, self.max_history)

        draw_bboxes(out, tracks)

        if show_events:
            draw_events(out, self._events)

        if info:
            draw_info_overlay(out, info, origin=(10, 30))

        return out
