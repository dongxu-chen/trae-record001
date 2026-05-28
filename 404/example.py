"""
Traffic Sign Recognition System - Advanced Features
====================================================

New Features (v2.0):
1. Temporal Fusion - Multi-frame voting for stable detection
2. Distance Estimation - Estimate distance to traffic signs
3. Country Adaptation - Support for international traffic signs
4. Enhanced FPN - Improved small target detection
5. Hard Example Mining - Better quantization calibration
6. Adaptive Resolution - FPS stability with dynamic resolution

Author: Traffic Sign Recognition System
"""

import cv2
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from detector import YOLODetector, TRTDetector, ModelQuantizer
from processor import (
    VideoProcessor, FrameHandler, StreamSource,
    TemporalFusion, SignDistanceEstimator, CountryAdapter
)
from config import TRAFFIC_SIGN_CLASSES, CLASS_CATEGORIES


def example_1_temporal_fusion():
    print("=" * 60)
    print("Example 1: Temporal Fusion for Stable Detection")
    print("=" * 60)

    detector = YOLODetector(use_enhanced_fpn=True)

    print("\nTemporal Fusion Features:")
    print("  - Multi-frame voting (window: 5 frames)")
    print("  - Stable detection after 3 consistent frames")
    print("  - Smoothed bounding boxes and confidence")
    print("  - False positive suppression")
    print()

    processor = VideoProcessor(
        detector=detector,
        source=0,
        conf_threshold=0.3,
        enable_temporal_fusion=True,
        enable_distance_estimation=False,
        enable_country_adaptation=False,
        display=True
    )

    print("Starting camera stream...")
    print("Press 'q' to quit")
    print()

    if processor.start():
        try:
            for i in range(100):
                result = processor.get_results(timeout=0.1)
                if result and result.detections:
                    temporal_results = processor.get_enhanced_results()["temporal"]

                    stable_count = sum(1 for t in temporal_results if t["is_stable"])
                    if stable_count > 0:
                        print(f"Frame {i}: {len(result.detections)} detections, "
                              f"{stable_count} stable")
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            processor.stop()


def example_2_distance_estimation():
    print("\n" + "=" * 60)
    print("Example 2: Traffic Sign Distance Estimation")
    print("=" * 60)

    detector = YOLODetector(use_enhanced_fpn=True)

    print("\nDistance Estimation Methods:")
    print("  1. Pinhole camera model (using known sign size)")
    print("  2. Geometric estimation (using camera height)")
    print("  3. Hybrid fusion (weighted combination)")
    print()

    estimator = SignDistanceEstimator(
        focal_length=800.0,
        image_width=640,
        image_height=480,
        camera_height=1.5,
        method="hybrid"
    )

    test_image = "test_road.jpg"
    if os.path.exists(test_image):
        image = cv2.imread(test_image)
        detections = detector.detect(image)

        distance_results = estimator.estimate_batch(detections, image.shape)

        print(f"\nDistance Estimation Results ({len(distance_results)} signs):")
        for dr in distance_results:
            dist = dr.distance
            bbox_size = min(dr.detection.bbox[2] - dr.detection.bbox[0],
                           dr.detection.bbox[3] - dr.detection.bbox[1])

            danger_level = "DANGER" if dist.distance < 5 else "WARNING" if dist.distance < 15 else "SAFE"
            print(f"  {dr.detection.class_name_zh}:")
            print(f"    Distance: {dist.distance:.1f} {dist.unit} [{danger_level}]")
            print(f"    Method: {dist.method}")
            print(f"    Confidence: {dist.confidence:.3f}")
            print(f"    Sign size: {bbox_size}px")
            print()

        annotated = estimator.draw_distance(image, distance_results)
        cv2.imwrite("result_distance.jpg", annotated)
        print("Annotated image saved: result_distance.jpg")

    else:
        print(f"Test image not found: {test_image}")


def example_3_country_adaptation():
    print("\n" + "=" * 60)
    print("Example 3: Country Adaptation for International Signs")
    print("=" * 60)

    adapter = CountryAdapter(default_country="CN")

    countries = adapter.get_supported_countries()
    print(f"\nSupported countries ({len(countries)}):")
    for c in countries:
        print(f"  {c['code']:3s} - {c['name']:20s} ({c['region']:15s}) - {c['units']}")

    print("\n" + "-" * 40)

    test_classes = [
        "speed_limit_30",
        "speed_limit_60",
        "stop",
        "yield",
        "no_parking",
        "pedestrian_crossing"
    ]

    for country_code in ["CN", "US", "EU", "JP", "GB", "DE"]:
        adapter.set_country(country_code)
        info = adapter.get_current_standard()

        print(f"\n[{country_code}] {info.country_name}")
        print(f"  Units: {info.speed_limit_units}")
        print(f"  Region: {info.region}")

        for cls in test_classes:
            adapted = adapter.adapt_class_name(cls)
            speed_val, speed, unit = adapter.adapt_speed_limit(cls)
            if speed:
                print(f"    {cls:25s} → {adapted.adapted_class:25s} "
                      f"({speed}{unit}, {adapted.confidence_adjustment:.2f})")
            else:
                print(f"    {cls:25s} → {adapted.adapted_class:25s}")

    print("\n\nAuto-detection example:")
    print("The system can auto-detect country based on:")
    print("  - Speed limit values (25/35/45 = US, 30/50/60 = EU)")
    print("  - Special signs (school = US, cow = IN)")
    print("  - Color patterns (yellow warnings = US/AU)")


def example_4_all_features_integration():
    print("\n" + "=" * 60)
    print("Example 4: Full Feature Integration Demo")
    print("=" * 60)

    detector = YOLODetector(
        use_enhanced_fpn=True,
        small_target_threshold=32,
        high_res_scale=2.0
    )

    processor = VideoProcessor(
        detector=detector,
        source=0,
        width=640,
        height=480,
        fps=30,
        conf_threshold=0.3,
        display=True,
        enable_adaptive_resolution=True,
        process_every_frame=True,
        enable_temporal_fusion=True,
        enable_distance_estimation=True,
        enable_country_adaptation=True,
        country_code="CN",
        temporal_window_size=5,
        focal_length=800.0,
        camera_height=1.5
    )

    print("\nAll Features Enabled:")
    print("  ✓ Enhanced FPN for small targets")
    print("  ✓ Temporal fusion (5-frame window)")
    print("  ✓ Distance estimation (hybrid method)")
    print("  ✓ Country adaptation (CN)")
    print("  ✓ Adaptive resolution")
    print("  ✓ Per-frame processing")
    print()

    print("Annotations Legend:")
    print("  [S] - Stable detection (temporal fusion)")
    print("  [HR] - High resolution (enhanced FPN)")
    print("  [S] - Small target (<32px)")
    print("  Distance values shown in meters")
    print()

    print("Starting camera... Press 'q' to quit")
    print()

    if processor.start():
        try:
            start_time = time.time()
            frame_count = 0

            while time.time() - start_time < 30:
                result = processor.get_results(timeout=0.1)
                if result:
                    frame_count += 1
                    if frame_count % 30 == 0:
                        info = processor.get_info()
                        print(f"Frame {frame_count}: "
                              f"Process FPS = {info['frames_processed'] / (time.time() - start_time):.1f}")

        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            processor.stop()
            info = processor.get_info()
            print(f"\nFinal stats: {info['frames_processed']} frames processed")

            enhanced = processor.get_enhanced_results()
            print(f"\nEnhanced results summary:")
            print(f"  Temporal tracks: {len(enhanced['temporal'])}")
            print(f"  Distance estimates: {len(enhanced['distances'])}")
            print(f"  Adapted classes: {len(enhanced['adapted'])}")


def example_5_api_usage():
    print("\n" + "=" * 60)
    print("Example 5: API Usage with Advanced Features")
    print("=" * 60)

    print("""
New API Endpoints:

1. Enhanced Image Detection
   POST /api/v1/detect/enhanced
   Parameters:
     - file: image
     - conf_threshold: float
     - use_enhanced_fpn: bool
     - enable_distance_estimation: bool
     - enable_country_adaptation: bool
     - country_code: str

2. Enhanced Video Stream
   GET /api/v1/video/enhanced
   Parameters:
     - source: int
     - enable_temporal_fusion: bool
     - enable_distance_estimation: bool
     - enable_country_adaptation: bool
     - country_code: str
     - temporal_window_size: int

3. Country Info
   GET /api/v1/country/supported
   GET /api/v1/country/info?country_code=US

4. Classes with Country Adaptation
   GET /api/v1/classes?country_code=EU

Example curl commands:

# Enhanced detection with distance
curl -X POST "http://localhost:8000/api/v1/detect/enhanced?enable_distance_estimation=true" \\
     -F "file=@road.jpg"

# Get supported countries
curl "http://localhost:8000/api/v1/country/supported"

# Get country-specific class mapping
curl "http://localhost:8000/api/v1/classes?country_code=US"

# Video stream with all features
curl "http://localhost:8000/api/v1/video/enhanced?enable_temporal_fusion=true&country_code=CN"
    """)


def main():
    print("=" * 60)
    print("Traffic Sign Recognition System - Advanced Features v2.0")
    print("=" * 60)
    print(f"Supported classes: {len(TRAFFIC_SIGN_CLASSES)}")
    print(f"Categories: {list(CLASS_CATEGORIES.keys())}")
    print("=" * 60)

    try:
        example_3_country_adaptation()
        example_2_distance_estimation()
        example_5_api_usage()

        print("\n" + "=" * 60)
        print("Interactive Examples (uncomment to run):")
        print("  example_1_temporal_fusion()      - Camera with temporal fusion")
        print("  example_4_all_features_integration()  - Full feature demo")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nExample execution interrupted.")
    except Exception as e:
        print(f"\n[ERROR] Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
