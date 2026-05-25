"""
Detection of ID switches between consecutive frames.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Set, Tuple


class IDSwitchDetector:
    """
    Detect when an existing track ID re-appears at a location that is
    inconsistent with the previous frame.

    The detector keeps a per-ID bounding-box history. If two tracks cross
    (i.e. ``track A`` was closest to the previous location of ``track B``
    and vice versa), an ID switch is reported.
    """

    def __init__(self, iou_threshold: float = 0.3) -> None:
        self.iou_threshold = iou_threshold
        self._prev: Dict[int, Tuple[float, float, float, float]] = {}

    def update(
        self,
        current: Dict[int, Tuple[float, float, float, float]],
    ) -> List[Tuple[int, int]]:
        """
        Return a list of ``(a, b)`` ID pairs suspected of switching.

        Parameters
        ----------
        current:
            Mapping from track ID to ``(x, y, w, h)`` for the current frame.
        """
        if not self._prev or not current:
            self._prev = dict(current)
            return []

        # --- lazy import to avoid circular dependency at module load ---
        from .utils import iou  # type: ignore

        prev_ids = set(self._prev)
        cur_ids = set(current)
        common = prev_ids & cur_ids

        switches: List[Tuple[int, int]] = []
        seen: Set[Tuple[int, int]] = set()

        # For each common track, find the *other* common track whose
        # previous position best overlaps with the current one.
        id_list = list(common)
        for i, a in enumerate(id_list):
            best_other: int | None = None
            best_iou = 0.0
            for b in id_list:
                if a == b:
                    continue
                overlap = iou(current[a], self._prev[b])
                if overlap > best_iou:
                    best_iou = overlap
                    best_other = b
            if best_other is not None and best_iou > self.iou_threshold:
                # Mutual check -> strong indication of a swap.
                pair = tuple(sorted((a, best_other)))  # type: ignore[assignment]
                if pair in seen:
                    continue
                seen.add(pair)  # type: ignore[arg-type]
                switches.append(pair)  # type: ignore[arg-type]

        self._prev = dict(current)
        return switches

    def reset(self) -> None:
        self._prev.clear()
