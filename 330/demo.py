"""
End-to-end demo of the ``tracking`` package with enhanced features.

Generates a synthetic video with two linearly-moving targets, runs every
tracker on it and prints MOTA/IDF1 evaluation results.

Demonstrates:
- **Kalman filter prediction during occlusion** (DeepSORT + TrackerManager)
- **Appearance re-identification** for recovery after occlusion
- **Dynamic cascade thresholds** that adapt to scene density
- **SiamRPN with optional TensorRT acceleration** (~3x inference speedup)
- **Event detection** (zone entry/exit, dwell timeout, line crossing)
- **Trajectory analysis** (motion pattern clustering, velocity statistics)
- **Visualization** (bbox drawing, trajectories, zones, event log)
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

import tracking as trk
from tracking.events import EventDetector, EventType, Zone, TripLine
from tracking.trajectory import TrajectoryAnalyzer
from tracking.visualize import TrackVisualizer


def generate_synthetic_video(
    num_frames: int = 60,
    height: int = 240,
    width: int = 320,
) -> Tuple[List[np.ndarray], List[List[Tuple[int, Tuple[float, float, float, float]]]]]:
    """
    Return a list of frames (``np.uint8`` BGR) and per-frame ground truth
    ``(track_id, bbox)`` tuples.

    The video contains two targets with a crossing pattern and an
    occlusion event to test recovery.
    """
    rng = np.random.default_rng(0)
    frames: List[np.ndarray] = []
    gts: List[List[Tuple[int, Tuple[float, float, float, float]]]] = []

    for t in range(num_frames):
        frame = (rng.random((height, width, 3)) * 40 + 40).astype(np.uint8)
        frame_gt: List[Tuple[int, Tuple[float, float, float, float]]] = []

        # Target 0: left -> right with occlusion between frames 20-30
        x0 = 20 + 150 * (t / max(num_frames - 1, 1))
        y0 = height * 0.3 + 10 * np.sin(t * 0.3)
        # Add a brief occlusion
        occluded = 20 <= t < 30
        if not occluded:
            bbox0 = (float(x0), float(y0), 40.0, 30.0)
            frame_gt.append((0, bbox0))

        # Target 1: right -> left, parallel track
        x1 = (width - 60) - 150 * (t / max(num_frames - 1, 1))
        y1 = height * 0.65 + 10 * np.cos(t * 0.3)
        bbox1 = (float(x1), float(y1), 40.0, 30.0)
        frame_gt.append((1, bbox1))

        # Draw the targets so a single-target tracker can follow them visually.
        for _, (bx, by, bw, bh) in frame_gt:
            bx_i = max(0, min(width - 1, int(bx)))
            by_i = max(0, min(height - 1, int(by)))
            bw_i = max(1, min(width - bx_i, int(bw)))
            bh_i = max(1, min(height - by_i, int(bh)))
            frame[by_i : by_i + bh_i, bx_i : bx_i + bw_i] = (255, 200, 100)

        frames.append(frame)
        gts.append(frame_gt)
    return frames, gts


def simulate_detector(
    gt: List[Tuple[int, Tuple[float, float, float, float]]],
    noise: float = 3.0,
    drop_prob: float = 0.05,
) -> List[Tuple[float, float, float, float]]:
    """Simulate a noisy detector for demonstration."""
    rng = np.random.default_rng()
    detections: List[Tuple[float, float, float, float]] = []
    for _, bbox in gt:
        if rng.random() < drop_prob:
            continue
        x, y, w, h = bbox
        detections.append(
            (
                x + rng.normal(0, noise),
                y + rng.normal(0, noise),
                w,
                h,
            )
        )
    return detections


def run_tracker(
    tracker_type: str,
    frames: List[np.ndarray],
    gts: List[List[Tuple[int, Tuple[float, float, float, float]]]],
) -> Tuple[List[List[Tuple[int, Tuple[float, float, float, float]]]], dict]:
    """
    Run a tracker type over all frames.  Returns predictions per frame
    plus a dictionary of statistics (e.g., measured speedup).
    """
    predictions: List[List[Tuple[int, Tuple[float, float, float, float]]]] = []
    stats: dict = {}

    if tracker_type == "DeepSORT":
        tracker = trk.DeepSORTTracker(
            max_age=15,
            n_init=2,
            enable_dynamic_thresholds=True,
        )
        thresholds_over_time = []
        for frame, gt in zip(frames, gts):
            detections = simulate_detector(gt, noise=2.0, drop_prob=0.0)
            results = tracker.multi_update(frame, detections)
            predictions.append(
                [(int(tid), tuple(float(v) for v in bbox)) for tid, bbox in results]
            )
            thresholds_over_time.append(tracker.current_thresholds.copy())
        if thresholds_over_time:
            stats["thresholds"] = thresholds_over_time
        return predictions, stats

    manager = trk.TrackerManager(
        tracker_type=tracker_type,
        iou_threshold=0.3,
        max_misses=15,
        n_init=1,
        enable_kalman=True,
        enable_appearance=True,
        enable_dynamic_thresholds=True,
        lambda_=0.5,
        tracker_kwargs={"use_trt": True} if tracker_type == "SiamRPN" else {},
    )

    thresholds_over_time = []
    for frame, gt in zip(frames, gts):
        detections = simulate_detector(gt, noise=1.0, drop_prob=0.0)
        results = manager.update(frame, detections)
        predictions.append(
            [(int(tid), tuple(float(v) for v in bbox)) for tid, bbox in results]
        )
        thresholds_over_time.append(manager.current_thresholds.copy())

    if thresholds_over_time:
        stats["thresholds"] = thresholds_over_time

    # Check SiamRPN TensorRT speedup
    if tracker_type == "SiamRPN" and manager._tracks:
        first_track = next(iter(manager._tracks.values()))
        tracker_obj = first_track.tracker
        if hasattr(tracker_obj, "trt_active"):
            stats["trt_active"] = tracker_obj.trt_active
            speedup = tracker_obj.speedup_ratio
            if speedup is not None:
                stats["speedup_ratio"] = speedup
                print(f"  TensorRT active: {tracker_obj.trt_active}, speedup: {speedup:.2f}x")

    return predictions, stats


def demonstrate_event_detection(
    frames: List[np.ndarray],
    gts: List[List[Tuple[int, Tuple[float, float, float, float]]]],
) -> None:
    """Demonstrate zone entry/exit, dwell timeout and line crossing."""
    print("\n=== Event Detection Demo ===")
    zones = [
        Zone("entry_zone", 0, 0, 100, 120, dwell_timeout=2.0),
        Zone("exit_zone", 220, 120, 320, 240, dwell_timeout=None),
    ]
    lines = [TripLine("mid_line", 160, 0, 160, 240)]
    detector = EventDetector(zones=zones, trip_lines=lines, fps=30)

    for frame_id, gt in enumerate(gts):
        tracks = {tid: bbox for tid, bbox in gt}
        events = detector.update(frame_id, tracks)
        for e in events:
            print(f"  {e}")

    print(f"  Summary: {detector.summary()}")


def demonstrate_trajectory_analysis(
    gts: List[List[Tuple[int, Tuple[float, float, float, float]]]],
) -> None:
    """Demonstrate trajectory analysis and clustering."""
    print("\n=== Trajectory Analysis Demo ===")
    analyzer = TrajectoryAnalyzer(fps=30, max_clusters=4)
    for frame_id, gt in enumerate(gts):
        analyzer.update(frame_id, gt)

    stats = analyzer.compute_stats()
    print(f"  Number of tracks: {stats.n_tracks}")
    print(f"  Mean duration: {stats.mean_duration:.2f}s")
    print(f"  Mean speed: {stats.mean_speed:.2f} px/s")
    print(f"  Mean straightness: {stats.mean_straightness:.3f}")
    print(f"  Std speed: {stats.std_speed:.2f} px/s")
    print(f"  Mean acceleration: {stats.mean_acceleration:.2f} px/s^2")

    labels, n_clusters = analyzer.cluster()
    print(f"  Motion patterns: {n_clusters} clusters")
    if labels:
        for i, (traj, label) in enumerate(zip(analyzer.trajectories(), labels)):
            print(f"    Track {traj.track_id}: cluster {label}, "
                  f"straightness={traj.straightness:.3f}, "
                  f"path={traj.path_length:.1f}px")


def demonstrate_visualization(
    frames: List[np.ndarray],
    gts: List[List[Tuple[int, Tuple[float, float, float, float]]]],
) -> None:
    """Demonstrate visualization rendering."""
    print("\n=== Visualization Demo ===")
    zones = [
        Zone("entry_zone", 0, 0, 100, 120),
        Zone("exit_zone", 220, 120, 320, 240),
    ]
    lines = [TripLine("mid_line", 160, 0, 160, 240)]
    visualizer = TrackVisualizer(zones=zones, trip_lines=lines)

    # Render first 5 frames
    for i in range(min(5, len(frames))):
        gt = gts[i]
        vis = visualizer.draw(
            frames[i],
            gt,
            info={"Frame": str(i), "Tracks": str(len(gt))},
        )
        visualizer.update(gt)
        assert vis.shape == frames[i].shape

    print("  Rendered 5 frames successfully")
    print("  Output shape:", vis.shape)


def main() -> None:
    print("Generating synthetic video ...")
    frames, gts = generate_synthetic_video()

    # Demonstrate new features
    demonstrate_event_detection(frames, gts)
    demonstrate_trajectory_analysis(gts)
    demonstrate_visualization(frames, gts)

    # Run all trackers and evaluate
    print("\n=== Tracker Evaluation ===")
    for tracker_type in ["KCF", "CSRT", "SiamRPN", "DeepSORT"]:
        print(f"\n--- {tracker_type} ---")
        predictions, stats = run_tracker(tracker_type, frames, gts)

        # Print dynamic threshold info
        if "thresholds" in stats and stats["thresholds"]:
            first = stats["thresholds"][0]
            mid = stats["thresholds"][len(stats["thresholds"]) // 2]
            last = stats["thresholds"][-1]
            if "iou_threshold" in first:
                print(f"  Dynamic thresholds: first={first['iou_threshold']:.2f}, "
                      f"mid={mid['iou_threshold']:.2f}, last={last['iou_threshold']:.2f}")

        evaluator = trk.Evaluator(iou_threshold=0.5)
        for frame_id, (gt, pred) in enumerate(zip(gts, predictions)):
            evaluator.update(frame_id, gt, pred)
        metrics = evaluator.compute()
        for key in ["MOTA", "IDF1", "precision", "recall", "num_switches"]:
            value = metrics.get(key, float("nan"))
            print(f"  {key:<14}: {value:6.3f}")

        if "speedup_ratio" in stats:
            print(f"  {'TRT speedup':<14}: {stats['speedup_ratio']:6.2f}x")


if __name__ == "__main__":
    main()
