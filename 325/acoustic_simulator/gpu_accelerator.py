import numpy as np
import logging
from typing import Union, Optional, Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GPUAccelerator:
    def __init__(self, use_gpu: bool = True, backend: str = "auto"):
        self.use_gpu = use_gpu
        self.backend = backend
        self.xp = None
        self._has_cupy = False
        self._has_numba = False
        self._init_backend()

    def _init_backend(self):
        if not self.use_gpu:
            self.xp = np
            self.backend = "numpy"
            logger.info("Using CPU backend (NumPy)")
            return

        if self.backend == "auto" or self.backend == "cupy":
            try:
                import cupy as cp
                self.xp = cp
                self._has_cupy = True
                self.backend = "cupy"
                logger.info(f"Using GPU backend (CuPy) - {cp.cuda.runtime.getDeviceProperties(0)['name'].decode()}")
                return
            except ImportError:
                logger.warning("CuPy not available, trying Numba...")

        if self.backend == "auto" or self.backend == "numba":
            try:
                import numba
                from numba import cuda
                if cuda.is_available():
                    self._has_numba = True
                    self.xp = np
                    self.backend = "numba"
                    logger.info("Using GPU backend (Numba CUDA)")
                    return
                else:
                    logger.warning("Numba CUDA not available, falling back to CPU...")
            except ImportError:
                logger.warning("Numba not available, falling back to CPU...")

        self.xp = np
        self.backend = "numpy"
        self.use_gpu = False
        logger.info("Using CPU backend (NumPy)")

    def to_gpu(self, array: np.ndarray) -> Union[np.ndarray, "cp.ndarray"]:
        if self._has_cupy and isinstance(array, np.ndarray):
            return self.xp.asarray(array)
        return array

    def to_cpu(self, array) -> np.ndarray:
        if self._has_cupy and hasattr(array, 'get'):
            return array.get()
        return np.asarray(array)

    def array(self, *args, **kwargs):
        return self.xp.array(*args, **kwargs)

    def zeros(self, *args, **kwargs):
        return self.xp.zeros(*args, **kwargs)

    def ones(self, *args, **kwargs):
        return self.xp.ones(*args, **kwargs)

    def linspace(self, *args, **kwargs):
        return self.xp.linspace(*args, **kwargs)

    def sqrt(self, x):
        return self.xp.sqrt(x)

    def exp(self, x):
        return self.xp.exp(x)

    def log10(self, x):
        return self.xp.log10(x)

    def abs(self, x):
        return self.xp.abs(x)

    def max(self, x, axis=None):
        return self.xp.max(x, axis=axis)

    def min(self, x, axis=None):
        return self.xp.min(x, axis=axis)

    def sum(self, x, axis=None):
        return self.xp.sum(x, axis=axis)

    def mean(self, x, axis=None):
        return self.xp.mean(x, axis=axis)

    def dot(self, a, b):
        return self.xp.dot(a, b)

    def norm(self, x, axis=None):
        return self.xp.linalg.norm(x, axis=axis)

    def convolve(self, a, b):
        if self._has_cupy:
            return self.xp.convolve(a, b)
        return np.convolve(a, b)

    def fft(self, x):
        if self._has_cupy:
            return self.xp.fft.fft(x)
        return np.fft.fft(x)

    def ifft(self, x):
        if self._has_cupy:
            return self.xp.fft.ifft(x)
        return np.fft.ifft(x)

    def parallel_distance_calculation(
        self,
        sources: np.ndarray,
        receivers: np.ndarray
    ) -> np.ndarray:
        sources_cpu = self.to_cpu(sources)
        receivers_cpu = self.to_cpu(receivers)

        if self._has_numba and self.use_gpu:
            return self._numba_distance_calc(sources_cpu, receivers_cpu)
        elif self._has_cupy:
            return self._cupy_distance_calc(sources_cpu, receivers_cpu)
        else:
            return self._numpy_distance_calc(sources_cpu, receivers_cpu)

    def _numpy_distance_calc(self, sources, receivers):
        diff = sources[:, np.newaxis, :] - receivers[np.newaxis, :, :]
        return np.sqrt(np.sum(diff ** 2, axis=-1))

    def _cupy_distance_calc(self, sources, receivers):
        sources_gpu = self.to_gpu(sources)
        receivers_gpu = self.to_gpu(receivers)
        diff = sources_gpu[:, self.xp.newaxis, :] - receivers_gpu[self.xp.newaxis, :, :]
        distances = self.xp.sqrt(self.xp.sum(diff ** 2, axis=-1))
        return self.to_cpu(distances)

    def _numba_distance_calc(self, sources, receivers):
        from numba import cuda
        import math

        @cuda.jit
        def distance_kernel(sources, receivers, distances):
            i, j = cuda.grid(2)
            if i < distances.shape[0] and j < distances.shape[1]:
                dx = sources[i, 0] - receivers[j, 0]
                dy = sources[i, 1] - receivers[j, 1]
                if sources.shape[1] == 3:
                    dz = sources[i, 2] - receivers[j, 2]
                    distances[i, j] = math.sqrt(dx * dx + dy * dy + dz * dz)
                else:
                    distances[i, j] = math.sqrt(dx * dx + dy * dy)

        n_sources = sources.shape[0]
        n_receivers = receivers.shape[0]
        distances = np.zeros((n_sources, n_receivers), dtype=np.float64)

        threadsperblock = (16, 16)
        blockspergrid_x = math.ceil(n_sources / threadsperblock[0])
        blockspergrid_y = math.ceil(n_receivers / threadsperblock[1])
        blockspergrid = (blockspergrid_x, blockspergrid_y)

        d_sources = cuda.to_device(sources)
        d_receivers = cuda.to_device(receivers)
        d_distances = cuda.to_device(distances)

        distance_kernel[blockspergrid, threadsperblock](d_sources, d_receivers, d_distances)
        d_distances.to_host()

        return distances

    def parallel_pressure_calculation(
        self,
        distances: np.ndarray,
        frequencies: np.ndarray,
        absorption: float = 0.1,
        sound_speed: float = 343.0
    ) -> np.ndarray:
        distances_cpu = self.to_cpu(distances)

        if self._has_numba and self.use_gpu:
            return self._numba_pressure_calc(distances_cpu, frequencies, absorption, sound_speed)
        elif self._has_cupy:
            return self._cupy_pressure_calc(distances_cpu, frequencies, absorption, sound_speed)
        else:
            return self._numpy_pressure_calc(distances_cpu, frequencies, absorption, sound_speed)

    def _numpy_pressure_calc(self, distances, frequencies, absorption, sound_speed):
        omega = 2 * np.pi * frequencies[:, np.newaxis, np.newaxis]
        k = omega / sound_speed
        distances_safe = np.where(distances < 0.01, 0.01, distances)
        attenuation = np.exp(-absorption * distances_safe)
        pressure = (np.exp(1j * k * distances_safe[np.newaxis, :, :]) /
                   (4 * np.pi * distances_safe[np.newaxis, :, :])) * attenuation[np.newaxis, :, :]
        return pressure

    def _cupy_pressure_calc(self, distances, frequencies, absorption, sound_speed):
        d_distances = self.to_gpu(distances)
        d_frequencies = self.to_gpu(frequencies)
        omega = 2 * self.xp.pi * d_frequencies[:, self.xp.newaxis, self.xp.newaxis]
        k = omega / sound_speed
        distances_safe = self.xp.where(d_distances < 0.01, 0.01, d_distances)
        attenuation = self.xp.exp(-absorption * distances_safe)
        pressure = (self.xp.exp(1j * k * distances_safe[self.xp.newaxis, :, :]) /
                   (4 * self.xp.pi * distances_safe[self.xp.newaxis, :, :])) * attenuation[self.xp.newaxis, :, :]
        return self.to_cpu(pressure)

    def _numba_pressure_calc(self, distances, frequencies, absorption, sound_speed):
        from numba import cuda
        import math
        import cmath

        @cuda.jit
        def pressure_kernel(distances, frequencies, absorption, sound_speed, pressure):
            freq_idx, src_idx, rec_idx = cuda.grid(3)
            if (freq_idx < pressure.shape[0] and
                src_idx < pressure.shape[1] and
                rec_idx < pressure.shape[2]):
                omega = 2 * math.pi * frequencies[freq_idx]
                k = omega / sound_speed
                r = max(distances[src_idx, rec_idx], 0.01)
                atten = math.exp(-absorption * r)
                phase = k * r
                real = math.cos(phase) / (4 * math.pi * r) * atten
                imag = math.sin(phase) / (4 * math.pi * r) * atten
                pressure[freq_idx, src_idx, rec_idx] = real + 1j * imag

        n_freq = len(frequencies)
        n_src, n_rec = distances.shape
        pressure = np.zeros((n_freq, n_src, n_rec), dtype=np.complex128)

        threadsperblock = (8, 8, 8)
        blockspergrid = (
            math.ceil(n_freq / threadsperblock[0]),
            math.ceil(n_src / threadsperblock[1]),
            math.ceil(n_rec / threadsperblock[2])
        )

        d_distances = cuda.to_device(distances)
        d_frequencies = cuda.to_device(frequencies)
        d_pressure = cuda.to_device(pressure)

        pressure_kernel[blockspergrid, threadsperblock](
            d_distances, d_frequencies, absorption, sound_speed, d_pressure
        )
        d_pressure.to_host()

        return pressure

    @property
    def is_gpu_available(self) -> bool:
        return self._has_cupy or self._has_numba

    @property
    def device_info(self) -> str:
        if self._has_cupy:
            import cupy as cp
            props = cp.cuda.runtime.getDeviceProperties(0)
            return f"CUDA Device: {props['name'].decode()}, Memory: {props['totalGlobalMem'] / 1e9:.1f} GB"
        elif self._has_numba:
            from numba import cuda
            device = cuda.get_current_device()
            return f"Numba CUDA Device: {device.name}, Compute Capability: {device.compute_capability}"
        else:
            return "CPU Only"
