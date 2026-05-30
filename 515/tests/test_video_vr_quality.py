#!/usr/bin/env python3
import sys
import os
import tempfile
import unittest
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import (
    FisheyeCorrector,
    CorrectionMethod,
    BorderHandlingMode,
    FisheyeProjectionType,
    create_projection_model,
    fisheye_to_equirectangular,
    create_vr_panorama,
    evaluate_correction_quality,
    BatchProcessor,
    estimate_fisheye_params_auto,
)


def generate_synthetic_fisheye(size: int = 400, fov_degrees: float = 180.0) -> np.ndarray:
    image = np.zeros((size, size, 3), dtype=np.uint8)
    center = (size // 2, size // 2)
    max_r = size // 2 - 10

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
                color = (int(255 * (j / size)), int(255 * (i / size)), 150)
                cv2.rectangle(image, (x_f - 5, y_f - 5), (x_f + 5, y_f + 5), color, -1)

    for angle in [0, 30, 60, 90, 120, 150]:
        rad = np.deg2rad(angle)
        for r_val in np.linspace(20, max_r - 10, 15):
            x = int(center[0] + r_val * np.cos(rad))
            y = int(center[1] + r_val * np.sin(rad))
            cv2.circle(image, (x, y), 3, (255, 200, 0), -1)

    cv2.circle(image, center, max_r, (255, 255, 255), 2)
    return image


def create_test_video(video_path: str, num_frames: int = 10, size: int = 300):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(video_path, fourcc, 30.0, (size, size))

    for i in range(num_frames):
        frame = generate_synthetic_fisheye(size=size)
        cv2.putText(frame, f"Frame {i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        out.write(frame)

    out.release()
    return video_path


class TestVideoCorrection(unittest.TestCase):
    def setUp(self):
        self.test_image = generate_synthetic_fisheye(size=400)
        params = estimate_fisheye_params_auto(self.test_image)
        self.test_model = params["model"]

    def test_process_video_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_video = os.path.join(tmpdir, "test_input.mp4")
            output_video = os.path.join(tmpdir, "test_output.mp4")
            create_test_video(input_video, num_frames=5, size=300)

            processor = BatchProcessor(
                distortion_model=self.test_model,
                num_workers=1,
            )

            result = processor.process_video(
                input_video,
                output_video,
                auto_params=False,
                stabilize_params=False,
            )

            self.assertTrue(result["success"])
            self.assertEqual(result["total_frames"], 5)
            self.assertEqual(result["processed_frames"], 5)
            self.assertTrue(os.path.exists(output_video))
            self.assertFalse(result["stabilized"])
            self.assertFalse(result["vr_mode"])

    def test_process_video_with_stabilization(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_video = os.path.join(tmpdir, "test_input.mp4")
            output_video = os.path.join(tmpdir, "test_output.mp4")
            create_test_video(input_video, num_frames=5, size=300)

            processor = BatchProcessor(num_workers=1)

            result = processor.process_video(
                input_video,
                output_video,
                auto_params=True,
                stabilize_params=True,
                calibration_frame_interval=2,
                temporal_smoothing=0.8,
            )

            self.assertTrue(result["success"])
            self.assertTrue(result["stabilized"])
            self.assertIn("final_params", result)
            self.assertIn("params_history", result)
            self.assertGreater(len(result["params_history"]), 0)

            if "params_stability" in result:
                self.assertIn("focal_std", result["params_stability"])
                self.assertIn("center_x_std", result["params_stability"])
                self.assertIn("center_y_std", result["params_stability"])

    def test_process_video_with_vr_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_video = os.path.join(tmpdir, "test_input.mp4")
            output_video = os.path.join(tmpdir, "test_output.mp4")
            create_test_video(input_video, num_frames=3, size=300)

            processor = BatchProcessor(
                distortion_model=self.test_model,
                num_workers=1,
            )

            result = processor.process_video(
                input_video,
                output_video,
                auto_params=False,
                use_vr_mode=True,
            )

            self.assertTrue(result["success"])
            self.assertTrue(result["vr_mode"])
            self.assertTrue(os.path.exists(output_video))

    def test_process_video_with_quality_scores(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_video = os.path.join(tmpdir, "test_input.mp4")
            output_video = os.path.join(tmpdir, "test_output.mp4")
            create_test_video(input_video, num_frames=5, size=300)

            processor = BatchProcessor(
                distortion_model=self.test_model,
                num_workers=1,
            )

            result = processor.process_video(
                input_video,
                output_video,
                auto_params=False,
                stabilize_params=False,
            )

            self.assertTrue(result["success"])
            self.assertIn("mean_quality_score", result)
            self.assertIn("std_quality_score", result)
            self.assertGreaterEqual(result["mean_quality_score"], 0.0)
            self.assertLessEqual(result["mean_quality_score"], 1.0)


class TestVRExpansion(unittest.TestCase):
    def setUp(self):
        self.test_image = generate_synthetic_fisheye(size=400)
        params = estimate_fisheye_params_auto(self.test_image)
        self.test_model = params["model"]

    def test_fisheye_to_equirectangular_basic(self):
        equirect = fisheye_to_equirectangular(
            self.test_image,
            distortion_model=self.test_model,
        )

        self.assertIsNotNone(equirect)
        self.assertEqual(len(equirect.shape), 3)
        self.assertEqual(equirect.shape[2], 3)
        h_orig, w_orig = self.test_image.shape[:2]
        h_out, w_out = equirect.shape[:2]
        self.assertEqual(h_out, h_orig)
        self.assertEqual(w_out, w_orig * 2)

    def test_fisheye_to_equirectangular_custom_size(self):
        output_size = (200, 400)
        equirect = fisheye_to_equirectangular(
            self.test_image,
            distortion_model=self.test_model,
            output_size=output_size,
        )

        self.assertEqual(equirect.shape[0], output_size[0])
        self.assertEqual(equirect.shape[1], output_size[1])

    def test_fisheye_to_equirectangular_with_offsets(self):
        equirect = fisheye_to_equirectangular(
            self.test_image,
            distortion_model=self.test_model,
            yaw_offset=90.0,
            pitch_offset=10.0,
        )

        self.assertIsNotNone(equirect)
        self.assertEqual(len(equirect.shape), 3)

    def test_fisheye_to_equirectangular_auto_params(self):
        equirect = fisheye_to_equirectangular(self.test_image)

        self.assertIsNotNone(equirect)
        self.assertEqual(len(equirect.shape), 3)

    def test_fisheye_to_equirectangular_grayscale(self):
        gray_image = cv2.cvtColor(self.test_image, cv2.COLOR_BGR2GRAY)
        equirect = fisheye_to_equirectangular(
            gray_image,
            distortion_model=self.test_model,
        )

        self.assertIsNotNone(equirect)
        self.assertEqual(len(equirect.shape), 2)

    def test_create_vr_panorama_single_image(self):
        panorama = create_vr_panorama(
            [self.test_image],
            distortion_model=self.test_model,
            output_size=(200, 400),
        )

        self.assertIsNotNone(panorama)
        self.assertEqual(panorama.shape[0], 200)
        self.assertEqual(panorama.shape[1], 400)
        self.assertEqual(panorama.shape[2], 3)

    def test_create_vr_panorama_multiple_images(self):
        images = [generate_synthetic_fisheye(size=300) for _ in range(3)]

        panorama = create_vr_panorama(
            images,
            distortion_model=self.test_model,
            output_size=(200, 400),
            blend_width=30,
        )

        self.assertIsNotNone(panorama)
        self.assertEqual(panorama.shape[0], 200)
        self.assertEqual(panorama.shape[1], 400)

    def test_create_vr_panorama_no_blend(self):
        images = [generate_synthetic_fisheye(size=300) for _ in range(2)]

        panorama = create_vr_panorama(
            images,
            distortion_model=self.test_model,
            output_size=(200, 400),
            blend_width=0,
        )

        self.assertIsNotNone(panorama)
        self.assertEqual(panorama.shape, (200, 400, 3))

    def test_create_vr_panorama_empty(self):
        with self.assertRaises(ValueError):
            create_vr_panorama([])


class TestCorrectionQuality(unittest.TestCase):
    def setUp(self):
        self.test_image = generate_synthetic_fisheye(size=400)
        params = estimate_fisheye_params_auto(self.test_image)
        self.test_model = params["model"]
        self.corrector = FisheyeCorrector(
            distortion_model=self.test_model,
            method=CorrectionMethod.SPHERICAL_PROJECTION,
        )
        self.corrected_image = self.corrector.correct(self.test_image)

    def test_evaluate_correction_quality_basic(self):
        quality = evaluate_correction_quality(
            self.test_image,
            self.corrected_image,
            self.test_model,
        )

        self.assertIsInstance(quality, dict)
        self.assertIn("quality_score", quality)
        self.assertIn("mean_straightness_error", quality)
        self.assertIn("frame_retention_ratio", quality)

    def test_evaluate_correction_quality_metrics(self):
        quality = evaluate_correction_quality(
            self.test_image,
            self.corrected_image,
            self.test_model,
        )

        self.assertGreaterEqual(quality["quality_score"], 0.0)
        self.assertLessEqual(quality["quality_score"], 1.0)
        self.assertGreaterEqual(quality["mean_straightness_error"], 0.0)
        self.assertGreaterEqual(quality["frame_retention_ratio"], 0.0)
        self.assertLessEqual(quality["frame_retention_ratio"], 1.0)

    def test_evaluate_correction_quality_straightness_metrics(self):
        quality = evaluate_correction_quality(
            self.test_image,
            self.corrected_image,
            self.test_model,
        )

        self.assertIn("median_straightness_error", quality)
        self.assertIn("max_straightness_error", quality)
        self.assertIn("weighted_straightness_error", quality)
        self.assertGreaterEqual(quality["median_straightness_error"], 0.0)
        self.assertGreaterEqual(quality["max_straightness_error"], 0.0)
        self.assertGreaterEqual(quality["weighted_straightness_error"], 0.0)

    def test_evaluate_correction_quality_frame_metrics(self):
        quality = evaluate_correction_quality(
            self.test_image,
            self.corrected_image,
            self.test_model,
        )

        self.assertIn("valid_pixels", quality)
        self.assertIn("total_pixels", quality)
        self.assertIn("original_resolution", quality)
        self.assertIn("corrected_resolution", quality)
        self.assertIn("area_ratio", quality)
        self.assertGreater(quality["total_pixels"], 0)
        self.assertGreater(quality["valid_pixels"], 0)
        self.assertEqual(len(quality["original_resolution"]), 2)
        self.assertEqual(len(quality["corrected_resolution"]), 2)

    def test_evaluate_correction_quality_segment_count(self):
        quality = evaluate_correction_quality(
            self.test_image,
            self.corrected_image,
            self.test_model,
        )

        self.assertIn("num_segments_analyzed", quality)
        self.assertGreaterEqual(quality["num_segments_analyzed"], 0)

    def test_evaluate_correction_quality_different_border_modes(self):
        corrector_crop = FisheyeCorrector(
            distortion_model=self.test_model,
            method=CorrectionMethod.SPHERICAL_PROJECTION,
            border_mode=BorderHandlingMode.CROP,
        )
        corrected_crop = corrector_crop.correct(self.test_image)

        quality_crop = evaluate_correction_quality(
            self.test_image,
            corrected_crop,
            self.test_model,
        )

        corrector_full = FisheyeCorrector(
            distortion_model=self.test_model,
            method=CorrectionMethod.SPHERICAL_PROJECTION,
            border_mode=BorderHandlingMode.FULL,
        )
        corrected_full = corrector_full.correct(self.test_image)

        quality_full = evaluate_correction_quality(
            self.test_image,
            corrected_full,
            self.test_model,
        )

        self.assertGreater(quality_full["frame_retention_ratio"], 0)
        self.assertGreater(quality_crop["frame_retention_ratio"], 0)
        self.assertGreater(quality_full["area_ratio"], quality_crop["area_ratio"])

    def test_evaluate_correction_quality_grayscale(self):
        gray_orig = cv2.cvtColor(self.test_image, cv2.COLOR_BGR2GRAY)
        gray_corrected = cv2.cvtColor(self.corrected_image, cv2.COLOR_BGR2GRAY)

        quality = evaluate_correction_quality(
            gray_orig,
            gray_corrected,
            self.test_model,
        )

        self.assertIsInstance(quality, dict)
        self.assertIn("quality_score", quality)
        self.assertIn("frame_retention_ratio", quality)

    def test_evaluate_correction_quality_area_ratio(self):
        quality = evaluate_correction_quality(
            self.test_image,
            self.corrected_image,
            self.test_model,
        )

        h_orig, w_orig = self.test_image.shape[:2]
        h_corr, w_corr = self.corrected_image.shape[:2]
        expected_ratio = (h_corr * w_corr) / (h_orig * w_orig)

        self.assertAlmostEqual(quality["area_ratio"], expected_ratio, places=5)


def run_all_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestVideoCorrection))
    suite.addTests(loader.loadTestsFromTestCase(TestVRExpansion))
    suite.addTests(loader.loadTestsFromTestCase(TestCorrectionQuality))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
