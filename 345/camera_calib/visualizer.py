"""Visualization helpers for calibration diagnostics.

Functions
---------
plot_reprojection_errors
    Bar chart of per-view reprojection error with the mean overlaid.
build_undistort_preview
    Side-by-side comparison of a raw image and its undistorted version.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .calibrator import CalibrationResult


def plot_reprojection_errors(
    result: CalibrationResult,
    save_path: Optional[str] = None,
    figsize: Tuple[float, float] = (10, 5),
) -> np.ndarray:
    """Plot per-view reprojection errors and return the rendered figure as
    an RGB ``numpy`` array.

    Parameters
    ----------
    result:
        Calibration output – ``per_view_errors`` and ``image_paths`` are
        used.
    save_path:
        If provided, the figure is saved to this location (e.g.
        ``"errors.png"``).
    figsize:
        Matplotlib figure size in inches.
    """
    labels = [
        p.rsplit("\\", 1)[-1].rsplit("/", 1)[-1] for p in result.image_paths
    ]
    values = result.per_view_errors
    mean_val = result.reprojection_error

    fig, ax = plt.subplots(figsize=figsize)
    x = np.arange(len(values))
    bars = ax.bar(x, values, color="#4C78A8")
    ax.axhline(mean_val, color="#E45756", linestyle="--", linewidth=1.5,
               label=f"Mean RMS = {mean_val:.3f} px")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Reprojection error (px)")
    ax.set_title("Per-view reprojection error")
    ax.set_ylim(0, max(values + [mean_val]) * 1.15 + 1e-6)
    for bar, v in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            v + max(values) * 0.02,
            f"{v:.3f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    ax.legend()
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150)

    fig.canvas.draw()
    width, height = fig.canvas.get_width_height()
    rgb = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
    rgb = rgb.reshape((height, width, 3))
    plt.close(fig)
    return rgb


def build_undistort_preview(
    image: np.ndarray,
    result: CalibrationResult,
    roi: bool = True,
) -> np.ndarray:
    """Return a horizontally concatenated ``(raw | undistorted)`` image.

    Parameters
    ----------
    image:
        BGR image (as returned by ``cv2.imread``).
    result:
        Calibration output used to call :meth:`CalibrationResult.undistort`.
    roi:
        If ``True`` and ``result.roi`` is available, crop the undistorted
        image to the valid-pixels region.
    """
    undistorted = result.undistort(image)

    if roi and result.roi is not None:
        x, y, w, h = result.roi
        if w > 0 and h > 0:
            undistorted = undistorted[y:y + h, x:x + w]

    # Normalize heights for side-by-side display.
    h_raw = image.shape[0]
    h_und = undistorted.shape[0]
    if h_und != h_raw:
        scale = h_raw / h_und
        new_w = max(1, int(round(undistorted.shape[1] * scale)))
        undistorted = cv2.resize(undistorted, (new_w, h_raw))

    return cv2.hconcat([image, undistorted])


def bgr_to_rgb(img: np.ndarray) -> np.ndarray:
    """Convert a BGR ``numpy`` array to RGB (for display in Qt/matplotlib)."""
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
