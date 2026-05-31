import numpy as np


class MutualInformationMetric:
    def __init__(self, num_bins=64, use_gpu=False, gpu_accelerator=None):
        self.num_bins = num_bins
        self.use_gpu = use_gpu
        self._gpu = gpu_accelerator

        if use_gpu and self._gpu is None:
            try:
                from .gpu import GPUAccelerator
                self._gpu = GPUAccelerator()
            except Exception:
                self._gpu = None
                self.use_gpu = False

    def compute(self, fixed, moving):
        if self.use_gpu and self._gpu and self._gpu.available:
            return self._compute_gpu(fixed, moving)
        return self._compute_cpu(fixed, moving)

    def _compute_cpu(self, fixed, moving):
        fixed = fixed.ravel()
        moving = moving.ravel()
        mask = np.isfinite(fixed) & np.isfinite(moving)
        fixed = fixed[mask]
        moving = moving[mask]

        if len(fixed) == 0:
            return 0.0

        hist_2d, _, _ = np.histogram2d(fixed, moving, bins=self.num_bins)

        pxy = hist_2d / hist_2d.sum()
        px = pxy.sum(axis=1)
        py = pxy.sum(axis=0)

        px_py = px[:, np.newaxis] * py[np.newaxis, :]

        nonzero = pxy > 0
        mi = np.sum(pxy[nonzero] * np.log(pxy[nonzero] / px_py[nonzero]))
        return float(mi)

    def _compute_gpu(self, fixed, moving):
        if self._gpu and self._gpu.available:
            mi = self._gpu.compute_mutual_information_gpu(fixed, moving, self.num_bins)
            if mi is not None:
                return mi
        return self._compute_cpu(fixed, moving)


class NormalizedMutualInformationMetric:
    def __init__(self, num_bins=64, use_gpu=False, gpu_accelerator=None):
        self.num_bins = num_bins
        self.use_gpu = use_gpu
        self._mi_metric = MutualInformationMetric(
            num_bins=num_bins, use_gpu=use_gpu, gpu_accelerator=gpu_accelerator
        )

    def compute(self, fixed, moving):
        mi = self._mi_metric.compute(fixed, moving)

        fixed_flat = fixed.ravel()
        moving_flat = moving.ravel()
        mask = np.isfinite(fixed_flat) & np.isfinite(moving_flat)
        fixed_flat = fixed_flat[mask]
        moving_flat = moving_flat[mask]

        if len(fixed_flat) == 0:
            return 0.0

        hist_f, _ = np.histogram(fixed_flat, bins=self.num_bins)
        hist_m, _ = np.histogram(moving_flat, bins=self.num_bins)

        pf = hist_f / hist_f.sum()
        pm = hist_m / hist_m.sum()

        pf = pf[pf > 0]
        pm = pm[pm > 0]

        h_f = -np.sum(pf * np.log(pf))
        h_m = -np.sum(pm * np.log(pm))

        if abs(h_f + h_m) < 1e-10:
            return 0.0

        nmi = 2.0 * mi / (h_f + h_m)
        return float(nmi)
