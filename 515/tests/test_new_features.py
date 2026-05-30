#!/usr/bin/env python3
import sys
import os
import tempfile
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2

from src import (
    FisheyeCorrector,
    CorrectionMethod,
    BorderHandlingMode,
    FisheyeProjectionType,
    create_projection_model,
    correct_fisheye_image,
    self_calibrate_from_lines,
    detect_line_segments,
    compute_straightness_error,
    evaluate_calibration_quality,
    LensConfig,
    LensConfigManager,
    create_default_lens_config,
    BatchProcessor,
)


def generate_synthetic_fisheye_with_lines(
    size: int = 500, fov_degrees: float = 180.0
) -> np.ndarray:
    image = np.zeros((size, size, 3), dtype=np.uint8)
    center = (size // 2, size // 2)
    max_r = size // 2 - 20

    for i in range(0, size, 60):
        for j in range(0, size, 60):
            dx = j - center[0]
            dy = i - center[1]
            r = np.sqrt(dx**2 + dy**2)
            if r < max_r and r > 0:
                theta = np.arcsin(r / max_r) * (fov_degrees / 180.0) * np.pi / 2
                r_fisheye = 2.0 * (size / 3.0) * np.sin(theta / 2.0)
                x_f = int(center[0] + r_fisheye * dx / r)
                y_f = int(center[1] + r_fisheye * dy / r)
                color = (200, 200, 200)
                cv2.rectangle(image, (x_f - 6, y_f - 6), (x_f + 6, y_f + 6), color, -1)

    num_lines = 8
    for i in range(num_lines):
        angle = (i / num_lines) * np.pi
        x1 = int(center[0] + max_r * 0.3 * np.cos(angle))
        y1 = int(center[1] + max_r * 0.3 * np.sin(angle))
        x2 = int(center[0] + max_r * 0.9 * np.cos(angle))
        y2 = int(center[1] + max_r * 0.9 * np.sin(angle))
        cv2.line(image, (x1, y1), (x2, y2), (255, 255, 255), 3)

    cv2.circle(image, center, max_r, (255, 255, 255), 2)
    return image


class TestSelfCalibration(unittest.TestCase):
    def test_detect_line_segments(self):
        image = generate_synthetic_fisheye_with_lines()
        segments = detect_line_segments(image, min_length=30, max_segments=100)

        self.assertIsInstance(segments, list)
        self.assertGreater(len(segments), 0)

        for segment in segments:
            self.assertEqual(segment.points.shape, (2, 2))
            self.assertGreater(segment.length, 30)
            self.assertGreaterEqual(segment.angle, -np.pi)
            self.assertLessEqual(segment.angle, np.pi)

    def test_compute_straightness_error(self):
        straight_line = np.array([[0, 0], [1, 1], [2, 2], [3, 3], [4, 4]], dtype=np.float64)
        error = compute_straightness_error(straight_line)
        self.assertAlmostEqual(error, 0.0, places=5)

        curved_line = np.array([[0, 0], [1, 0.5], [2, 2.5], [3, 3], [4, 4]], dtype=np.float64)
        error = compute_straightness_error(curved_line)
        self.assertGreater(error, 0.1)

    def test_self_calibrate_from_lines(self):
        image = generate_synthetic_fisheye_with_lines()
        params = self_calibrate_from_lines(image, verbose=False)

        self.assertIn("center", params)
        self.assertIn("focal_length", params)
        self.assertIn("fov_degrees", params)
        self.assertIn("projection_type", params)
        self.assertIn("model", params)
        self.assertIn("method", params)

        self.assertIsInstance(params["projection_type"], FisheyeProjectionType)
        self.assertIsNotNone(params["model"])

        self.assertGreater(params["focal_length"], 100)
        self.assertLess(params["focal_length"], 600)

        center = params["center"]
        self.assertAlmostEqual(center[0], 250.0, delta=30)
        self.assertAlmostEqual(center[1], 250.0, delta=30)

    def test_evaluate_calibration_quality(self):
        image = generate_synthetic_fisheye_with_lines()
        params = self_calibrate_from_lines(image, verbose=False)

        quality = evaluate_calibration_quality(image, params["model"])

        self.assertIn("quality_score", quality)
        self.assertIn("mean_error", quality)
        self.assertIn("num_segments", quality)

        self.assertGreaterEqual(quality["quality_score"], 0.0)
        self.assertLessEqual(quality["quality_score"], 1.0)
        self.assertGreater(quality["num_segments"], 0)


class TestBorderHandling(unittest.TestCase):
    def test_border_mode_enum(self):
        self.assertEqual(BorderHandlingMode.FULL.value, "full")
        self.assertEqual(BorderHandlingMode.CROP.value, "crop")
        self.assertEqual(BorderHandlingMode.PAD.value, "pad")

    def test_corrector_border_mode_init(self):
        corrector = FisheyeCorrector(
            border_mode=BorderHandlingMode.CROP,
            pad_value=50,
        )
        self.assertEqual(corrector.border_mode, BorderHandlingMode.CROP)
        self.assertEqual(corrector.pad_value, 50)

    def test_set_border_mode(self):
        corrector = FisheyeCorrector()
        corrector.set_border_mode(BorderHandlingMode.PAD)
        self.assertEqual(corrector.border_mode, BorderHandlingMode.PAD)

    def test_set_pad_value(self):
        corrector = FisheyeCorrector()
        corrector.set_pad_value((100, 150, 200))
        self.assertEqual(corrector.pad_value, (100, 150, 200))

    def test_correct_full_mode(self):
        image = generate_synthetic_fisheye_with_lines(size=300)
        params = self_calibrate_from_lines(image, verbose=False)

        corrector = FisheyeCorrector(
            distortion_model=params["model"],
            border_mode=BorderHandlingMode.FULL,
        )
        corrected = corrector.correct(image, output_size=(400, 400))

        self.assertEqual(corrected.shape[0], 400)
        self.assertEqual(corrected.shape[1], 400)

    def test_correct_crop_mode(self):
        image = generate_synthetic_fisheye_with_lines(size=300)
        params = self_calibrate_from_lines(image, verbose=False)

        corrector = FisheyeCorrector(
            distortion_model=params["model"],
            border_mode=BorderHandlingMode.CROP,
        )
        corrected = corrector.correct(image, output_size=(450, 450))

        self.assertLessEqual(corrected.shape[0], 450)
        self.assertLessEqual(corrected.shape[1], 450)
        self.assertGreater(corrected.shape[0], 200)
        self.assertGreater(corrected.shape[1], 200)

    def test_correct_pad_mode(self):
        image = generate_synthetic_fisheye_with_lines(size=300)
        params = self_calibrate_from_lines(image, verbose=False)

        corrector = FisheyeCorrector(
            distortion_model=params["model"],
            border_mode=BorderHandlingMode.PAD,
            pad_value=0,
        )
        corrected = corrector.correct(image, output_size=(450, 450))

        self.assertGreaterEqual(corrected.shape[0], 450)
        self.assertGreaterEqual(corrected.shape[1], 450)

    def test_correct_fisheye_image_with_border_mode(self):
        image = generate_synthetic_fisheye_with_lines(size=300)

        corrected_crop = correct_fisheye_image(
            image,
            handling_mode=BorderHandlingMode.CROP,
        )

        corrected_full = correct_fisheye_image(
            image,
            handling_mode=BorderHandlingMode.FULL,
        )

        self.assertLessEqual(corrected_crop.shape[0], corrected_full.shape[0])
        self.assertLessEqual(corrected_crop.shape[1], corrected_full.shape[1])

    def test_get_valid_bbox(self):
        mask = np.zeros((100, 100), dtype=bool)
        mask[20:80, 30:70] = True

        corrector = FisheyeCorrector()
        bbox = corrector._get_valid_bbox(mask)

        self.assertIsNotNone(bbox)
        top, bottom, left, right = bbox
        self.assertEqual(top, 20)
        self.assertEqual(bottom, 79)
        self.assertEqual(left, 30)
        self.assertEqual(right, 69)

    def test_get_largest_valid_rect(self):
        mask = np.zeros((100, 100), dtype=bool)
        mask[10:90, 20:80] = True

        corrector = FisheyeCorrector()
        rect = corrector._get_largest_valid_rect(mask)

        self.assertIsNotNone(rect)
        top, bottom, left, right = rect
        height = bottom - top
        width = right - left
        self.assertEqual(height, width)


class TestLensConfig(unittest.TestCase):
    def test_lens_config_creation(self):
        lens = LensConfig(
            name="test_lens",
            projection_type=FisheyeProjectionType.EQUISOLID,
            focal_length=500.0,
            center=(640.0, 480.0),
            fov_degrees=180.0,
            description="Test lens",
        )

        self.assertEqual(lens.name, "test_lens")
        self.assertEqual(lens.projection_type, FisheyeProjectionType.EQUISOLID)
        self.assertEqual(lens.focal_length, 500.0)
        self.assertEqual(lens.center, (640.0, 480.0))
        self.assertEqual(lens.fov_degrees, 180.0)

    def test_lens_config_to_dict(self):
        lens = LensConfig(
            name="test_lens",
            projection_type=FisheyeProjectionType.EQUISOLID,
            focal_length=500.0,
            center=(640.0, 480.0),
        )

        data = lens.to_dict()
        self.assertEqual(data["name"], "test_lens")
        self.assertEqual(data["projection_type"], "equisolid")
        self.assertEqual(data["focal_length"], 500.0)
        self.assertEqual(data["center"], [640.0, 480.0])

    def test_lens_config_from_dict(self):
        data = {
            "name": "test_lens",
            "projection_type": "stereographic",
            "focal_length": 400.0,
            "center": [320.0, 240.0],
            "fov_degrees": 220.0,
            "description": "Test from dict",
        }

        lens = LensConfig.from_dict(data)
        self.assertEqual(lens.name, "test_lens")
        self.assertEqual(lens.projection_type, FisheyeProjectionType.STEREOGRAPHIC)
        self.assertEqual(lens.focal_length, 400.0)
        self.assertEqual(lens.center, (320.0, 240.0))
        self.assertEqual(lens.fov_degrees, 220.0)

    def test_lens_get_model(self):
        lens = LensConfig(
            name="test_lens",
            projection_type=FisheyeProjectionType.EQUIDISTANT,
            focal_length=300.0,
            center=(500.0, 400.0),
        )

        model = lens.get_model()
        self.assertIsNotNone(model)
        self.assertIsInstance(model, object)

    def test_lens_config_manager_init(self):
        manager = LensConfigManager()
        self.assertEqual(len(manager.lenses), 0)
        self.assertIsNone(manager.active_lens)

    def test_lens_config_manager_add_remove(self):
        manager = LensConfigManager()

        lens = LensConfig(
            name="lens1",
            projection_type=FisheyeProjectionType.EQUISOLID,
            focal_length=500.0,
            center=(640.0, 480.0),
        )

        manager.add_lens(lens)
        self.assertIn("lens1", manager.list_lenses())
        self.assertIsNotNone(manager.get_lens("lens1"))

        manager.remove_lens("lens1")
        self.assertNotIn("lens1", manager.list_lenses())
        self.assertIsNone(manager.get_lens("lens1"))

    def test_lens_config_manager_active_lens(self):
        manager = create_default_lens_config()

        self.assertEqual(manager.active_lens, "lens_a_180")
        self.assertIsNotNone(manager.get_active_lens())
        self.assertIsNotNone(manager.get_active_model())

        manager.set_active_lens("lens_b_220")
        self.assertEqual(manager.active_lens, "lens_b_220")

    def test_lens_config_manager_list_lenses(self):
        manager = create_default_lens_config()
        lenses = manager.list_lenses()

        self.assertIsInstance(lenses, list)
        self.assertEqual(len(lenses), 3)
        self.assertIn("lens_a_180", lenses)
        self.assertIn("lens_b_220", lenses)
        self.assertIn("lens_c_120", lenses)

    def test_lens_config_manager_get_lens_info(self):
        manager = create_default_lens_config()
        info = manager.get_lens_info("lens_a_180")

        self.assertIsNotNone(info)
        self.assertEqual(info["name"], "lens_a_180")
        self.assertEqual(info["projection_type"], "equisolid")
        self.assertTrue(info["is_active"])

    def test_lens_config_manager_get_all_lenses_info(self):
        manager = create_default_lens_config()
        all_info = manager.get_all_lenses_info()

        self.assertEqual(len(all_info), 3)
        for info in all_info:
            self.assertIn("name", info)
            self.assertIn("projection_type", info)

    def test_lens_config_save_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = os.path.join(tmpdir, "lens_config.json")

            manager = create_default_lens_config()
            manager.save(config_file)

            self.assertTrue(os.path.exists(config_file))

            manager2 = LensConfigManager(config_file)
            self.assertEqual(len(manager2.lenses), 3)
            self.assertEqual(manager2.active_lens, "lens_a_180")

            lens = manager2.get_lens("lens_a_180")
            self.assertEqual(lens.focal_length, 500.0)
            self.assertEqual(lens.center, (640.0, 480.0))

    def test_create_lens_from_params(self):
        manager = LensConfigManager()

        params = {
            "focal_length": 450.0,
            "center": (320.0, 240.0),
            "fov_degrees": 150.0,
            "projection_type": FisheyeProjectionType.EQUISOLID,
        }

        lens = manager.create_lens_from_params(
            name="new_lens",
            params=params,
            description="Created from params",
            set_active=True,
        )

        self.assertEqual(lens.name, "new_lens")
        self.assertEqual(lens.focal_length, 450.0)
        self.assertEqual(lens.center, (320.0, 240.0))
        self.assertEqual(manager.active_lens, "new_lens")

    def test_calibrate_lens_from_image(self):
        manager = LensConfigManager()
        image = generate_synthetic_fisheye_with_lines(size=400)

        lens = manager.calibrate_lens_from_image(
            name="calibrated_lens",
            image=image,
            use_line_calibration=True,
            set_active=True,
        )

        self.assertIsNotNone(lens)
        self.assertEqual(lens.name, "calibrated_lens")
        self.assertEqual(manager.active_lens, "calibrated_lens")
        self.assertGreater(lens.focal_length, 100)

    def test_get_lens_for_image(self):
        manager = create_default_lens_config()

        path1 = "/path/to/image_lens_a_180_001.jpg"
        lens1 = manager.get_lens_for_image(path1)
        self.assertIsNotNone(lens1)
        self.assertEqual(lens1.name, "lens_a_180")

        path2 = "/path/to/image_no_match.jpg"
        lens2 = manager.get_lens_for_image(path2)
        self.assertIsNone(lens2)


class TestBatchProcessorNewFeatures(unittest.TestCase):
    def test_batch_processor_with_border_mode(self):
        processor = BatchProcessor(
            border_mode=BorderHandlingMode.CROP,
        )
        self.assertEqual(processor.border_mode, BorderHandlingMode.CROP)

    def test_batch_processor_set_border_mode(self):
        processor = BatchProcessor()
        processor.set_border_mode(BorderHandlingMode.PAD)
        self.assertEqual(processor.border_mode, BorderHandlingMode.PAD)

    def test_batch_processor_with_lens_config(self):
        manager = create_default_lens_config()
        processor = BatchProcessor(lens_config_manager=manager)

        self.assertIsNotNone(processor.lens_config_manager)

    def test_batch_processor_set_lens_config_manager(self):
        processor = BatchProcessor()
        manager = create_default_lens_config()
        processor.set_lens_config_manager(manager)

        self.assertIsNotNone(processor.lens_config_manager)

    def test_process_directory_with_lens_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = os.path.join(tmpdir, "input")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(input_dir)

            manager = create_default_lens_config()

            for i in range(3):
                img = generate_synthetic_fisheye_with_lines(size=200)
                cv2.imwrite(os.path.join(input_dir, f"img_lens_a_180_{i:03d}.jpg"), img)

            processor = BatchProcessor(
                lens_config_manager=manager,
                border_mode=BorderHandlingMode.CROP,
                num_workers=1,
            )

            results = processor.process_directory_with_lens_config(
                input_dir,
                output_dir,
            )

            self.assertEqual(len(results), 3)
            for result in results:
                self.assertTrue(result["success"])
                self.assertEqual(result["lens_used"], "lens_a_180")

    def test_process_groups_by_lens(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = os.path.join(tmpdir, "input")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(input_dir)

            manager = create_default_lens_config()

            lens_config_a = LensConfig(
                name="lens_a_180",
                projection_type=FisheyeProjectionType.EQUISOLID,
                focal_length=100.0,
                center=(100.0, 100.0),
                fov_degrees=180.0,
            )
            lens_config_b = LensConfig(
                name="lens_b_220",
                projection_type=FisheyeProjectionType.EQUIDISTANT,
                focal_length=90.0,
                center=(100.0, 100.0),
                fov_degrees=220.0,
            )
            manager.add_lens(lens_config_a)
            manager.add_lens(lens_config_b)

            for i in range(2):
                img = generate_synthetic_fisheye_with_lines(size=200)
                cv2.imwrite(os.path.join(input_dir, f"lens_a_180_img_{i:03d}.jpg"), img)

            for i in range(2):
                img = generate_synthetic_fisheye_with_lines(size=200)
                cv2.imwrite(os.path.join(input_dir, f"lens_b_220_img_{i:03d}.jpg"), img)

            processor = BatchProcessor(
                lens_config_manager=manager,
                num_workers=1,
            )

            lens_name_patterns = {
                "lens_a_180": "lens_a",
                "lens_b_220": "lens_b",
            }

            results = processor.process_groups_by_lens(
                input_dir,
                output_dir,
                lens_name_patterns=lens_name_patterns,
            )

            self.assertEqual(len(results), 4)

            lens_groups = {}
            for r in results:
                group = r.get("lens_group", "unknown")
                lens_groups[group] = lens_groups.get(group, 0) + 1

            self.assertIn("lens_a_180", lens_groups)
            self.assertIn("lens_b_220", lens_groups)
            self.assertEqual(lens_groups["lens_a_180"], 2)
            self.assertEqual(lens_groups["lens_b_220"], 2)


def run_all_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestSelfCalibration))
    suite.addTests(loader.loadTestsFromTestCase(TestBorderHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestLensConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestBatchProcessorNewFeatures))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
