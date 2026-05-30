import os
import glob
from typing import List, Optional, Tuple, Callable, Dict, Any
import numpy as np
import cv2
from concurrent.futures import ThreadPoolExecutor, as_completed
from .distortion_models import FisheyeDistortionModel, FisheyeProjectionType
from .fisheye_corrector import (
    FisheyeCorrector,
    CorrectionMethod,
    BorderHandlingMode,
    correct_fisheye_with_params,
)
from .calibration import (
    estimate_fisheye_params_auto,
    estimate_params_from_multiple_images,
    FisheyeCalibrator,
)
from .lens_config import LensConfigManager, LensConfig


class BatchProcessor:
    SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif")

    def __init__(
        self,
        distortion_model: Optional[FisheyeDistortionModel] = None,
        method: CorrectionMethod = CorrectionMethod.SPHERICAL_PROJECTION,
        output_size: Optional[Tuple[int, int]] = None,
        num_workers: int = 4,
        border_mode: BorderHandlingMode = BorderHandlingMode.FULL,
        lens_config_manager: Optional[LensConfigManager] = None,
    ):
        self.distortion_model = distortion_model
        self.method = method
        self.output_size = output_size
        self.num_workers = num_workers
        self.border_mode = border_mode
        self.lens_config_manager = lens_config_manager
        self.results: List[Dict[str, Any]] = []

    def set_distortion_model(self, model: FisheyeDistortionModel):
        self.distortion_model = model

    def set_method(self, method: CorrectionMethod):
        self.method = method

    def set_output_size(self, size: Tuple[int, int]):
        self.output_size = size

    def set_border_mode(self, mode: BorderHandlingMode):
        self.border_mode = mode

    def set_lens_config_manager(self, manager: LensConfigManager):
        self.lens_config_manager = manager

    def _get_image_files(self, input_dir: str) -> List[str]:
        image_files = set()
        for ext in self.SUPPORTED_EXTENSIONS:
            pattern = os.path.join(input_dir, f"*{ext}")
            image_files.update(glob.glob(pattern))
            pattern = os.path.join(input_dir, f"*{ext.upper()}")
            image_files.update(glob.glob(pattern))
        return sorted(image_files)

    def _process_single_image(
        self,
        image_path: str,
        output_path: str,
        corrector: FisheyeCorrector,
        auto_params: bool = False,
        lens_model: Optional[FisheyeDistortionModel] = None,
    ) -> Dict[str, Any]:
        try:
            image = cv2.imread(image_path)
            if image is None:
                return {
                    "input": image_path,
                    "output": output_path,
                    "success": False,
                    "error": "Could not read image",
                }

            used_lens = None
            if lens_model is not None:
                corrector.set_distortion_model(lens_model)
                used_lens = "custom"
            elif auto_params or self.distortion_model is None:
                if self.lens_config_manager is not None:
                    lens_config = self.lens_config_manager.get_lens_for_image(image_path)
                    if lens_config is not None:
                        corrector.set_distortion_model(lens_config.get_model())
                        used_lens = lens_config.name
                    else:
                        params = estimate_fisheye_params_auto(image)
                        corrector.set_distortion_model(params["model"])
                        used_lens = "auto_estimated"
                else:
                    params = estimate_fisheye_params_auto(image)
                    corrector.set_distortion_model(params["model"])
                    used_lens = "auto_estimated"

            corrected = corrector.correct(
                image,
                output_size=self.output_size,
                handling_mode=self.border_mode,
            )

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            cv2.imwrite(output_path, corrected)

            return {
                "input": image_path,
                "output": output_path,
                "success": True,
                "shape": corrected.shape,
                "lens_used": used_lens,
            }

        except Exception as e:
            return {
                "input": image_path,
                "output": output_path,
                "success": False,
                "error": str(e),
            }

    def process_directory(
        self,
        input_dir: str,
        output_dir: str,
        auto_params: bool = False,
        calibrate_first: bool = False,
        callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        if not os.path.exists(input_dir):
            raise ValueError(f"Input directory does not exist: {input_dir}")

        image_files = self._get_image_files(input_dir)
        if len(image_files) == 0:
            raise ValueError(f"No images found in directory: {input_dir}")

        if calibrate_first and self.distortion_model is None:
            print("Calibrating from images...")
            params = estimate_params_from_multiple_images(image_files)
            self.distortion_model = params["model"]
            print(f"Calibration complete. FOV: {params['fov_degrees']:.1f}°")

        corrector = FisheyeCorrector(
            distortion_model=self.distortion_model,
            method=self.method,
        )

        os.makedirs(output_dir, exist_ok=True)

        self.results = []
        total = len(image_files)

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = []
            for idx, image_path in enumerate(image_files):
                filename = os.path.basename(image_path)
                name, ext = os.path.splitext(filename)
                output_path = os.path.join(output_dir, f"{name}_corrected{ext}")

                future = executor.submit(
                    self._process_single_image,
                    image_path,
                    output_path,
                    corrector,
                    auto_params,
                )
                futures.append((future, idx, image_path, output_path))

            completed = 0
            for future, idx, input_path, output_path in futures:
                result = future.result()
                self.results.append(result)
                completed += 1

                if callback is not None:
                    callback(completed, total, result)
                else:
                    status = "OK" if result["success"] else "FAIL"
                    print(f"[{completed}/{total}] {status} {os.path.basename(input_path)}")

        return self.results

    def process_with_custom_params(
        self,
        input_dir: str,
        output_dir: str,
        param_file: Optional[str] = None,
        callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        if param_file is not None and os.path.exists(param_file):
            params = self._load_params(param_file)
            if "model" in params:
                self.distortion_model = params["model"]
        elif self.distortion_model is None:
            return self.process_directory(
                input_dir, output_dir, auto_params=True, callback=callback
            )

        return self.process_directory(
            input_dir, output_dir, auto_params=False, callback=callback
        )

    def process_directory_with_lens_config(
        self,
        input_dir: str,
        output_dir: str,
        lens_config_file: Optional[str] = None,
        lens_config_manager: Optional[LensConfigManager] = None,
        callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        if not os.path.exists(input_dir):
            raise ValueError(f"Input directory does not exist: {input_dir}")

        if lens_config_manager is not None:
            self.lens_config_manager = lens_config_manager
        elif lens_config_file is not None and os.path.exists(lens_config_file):
            self.lens_config_manager = LensConfigManager(lens_config_file)
        elif self.lens_config_manager is None:
            raise ValueError(
                "No lens configuration available. Provide either lens_config_file or lens_config_manager"
            )

        image_files = self._get_image_files(input_dir)
        if len(image_files) == 0:
            raise ValueError(f"No images found in directory: {input_dir}")

        corrector = FisheyeCorrector(
            distortion_model=self.lens_config_manager.get_active_model(),
            method=self.method,
            border_mode=self.border_mode,
        )

        os.makedirs(output_dir, exist_ok=True)

        self.results = []
        total = len(image_files)

        lens_usage: Dict[str, int] = {}

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = []
            for idx, image_path in enumerate(image_files):
                filename = os.path.basename(image_path)
                name, ext = os.path.splitext(filename)
                output_path = os.path.join(output_dir, f"{name}_corrected{ext}")

                future = executor.submit(
                    self._process_single_image,
                    image_path,
                    output_path,
                    corrector,
                    True,
                )
                futures.append((future, idx, image_path, output_path))

            completed = 0
            for future, idx, input_path, output_path in futures:
                result = future.result()
                self.results.append(result)
                completed += 1

                if result.get("lens_used"):
                    lens_usage[result["lens_used"]] = lens_usage.get(result["lens_used"], 0) + 1

                if callback is not None:
                    callback(completed, total, result)
                else:
                    status = "✓" if result["success"] else "✗"
                    lens_info = f" [{result.get('lens_used', 'unknown')}]" if result["success"] else ""
                    print(f"[{completed}/{total}] {status} {os.path.basename(input_path)}{lens_info}")

        if lens_usage:
            print("\nLens usage summary:")
            for lens_name, count in sorted(lens_usage.items()):
                print(f"  {lens_name}: {count} images")

        return self.results

    def process_groups_by_lens(
        self,
        input_dir: str,
        output_dir: str,
        lens_name_patterns: Optional[Dict[str, str]] = None,
        callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        if not os.path.exists(input_dir):
            raise ValueError(f"Input directory does not exist: {input_dir}")

        if self.lens_config_manager is None:
            raise ValueError("LensConfigManager must be set for group processing")

        image_files = self._get_image_files(input_dir)
        if len(image_files) == 0:
            raise ValueError(f"No images found in directory: {input_dir}")

        if lens_name_patterns is None:
            lens_groups = self.lens_config_manager.batch_config_from_directory(input_dir, {})
        else:
            lens_groups = self.lens_config_manager.batch_config_from_directory(
                input_dir, lens_name_patterns
            )

        print("Processing images grouped by lens:")
        for lens_name, images in lens_groups.items():
            if len(images) > 0:
                print(f"  {lens_name}: {len(images)} images")

        all_results = []

        for lens_name, images in lens_groups.items():
            if len(images) == 0:
                continue

            lens_config = self.lens_config_manager.get_lens(lens_name)
            if lens_config is None:
                print(f"Warning: Lens '{lens_name}' not found in config, using auto estimation")
                lens_model = None
            else:
                lens_model = lens_config.get_model()
                print(f"\nProcessing group: {lens_name}")

            group_output_dir = os.path.join(output_dir, lens_name)
            os.makedirs(group_output_dir, exist_ok=True)

            corrector = FisheyeCorrector(
                distortion_model=lens_model,
                method=self.method,
                border_mode=self.border_mode,
            )

            group_results = []
            total = len(images)

            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                futures = []
                for idx, image_path in enumerate(images):
                    filename = os.path.basename(image_path)
                    name, ext = os.path.splitext(filename)
                    output_path = os.path.join(group_output_dir, f"{name}_corrected{ext}")

                    future = executor.submit(
                        self._process_single_image,
                        image_path,
                        output_path,
                        corrector,
                        lens_model is None,
                        lens_model,
                    )
                    futures.append((future, idx, image_path, output_path))

                completed = 0
                for future, idx, input_path, output_path in futures:
                    result = future.result()
                    result["lens_group"] = lens_name
                    group_results.append(result)
                    all_results.append(result)
                    completed += 1

                    if callback is not None:
                        callback(completed, total, result)
                    else:
                        status = "OK" if result["success"] else "FAIL"
                        print(f"  [{completed}/{total}] {status} {os.path.basename(input_path)}")

        self.results = all_results
        return all_results

    def process_list(
        self,
        image_paths: List[str],
        output_paths: List[str],
        auto_params: bool = False,
        callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        if len(image_paths) != len(output_paths):
            raise ValueError("Number of input and output paths must match")

        corrector = FisheyeCorrector(
            distortion_model=self.distortion_model,
            method=self.method,
        )

        self.results = []
        total = len(image_paths)

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = []
            for idx, (input_path, output_path) in enumerate(
                zip(image_paths, output_paths)
            ):
                future = executor.submit(
                    self._process_single_image,
                    input_path,
                    output_path,
                    corrector,
                    auto_params,
                )
                futures.append((future, idx, input_path, output_path))

            completed = 0
            for future, idx, input_path, output_path in futures:
                result = future.result()
                self.results.append(result)
                completed += 1

                if callback is not None:
                    callback(completed, total, result)

        return self.results

    def calibrate_and_process(
        self,
        calibration_images: List[str],
        input_dir: str,
        output_dir: str,
        chessboard_size: Tuple[int, int] = (9, 6),
        square_size: float = 1.0,
        callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        calibrator = FisheyeCalibrator(
            chessboard_size=chessboard_size, square_size=square_size
        )

        print("Running chessboard calibration...")
        success = calibrator.calibrate_from_images(calibration_images)

        if not success:
            print("Chessboard calibration failed, falling back to auto-calibration")
            return self.process_directory(
                input_dir, output_dir, auto_params=True, callback=callback
            )

        print(
            f"Calibration successful. Reprojection error: {calibrator.reprojection_error:.4f}"
        )
        self.distortion_model = calibrator.get_projection_model()

        return self.process_directory(
            input_dir, output_dir, auto_params=False, callback=callback
        )

    def process_video(
        self,
        video_path: str,
        output_path: str,
        frame_interval: int = 1,
        auto_params: bool = False,
        stabilize_params: bool = True,
        calibration_frame_interval: int = 30,
        temporal_smoothing: float = 0.9,
        use_vr_mode: bool = False,
    ) -> Dict[str, Any]:
        if not os.path.exists(video_path):
            raise ValueError(f"Video file does not exist: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if use_vr_mode:
            if self.output_size is not None:
                out_size = self.output_size[::-1]
            else:
                out_size = (width * 2, height)
            method = CorrectionMethod.EQURECTANGULAR_PROJECTION
        else:
            if self.output_size is not None:
                out_size = self.output_size[::-1]
            else:
                out_size = (int(width * 1.5), int(height * 1.5))
            method = self.method

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, fps, out_size)

        corrector = FisheyeCorrector(
            distortion_model=self.distortion_model,
            method=method,
            output_size=self.output_size,
            border_mode=self.border_mode,
        )

        frame_count = 0
        processed_count = 0
        last_calibration_frame = -calibration_frame_interval - 1

        smoothed_focal = None
        smoothed_center = None
        current_params = None
        params_history = []
        frame_quality_scores = []

        from .self_calibration import evaluate_calibration_quality

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                need_calibration = False
                if auto_params or self.distortion_model is None:
                    if current_params is None:
                        need_calibration = True
                    elif stabilize_params and (frame_count - last_calibration_frame) >= calibration_frame_interval:
                        need_calibration = True

                if need_calibration:
                    try:
                        params = estimate_fisheye_params_auto(frame)
                        new_focal = params["focal_length"]
                        new_center = params["center"]

                        if stabilize_params and smoothed_focal is not None:
                            smoothed_focal = temporal_smoothing * smoothed_focal + (1 - temporal_smoothing) * new_focal
                            smoothed_center = (
                                temporal_smoothing * smoothed_center[0] + (1 - temporal_smoothing) * new_center[0],
                                temporal_smoothing * smoothed_center[1] + (1 - temporal_smoothing) * new_center[1],
                            )
                        else:
                            smoothed_focal = new_focal
                            smoothed_center = new_center

                        from .distortion_models import create_projection_model
                        stable_model = create_projection_model(
                            params["projection_type"],
                            smoothed_focal,
                            smoothed_center,
                        )
                        corrector.set_distortion_model(stable_model)
                        last_calibration_frame = frame_count

                        current_params = {
                            "focal_length": smoothed_focal,
                            "center": smoothed_center,
                            "projection_type": params["projection_type"],
                        }
                        params_history.append({
                            "frame": frame_count,
                            "focal_length": smoothed_focal,
                            "center_x": smoothed_center[0],
                            "center_y": smoothed_center[1],
                        })
                    except Exception:
                        pass

                if current_params is None and self.distortion_model is None:
                    try:
                        params = estimate_fisheye_params_auto(frame)
                        smoothed_focal = params["focal_length"]
                        smoothed_center = params["center"]
                        corrector.set_distortion_model(params["model"])
                        current_params = {
                            "focal_length": smoothed_focal,
                            "center": smoothed_center,
                            "projection_type": params["projection_type"],
                        }
                    except Exception:
                        pass

                corrected = corrector.correct(frame, handling_mode=self.border_mode)
                out.write(corrected)
                processed_count += 1

                try:
                    quality = evaluate_calibration_quality(frame, corrector.distortion_model, num_segments=20)
                    frame_quality_scores.append(quality["quality_score"])
                except Exception:
                    pass

            frame_count += 1
            if frame_count % 100 == 0:
                print(f"Processed {frame_count}/{total_frames} frames")

        cap.release()
        out.release()

        result = {
            "input": video_path,
            "output": output_path,
            "success": True,
            "total_frames": total_frames,
            "processed_frames": processed_count,
            "fps": fps,
            "output_size": out_size,
            "stabilized": stabilize_params,
            "vr_mode": use_vr_mode,
        }

        if current_params is not None:
            result["final_params"] = current_params
        if len(params_history) > 0:
            result["params_history"] = params_history
        if len(frame_quality_scores) > 0:
            quality_array = np.array(frame_quality_scores)
            result["mean_quality_score"] = float(np.mean(quality_array))
            result["std_quality_score"] = float(np.std(quality_array))

        if len(params_history) > 1:
            foci = [p["focal_length"] for p in params_history]
            centers_x = [p["center_x"] for p in params_history]
            centers_y = [p["center_y"] for p in params_history]
            result["params_stability"] = {
                "focal_std": float(np.std(foci)),
                "center_x_std": float(np.std(centers_x)),
                "center_y_std": float(np.std(centers_y)),
            }

        return result

    def get_summary(self) -> Dict[str, Any]:
        if len(self.results) == 0:
            return {"total": 0, "success": 0, "failed": 0}

        success_count = sum(1 for r in self.results if r["success"])
        failed_count = len(self.results) - success_count
        failed_items = [r for r in self.results if not r["success"]]

        return {
            "total": len(self.results),
            "success": success_count,
            "failed": failed_count,
            "success_rate": success_count / len(self.results),
            "failed_items": failed_items,
        }

    def save_params(self, filepath: str, params: Dict[str, Any]):
        import json

        save_params = {
            "center": list(params.get("center", (0, 0))),
            "focal_length": float(params.get("focal_length", 0)),
            "fov_degrees": float(params.get("fov_degrees", 180)),
            "projection_type": params.get("projection_type", FisheyeProjectionType.EQUISOLID).value,
        }

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(save_params, f, indent=2)

    def _load_params(self, filepath: str) -> Dict[str, Any]:
        import json
        from .distortion_models import create_projection_model

        with open(filepath, "r") as f:
            data = json.load(f)

        projection_type = FisheyeProjectionType(data.get("projection_type", "equisolid"))
        center = tuple(data.get("center", [0, 0]))
        focal_length = float(data.get("focal_length", 0))

        model = create_projection_model(projection_type, focal_length, center)

        return {
            "center": center,
            "focal_length": focal_length,
            "fov_degrees": float(data.get("fov_degrees", 180)),
            "projection_type": projection_type,
            "model": model,
        }


def process_batch_simple(
    input_dir: str,
    output_dir: str,
    method: CorrectionMethod = CorrectionMethod.SPHERICAL_PROJECTION,
    auto_params: bool = True,
    num_workers: int = 4,
) -> List[Dict[str, Any]]:
    processor = BatchProcessor(method=method, num_workers=num_workers)
    return processor.process_directory(input_dir, output_dir, auto_params=auto_params)
