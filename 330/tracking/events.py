"""
Event detection for object tracking.

Detects when tracked objects enter/leave user-defined zones, stay in a
zone for too long (dwell-timeout), or cross a trip-wire line.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .utils.utils import bbox_xywh_to_xyxy, iou


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------
class EventType(str, Enum):
    ENTER_ZONE = "enter_zone"
    EXIT_ZONE = "exit_zone"
    DWELL_TIMEOUT = "dwell_timeout"
    CROSS_LINE = "cross_line"


@dataclass
class TrackingEvent:
    """A single event emitted by the :class:`EventDetector`."""

    event_type: EventType
    track_id: int
    frame_id: int
    zone_id: Optional[str] = None
    position: Optional[Tuple[float, float]] = None
    metadata: Dict[str, float] = field(default_factory=dict)

    def __str__(self) -> str:
        parts = [f"[{self.frame_id}] {self.event_type.value} id={self.track_id}"]
        if self.zone_id:
            parts.append(f"zone={self.zone_id}")
        if self.position:
            parts.append(f"pos=({self.position[0]:.1f},{self.position[1]:.1f})")
        for k, v in self.metadata.items():
            parts.append(f"{k}={v:.2f}")
        return " ".join(parts)


# ---------------------------------------------------------------------------
# Zone definitions
# ---------------------------------------------------------------------------
@dataclass
class Zone:
    """A rectangular zone defined in pixel coordinates."""

    zone_id: str
    x1: float
    y1: float
    x2: float
    y2: float
    dwell_timeout: Optional[float] = None  # seconds or frames

    def contains(self, x: float, y: float) -> bool:
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def iou_with_bbox(self, bbox: Tuple[float, float, float, float]) -> float:
        """Return IoU between the zone and a ``(x, y, w, h)`` bbox."""
        zx1, zy1, zx2, zy2 = self.x1, self.y1, self.x2, self.y2
        bx1, by1, bx2, by2 = bbox_xywh_to_xyxy(bbox)
        return iou((zx1, zy1, zx2 - zx1, zy2 - zy1), (bx1, by1, bx2 - bx1, by2 - by1))


@dataclass
class TripLine:
    """A line segment that tracks can cross."""

    line_id: str
    x1: float
    y1: float
    x2: float
    y2: float

    def crosses(
        self, p1: Tuple[float, float], p2: Tuple[float, float]
    ) -> Optional[int]:
        """
        Return +1 if the segment ``p1 -> p2`` crosses the line in one
        direction, -1 for the opposite direction, ``None`` if no crossing.
        """
        x1, y1 = p1
        x2, y2 = p2
        lx1, ly1, lx2, ly2 = self.x1, self.y1, self.x2, self.y2

        def _ccw(a, b, c):
            return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])

        d1 = _ccw((lx1, ly1), (lx2, ly2), (x1, y1))
        d2 = _ccw((lx1, ly1), (lx2, ly2), (x2, y2))
        d3 = _ccw((x1, y1), (x2, y2), (lx1, ly1))
        d4 = _ccw((x1, y1), (x2, y2), (lx2, ly2))

        if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
            (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
        ):
            return 1 if d1 > 0 else -1
        return None


# ---------------------------------------------------------------------------
# Per-track state
# ---------------------------------------------------------------------------
@dataclass
class _TrackZoneState:
    inside_zones: Dict[str, int] = field(default_factory=dict)
    dwell_start: Dict[str, int] = field(default_factory=dict)
    last_pos: Optional[Tuple[float, float]] = None
    prev_pos: Optional[Tuple[float, float]] = None


# ---------------------------------------------------------------------------
# Event detector
# ---------------------------------------------------------------------------
class EventDetector:
    """
    Detect zone entry/exit, dwell-timeout and line-crossing events.

    Parameters
    ----------
    zones:
        List of :class:`Zone` instances to monitor.
    trip_lines:
        List of :class:`TripLine` instances to monitor.
    fps:
        Frames per second, used to convert dwell timeouts from seconds.
    require_iou:
        If ``True``, a track is considered inside a zone only when its
        bbox overlaps the zone (conservative).  Otherwise only the
        centre point is checked.
    """

    def __init__(
        self,
        zones: Optional[Sequence[Zone]] = None,
        trip_lines: Optional[Sequence[TripLine]] = None,
        fps: float = 30.0,
        require_iou: bool = True,
    ) -> None:
        self.zones: List[Zone] = list(zones) if zones else []
        self.trip_lines: List[TripLine] = list(trip_lines) if trip_lines else []
        self.fps = fps
        self.require_iou = require_iou

        self._states: Dict[int, _TrackZoneState] = {}
        self._events: List[TrackingEvent] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def events(self) -> List[TrackingEvent]:
        """All events recorded so far (most recent last)."""
        return list(self._events)

    def reset(self) -> None:
        self._states.clear()
        self._events.clear()

    def update(
        self,
        frame_id: int,
        tracks: Dict[int, Tuple[float, float, float, float]],
    ) -> List[TrackingEvent]:
        """
        Process one frame of tracks and return any newly detected events.

        Parameters
        ----------
        frame_id:
            Current frame number.
        tracks:
            ``{track_id: (x, y, w, h)}`` mapping.

        Returns
        -------
        List of :class:`TrackingEvent` emitted in this frame.
        """
        new_events: List[TrackingEvent] = []

        # Remove stale states for tracks that disappeared
        active_ids = set(tracks.keys())
        stale = [tid for tid in self._states if tid not in active_ids]
        for tid in stale:
            st = self._states.pop(tid)
            for zid in st.inside_zones:
                new_events.append(
                    TrackingEvent(
                        event_type=EventType.EXIT_ZONE,
                        track_id=tid,
                        frame_id=frame_id,
                        zone_id=zid,
                    )
                )

        for tid, bbox in tracks.items():
            st = self._states.setdefault(tid, _TrackZoneState())

            cx = bbox[0] + bbox[2] / 2.0
            cy = bbox[1] + bbox[3] / 2.0
            st.prev_pos = st.last_pos
            st.last_pos = (cx, cy)

            # --- Zone checks ---
            for zone in self.zones:
                inside_now = zone.iou_with_bbox(bbox) > 0.0 if self.require_iou else zone.contains(cx, cy)

                if inside_now and zone.zone_id not in st.inside_zones:
                    st.inside_zones[zone.zone_id] = frame_id
                    st.dwell_start[zone.zone_id] = frame_id
                    new_events.append(
                        TrackingEvent(
                            event_type=EventType.ENTER_ZONE,
                            track_id=tid,
                            frame_id=frame_id,
                            zone_id=zone.zone_id,
                            position=(cx, cy),
                        )
                    )
                elif not inside_now and zone.zone_id in st.inside_zones:
                    enter_frame = st.inside_zones.pop(zone.zone_id)
                    dwell_frames = frame_id - enter_frame
                    st.dwell_start.pop(zone.zone_id, None)
                    new_events.append(
                        TrackingEvent(
                            event_type=EventType.EXIT_ZONE,
                            track_id=tid,
                            frame_id=frame_id,
                            zone_id=zone.zone_id,
                            position=(cx, cy),
                            metadata={"dwell_frames": float(dwell_frames)},
                        )
                    )

                # Dwell timeout check
                if inside_now and zone.dwell_timeout is not None:
                    enter_frame = st.dwell_start.get(zone.zone_id, frame_id)
                    elapsed_frames = frame_id - enter_frame
                    if elapsed_frames >= int(zone.dwell_timeout * self.fps):
                        new_events.append(
                            TrackingEvent(
                                event_type=EventType.DWELL_TIMEOUT,
                                track_id=tid,
                                frame_id=frame_id,
                                zone_id=zone.zone_id,
                                position=(cx, cy),
                                metadata={
                                    "dwell_frames": float(elapsed_frames),
                                    "dwell_seconds": elapsed_frames / self.fps,
                                },
                            )
                        )

            # --- Trip-line checks ---
            if st.prev_pos is not None:
                for line in self.trip_lines:
                    direction = line.crosses(st.prev_pos, st.last_pos)
                    if direction is not None:
                        new_events.append(
                            TrackingEvent(
                                event_type=EventType.CROSS_LINE,
                                track_id=tid,
                                frame_id=frame_id,
                                zone_id=line.line_id,
                                position=(cx, cy),
                                metadata={"direction": float(direction)},
                            )
                        )

        self._events.extend(new_events)
        return new_events

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def count_by_type(self, event_type: EventType) -> int:
        return sum(1 for e in self._events if e.event_type == event_type)

    def summary(self) -> Dict[str, int]:
        """Return a dictionary with event counts by type."""
        counts: Dict[str, int] = {t.value: 0 for t in EventType}
        for e in self._events:
            counts[e.event_type.value] += 1
        return counts


# ---------------------------------------------------------------------------
# Callback registry
# ---------------------------------------------------------------------------
class EventCallbackRegistry:
    """
    Simple registry that lets users attach callbacks to event types.

    Example::

        registry = EventCallbackRegistry()
        registry.on(EventType.ENTER_ZONE, lambda e: print(f"Entered: {e}"))
        for event in detector.update(frame_id, tracks):
            registry.dispatch(event)
    """

    def __init__(self) -> None:
        self._handlers: Dict[EventType, List[Callable[[TrackingEvent], None]]] = {}

    def on(
        self, event_type: EventType, handler: Callable[[TrackingEvent], None]
    ) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def dispatch(self, event: TrackingEvent) -> None:
        for handler in self._handlers.get(event.event_type, []):
            handler(event)
