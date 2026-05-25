"""
MOTA / IDF1 evaluation built on top of the ``motmetrics`` package.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

try:  # pragma: no cover - optional dependency
    import motmetrics as mm
except Exception:  # pragma: no cover
    mm = None  # type: ignore

# numpy 2.0 dropped ``np.asfarray`` which is still used by older
# ``motmetrics`` releases.  Provide a shim so the evaluator works
# regardless of the installed version.
if not hasattr(np, "asfarray"):  # pragma: no cover
    np.asfarray = np.asarray  # type: ignore[attr-defined]


@dataclass
class FrameRecord:
    """Record produced by :meth:`Evaluator.update`."""

    frame_id: int
    ground_truth: List[Tuple[int, Tuple[float, float, float, float]]]
    predictions: List[Tuple[int, Tuple[float, float, float, float]]]


class Evaluator:
    """
    Accumulates per-frame ground truth and predictions, then evaluates
    tracking performance using the ``motmetrics`` library.

    Parameters
    ----------
    iou_threshold:
        IoU threshold for a true positive match (default ``0.5``).
    """

    def __init__(self, iou_threshold: float = 0.5) -> None:
        if mm is None:  # pragma: no cover
            raise ImportError(
                "Evaluator requires motmetrics (pip install motmetrics)"
            )
        self.iou_threshold = iou_threshold
        self._accumulator = mm.MOTAccumulator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update(
        self,
        frame_id: int,
        ground_truth: Sequence[Tuple[int, Tuple[float, float, float, float]]],
        predictions: Sequence[Tuple[int, Tuple[float, float, float, float]]],
    ) -> None:
        """
        Add one frame of ground truth and predictions.

        Parameters
        ----------
        frame_id:
            Integer frame index.
        ground_truth:
            Sequence of ``(track_id, (x, y, w, h))`` tuples.
        predictions:
            Sequence of ``(track_id, (x, y, w, h))`` tuples produced by
            the tracker.
        """
        gt_ids = [int(tid) for tid, _ in ground_truth]
        gt_boxes = np.array([_to_xywh(bbox) for _, bbox in ground_truth], dtype=float)

        pred_ids = [int(tid) for tid, _ in predictions]
        pred_boxes = np.array([_to_xywh(bbox) for _, bbox in predictions], dtype=float)

        if gt_boxes.size == 0 and pred_boxes.size == 0:
            return

        if gt_boxes.size == 0 or pred_boxes.size == 0:
            dist: Optional[np.ndarray] = np.empty((len(gt_ids), len(pred_ids)))
        else:
            dist = mm.distances.iou_matrix(gt_boxes, pred_boxes, max_iou=1.0)

        self._accumulator.update(
            gt_ids, pred_ids, dist, frameid=frame_id
        )

    def compute(self) -> Dict[str, float]:
        """
        Compute the tracking metrics.

        Returns
        -------
        dict
            Metric name -> value.  At minimum ``MOTA``, ``IDF1``,
            ``IDP``, ``IDR``, ``precision``, ``recall`` and ``num_switches``
            are returned (when available).
        """
        mh = mm.metrics.create()
        summary = mh.compute(
            self._accumulator,
            metrics=[
                "num_frames",
                "mota",
                "motp",
                "idf1",
                "idp",
                "idr",
                "num_switches",
                "precision",
                "recall",
                "num_false_positives",
                "num_misses",
            ],
            name="overall",
        )
        record = summary.iloc[0].to_dict()
        # Make sure the canonical keys exist
        result: Dict[str, float] = {}
        mapping = {
            "mota": "MOTA",
            "motp": "MOTP",
            "idf1": "IDF1",
            "idp": "IDP",
            "idr": "IDR",
            "precision": "precision",
            "recall": "recall",
            "num_switches": "num_switches",
            "num_false_positives": "num_false_positives",
            "num_misses": "num_misses",
            "num_frames": "num_frames",
        }
        for src, dst in mapping.items():
            result[dst] = float(record.get(src, float("nan")))
        return result

    def reset(self) -> None:
        self._accumulator = mm.MOTAccumulator()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _to_xywh(bbox: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """motmetrics expects (X, Y, W, H)."""
    return (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
