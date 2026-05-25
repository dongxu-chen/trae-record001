"""
Object tracking library.

Provides KCF/CSRT, SiamRPN and DeepSORT trackers, multi-target tracking
with occlusion handling, ID switching detection, event detection,
trajectory analysis, visualization and MOTA/IDF1 evaluation.
"""

from ._version import __version__
from .tracker_base import BaseTracker
from .tracker_manager import TrackerManager
from .trackers import KCFTracker, CSRTTracker, SiamRPNTracker, DeepSORTTracker
from .evaluate import Evaluator
from .events import (
    EventDetector,
    EventCallbackRegistry,
    EventType,
    TrackingEvent,
    Zone,
    TripLine,
)
from .trajectory import (
    TrajectoryAnalyzer,
    TrajectoryBuilder,
    TrajectoryClusterer,
    Trajectory,
    TrackStatistics,
)
from .visualize import (
    TrackVisualizer,
    draw_bboxes,
    draw_trajectories,
    draw_zones,
    draw_trip_lines,
    draw_events,
    draw_info_overlay,
)
from .interactive import TrackerTuner, sweep_parameters

__all__ = [
    "__version__",
    "BaseTracker",
    "TrackerManager",
    "KCFTracker",
    "CSRTTracker",
    "SiamRPNTracker",
    "DeepSORTTracker",
    "Evaluator",
    # Event detection
    "EventDetector",
    "EventCallbackRegistry",
    "EventType",
    "TrackingEvent",
    "Zone",
    "TripLine",
    # Trajectory analysis
    "TrajectoryAnalyzer",
    "TrajectoryBuilder",
    "TrajectoryClusterer",
    "Trajectory",
    "TrackStatistics",
    # Visualization
    "TrackVisualizer",
    "draw_bboxes",
    "draw_trajectories",
    "draw_zones",
    "draw_trip_lines",
    "draw_events",
    "draw_info_overlay",
    # Interactive tuning
    "TrackerTuner",
    "sweep_parameters",
]
