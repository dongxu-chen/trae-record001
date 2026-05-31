import numpy as np
import SimpleITK as sitk
from .transforms import RigidTransform, AffineTransform, BSplineTransform
from .optimizer import RegistrationOptimizer
from .gpu import GPUAccelerator
from .evaluation import RegistrationEvaluator
from .visualization import RegistrationVisualizer
from .utils import normalize_image, normalize_joint


class RegistrationPipeline:
    def __init__(
        self,
        transform_type="rigid",
        dim=2,
        metric="nmi",
        optimizer="lbfgsb",
        num_bins=64,
        max_iter=200,
        tol=1e-6,
        use_gpu=False,
        multi_resolution=True,
        num_levels=3,
        verbose=True,
        grid_spacing=32,
        bspline_order=3,
        regularization_weight=0.01,
    ):
        self.transform_type = transform_type
        self.dim = dim
        self.metric_name = metric
        self.optimizer_name = optimizer
        self.num_bins = num_bins
        self.max_iter = max_iter
        self.tol = tol
        self.use_gpu = use_gpu
        self.multi_resolution = multi_resolution
        self.num_levels = num_levels
        self.verbose = verbose
        self.grid_spacing = grid_spacing
        self.bspline_order = bspline_order
        self.regularization_weight = regularization_weight

        self.gpu = GPUAccelerator()
        if use_gpu and self.gpu.available:
            print(f"[GPU] Using GPU: {self.gpu.device_name}")
        elif use_gpu:
            print("[GPU] GPU requested but not available, falling back to CPU")

        self.evaluator = RegistrationEvaluator()
        self.visualizer = RegistrationVisualizer()

        if transform_type == "rigid":
            self.transform = RigidTransform(dim=dim)
        elif transform_type == "affine":
            self.transform = AffineTransform(dim=dim)
        elif transform_type == "bspline":
            self.transform = BSplineTransform(
                dim=dim, grid_spacing=grid_spacing, order=bspline_order
            )
        else:
            raise ValueError(f"Unknown transform type: {transform_type}")

        self.result = None

    def register(self, fixed, moving, initial_params=None, output_dir=None,
                 ground_truth_transform=None, ground_truth_params=None,
                 landmark_points=None, compute_tre=True, num_landmarks=50,
                 spacing=None):
        fixed_arr = self._ensure_array(fixed)
        moving_arr = self._ensure_array(moving)

        if self.transform_type == "bspline":
            self.transform._setup_grid(fixed_arr.shape)
            self.transform.image_shape = fixed_arr.shape

        if self.verbose:
            print(f"[Registration] Fixed image shape: {fixed_arr.shape}")
            print(f"[Registration] Moving image shape: {moving_arr.shape}")
            print(f"[Registration] Transform: {self.transform_type}")
            print(f"[Registration] Metric: {self.metric_name}")
            print(f"[Registration] Optimizer: {self.optimizer_name}")
            print(f"[Registration] GPU: {self.use_gpu and self.gpu.available}")
            print(f"[Registration] Multi-resolution: {self.multi_resolution}")

        fixed_norm, moving_norm, norm_params = normalize_joint(fixed_arr, moving_arr, target_range=(0.0, 1.0))
        self._norm_params = norm_params

        if self.verbose:
            print(f"[Preprocess] Joint intensity normalization to [0, 1]")
            print(f"  Combined range: [{norm_params['combined_min']:.2f}, {norm_params['combined_max']:.2f}]")
            print(f"  Fixed original: [{norm_params['fixed_original'][0]:.2f}, {norm_params['fixed_original'][1]:.2f}]")
            print(f"  Moving original: [{norm_params['moving_original'][0]:.2f}, {norm_params['moving_original'][1]:.2f}]")

        if compute_tre and landmark_points is None and ground_truth_transform is not None:
            landmark_points = self.evaluator.generate_landmark_points(
                fixed_arr.shape, num_points=num_landmarks, seed=42
            )
            if self.verbose:
                print(f"[TRE] Generated {len(landmark_points)} landmark points for evaluation")

        if self.multi_resolution:
            result = self._multi_resolution_registration(fixed_norm, moving_norm, initial_params)
        else:
            result = self._single_level_registration(fixed_norm, moving_norm, initial_params)

        moving_warped = self.transform.apply_to_image(moving_arr, result["params"])

        transform_matrix = result.get("matrix")
        eval_results = self.evaluator.compute_all(
            fixed_arr, moving_arr, moving_warped, transform_matrix=transform_matrix
        )
        result["evaluation"] = eval_results
        result["warped_image"] = moving_warped
        result["norm_params"] = norm_params

        if compute_tre and landmark_points is not None:
            try:
                landmark_points = np.asarray(landmark_points, dtype=np.float64)
                if ground_truth_transform is not None and ground_truth_params is not None:
                    gt_points_in_moving = self.evaluator.apply_transform_to_points(
                        landmark_points, ground_truth_transform, ground_truth_params, invert=False
                    )
                    transformed_points = self.evaluator.apply_transform_to_points(
                        gt_points_in_moving, self.transform, result["params"], invert=False
                    )
                    tre_result = self.evaluator.target_registration_error(
                        landmark_points, transformed_points, spacing=spacing
                    )
                    result["tre"] = tre_result
                    result["landmark_points"] = landmark_points
                    result["landmark_transformed"] = transformed_points
                    result["landmark_ground_truth"] = gt_points_in_moving
                else:
                    gt_points = np.asarray(landmark_points, dtype=np.float64)
                    transformed_points = self.evaluator.apply_transform_to_points(
                        landmark_points, self.transform, result["params"], invert=False
                    )
                    tre_result = self.evaluator.target_registration_error(
                        gt_points, transformed_points, spacing=spacing
                    )
                    result["tre"] = tre_result
                    result["landmark_points"] = landmark_points
                    result["landmark_transformed"] = transformed_points
                    result["landmark_ground_truth"] = gt_points

                if self.verbose:
                    print("\n[Target Registration Error (TRE)]")
                    print(f"  Mean:   {tre_result['mean']:.4f} px")
                    print(f"  Median: {tre_result['median']:.4f} px")
                    print(f"  RMSE:   {tre_result['rmse']:.4f} px")
                    print(f"  p95:    {tre_result['p95']:.4f} px")
                    print(f"  Max:    {tre_result['max']:.4f} px")
            except Exception as e:
                print(f"[Warning] Failed to compute TRE: {e}")
                result["tre"] = None

        if self.verbose:
            print("\n" + self.evaluator.summary())

        if output_dir:
            self._save_results(result, output_dir, fixed_arr, moving_arr, moving_warped)

        self.result = result
        return result

    def register_sitk(self, fixed_path, moving_path, output_dir=None):
        fixed_sitk = sitk.ReadImage(fixed_path)
        moving_sitk = sitk.ReadImage(moving_path)

        fixed_arr = sitk.GetArrayFromImage(fixed_sitk).astype(np.float64)
        moving_arr = sitk.GetArrayFromImage(moving_sitk).astype(np.float64)

        result = self.register(fixed_arr, moving_arr, output_dir=output_dir)

        result["fixed_sitk"] = fixed_sitk
        result["moving_sitk"] = moving_sitk
        result["fixed_spacing"] = np.array(fixed_sitk.GetSpacing()[::-1])
        result["moving_spacing"] = np.array(moving_sitk.GetSpacing()[::-1])

        return result

    def _multi_resolution_registration(self, fixed, moving, initial_params):
        if self.transform_type == "bspline":
            self.transform._setup_grid(fixed.shape)
            self.transform.image_shape = fixed.shape

        if initial_params is None:
            current_params = self.transform.get_default_params()
        else:
            current_params = np.asarray(initial_params, dtype=np.float64)

        auto_levels = self._compute_optimal_levels(fixed.shape)
        num_levels = max(self.num_levels, auto_levels)
        if self.verbose:
            print(f"[MultiRes] Auto-detected optimal levels: {auto_levels}, using {num_levels}")

        shrink_factors = [2 ** (num_levels - 1 - i) for i in range(num_levels)]
        sigmas = [max(1.0, 0.5 * sf) for sf in shrink_factors]

        if self.dim == 2:
            fixed_pyramid = self._build_pyramid_2d_enhanced(fixed, shrink_factors, sigmas)
            moving_pyramid = self._build_pyramid_2d_enhanced(moving, shrink_factors, sigmas)
        else:
            fixed_pyramid = self._build_pyramid_3d_enhanced(fixed, shrink_factors, sigmas)
            moving_pyramid = self._build_pyramid_3d_enhanced(moving, shrink_factors, sigmas)

        all_metric_history = []
        param_history = []
        param_history.append(current_params.copy())

        for level in range(num_levels):
            fixed_level = fixed_pyramid[level]
            moving_level = moving_pyramid[level]
            sf = shrink_factors[level]
            sigma = sigmas[level]

            is_bspline = self.transform_type == "bspline"

            if not is_bspline:
                scaled_params = self._scale_params_for_level(current_params, sf, upscale=False)
            else:
                scaled_params = None

            level_config = self._get_level_config(level, num_levels)
            level_bins = max(16, self.num_bins // (2 ** (num_levels - 1 - level)))
            level_tol = self.tol * (10 ** (num_levels - 1 - level))
            level_max_iter = int(self.max_iter * level_config["iter_scale"])

            level_grid_spacing = max(8, self.grid_spacing // sf) if is_bspline else self.grid_spacing

            if self.verbose:
                print(f"\n[Level {level + 1}/{num_levels}] "
                      f"Shape: {fixed_level.shape}, "
                      f"Scale: {sf:.0f}x, "
                      f"Sigma: {sigma:.1f}, "
                      f"Bins: {level_bins}, "
                      f"Optimizer: {level_config['optimizer']}, "
                      f"Iters: {level_max_iter}"
                      + (f", GridSpacing: {level_grid_spacing}" if is_bspline else ""))

            level_opt = RegistrationOptimizer(
                transform_type=self.transform_type,
                dim=self.dim,
                metric=self.metric_name,
                num_bins=level_bins,
                optimizer=level_config["optimizer"],
                max_iter=level_max_iter,
                tol=level_tol,
                use_gpu=self.use_gpu and self.gpu.available,
                gpu_accelerator=self.gpu if self.use_gpu else None,
                image_shape=fixed_level.shape,
                grid_spacing=level_grid_spacing,
                bspline_order=self.bspline_order,
                regularization_weight=self.regularization_weight,
            )

            level_result = level_opt.optimize(
                fixed_level, moving_level, initial_params=scaled_params
            )

            if not is_bspline:
                recovered_params = self._scale_params_for_level(level_result["params"], sf, upscale=True)
                param_change = np.linalg.norm(recovered_params - current_params)
                if level > 0:
                    max_change = np.mean(np.abs(current_params)) * 0.5 + 1e-3
                    if param_change > max_change and self.verbose:
                        print(f"  Warning: Large param change detected ({param_change:.3f} > {max_change:.3f})")
                        recovered_params = current_params + 0.5 * (recovered_params - current_params)
                current_params = recovered_params
            else:
                current_params = level_result["params"]
                param_change = np.linalg.norm(current_params) if level == 0 else np.linalg.norm(current_params - param_history[-1])

            param_history.append(current_params.copy())
            all_metric_history.extend(level_result["metric_history"])

            if self.verbose:
                print(f"  Metric value: {level_result['metric_value']:.6f}")
                if not is_bspline:
                    print(f"  Params: {current_params}")
                else:
                    print(f"  Params norm: {np.linalg.norm(current_params):.4f}, Max: {np.max(np.abs(current_params)):.4f}")
                print(f"  Params change: {param_change:.4f}")

        if self.verbose and len(param_history) > 1:
            print(f"\n[MultiRes] Param evolution across {len(param_history) - 1} levels:")
            for i, p in enumerate(param_history[1:], 1):
                if not is_bspline:
                    print(f"  Level {i}: {p}")
                else:
                    print(f"  Level {i}: norm={np.linalg.norm(p):.4f}, max={np.max(np.abs(p)):.4f}")

        if self.transform_type == "bspline":
            final_matrix = None
        else:
            final_matrix = self.transform.get_matrix(current_params)
        final_mi = all_metric_history[-1] if all_metric_history else 0.0

        return {
            "params": current_params,
            "matrix": final_matrix,
            "metric_value": final_mi,
            "metric_history": all_metric_history,
            "iterations": len(all_metric_history),
            "success": True,
            "message": "Enhanced multi-resolution registration completed",
            "param_history": param_history,
            "num_levels": num_levels,
            "shrink_factors": shrink_factors,
        }

    def _compute_optimal_levels(self, shape):
        min_dim = min(shape)
        max_levels = int(np.log2(min_dim / 16)) + 1
        return max(1, min(max_levels, 5))

    def _get_level_config(self, level, num_levels):
        if level == 0:
            return {"optimizer": "neldermead", "iter_scale": 1.5}
        elif level == num_levels - 1:
            return {"optimizer": self.optimizer_name, "iter_scale": 2.0}
        else:
            return {"optimizer": "powell", "iter_scale": 1.2}

    def _scale_params_for_level(self, params, scale, upscale):
        scaled = params.copy()
        factor = scale if not upscale else 1.0 / scale

        if self.transform_type == "rigid":
            if self.dim == 2:
                scaled[1] = params[1] / factor
                scaled[2] = params[2] / factor
            else:
                scaled[3] = params[3] / factor
                scaled[4] = params[4] / factor
                scaled[5] = params[5] / factor
        elif self.transform_type == "affine":
            if self.dim == 2:
                scaled[2] = params[2] / factor
                scaled[5] = params[5] / factor
            else:
                scaled[3] = params[3] / factor
                scaled[7] = params[7] / factor
                scaled[11] = params[11] / factor
        return scaled

    def _single_level_registration(self, fixed, moving, initial_params):
        if self.transform_type == "bspline":
            self.transform._setup_grid(fixed.shape)
            self.transform.image_shape = fixed.shape

        if initial_params is None:
            initial_params = self.transform.get_default_params()

        optimizer = RegistrationOptimizer(
            transform_type=self.transform_type,
            dim=self.dim,
            metric=self.metric_name,
            num_bins=self.num_bins,
            optimizer=self.optimizer_name,
            max_iter=self.max_iter,
            tol=self.tol,
            use_gpu=self.use_gpu and self.gpu.available,
            gpu_accelerator=self.gpu if self.use_gpu else None,
            image_shape=fixed.shape,
            grid_spacing=self.grid_spacing,
            bspline_order=self.bspline_order,
            regularization_weight=self.regularization_weight,
        )

        result = optimizer.optimize(fixed, moving, initial_params=initial_params)
        return result

    def _build_pyramid_2d_enhanced(self, image, shrink_factors, sigmas):
        from scipy.ndimage import zoom, gaussian_filter

        pyramid = []
        for sf, sigma in zip(shrink_factors, sigmas):
            if sf == 1:
                pyramid.append(image.copy())
            else:
                smoothed = gaussian_filter(image, sigma=sigma, mode="nearest")
                new_shape = tuple(int(s / sf) for s in image.shape)
                zoom_factors = tuple(ns / o for ns, o in zip(new_shape, image.shape))
                current = zoom(smoothed, zoom_factors, order=1, mode="nearest")
                pyramid.append(current)
        return pyramid

    def _build_pyramid_3d_enhanced(self, image, shrink_factors, sigmas):
        from scipy.ndimage import zoom, gaussian_filter

        pyramid = []
        for sf, sigma in zip(shrink_factors, sigmas):
            if sf == 1:
                pyramid.append(image.copy())
            else:
                sigma_tuple = (sigma,) * image.ndim
                smoothed = gaussian_filter(image, sigma=sigma_tuple, mode="nearest")
                new_shape = tuple(int(s / sf) for s in image.shape)
                zoom_factors = tuple(ns / o for ns, o in zip(new_shape, image.shape))
                current = zoom(smoothed, zoom_factors, order=1, mode="nearest")
                pyramid.append(current)
        return pyramid

    def _save_results(self, result, output_dir, fixed, moving, warped):
        import os
        os.makedirs(output_dir, exist_ok=True)

        self.visualizer.plot_registration_result(
            fixed, moving, warped,
            title=f"Registration Result ({self.transform_type})",
            save_path=os.path.join(output_dir, "registration_result.png"),
        )

        self.visualizer.plot_convergence(
            result["metric_history"],
            title="Optimization Convergence",
            save_path=os.path.join(output_dir, "convergence.png"),
        )

        self.visualizer.plot_checkerboard(
            fixed, warped,
            title="Checkerboard After Registration",
            save_path=os.path.join(output_dir, "checkerboard.png"),
        )

        self.visualizer.plot_difference(
            fixed, warped,
            title="Difference After Registration",
            save_path=os.path.join(output_dir, "difference.png"),
        )

        self.visualizer.plot_fusion_overlay(
            fixed, warped,
            title="Fusion Overlay",
            save_path=os.path.join(output_dir, "fusion_overlay.png"),
        )

        if "tre" in result and result["tre"] is not None:
            try:
                self.visualizer.plot_tre_histogram(
                    result["tre"],
                    title="Target Registration Error Distribution",
                    save_path=os.path.join(output_dir, "tre_distribution.png"),
                )

                if "landmark_points" in result:
                    self.visualizer.plot_landmark_points(
                        fixed,
                        ground_truth_points=result.get("landmark_ground_truth"),
                        transformed_points=result.get("landmark_transformed"),
                        initial_points=result.get("landmark_points"),
                        title="Landmark Points - TRE Evaluation",
                        save_path=os.path.join(output_dir, "landmark_points.png"),
                    )
            except Exception as e:
                print(f"[Warning] Failed to generate TRE visualization: {e}")

        if self.transform_type == "bspline" and hasattr(self.transform, "get_displacement_field"):
            try:
                disp_field = self.transform.get_displacement_field(result["params"], fixed.shape)
                self.visualizer.plot_displacement_field(
                    disp_field,
                    title="Displacement Field",
                    save_path=os.path.join(output_dir, "displacement_field.png"),
                )
                np.save(os.path.join(output_dir, "displacement_field.npy"), disp_field)

                jac_det = self.transform.get_jacobian_determinant(result["params"], fixed.shape)
                self.visualizer.plot_jacobian_determinant(
                    jac_det,
                    title="Jacobian Determinant",
                    save_path=os.path.join(output_dir, "jacobian_determinant.png"),
                )
                np.save(os.path.join(output_dir, "jacobian_determinant.npy"), jac_det)
            except Exception as e:
                print(f"[Warning] Failed to generate displacement/Jacobian visualization: {e}")

        warped_sitk = sitk.GetImageFromArray(warped)
        sitk.WriteImage(warped_sitk, os.path.join(output_dir, "warped_moving.nii.gz"))

        np.save(os.path.join(output_dir, "transform_params.npy"), result["params"])

        if "matrix" in result and result["matrix"] is not None:
            np.save(os.path.join(output_dir, "transform_matrix.npy"), result["matrix"])

        with open(os.path.join(output_dir, "registration_report.txt"), "w") as f:
            f.write(self.evaluator.summary())
            f.write(f"\n\nTransform Type: {self.transform_type}")
            f.write(f"\nTransform Parameters (first 20): {result['params'][:20]}...")
            if "matrix" in result and result["matrix"] is not None:
                f.write(f"\nTransform Matrix:\n{result['matrix']}")
            f.write(f"\n\nMetric History (first 10): {result['metric_history'][:10]}...")
            if "tre" in result:
                f.write(f"\n\nTarget Registration Error (TRE):")
                for k, v in result["tre"].items():
                    if k not in ["all_errors", "sorted_errors"] and np.isscalar(v):
                        f.write(f"\n  {k}: {v:.4f}")

        if self.verbose:
            print(f"\n[Results] Saved to: {output_dir}")

    @staticmethod
    def _ensure_array(image):
        if isinstance(image, np.ndarray):
            return image.astype(np.float64)
        if isinstance(image, sitk.Image):
            return sitk.GetArrayFromImage(image).astype(np.float64)
        raise TypeError(f"Unsupported image type: {type(image)}")
