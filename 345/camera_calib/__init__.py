"""Camera calibration tool package.

Modules:
    calibrator   - Core calibration using OpenCV (mono & stereo).
    visualizer   - Reprojection error visualization and undistort preview.
    gui          - PyQt5 GUI for batch image calibration.
    cli          - Headless command-line interface.
"""

from .calibrator import (
    CameraCalibrator,
    CalibrationResult,
    PatternType,
    QualityReport,
    StereoCalibrator,
    StereoCalibrationResult,
)

__all__ = [
    "CameraCalibrator",
    "CalibrationResult",
    "PatternType",
    "QualityReport",
    "StereoCalibrator",
    "StereoCalibrationResult",
]
__version__ = "1.1.0"
