"""
Common geometry helpers: bbox conversions, IoU and linear assignment.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

BBoxXYWH = Tuple[float, float, float, float]
BBoxXYXY = Tuple[float, float, float, float]


# ---------------------------------------------------------------------------
# BBox conversions
# ---------------------------------------------------------------------------
def bbox_xywh_to_xyxy(bbox: BBoxXYWH) -> BBoxXYXY:
    x, y, w, h = bbox
    return (float(x), float(y), float(x + w), float(y + h))


def bbox_xyxy_to_xywh(bbox: BBoxXYXY) -> BBoxXYWH:
    x1, y1, x2, y2 = bbox
    return (float(x1), float(y1), float(x2 - x1), float(y2 - y1))


# ---------------------------------------------------------------------------
# IoU
# ---------------------------------------------------------------------------
def iou(a: BBoxXYWH, b: BBoxXYWH) -> float:
    """Intersection over union between two ``(x, y, w, h)`` boxes."""
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter = inter_w * inter_h
    union = aw * ah + bw * bh - inter
    if union <= 0:
        return 0.0
    return float(inter / union)


def vectorized_iou(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """
    Return the ``(M, N)`` IoU matrix between two sets of
    ``(x, y, w, h)`` boxes.
    """
    if boxes_a.size == 0 or boxes_b.size == 0:
        return np.zeros((len(boxes_a), len(boxes_b)), dtype=np.float32)

    a = boxes_a.astype(np.float32, copy=False)
    b = boxes_b.astype(np.float32, copy=False)

    ax1 = a[:, 0]
    ay1 = a[:, 1]
    ax2 = a[:, 0] + a[:, 2]
    ay2 = a[:, 1] + a[:, 3]

    bx1 = b[:, 0][None, :]
    by1 = b[:, 1][None, :]
    bx2 = (b[:, 0] + b[:, 2])[None, :]
    by2 = (b[:, 1] + b[:, 3])[None, :]

    inter_x1 = np.maximum(ax1[:, None], bx1)
    inter_y1 = np.maximum(ay1[:, None], by1)
    inter_x2 = np.minimum(ax2[:, None], bx2)
    inter_y2 = np.minimum(ay2[:, None], by2)

    inter_w = np.clip(inter_x2 - inter_x1, 0, None)
    inter_h = np.clip(inter_y2 - inter_y1, 0, None)
    inter = inter_w * inter_h

    area_a = (a[:, 2] * a[:, 3])[:, None]
    area_b = (b[:, 2] * b[:, 3])[None, :]
    union = area_a + area_b - inter
    with np.errstate(divide="ignore", invalid="ignore"):
        iou_matrix = np.where(union > 0, inter / union, 0.0)
    return iou_matrix.astype(np.float32)


# ---------------------------------------------------------------------------
# Linear assignment (Hungarian)
# ---------------------------------------------------------------------------
def linear_assignment(cost_matrix: np.ndarray) -> np.ndarray:
    """
    Solve the bipartite assignment problem.

    Parameters
    ----------
    cost_matrix:
        2D matrix of costs. ``inf`` entries are treated as forbidden edges.

    Returns
    -------
    ndarray of shape ``(K, 2)`` with ``(row_idx, col_idx)`` assignments.
    """
    try:
        from scipy.optimize import linear_sum_assignment  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dep
        raise ImportError(
            "linear_assignment requires scipy (pip install scipy)"
        ) from exc

    cost_matrix = np.asarray(cost_matrix)
    if cost_matrix.size == 0:
        return np.empty((0, 2), dtype=int)

    # scipy cannot handle inf; replace with a large finite value.
    finite_mask = np.isfinite(cost_matrix)
    if not np.any(finite_mask):
        return np.empty((0, 2), dtype=int)

    max_val = cost_matrix[finite_mask].max() if finite_mask.any() else 0.0
    safe = np.where(finite_mask, cost_matrix, max_val + 1e6)

    rows, cols = linear_sum_assignment(safe)
    matches = np.stack([rows, cols], axis=1)

    # Drop matches that correspond to forbidden edges.
    if matches.size:
        valid = finite_mask[matches[:, 0], matches[:, 1]]
        matches = matches[valid]
    return matches
