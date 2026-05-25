import cv2
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from depth_estimation.camera_calibration import (
    CameraCalibrator, DepthConverter, CameraCalibrationConfig
)
from depth_estimation.depth_rgb_alignment import DepthRGBAligner, AlignmentConfig
from depth_estimation.ar_overlay import AROverlay, ARConfig


def example_camera_calibration():
    print("=" * 60)
    print("Example 1: Camera Calibration and Metric Depth Conversion")
    print("=" * 60)
    
    calib_config = CameraCalibrationConfig(
        fx=525.0, fy=525.0,
        cx=320.0, cy=240.0,
        image_width=640, image_height=480,
        depth_scale=1000.0
    )
    
    calibrator = CameraCalibrator(calib_config)
    
    print(f"\nIntrinsics Matrix:")
    print(calibrator.get_intrinsics_matrix())
    
    print(f"\nFocal lengths: {calibrator.get_focal_lengths()}")
    print(f"Principal point: {calibrator.get_principal_point()}")
    
    relative_depth = np.random.rand(480, 640).astype(np.float32) * 0.5 + 0.5
    
    converter = DepthConverter(calibrator)
    metric_depth = converter.relative_to_metric_depth(
        relative_depth, method='median', reference_distance=2.0
    )
    
    print(f"\nRelative depth range: [{relative_depth.min():.3f}, {relative_depth.max():.3f}]")
    print(f"Metric depth range: [{metric_depth.min():.3f}, {metric_depth.max():.3f}]")
    
    test_point = (320, 240)
    depth_at_point = converter.get_depth_value_at_point(metric_depth, *test_point)
    print(f"\nDepth at pixel {test_point}: {depth_at_point:.3f} meters")
    
    point_3d = converter.get_3d_point_at_pixel(metric_depth, *test_point)
    if point_3d is not None:
        print(f"3D point at pixel {test_point}: [{point_3d[0]:.3f}, {point_3d[1]:.3f}, {point_3d[2]:.3f}]")
    
    save_path = "output_calib/calibration.json"
    os.makedirs("output_calib", exist_ok=True)
    calibrator.save_calibration(save_path)
    print(f"\nCalibration saved to: {save_path}")
    
    return calibrator, converter


def example_depth_rgb_alignment():
    print("\n" + "=" * 60)
    print("Example 2: Depth-RGB Alignment and Colored Depth Map")
    print("=" * 60)
    
    calib_config = CameraCalibrationConfig()
    calibrator = CameraCalibrator(calib_config)
    
    align_config = AlignmentConfig(
        alpha_blend=0.5,
        colormap=cv2.COLORMAP_JET
    )
    aligner = DepthRGBAligner(calibrator, align_config)
    
    rgb_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    depth_map = np.random.rand(480, 640).astype(np.float32) * 4.0 + 1.0
    
    aligned = aligner.align(rgb_image, depth_map)
    
    print(f"\nAligned RGB shape: {aligned['rgb_aligned'].shape}")
    print(f"Aligned depth shape: {aligned['depth_aligned'].shape}")
    print(f"Colored depth shape: {aligned['depth_colored'].shape}")
    
    overlay = aligner.generate_depth_overlay(rgb_image, depth_map, alpha=0.6)
    print(f"Depth overlay shape: {overlay.shape}")
    
    edge_overlay = aligner.generate_edge_aware_overlay(rgb_image, depth_map)
    print(f"Edge-aware overlay shape: {edge_overlay.shape}")
    
    colored_depth = aligner.depth_to_rgb_color(depth_map, rgb_image)
    print(f"RGB-colored depth shape: {colored_depth.shape}")
    
    pcl_data = aligner.generate_pointcloud_colored(rgb_image, depth_map)
    print(f"\nPoint cloud: {len(pcl_data['points'])} points, {len(pcl_data['colors'])} colors")
    
    os.makedirs("output_alignment", exist_ok=True)
    saved = aligner.save_aligned_output(rgb_image, depth_map, "output_alignment")
    print(f"\nSaved aligned outputs to: output_alignment/")
    
    return aligner


def example_ar_overlay():
    print("\n" + "=" * 60)
    print("Example 3: AR Object Placement and Occlusion")
    print("=" * 60)
    
    calib_config = CameraCalibrationConfig(
        fx=525.0, fy=525.0,
        cx=320.0, cy=240.0
    )
    calibrator = CameraCalibrator(calib_config)
    
    ar_config = ARConfig(
        object_scale=0.3,
        object_color=(0, 255, 0),
        object_alpha=0.7,
        occlusion_threshold=0.1,
        shadow_enabled=True
    )
    ar_overlay = AROverlay(calibrator, ar_config)
    
    rgb_image = np.ones((480, 640, 3), dtype=np.uint8) * 128
    rgb_image[:240, :] = [100, 150, 200]
    depth_map = np.ones((480, 640), dtype=np.float32) * 5.0
    depth_map[240:, :] = 10.0
    
    print("\nPlacing AR objects...")
    
    obj_id1 = ar_overlay.add_object(
        position_3d=np.array([0.0, 0.0, 2.0]),
        object_type='cube',
        scale=0.5,
        color=(0, 255, 0)
    )
    print(f"Cube placed at [0, 0, 2], ID: {obj_id1}")
    
    obj_id2 = ar_overlay.add_object(
        position_3d=np.array([0.5, 0.0, 3.0]),
        object_type='sphere',
        scale=0.4,
        color=(255, 0, 0)
    )
    print(f"Sphere placed at [0.5, 0, 3], ID: {obj_id2}")
    
    obj_id3 = ar_overlay.add_object(
        position_3d=np.array([-0.5, 0.2, 2.5]),
        object_type='pyramid',
        scale=0.3,
        color=(0, 0, 255)
    )
    print(f"Pyramid placed at [-0.5, 0.2, 2.5], ID: {obj_id3}")
    
    obj_id4 = ar_overlay.place_object_at_pixel(
        depth_map, 320, 240,
        object_type='cylinder',
        scale=0.3
    )
    if obj_id4 is not None:
        print(f"Cylinder placed at pixel (320, 240), ID: {obj_id4}")
    
    print(f"\nTotal objects: {len(ar_overlay.objects)}")
    
    result = ar_overlay.render(rgb_image, depth_map)
    print(f"Rendered image shape: {result.shape}")
    
    result_with_shadow = ar_overlay.render_shadow(result, depth_map)
    print(f"Shadow-rendered image shape: {result_with_shadow.shape}")
    
    stats = ar_overlay.get_objects_stats()
    print(f"\nAR Stats: {stats['num_objects']} objects")
    
    os.makedirs("output_ar", exist_ok=True)
    cv2.imwrite("output_ar/ar_result.png", result)
    cv2.imwrite("output_ar/ar_result_with_shadow.png", result_with_shadow)
    print(f"\nAR results saved to: output_ar/")
    
    print("\nTesting occlusion...")
    occluded_depth = np.ones((480, 640), dtype=np.float32) * 1.0
    occluded_result = ar_overlay.render(rgb_image, occluded_depth)
    print("Objects behind scene are occluded (not rendered)")
    
    print("\nTesting object management...")
    ar_overlay.remove_object(0)
    print(f"After removing object 0: {len(ar_overlay.objects)} objects")
    
    ar_overlay.clear_objects()
    print(f"After clearing: {len(ar_overlay.objects)} objects")
    
    return ar_overlay


def example_integration():
    print("\n" + "=" * 60)
    print("Example 4: Full Integration Pipeline")
    print("=" * 60)
    
    calib_config = CameraCalibrationConfig(
        fx=525.0, fy=525.0,
        cx=320.0, cy=240.0
    )
    calibrator = CameraCalibrator(calib_config)
    
    converter = DepthConverter(calibrator)
    aligner = DepthRGBAligner(calibrator, AlignmentConfig(alpha_blend=0.4))
    ar_overlay = AROverlay(calibrator, ARConfig(object_scale=0.25))
    
    num_frames = 5
    os.makedirs("output_integration", exist_ok=True)
    
    for i in range(num_frames):
        print(f"\nProcessing frame {i+1}/{num_frames}...")
        
        rgb_image = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
        relative_depth = np.random.rand(480, 640).astype(np.float32) * 0.5 + 0.5
        
        metric_depth = converter.relative_to_metric_depth(
            relative_depth, method='median', reference_distance=3.0
        )
        
        aligned = aligner.align(rgb_image, metric_depth)
        
        if i == 0:
            ar_overlay.place_object_at_pixel(metric_depth, 200, 300, object_type='cube')
            ar_overlay.place_object_at_pixel(metric_depth, 450, 200, object_type='sphere')
        
        ar_result = ar_overlay.render(aligned['rgb_aligned'], metric_depth)
        ar_result = ar_overlay.render_shadow(ar_result, metric_depth)
        
        overlay = aligner.generate_depth_overlay(rgb_image, metric_depth, alpha=0.3)
        
        combined = np.hstack((ar_result, overlay))
        
        cv2.imwrite(f"output_integration/frame_{i:03d}_combined.png", combined)
        
        print(f"  Metric depth range: [{metric_depth.min():.2f}, {metric_depth.max():.2f}]m")
        print(f"  AR objects: {len(ar_overlay.objects)}")
    
    print(f"\nAll frames saved to: output_integration/")
    print("\nIntegration complete!")


if __name__ == "__main__":
    print("Camera Calibration, Depth-RGB Alignment, and AR Overlay Examples")
    print("=" * 70)
    
    try:
        example_camera_calibration()
        example_depth_rgb_alignment()
        example_ar_overlay()
        example_integration()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
