"""
8-state constant-velocity Kalman filter used by DeepSORT.

The state vector is ``[x, y, a, h, vx, vy, va, vh]`` where
``(x, y)`` is the bounding-box centre, ``a`` is the aspect ratio
``w / h`` and ``h`` is the height.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np


class KalmanFilter:
    """
    Simple Kalman filter for a single 2D bounding box.

    This is the exact same motion model used by the original DeepSORT
    implementation (Bewley et al., 2016 / Wojke et al., 2017).
    """

    _ndim = 4
    _std_weight_position = 1.0 / 20
    _std_weight_velocity = 1.0 / 160

    def __init__(self) -> None:
        ndim, dt = self._ndim, 1.0

        self._motion_mat = np.eye(2 * ndim, 2 * ndim)
        for i in range(ndim):
            self._motion_mat[i, ndim + i] = dt

        self._update_mat = np.eye(ndim, 2 * ndim)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def initiate(self, measurement: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create a track from an unassociated measurement.

        Parameters
        ----------
        measurement:
            Bounding box in ``(x, y, a, h)`` format.

        Returns
        -------
        (mean, covariance) of the new track.
        """
        mean_pos = measurement
        mean_vel = np.zeros_like(mean_pos)
        mean = np.r_[mean_pos, mean_vel]

        std = [
            2 * self._std_weight_position * measurement[3],
            2 * self._std_weight_position * measurement[3],
            1e-2,
            2 * self._std_weight_position * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            1e-5,
            10 * self._std_weight_velocity * measurement[3],
        ]
        covariance = np.diag(np.square(std))
        return mean, covariance

    def predict(
        self, mean: np.ndarray, covariance: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Run the Kalman filter prediction step."""
        std_pos = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-2,
            self._std_weight_position * mean[3],
        ]
        std_vel = [
            self._std_weight_velocity * mean[3],
            self._std_weight_velocity * mean[3],
            1e-5,
            self._std_weight_velocity * mean[3],
        ]
        motion_cov = np.diag(np.square(np.r_[std_pos, std_vel]))

        mean = self._motion_mat @ mean
        covariance = (
            self._motion_mat @ covariance @ self._motion_mat.T + motion_cov
        )
        return mean, covariance

    def project(
        self, mean: np.ndarray, covariance: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Project state to measurement space."""
        std = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-1,
            self._std_weight_position * mean[3],
        ]
        innovation_cov = np.diag(np.square(std))

        mean = self._update_mat @ mean
        covariance = (
            self._update_mat @ covariance @ self._update_mat.T + innovation_cov
        )
        return mean, covariance

    def update(
        self,
        mean: np.ndarray,
        covariance: np.ndarray,
        measurement: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Run the Kalman filter correction step."""
        projected_mean, projected_cov = self.project(mean, covariance)

        chol = np.linalg.cholesky(projected_cov)
        PHt = covariance @ self._update_mat.T
        kalman_gain = np.linalg.solve(
            chol.T, np.linalg.solve(chol, PHt.T)
        ).T

        innovation = measurement - projected_mean
        new_mean = mean + innovation @ kalman_gain.T
        new_covariance = (
            covariance
            - kalman_gain @ projected_cov @ kalman_gain.T
        )
        return new_mean, new_covariance
