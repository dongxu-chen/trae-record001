import numpy as np
from scipy.optimize import minimize, differential_evolution
from .metrics import MutualInformationMetric, NormalizedMutualInformationMetric
from .transforms import RigidTransform, AffineTransform, BSplineTransform


class RegistrationOptimizer:
    def __init__(
        self,
        transform_type="rigid",
        dim=2,
        metric="mi",
        num_bins=64,
        optimizer="lbfgsb",
        max_iter=200,
        tol=1e-6,
        use_gpu=False,
        callback=None,
        gpu_accelerator=None,
        image_shape=None,
        grid_spacing=32,
        bspline_order=3,
        regularization_weight=0.01,
    ):
        self.transform_type = transform_type
        self.dim = dim
        self.metric_name = metric
        self.num_bins = num_bins
        self.optimizer_name = optimizer
        self.max_iter = max_iter
        self.tol = tol
        self.use_gpu = use_gpu
        self.external_callback = callback
        self._gpu = gpu_accelerator
        self.image_shape = image_shape
        self.regularization_weight = regularization_weight

        if transform_type == "rigid":
            self.transform = RigidTransform(dim=dim, image_shape=image_shape)
        elif transform_type == "affine":
            self.transform = AffineTransform(dim=dim, image_shape=image_shape)
        elif transform_type == "bspline":
            self.transform = BSplineTransform(
                dim=dim, image_shape=image_shape,
                grid_spacing=grid_spacing, order=bspline_order
            )
        else:
            raise ValueError(f"Unknown transform type: {transform_type}")

        if metric == "mi":
            self.metric = MutualInformationMetric(
                num_bins=num_bins, use_gpu=use_gpu, gpu_accelerator=gpu_accelerator
            )
        elif metric == "nmi":
            self.metric = NormalizedMutualInformationMetric(
                num_bins=num_bins, use_gpu=use_gpu, gpu_accelerator=gpu_accelerator
            )
        else:
            raise ValueError(f"Unknown metric: {metric}")

        self.iteration_count = 0
        self.metric_values = []
        self.best_params = None
        self.best_metric = -np.inf

    def _cost_function(self, params, fixed, moving):
        try:
            warped = self.transform.apply_to_image(moving, params)
        except (np.linalg.LinAlgError, ValueError):
            return 1e10

        overlap_mask = (np.abs(warped) > 1e-8) & (np.abs(fixed) > 1e-8)
        if overlap_mask.sum() < 100:
            return 1e10

        mi_value = self.metric.compute(fixed[overlap_mask], warped[overlap_mask])
        self.iteration_count += 1

        cost = -mi_value

        if self.transform_type == "bspline" and self.regularization_weight > 0:
            try:
                bending = self.transform.bending_energy(params)
                reg_term = self.regularization_weight * bending
                cost += reg_term
            except Exception:
                pass

        current_metric = mi_value
        if current_metric > self.best_metric:
            self.best_metric = current_metric
            self.best_params = params.copy()

        self.metric_values.append(current_metric)

        if self.external_callback is not None:
            self.external_callback(self.iteration_count, current_metric, params)

        return cost

    def optimize(self, fixed, moving, initial_params=None, bounds=None):
        if initial_params is None:
            initial_params = self.transform.get_default_params()

        initial_params = np.asarray(initial_params, dtype=np.float64)
        self.iteration_count = 0
        self.metric_values = []
        self.best_params = initial_params.copy()
        self.best_metric = -np.inf

        fixed_norm = self._preprocess(fixed)
        moving_norm = self._preprocess(moving)

        if bounds is None:
            bounds = self._get_default_bounds()

        if self.optimizer_name == "lbfgsb":
            result = minimize(
                self._cost_function,
                initial_params,
                args=(fixed_norm, moving_norm),
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": self.max_iter, "ftol": self.tol},
            )
        elif self.optimizer_name == "powell":
            result = minimize(
                self._cost_function,
                initial_params,
                args=(fixed_norm, moving_norm),
                method="Powell",
                options={"maxiter": self.max_iter, "ftol": self.tol},
            )
        elif self.optimizer_name == "neldermead":
            result = minimize(
                self._cost_function,
                initial_params,
                args=(fixed_norm, moving_norm),
                method="Nelder-Mead",
                options={"maxiter": self.max_iter, "xatol": self.tol},
            )
        elif self.optimizer_name == "de":
            result = differential_evolution(
                self._cost_function,
                bounds=bounds,
                args=(fixed_norm, moving_norm),
                maxiter=self.max_iter,
                tol=self.tol,
            )
        else:
            raise ValueError(f"Unknown optimizer: {self.optimizer_name}")

        final_params = self.best_params if self.best_metric > -result.fun else result.x

        if self.transform_type == "bspline":
            final_matrix = None
        else:
            final_matrix = self.transform.get_matrix(final_params)

        return {
            "params": final_params,
            "matrix": final_matrix,
            "metric_value": self.best_metric if self.best_metric > -result.fun else -result.fun,
            "iterations": self.iteration_count,
            "metric_history": self.metric_values,
            "success": result.success if hasattr(result, "success") else True,
            "message": result.message if hasattr(result, "message") else "",
        }

    def _preprocess(self, image):
        arr = image.copy().astype(np.float64)
        p2, p98 = np.percentile(arr, (2, 98))
        arr = np.clip(arr, p2, p98)
        min_val, max_val = arr.min(), arr.max()
        if max_val - min_val > 1e-10:
            arr = (arr - min_val) / (max_val - min_val)
        else:
            arr = np.zeros_like(arr)
        return arr

    def _get_default_bounds(self):
        if self.transform_type == "rigid":
            if self.dim == 2:
                return [
                    (-np.pi / 4, np.pi / 4),
                    (-50, 50),
                    (-50, 50),
                ]
            return [
                (-np.pi / 4, np.pi / 4),
                (-np.pi / 4, np.pi / 4),
                (-np.pi / 4, np.pi / 4),
                (-50, 50),
                (-50, 50),
                (-50, 50),
            ]
        elif self.transform_type == "affine":
            if self.dim == 2:
                return [
                    (0.5, 1.5),
                    (-0.5, 0.5),
                    (-50, 50),
                    (-0.5, 0.5),
                    (0.5, 1.5),
                    (-50, 50),
                ]
            return [
                (0.5, 1.5), (-0.5, 0.5), (-0.5, 0.5), (-50, 50),
                (-0.5, 0.5), (0.5, 1.5), (-0.5, 0.5), (-50, 50),
                (-0.5, 0.5), (-0.5, 0.5), (0.5, 1.5), (-50, 50),
            ]
        elif self.transform_type == "bspline":
            max_displacement = self.transform.grid_spacing * 0.5
            num_params = self.transform.get_num_params()
            return [(-max_displacement, max_displacement)] * num_params
        return None
