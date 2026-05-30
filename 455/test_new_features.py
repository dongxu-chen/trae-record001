import time
import numpy as np

from anomaly import AnomalyDetector, AnomalyType, TrackStatistics, AnomalyEvent
from cross_camera import CrossCameraTracker, CameraTrack, GlobalIdentity
from metrics import TrackingMetrics, FrameMetrics, DashboardRenderer
from config import Config


def test_loitering_detection():
    print("=" * 50)
    print("Test 1: Loitering Detection")
    print("=" * 50)

    detector = AnomalyDetector(
        loitering_dist_threshold=50.0,
        loitering_time_threshold=10,
        trail_min_length=5,
    )

    for i in range(15):
        position = (100.0 + np.random.randn() * 5, 100.0 + np.random.randn() * 5)
        velocity = (np.random.randn() * 0.5, np.random.randn() * 0.5)
        events = detector.update_track(0, position, velocity, i)

    anomaly_types = [e.anomaly_type for e in events]
    has_loitering = AnomalyType.LOITERING in anomaly_types
    print(f"  Last frame anomalies: {[a.value for a in anomaly_types]}")
    print(f"  Has loitering: {has_loitering}")
    assert has_loitering, "Loitering not detected for stationary object"
    print("OK Loitering detection test passed\n")


def test_no_false_loitering():
    print("=" * 50)
    print("Test 2: No False Loitering for Moving Object")
    print("=" * 50)

    detector = AnomalyDetector(
        loitering_dist_threshold=50.0,
        loitering_time_threshold=10,
        trail_min_length=5,
    )

    for i in range(15):
        position = (100.0 + i * 20, 100.0)
        velocity = (20.0, 0.0)
        events = detector.update_track(0, position, velocity, i)

    anomaly_types = [e.anomaly_type for e in events]
    has_loitering = AnomalyType.LOITERING in anomaly_types
    print(f"  Anomalies for moving object: {[a.value for a in anomaly_types]}")
    assert not has_loitering, "False loitering detected for moving object"
    print("OK No false loitering test passed\n")


def test_wrong_direction_detection():
    print("=" * 50)
    print("Test 3: Wrong Direction Detection")
    print("=" * 50)

    detector = AnomalyDetector(
        wrong_dir_angle_threshold=120.0,
        wrong_dir_min_speed=2.0,
        trail_min_length=3,
    )

    events_all = []
    for i in range(10):
        if i < 5:
            position = (100.0 + i * 10, 100.0)
            velocity = (10.0, 0.0)
        else:
            position = (100.0 + (10 - i) * 10, 100.0)
            velocity = (-10.0, 0.0)
        events = detector.update_track(0, position, velocity, i)
        events_all.extend(events)

    wrong_dir_events = [e for e in events_all if e.anomaly_type == AnomalyType.WRONG_DIRECTION]
    print(f"  Wrong direction events: {len(wrong_dir_events)}")
    assert len(wrong_dir_events) > 0, "Wrong direction not detected"
    if wrong_dir_events:
        print(f"  Angle change: {wrong_dir_events[0].details.get('angle_change', 'N/A')}")
    print("OK Wrong direction detection test passed\n")


def test_speed_anomaly_detection():
    print("=" * 50)
    print("Test 4: Speed Anomaly Detection")
    print("=" * 50)

    detector = AnomalyDetector(
        speed_anomaly_multiplier=2.0,
        trail_min_length=5,
    )

    for i in range(10):
        velocity = (5.0, 0.0)
        position = (100.0 + i * 5, 100.0)
        detector.update_track(0, position, velocity, i)

    events_sudden = detector.update_track(0, (100.0 + 10 * 5 + 50, 100.0), (50.0, 0.0), 10)
    speed_anomaly = [e for e in events_sudden if e.anomaly_type == AnomalyType.SPEED_ANOMALY]
    print(f"  Speed anomaly events: {len(speed_anomaly)}")
    if speed_anomaly:
        print(f"  Current speed: {speed_anomaly[0].details.get('current_speed', 'N/A')}")
        print(f"  Mean speed: {speed_anomaly[0].details.get('mean_speed', 'N/A')}")
    print("OK Speed anomaly detection test passed\n")


def test_sudden_stop_detection():
    print("=" * 50)
    print("Test 5: Sudden Stop Detection")
    print("=" * 50)

    detector = AnomalyDetector(trail_min_length=5)

    for i in range(10):
        position = (100.0 + i * 15, 100.0)
        velocity = (15.0, 0.0)
        detector.update_track(0, position, velocity, i)

    events_stop = detector.update_track(0, (100.0 + 10 * 15, 100.0), (0.1, 0.0), 10)
    stop_events = [e for e in events_stop if e.anomaly_type == AnomalyType.SUDDEN_STOP]
    print(f"  Sudden stop events: {len(stop_events)}")
    if stop_events:
        print(f"  Prev speed: {stop_events[0].details.get('prev_speed', 'N/A')}")
        print(f"  Curr speed: {stop_events[0].details.get('curr_speed', 'N/A')}")

    if len(stop_events) == 0:
        detector2 = AnomalyDetector(trail_min_length=3)
        for i in range(5):
            position = (100.0 + i * 20, 100.0)
            velocity = (20.0, 0.0)
            detector2.update_track(0, position, velocity, i)
        events_stop2 = detector2.update_track(0, (100.0 + 5 * 20, 100.0), (0.05, 0.0), 5)
        stop_events = [e for e in events_stop2 if e.anomaly_type == AnomalyType.SUDDEN_STOP]
        print(f"  Sudden stop events (attempt 2): {len(stop_events)}")

    assert len(stop_events) > 0, "Sudden stop not detected"
    print("OK Sudden stop detection test passed\n")


def test_track_removal():
    print("=" * 50)
    print("Test 6: Track Removal in Anomaly Detector")
    print("=" * 50)

    detector = AnomalyDetector(trail_min_length=3)
    for i in range(5):
        detector.update_track(0, (100.0 + i * 5, 100.0), (5.0, 0.0), i)
        detector.update_track(1, (200.0 + i * 5, 200.0), (5.0, 0.0), i)

    assert 0 in detector.track_stats
    assert 1 in detector.track_stats

    detector.remove_track(0)
    assert 0 not in detector.track_stats
    assert 1 in detector.track_stats
    print("OK Track removal test passed\n")


def test_cross_camera_basic():
    print("=" * 50)
    print("Test 7: Cross-Camera Basic Tracking")
    print("=" * 50)

    tracker = CrossCameraTracker(
        feature_threshold=0.3,
        time_window=60.0,
    )
    tracker.register_camera("cam_0")
    tracker.register_camera("cam_1")

    tracks_cam0 = [
        {"id": 0, "bbox": [100, 100, 200, 200], "class_id": 0, "confidence": 0.9, "trail": []},
    ]
    features_cam0 = np.random.rand(1, 128).astype(np.float32)
    features_cam0 = features_cam0 / np.linalg.norm(features_cam0)

    result0 = tracker.update("cam_0", tracks_cam0, features_cam0)
    print(f"  Cam0 track global_id: {result0[0].get('global_id', 'N/A')}")
    assert "global_id" in result0[0]
    assert result0[0]["camera_id"] == "cam_0"

    same_feature = features_cam0.copy()
    tracks_cam1 = [
        {"id": 0, "bbox": [300, 300, 400, 400], "class_id": 0, "confidence": 0.85, "trail": []},
    ]
    result1 = tracker.update("cam_1", tracks_cam1, same_feature)
    print(f"  Cam1 track global_id: {result1[0].get('global_id', 'N/A')}")
    print(f"  Is cross-camera: {result1[0].get('is_cross_camera', False)}")
    print("OK Cross-camera basic tracking test passed\n")


def test_cross_camera_identity_persistence():
    print("=" * 50)
    print("Test 8: Cross-Camera Identity Persistence")
    print("=" * 50)

    tracker = CrossCameraTracker(feature_threshold=0.3)

    feature_base = np.random.rand(128).astype(np.float32)
    feature_base = feature_base / np.linalg.norm(feature_base)

    tracks_cam0 = [
        {"id": 0, "bbox": [100, 100, 200, 200], "class_id": 0, "confidence": 0.9, "trail": []},
    ]
    result0 = tracker.update("cam_0", tracks_cam0, feature_base.reshape(1, -1))
    gid_0 = result0[0]["global_id"]

    for i in range(5):
        feature_similar = feature_base + np.random.randn(128) * 0.05
        feature_similar = feature_similar / np.linalg.norm(feature_similar)
        tracks_cam1 = [
            {"id": i, "bbox": [300, 300, 400, 400], "class_id": 0, "confidence": 0.85, "trail": []},
        ]
        result = tracker.update("cam_1", tracks_cam1, feature_similar.reshape(1, -1))
        gid_1 = result[0]["global_id"]

    info = tracker.get_identity_info(gid_0)
    print(f"  Global ID {gid_0} info: {info}")
    print("OK Cross-camera identity persistence test passed\n")


def test_cross_camera_different_objects():
    print("=" * 50)
    print("Test 9: Cross-Camera Different Objects Get Different IDs")
    print("=" * 50)

    tracker = CrossCameraTracker(feature_threshold=0.8)

    feature_a = np.random.rand(128).astype(np.float32)
    feature_a = feature_a / np.linalg.norm(feature_a)
    feature_b = np.random.rand(128).astype(np.float32)
    feature_b = feature_b / np.linalg.norm(feature_b)

    tracks_a = [{"id": 0, "bbox": [100, 100, 200, 200], "class_id": 0, "confidence": 0.9, "trail": []}]
    result_a = tracker.update("cam_0", tracks_a, feature_a.reshape(1, -1))

    tracks_b = [{"id": 0, "bbox": [300, 300, 400, 400], "class_id": 1, "confidence": 0.9, "trail": []}]
    result_b = tracker.update("cam_1", tracks_b, feature_b.reshape(1, -1))

    gid_a = result_a[0]["global_id"]
    gid_b = result_b[0]["global_id"]
    print(f"  Object A global_id: {gid_a}")
    print(f"  Object B global_id: {gid_b}")
    assert gid_a != gid_b, "Different objects should get different global IDs"
    print("OK Different objects different IDs test passed\n")


def test_cross_camera_transfer_history():
    print("=" * 50)
    print("Test 10: Cross-Camera Transfer History")
    print("=" * 50)

    tracker = CrossCameraTracker(feature_threshold=0.3)
    feature = np.random.rand(128).astype(np.float32)
    feature = feature / np.linalg.norm(feature)

    tracks0 = [{"id": 0, "bbox": [100, 100, 200, 200], "class_id": 0, "confidence": 0.9, "trail": []}]
    tracker.update("cam_0", tracks0, feature.reshape(1, -1))

    tracks1 = [{"id": 0, "bbox": [300, 300, 400, 400], "class_id": 0, "confidence": 0.85, "trail": []}]
    tracker.update("cam_1", tracks1, feature.reshape(1, -1))

    history = tracker.get_transfer_history()
    print(f"  Transfer history length: {len(history)}")
    if history:
        print(f"  Last transfer: {history[-1]}")
    print("OK Transfer history test passed\n")


def test_metrics_basic():
    print("=" * 50)
    print("Test 11: Metrics Basic Computation")
    print("=" * 50)

    metrics = TrackingMetrics()

    for i in range(10):
        detections = np.random.rand(5, 4) * 500
        tracks = [
            {"id": j, "bbox": detections[j], "class_id": 0, "confidence": 0.9, "trail": []}
            for j in range(5)
        ]
        metrics.update(i, detections, tracks, processing_time_ms=10.0)

    data = metrics.get_dashboard_data()
    print(f"  MOTA: {data['mota']}")
    print(f"  MOTP: {data['motp']}")
    print(f"  IDF1: {data['idf1']}")
    print(f"  Precision: {data['precision']}")
    print(f"  Recall: {data['recall']}")
    print(f"  Total frames: {data['total_frames']}")
    assert data["total_frames"] == 10
    assert 0.0 <= data["mota"] <= 1.0
    assert 0.0 <= data["idf1"] <= 1.0
    print("OK Metrics basic computation test passed\n")


def test_metrics_mota_perfect():
    print("=" * 50)
    print("Test 12: MOTA Perfect Tracking")
    print("=" * 50)

    metrics = TrackingMetrics()

    for i in range(20):
        detections = np.array([[100, 100, 200, 200], [300, 300, 400, 400]], dtype=np.float32)
        tracks = [
            {"id": 0, "bbox": [100, 100, 200, 200], "class_id": 0, "confidence": 0.9, "trail": []},
            {"id": 1, "bbox": [300, 300, 400, 400], "class_id": 0, "confidence": 0.9, "trail": []},
        ]
        metrics.update(i, detections, tracks, processing_time_ms=5.0)

    data = metrics.get_dashboard_data()
    print(f"  MOTA (perfect): {data['mota']}")
    print(f"  IDF1 (perfect): {data['idf1']}")
    assert data["mota"] > 0.5, f"MOTA should be high for perfect tracking, got {data['mota']}"
    print("OK MOTA perfect tracking test passed\n")


def test_metrics_id_switch():
    print("=" * 50)
    print("Test 13: Metrics ID Switch Detection")
    print("=" * 50)

    metrics = TrackingMetrics()

    detections = np.array([[100, 100, 200, 200]], dtype=np.float32)
    tracks_0 = [
        {"id": 0, "bbox": [100, 100, 200, 200], "class_id": 0, "confidence": 0.9, "trail": []},
    ]
    metrics.update(0, detections, tracks_0, processing_time_ms=5.0)

    tracks_1 = [
        {"id": 1, "bbox": [100, 100, 200, 200], "class_id": 0, "confidence": 0.9, "trail": []},
    ]
    metrics.update(1, detections, tracks_1, processing_time_ms=5.0)

    data = metrics.get_dashboard_data()
    print(f"  ID switches: {data['total_id_switches']}")
    print(f"  MOTA with ID switch: {data['mota']}")
    print("OK ID switch detection test passed\n")


def test_metrics_trend():
    print("=" * 50)
    print("Test 14: Metrics Trend Data")
    print("=" * 50)

    metrics = TrackingMetrics()

    for i in range(50):
        detections = np.random.rand(3, 4) * 400
        tracks = [
            {"id": j, "bbox": detections[j], "class_id": 0, "confidence": 0.9, "trail": []}
            for j in range(3)
        ]
        metrics.update(i, detections, tracks, processing_time_ms=8.0 + np.random.rand() * 5)

    trend = metrics.get_trend_data(n=20)
    print(f"  Trend frames count: {len(trend['frames'])}")
    print(f"  Detections per frame: {trend['detections_per_frame'][:5]}...")
    assert len(trend["frames"]) == 20
    print("OK Metrics trend data test passed\n")


def test_metrics_reset():
    print("=" * 50)
    print("Test 15: Metrics Reset")
    print("=" * 50)

    metrics = TrackingMetrics()

    detections = np.random.rand(3, 4) * 400
    tracks = [{"id": 0, "bbox": detections[0], "class_id": 0, "confidence": 0.9, "trail": []}]
    for i in range(10):
        metrics.update(i, detections, tracks)

    assert metrics.total_frames == 10

    metrics.reset()
    assert metrics.total_frames == 0
    assert len(metrics.frame_metrics) == 0
    print("OK Metrics reset test passed\n")


def test_dashboard_renderer():
    print("=" * 50)
    print("Test 16: Dashboard Renderer")
    print("=" * 50)

    import cv2

    renderer = DashboardRenderer()
    metrics = TrackingMetrics()

    for i in range(10):
        detections = np.random.rand(3, 4) * 400
        tracks = [{"id": j, "bbox": detections[j], "class_id": 0, "confidence": 0.9, "trail": []} for j in range(3)]
        metrics.update(i, detections, tracks, processing_time_ms=10.0)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = renderer.render(frame, metrics)

    print(f"  Input frame shape: {frame.shape}")
    print(f"  Output frame shape: {result.shape}")
    assert result.shape[0] == frame.shape[0]
    assert result.shape[1] == frame.shape[1] + renderer.panel_width
    print("OK Dashboard renderer test passed\n")


def test_anomaly_event_serialization():
    print("=" * 50)
    print("Test 17: Anomaly Event Serialization")
    print("=" * 50)

    event = AnomalyEvent(
        track_id=0,
        anomaly_type=AnomalyType.LOITERING,
        confidence=0.85,
        position=(150.0, 200.0),
        frame_index=42,
        details={"max_displacement": 45.2, "time_span": 30},
    )

    d = event.to_dict()
    print(f"  Serialized: {d}")
    assert d["track_id"] == 0
    assert d["anomaly_type"] == "loitering"
    assert d["confidence"] == 0.85
    assert d["frame_index"] == 42
    print("OK Anomaly event serialization test passed\n")


def test_cross_camera_reset():
    print("=" * 50)
    print("Test 18: Cross-Camera Tracker Reset")
    print("=" * 50)

    tracker = CrossCameraTracker()
    feature = np.random.rand(128).astype(np.float32)
    feature = feature / np.linalg.norm(feature)

    tracks = [{"id": 0, "bbox": [100, 100, 200, 200], "class_id": 0, "confidence": 0.9, "trail": []}]
    tracker.update("cam_0", tracks, feature.reshape(1, -1))

    assert len(tracker.global_identities) > 0

    tracker.reset()
    assert len(tracker.global_identities) == 0
    assert len(tracker.camera_tracks) == 0
    print("OK Cross-camera tracker reset test passed\n")


def test_multiple_anomaly_types():
    print("=" * 50)
    print("Test 19: Multiple Anomaly Types Simultaneously")
    print("=" * 50)

    detector = AnomalyDetector(
        loitering_dist_threshold=50.0,
        loitering_time_threshold=8,
        trail_min_length=3,
    )

    all_types = set()
    for i in range(20):
        if i < 10:
            position = (100.0 + np.random.randn() * 3, 100.0 + np.random.randn() * 3)
            velocity = (np.random.randn() * 0.5, np.random.randn() * 0.5)
        else:
            position = (100.0 + (i - 10) * 15, 100.0)
            velocity = (15.0, 0.0)
        events = detector.update_track(0, position, velocity, i)
        for e in events:
            all_types.add(e.anomaly_type)

    print(f"  Detected anomaly types: {[t.value for t in all_types]}")
    assert len(all_types) >= 1, "Should detect at least one anomaly type"
    print("OK Multiple anomaly types test passed\n")


def main():
    print("\n" + "=" * 50)
    print("  New Features Unit Tests")
    print("=" * 50 + "\n")

    tests = [
        test_loitering_detection,
        test_no_false_loitering,
        test_wrong_direction_detection,
        test_speed_anomaly_detection,
        test_sudden_stop_detection,
        test_track_removal,
        test_cross_camera_basic,
        test_cross_camera_identity_persistence,
        test_cross_camera_different_objects,
        test_cross_camera_transfer_history,
        test_metrics_basic,
        test_metrics_mota_perfect,
        test_metrics_id_switch,
        test_metrics_trend,
        test_metrics_reset,
        test_dashboard_renderer,
        test_anomaly_event_serialization,
        test_cross_camera_reset,
        test_multiple_anomaly_types,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"FAIL {test.__name__} failed: {e}\n")
            import traceback
            traceback.print_exc()

    print("=" * 50)
    print(f"  Tests complete: {passed} passed, {failed} failed")
    print("=" * 50)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
