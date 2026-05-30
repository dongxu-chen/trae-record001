#!/usr/bin/env python3
import sys
import os
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2

from src.distortion_models import (
    FisheyeProjectionType,
    EquidistantProjection,
    EquisolidProjection,
    OrthographicProjection,
    StereographicProjection,
    create_projection_model,
    estimate_projection_type_from_fov,
)
from src.calibration import (
    FisheyeCalibrator,
    estimate_fov_from_image,
    estimate_center_auto,
    estimate_focal_length_auto,
    estimate_fisheye_params_auto,
    estimate_params_from_multiple_images,
)
from src.fisheye_corrector import (
    FisheyeCorrector,
    CorrectionMethod,
    correct_fisheye_image,
    correct_fisheye_with_params,
    create_panorama_from_fisheye,
    generate_correction_grid,
)
from src.batch_processor import BatchProcessor, process_batch_simple
from src.visualizer import FisheyeVisualizer


def generate_synthetic_fisheye(
    size: int = 400, fov_degrees: float = 180.0, add_grid: bool = True
) -> np.ndarray:
    image = np.zeros((size, size, 3), dtype=np.uint8)
    center = (size // 2, size // 2)
    max_r = size // 2 - 10

    if add_grid:
        for i in range(0, size, 40):
            for j in range(0, size, 40):
                dx = j - center[0]
                dy = i - center[1]
                r = np.sqrt(dx**2 + dy**2)
                if r < max_r and r > 0:
                    theta = np.arcsin(r / max_r) * (fov_degrees / 180.0) * np.pi / 2
                    r_fisheye = 2.0 * (size / 3.0) * np.sin(theta / 2.0)
                    x_f = int(center[0] + r_fisheye * dx / r)
                    y_f = int(center[1] + r_fisheye * dy / r)
                    color = (int(255 * (j / size)), int(255 * (i / size)), 128)
                    cv2.rectangle(image, (x_f - 5, y_f - 5), (x_f + 5, y_f + 5), color, -1)

    cv2.circle(image, center, max_r, (255, 255, 255), 2)
    return image


class TestDistortionModels(unittest.TestCase):
    def test_equidistant_projection(self):
        model = EquidistantProjection(focal_length=100.0, center=(320, 240))

        theta = np.radians(45)
        r = model.project(theta)
        self.assertAlmostEqual(r, 100.0 * np.pi / 4, places=5)

        r_test = 50.0
        theta_unproj = model.unproject(r_test)
        self.assertAlmostEqual(theta_unproj, 0.5, places=5)

    def test_equisolid_projection(self):
        model = EquisolidProjection(focal_length=100.0, center=(320, 240))

        theta = np.radians(90)
        r = model.project(theta)
        self.assertAlmostEqual(r, 200.0 * np.sin(np.pi / 4), places=5)

        r_test = model.project(np.radians(60))
        theta_unproj = model.unproject(r_test)
        self.assertAlmostEqual(theta_unproj, np.radians(60), places=5)

    def test_orthographic_projection(self):
        model = OrthographicProjection(focal_length=100.0, center=(320, 240))

        theta = np.radians(30)
        r = model.project(theta)
        self.assertAlmostEqual(r, 50.0, places=5)

        r_test = 86.60254
        theta_unproj = model.unproject(r_test)
        self.assertAlmostEqual(theta_unproj, np.radians(60), places=4)

    def test_stereographic_projection(self):
        model = StereographicProjection(focal_length=100.0, center=(320, 240))

        theta = np.radians(90)
        r = model.project(theta)
        self.assertAlmostEqual(r, 200.0, places=5)

        r_test = 200.0
        theta_unproj = model.unproject(r_test)
        self.assertAlmostEqual(theta_unproj, np.pi / 2, places=5)

    def test_pixel_angle_conversion(self):
        model = EquidistantProjection(focal_length=200.0, center=(400, 300))

        pixel = np.array([400.0, 100.0])
        angles = model.pixel_to_angle(pixel)

        self.assertAlmostEqual(angles[0], 1.0, places=5)
        self.assertAlmostEqual(angles[1], -np.pi / 2, places=5)

        pixel_back = model.angle_to_pixel(angles)
        self.assertAlmostEqual(pixel_back[0], pixel[0], places=3)
        self.assertAlmostEqual(pixel_back[1], pixel[1], places=3)

    def test_pixel_cartesian_conversion(self):
        model = EquisolidProjection(focal_length=200.0, center=(400, 300))

        pixel = np.array([400.0, 300.0])
        cart = model.pixel_to_cartesian(pixel)

        self.assertAlmostEqual(cart[0], 0.0, places=5)
        self.assertAlmostEqual(cart[1], 0.0, places=5)
        self.assertAlmostEqual(cart[2], 1.0, places=5)

        pixel_back = model.cartesian_to_pixel(cart)
        self.assertAlmostEqual(pixel_back[0], pixel[0], places=3)
        self.assertAlmostEqual(pixel_back[1], pixel[1], places=3)

    def test_create_projection_model(self):
        for proj_type in FisheyeProjectionType:
            model = create_projection_model(proj_type, 100.0, (100, 100))
            self.assertIsNotNone(model)

    def test_estimate_projection_type(self):
        self.assertEqual(
            estimate_projection_type_from_fov(80), FisheyeProjectionType.ORTHOGRAPHIC
        )
        self.assertEqual(
            estimate_projection_type_from_fov(100), FisheyeProjectionType.EQUISOLID
        )
        self.assertEqual(
            estimate_projection_type_from_fov(150), FisheyeProjectionType.EQUIDISTANT
        )
        self.assertEqual(
            estimate_projection_type_from_fov(200), FisheyeProjectionType.STEREOGRAPHIC
        )


class TestCalibration(unittest.TestCase):
    def test_estimate_center_auto(self):
        image = generate_synthetic_fisheye(size=400)
        center = estimate_center_auto(image)

        self.assertAlmostEqual(center[0], 200.0, delta=20)
        self.assertAlmostEqual(center[1], 200.0, delta=20)

    def test_estimate_fov_from_image(self):
        image = generate_synthetic_fisheye(size=400, fov_degrees=180)
        fov = estimate_fov_from_image(image)

        self.assertGreater(fov, 90)
        self.assertLess(fov, 220)

    def test_estimate_focal_length_auto(self):
        image = generate_synthetic_fisheye(size=400)
        center = estimate_center_auto(image)
        focal = estimate_focal_length_auto(image, center, fov_degrees=180)

        self.assertGreater(focal, 50)
        self.assertLess(focal, 250)

    def test_estimate_fisheye_params_auto(self):
        image = generate_synthetic_fisheye(size=400)
        params = estimate_fisheye_params_auto(image)

        self.assertIn("center", params)
        self.assertIn("focal_length", params)
        self.assertIn("fov_degrees", params)
        self.assertIn("projection_type", params)
        self.assertIn("model", params)

        self.assertIsInstance(params["projection_type"], FisheyeProjectionType)
        self.assertIsNotNone(params["model"])

    def test_estimate_params_from_multiple_images(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_paths = []
            for i in range(3):
                img = generate_synthetic_fisheye(size=300)
                path = os.path.join(tmpdir, f"img_{i}.jpg")
                cv2.imwrite(path, img)
                image_paths.append(path)

            params = estimate_params_from_multiple_images(image_paths)

            self.assertIn("center", params)
            self.assertIn("focal_length", params)
            self.assertIn("fov_degrees", params)
            self.assertIn("model", params)


class TestFisheyeCorrector(unittest.TestCase):
    def test_spherical_correction(self):
        image = generate_synthetic_fisheye(size=400)
        corrector = FisheyeCorrector(method=CorrectionMethod.SPHERICAL_PROJECTION)

        corrected = corrector.correct(image)

        self.assertEqual(len(corrected.shape), 3)
        self.assertEqual(corrected.shape[2], 3)
        self.assertGreater(corrected.shape[0], image.shape[0])
        self.assertGreater(corrected.shape[1], image.shape[1])

    def test_equirectangular_correction(self):
        image = generate_synthetic_fisheye(size=400)
        corrector = FisheyeCorrector(method=CorrectionMethod.EQURECTANGULAR_PROJECTION)

        corrected = corrector.correct(image, output_size=(400, 800))

        self.assertEqual(corrected.shape[0], 400)
        self.assertEqual(corrected.shape[1], 800)

    def test_perspective_correction(self):
        image = generate_synthetic_fisheye(size=400)
        corrector = FisheyeCorrector(method=CorrectionMethod.PERSPECTIVE_PROJECTION)

        corrected = corrector.correct(image)

        self.assertEqual(len(corrected.shape), 3)

    def test_correction_with_custom_output_size(self):
        image = generate_synthetic_fisheye(size=400)
        output_size = (500, 600)

        corrected = correct_fisheye_image(image, output_size=output_size)

        self.assertEqual(corrected.shape[0], output_size[0])
        self.assertEqual(corrected.shape[1], output_size[1])

    def test_correct_with_custom_rotation(self):
        image = generate_synthetic_fisheye(size=400)
        params = estimate_fisheye_params_auto(image)

        corrector = FisheyeCorrector(distortion_model=params["model"])
        corrected = corrector.correct_with_custom_rotation(
            image, yaw=30, pitch=15, roll=0
        )

        self.assertEqual(len(corrected.shape), 3)

    def test_correct_fisheye_with_params(self):
        image = generate_synthetic_fisheye(size=400)
        params = estimate_fisheye_params_auto(image)

        corrected = correct_fisheye_with_params(image, params["model"])

        self.assertEqual(len(corrected.shape), 3)

    def test_create_panorama(self):
        image = generate_synthetic_fisheye(size=400)
        panorama = create_panorama_from_fisheye(image, output_size=(540, 1080))

        self.assertEqual(panorama.shape[0], 540)
        self.assertEqual(panorama.shape[1], 1080)

    def test_generate_correction_grid(self):
        image = generate_synthetic_fisheye(size=400)
        params = estimate_fisheye_params_auto(image)

        h_lines_x, h_lines_y, v_lines_x, v_lines_y = generate_correction_grid(
            image.shape[:2], params["model"], grid_spacing=50
        )

        self.assertEqual(len(h_lines_x.shape), 2)
        self.assertEqual(len(v_lines_x.shape), 2)


class TestBatchProcessor(unittest.TestCase):
    def test_process_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = os.path.join(tmpdir, "input")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(input_dir)

            for i in range(3):
                img = generate_synthetic_fisheye(size=200)
                cv2.imwrite(os.path.join(input_dir, f"img_{i}.jpg"), img)

            processor = BatchProcessor(num_workers=2)
            results = processor.process_directory(
                input_dir, output_dir, auto_params=True
            )

            self.assertEqual(len(results), 3)
            for result in results:
                self.assertTrue(result["success"])
                self.assertTrue(os.path.exists(result["output"]))

            summary = processor.get_summary()
            self.assertEqual(summary["total"], 3)
            self.assertEqual(summary["success"], 3)
            self.assertEqual(summary["success_rate"], 1.0)

    def test_process_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            output_paths = []

            for i in range(2):
                img = generate_synthetic_fisheye(size=200)
                in_path = os.path.join(tmpdir, f"in_{i}.jpg")
                out_path = os.path.join(tmpdir, f"out_{i}.jpg")
                cv2.imwrite(in_path, img)
                input_paths.append(in_path)
                output_paths.append(out_path)

            processor = BatchProcessor(num_workers=1)
            results = processor.process_list(
                input_paths, output_paths, auto_params=True
            )

            self.assertEqual(len(results), 2)
            for result in results:
                self.assertTrue(result["success"])

    def test_save_load_params(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            param_file = os.path.join(tmpdir, "params.json")

            processor = BatchProcessor()

            test_params = {
                "center": (320.0, 240.0),
                "focal_length": 500.0,
                "fov_degrees": 180.0,
                "projection_type": FisheyeProjectionType.EQUISOLID,
            }

            processor.save_params(param_file, test_params)
            self.assertTrue(os.path.exists(param_file))

            loaded = processor._load_params(param_file)
            self.assertAlmostEqual(loaded["center"][0], 320.0, places=1)
            self.assertAlmostEqual(loaded["center"][1], 240.0, places=1)
            self.assertAlmostEqual(loaded["focal_length"], 500.0, places=1)
            self.assertEqual(loaded["projection_type"], FisheyeProjectionType.EQUISOLID)


class TestVisualizer(unittest.TestCase):
    def test_visualizer_creation(self):
        visualizer = FisheyeVisualizer(figsize=(10, 8), dpi=100)
        self.assertIsNotNone(visualizer)

    def test_show_image_pair(self):
        image1 = generate_synthetic_fisheye(size=200)
        image2 = generate_synthetic_fisheye(size=300)

        visualizer = FisheyeVisualizer()
        try:
            visualizer._create_figure(1, 2)
            visualizer._imshow(visualizer.axes[0, 0], image1, "Test 1")
            visualizer._imshow(visualizer.axes[0, 1], image2, "Test 2")
        finally:
            visualizer.close()

    def test_show_projection_curves(self):
        visualizer = FisheyeVisualizer()
        try:
            import matplotlib

            matplotlib.use("Agg")
            visualizer.show_projection_curves(fov_degrees=180.0)
        finally:
            visualizer.close()


def run_all_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestDistortionModels))
    suite.addTests(loader.loadTestsFromTestCase(TestCalibration))
    suite.addTests(loader.loadTestsFromTestCase(TestFisheyeCorrector))
    suite.addTests(loader.loadTestsFromTestCase(TestBatchProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestVisualizer))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
