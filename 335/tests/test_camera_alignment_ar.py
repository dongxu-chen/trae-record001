import numpy as np
import cv2
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from depth_estimation.camera_calibration import CameraCalibrator, DepthConverter, CameraCalibrationConfig
from depth_estimation.depth_rgb_alignment import DepthRGBAligner, AlignmentConfig
from depth_estimation.ar_overlay import AROverlay, ARConfig, ARObject


class TestCameraCalibration:
    def test_default_intrinsics(self):
        config = CameraCalibrationConfig(
            fx=525.0, fy=525.0,
            image_width=640, image_height=480
        )
        calibrator = CameraCalibrator(config)
        
        intrinsics = calibrator.get_intrinsics_matrix()
        assert intrinsics.shape == (3, 3)
        assert intrinsics[0, 0] == 525.0
        assert intrinsics[1, 1] == 525.0
        assert intrinsics[0, 2] == 320.0
        assert intrinsics[1, 2] == 240.0
    
    def test_custom_principal_point(self):
        config = CameraCalibrationConfig(
            fx=525.0, fy=525.0,
            cx=300.0, cy=250.0,
            image_width=640, image_height=480
        )
        calibrator = CameraCalibrator(config)
        
        intrinsics = calibrator.get_intrinsics_matrix()
        assert intrinsics[0, 2] == 300.0
        assert intrinsics[1, 2] == 250.0
    
    def test_pixel_to_metric(self):
        config = CameraCalibrationConfig(depth_scale=1000.0)
        calibrator = CameraCalibrator(config)
        
        depth_map = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        metric_depth = calibrator.pixel_to_metric(depth_map)
        
        expected = depth_map * 1000.0
        np.testing.assert_array_equal(metric_depth, expected)
    
    def test_relative_to_metric(self):
        config = CameraCalibrationConfig()
        calibrator = CameraCalibrator(config)
        
        relative_depth = np.random.rand(100, 100).astype(np.float32) * 0.5 + 0.5
        metric_depth = calibrator.relative_to_metric(relative_depth, reference_distance=2.0)
        
        assert np.all(metric_depth >= 0.1)
        assert np.all(metric_depth <= 10.0)
        
        median_rel = np.median(relative_depth)
        median_metric = np.median(metric_depth)
        assert abs(median_metric - 2.0) < 0.5
    
    def test_backproject_to_3d(self):
        config = CameraCalibrationConfig(
            fx=525.0, fy=525.0,
            cx=320.0, cy=240.0
        )
        calibrator = CameraCalibrator(config)
        
        point_3d = calibrator.backproject_to_3d(320, 240, 1.0)
        
        assert point_3d[0] == pytest.approx(0.0, abs=0.01)
        assert point_3d[1] == pytest.approx(0.0, abs=0.01)
        assert point_3d[2] == 1.0
    
    def test_project_to_pixel(self):
        config = CameraCalibrationConfig(
            fx=525.0, fy=525.0,
            cx=320.0, cy=240.0
        )
        calibrator = CameraCalibrator(config)
        
        point_3d = np.array([0.0, 0.0, 1.0])
        u, v = calibrator.project_to_pixel(point_3d)
        
        assert u == 320
        assert v == 240
    
    def test_backproject_depth_map(self):
        config = CameraCalibrationConfig(
            fx=525.0, fy=525.0,
            cx=320.0, cy=240.0
        )
        calibrator = CameraCalibrator(config)
        
        depth_map = np.ones((480, 640), dtype=np.float32)
        points_3d, valid_mask = calibrator.backproject_depth_map(depth_map)
        
        assert points_3d.shape == (480, 640, 3)
        assert valid_mask.shape == (480, 640)
        assert np.all(valid_mask)
        assert np.all(points_3d[..., 2] == 1.0)
    
    def test_undistort_image(self):
        config = CameraCalibrationConfig(
            apply_undistortion=True,
            image_width=64, image_height=48
        )
        calibrator = CameraCalibrator(config)
        
        image = np.random.randint(0, 255, (48, 64, 3), dtype=np.uint8)
        undistorted = calibrator.undistort_image(image)
        
        assert undistorted.shape == image.shape


class TestDepthConverter:
    def test_median_scale_conversion(self):
        config = CameraCalibrationConfig()
        calibrator = CameraCalibrator(config)
        converter = DepthConverter(calibrator)
        
        relative_depth = np.random.rand(100, 100).astype(np.float32) * 0.5 + 0.5
        metric_depth = converter.relative_to_metric_depth(
            relative_depth, method='median', reference_distance=3.0
        )
        
        assert np.all(metric_depth >= 0.1)
        assert np.all(metric_depth <= 10.0)
    
    def test_minmax_scale_conversion(self):
        config = CameraCalibrationConfig()
        calibrator = CameraCalibrator(config)
        converter = DepthConverter(calibrator)
        
        relative_depth = np.random.rand(100, 100).astype(np.float32) * 0.5 + 0.5
        metric_depth = converter.relative_to_metric_depth(
            relative_depth, method='minmax'
        )
        
        assert np.all(metric_depth >= 0.1)
        assert np.all(metric_depth <= 10.0)
    
    def test_get_depth_value_at_point(self):
        config = CameraCalibrationConfig()
        calibrator = CameraCalibrator(config)
        converter = DepthConverter(calibrator)
        
        depth_map = np.ones((100, 100), dtype=np.float32) * 5.0
        value = converter.get_depth_value_at_point(depth_map, 50, 50)
        
        assert value == 5.0
    
    def test_get_depth_value_out_of_bounds(self):
        config = CameraCalibrationConfig()
        calibrator = CameraCalibrator(config)
        converter = DepthConverter(calibrator)
        
        depth_map = np.ones((100, 100), dtype=np.float32) * 5.0
        value = converter.get_depth_value_at_point(depth_map, 200, 200)
        
        assert value == 0.0


class TestDepthRGBAlignment:
    def test_alignment_same_size(self):
        calib_config = CameraCalibrationConfig()
        calibrator = CameraCalibrator(calib_config)
        
        align_config = AlignmentConfig()
        aligner = DepthRGBAligner(calibrator, align_config)
        
        rgb_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        depth_map = np.random.rand(480, 640).astype(np.float32) * 5.0 + 0.1
        
        result = aligner.align(rgb_image, depth_map)
        
        assert 'rgb_aligned' in result
        assert 'depth_aligned' in result
        assert 'depth_colored' in result
        assert result['rgb_aligned'].shape == (480, 640, 3)
        assert result['depth_aligned'].shape == (480, 640)
        assert result['depth_colored'].shape == (480, 640, 3)
    
    def test_alignment_different_size(self):
        calib_config = CameraCalibrationConfig()
        calibrator = CameraCalibrator(calib_config)
        
        align_config = AlignmentConfig(scale_depth_to_rgb=True)
        aligner = DepthRGBAligner(calibrator, align_config)
        
        rgb_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        depth_map = np.random.rand(240, 320).astype(np.float32) * 5.0 + 0.1
        
        result = aligner.align(rgb_image, depth_map)
        
        assert result['depth_aligned'].shape == (480, 640)
    
    def test_generate_depth_overlay(self):
        calib_config = CameraCalibrationConfig()
        calibrator = CameraCalibrator(calib_config)
        
        align_config = AlignmentConfig(alpha_blend=0.5)
        aligner = DepthRGBAligner(calibrator, align_config)
        
        rgb_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        depth_map = np.random.rand(480, 640).astype(np.float32) * 5.0 + 0.1
        
        overlay = aligner.generate_depth_overlay(rgb_image, depth_map, alpha=0.6)
        
        assert overlay.shape == (480, 640, 3)
    
    def test_depth_to_rgb_color(self):
        calib_config = CameraCalibrationConfig()
        calibrator = CameraCalibrator(calib_config)
        
        align_config = AlignmentConfig()
        aligner = DepthRGBAligner(calibrator, align_config)
        
        rgb_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        depth_map = np.random.rand(480, 640).astype(np.float32) * 5.0 + 0.1
        
        colored_depth = aligner.depth_to_rgb_color(depth_map, rgb_image)
        
        assert colored_depth.shape == (480, 640, 3)
    
    def test_generate_pointcloud_colored(self):
        calib_config = CameraCalibrationConfig()
        calibrator = CameraCalibrator(calib_config)
        
        align_config = AlignmentConfig()
        aligner = DepthRGBAligner(calibrator, align_config)
        
        rgb_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        depth_map = np.random.rand(480, 640).astype(np.float32) * 5.0 + 0.1
        
        pcl_data = aligner.generate_pointcloud_colored(rgb_image, depth_map)
        
        assert 'points' in pcl_data
        assert 'colors' in pcl_data
        assert 'valid_mask' in pcl_data
        assert len(pcl_data['points']) > 0


class TestAROverlay:
    def test_add_object(self):
        calib_config = CameraCalibrationConfig()
        calibrator = CameraCalibrator(calib_config)
        
        ar_config = ARConfig()
        ar_overlay = AROverlay(calibrator, ar_config)
        
        position = np.array([0.0, 0.0, 2.0])
        obj_id = ar_overlay.add_object(position, object_type='cube', scale=0.5)
        
        assert obj_id == 0
        assert len(ar_overlay.objects) == 1
        assert ar_overlay.objects[0].object_type == 'cube'
        assert ar_overlay.objects[0].scale == 0.5
    
    def test_remove_object(self):
        calib_config = CameraCalibrationConfig()
        calibrator = CameraCalibrator(calib_config)
        
        ar_config = ARConfig()
        ar_overlay = AROverlay(calibrator, ar_config)
        
        ar_overlay.add_object(np.array([0.0, 0.0, 2.0]))
        ar_overlay.add_object(np.array([1.0, 0.0, 2.0]))
        
        ar_overlay.remove_object(0)
        assert len(ar_overlay.objects) == 1
    
    def test_clear_objects(self):
        calib_config = CameraCalibrationConfig()
        calibrator = CameraCalibrator(calib_config)
        
        ar_config = ARConfig()
        ar_overlay = AROverlay(calibrator, ar_config)
        
        ar_overlay.add_object(np.array([0.0, 0.0, 2.0]))
        ar_overlay.add_object(np.array([1.0, 0.0, 2.0]))
        
        ar_overlay.clear_objects()
        assert len(ar_overlay.objects) == 0
    
    def test_place_object_at_pixel(self):
        calib_config = CameraCalibrationConfig(
            fx=525.0, fy=525.0,
            cx=320.0, cy=240.0
        )
        calibrator = CameraCalibrator(calib_config)
        
        ar_config = ARConfig()
        ar_overlay = AROverlay(calibrator, ar_config)
        
        depth_map = np.ones((480, 640), dtype=np.float32) * 2.0
        
        obj_id = ar_overlay.place_object_at_pixel(depth_map, 320, 240)
        
        assert obj_id is not None
        assert len(ar_overlay.objects) == 1
    
    def test_render_cube(self):
        calib_config = CameraCalibrationConfig(
            fx=525.0, fy=525.0,
            cx=320.0, cy=240.0
        )
        calibrator = CameraCalibrator(calib_config)
        
        ar_config = ARConfig(wireframe=False)
        ar_overlay = AROverlay(calibrator, ar_config)
        
        rgb_image = np.ones((480, 640, 3), dtype=np.uint8) * 128
        depth_map = np.ones((480, 640), dtype=np.float32) * 10.0
        
        ar_overlay.add_object(np.array([0.0, 0.0, 2.0]), object_type='cube')
        
        result = ar_overlay.render(rgb_image, depth_map)
        
        assert result.shape == (480, 640, 3)
    
    def test_render_sphere(self):
        calib_config = CameraCalibrationConfig(
            fx=525.0, fy=525.0,
            cx=320.0, cy=240.0
        )
        calibrator = CameraCalibrator(calib_config)
        
        ar_config = ARConfig()
        ar_overlay = AROverlay(calibrator, ar_config)
        
        rgb_image = np.ones((480, 640, 3), dtype=np.uint8) * 128
        depth_map = np.ones((480, 640), dtype=np.float32) * 10.0
        
        ar_overlay.add_object(np.array([0.0, 0.0, 2.0]), object_type='sphere')
        
        result = ar_overlay.render(rgb_image, depth_map)
        
        assert result.shape == (480, 640, 3)
    
    def test_render_pyramid(self):
        calib_config = CameraCalibrationConfig(
            fx=525.0, fy=525.0,
            cx=320.0, cy=240.0
        )
        calibrator = CameraCalibrator(calib_config)
        
        ar_config = ARConfig()
        ar_overlay = AROverlay(calibrator, ar_config)
        
        rgb_image = np.ones((480, 640, 3), dtype=np.uint8) * 128
        depth_map = np.ones((480, 640), dtype=np.float32) * 10.0
        
        ar_overlay.add_object(np.array([0.0, 0.0, 2.0]), object_type='pyramid')
        
        result = ar_overlay.render(rgb_image, depth_map)
        
        assert result.shape == (480, 640, 3)
    
    def test_render_cylinder(self):
        calib_config = CameraCalibrationConfig(
            fx=525.0, fy=525.0,
            cx=320.0, cy=240.0
        )
        calibrator = CameraCalibrator(calib_config)
        
        ar_config = ARConfig()
        ar_overlay = AROverlay(calibrator, ar_config)
        
        rgb_image = np.ones((480, 640, 3), dtype=np.uint8) * 128
        depth_map = np.ones((480, 640), dtype=np.float32) * 10.0
        
        ar_overlay.add_object(np.array([0.0, 0.0, 2.0]), object_type='cylinder')
        
        result = ar_overlay.render(rgb_image, depth_map)
        
        assert result.shape == (480, 640, 3)
    
    def test_occlusion_check(self):
        calib_config = CameraCalibrationConfig(
            fx=525.0, fy=525.0,
            cx=320.0, cy=240.0
        )
        calibrator = CameraCalibrator(calib_config)
        
        ar_config = ARConfig(occlusion_threshold=0.05)
        ar_overlay = AROverlay(calibrator, ar_config)
        
        depth_map = np.ones((480, 640), dtype=np.float32) * 1.0
        
        far_point = np.array([0.0, 0.0, 5.0])
        is_occluded = ar_overlay._check_occlusion(far_point, depth_map)
        
        assert is_occluded == True
    
    def test_render_shadow(self):
        calib_config = CameraCalibrationConfig(
            fx=525.0, fy=525.0,
            cx=320.0, cy=240.0
        )
        calibrator = CameraCalibrator(calib_config)
        
        ar_config = ARConfig(shadow_enabled=True)
        ar_overlay = AROverlay(calibrator, ar_config)
        
        rgb_image = np.ones((480, 640, 3), dtype=np.uint8) * 200
        depth_map = np.ones((480, 640), dtype=np.float32) * 2.0
        
        ar_overlay.add_object(np.array([0.0, 0.0, 2.0]))
        
        result = ar_overlay.render_shadow(rgb_image, depth_map)
        
        assert result.shape == (480, 640, 3)
    
    def test_get_objects_stats(self):
        calib_config = CameraCalibrationConfig()
        calibrator = CameraCalibrator(calib_config)
        
        ar_config = ARConfig()
        ar_overlay = AROverlay(calibrator, ar_config)
        
        ar_overlay.add_object(np.array([0.0, 0.0, 2.0]))
        ar_overlay.add_object(np.array([1.0, 0.0, 3.0]))
        
        stats = ar_overlay.get_objects_stats()
        
        assert stats['num_objects'] == 2
        assert len(stats['objects']) == 2


class TestSaveAndLoadCalibration:
    def test_save_and_load_calibration(self, tmp_path):
        config = CameraCalibrationConfig(
            fx=600.0, fy=600.0,
            cx=320.0, cy=240.0
        )
        calibrator = CameraCalibrator(config)
        
        filepath = str(tmp_path / "calibration.json")
        calibrator.save_calibration(filepath)
        
        assert os.path.exists(filepath)
        
        load_config = CameraCalibrationConfig(calibration_file=filepath)
        calibrator2 = CameraCalibrator(load_config)
        
        intrinsics = calibrator2.get_intrinsics_matrix()
        assert intrinsics[0, 0] == 600.0
        assert intrinsics[1, 1] == 600.0
        assert intrinsics[0, 2] == 320.0
        assert intrinsics[1, 2] == 240.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
