import numpy as np
from typing import List, Tuple, Optional, Union, Dict, Callable
from dataclasses import dataclass, field
import logging
from scipy import interpolate
from .sound_source import SoundSource, DynamicSource, SourceManager
from .gpu_accelerator import GPUAccelerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import pyroomacoustics as pra
    PRA_AVAILABLE = True
    logger.info("Pyroomacoustics available")
except ImportError:
    PRA_AVAILABLE = False
    logger.warning("Pyroomacoustics not available, using custom implementation only")
    pra = None


STANDARD_OCTAVE_BANDS = np.array([125, 250, 500, 1000, 2000, 4000, 8000], dtype=np.float64)
STANDARD_13_OCTAVE_BANDS = np.array([
    100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000,
    1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000
], dtype=np.float64)


@dataclass
class AbsorptionBand:
    frequencies: np.ndarray
    coefficients: np.ndarray

    def __post_init__(self):
        self.frequencies = np.asarray(self.frequencies, dtype=np.float64)
        self.coefficients = np.asarray(self.coefficients, dtype=np.float64)
        if len(self.frequencies) != len(self.coefficients):
            raise ValueError("Frequencies and coefficients must have the same length")

    def get_absorption_at(self, freq: float) -> float:
        idx = np.argmin(np.abs(self.frequencies - freq))
        return float(self.coefficients[idx])

    def interp_absorption(self, freq: float) -> float:
        if len(self.frequencies) < 2:
            return float(self.coefficients[0])
        return float(np.interp(freq, self.frequencies, self.coefficients))


@dataclass
class RoomGeometry:
    dimensions: np.ndarray
    absorption: Union[float, List[float], np.ndarray, AbsorptionBand] = 0.5
    scattering: Union[float, List[float], np.ndarray, AbsorptionBand] = 0.1
    max_order: Optional[int] = None
    use_pra: bool = True
    adaptive_order: bool = True
    adaptive_order_db_threshold: float = 60.0
    band_type: str = "octave"
    frequencies: Optional[np.ndarray] = None

    def __post_init__(self):
        self.dimensions = np.asarray(self.dimensions, dtype=np.float64)
        self.ndim = len(self.dimensions)

        if self.frequencies is None:
            if self.band_type == "octave":
                self.frequencies = STANDARD_OCTAVE_BANDS.copy()
            elif self.band_type == "1/3_octave":
                self.frequencies = STANDARD_13_OCTAVE_BANDS.copy()
            else:
                raise ValueError(f"Unknown band type: {self.band_type}")
        else:
            self.frequencies = np.asarray(self.frequencies, dtype=np.float64)

        self.n_bands = len(self.frequencies)
        self._init_absorption()
        self._init_scattering()

        if self.max_order is None and not self.adaptive_order:
            self.max_order = 3

    def _init_absorption(self):
        n_walls = 2 * self.ndim
        n_bands = self.n_bands

        if isinstance(self.absorption, AbsorptionBand):
            self.absorption_band = self.absorption
            self.absorption = np.tile(self.absorption_band.coefficients, (n_walls, 1))
        elif isinstance(self.absorption, (int, float)):
            self.absorption = np.ones((n_walls, n_bands)) * float(self.absorption)
        elif isinstance(self.absorption, (list, np.ndarray)):
            abs_arr = np.asarray(self.absorption, dtype=np.float64)
            if abs_arr.ndim == 1:
                if len(abs_arr) == n_walls:
                    self.absorption = np.tile(abs_arr[:, np.newaxis], (1, n_bands))
                elif len(abs_arr) == n_bands:
                    self.absorption = np.tile(abs_arr[np.newaxis, :], (n_walls, 1))
                else:
                    raise ValueError(
                        f"1D absorption must have {n_walls} walls or {n_bands} bands, got {len(abs_arr)}"
                    )
            elif abs_arr.ndim == 2:
                if abs_arr.shape == (n_walls, n_bands):
                    self.absorption = abs_arr
                else:
                    raise ValueError(
                        f"2D absorption shape must be ({n_walls}, {n_bands}), got {abs_arr.shape}"
                    )
            else:
                raise ValueError(f"Absorption must be 1D or 2D, got {abs_arr.ndim}D")

        if not hasattr(self, 'absorption_band'):
            avg_abs = np.mean(self.absorption, axis=0)
            self.absorption_band = AbsorptionBand(self.frequencies, avg_abs)

    def _init_scattering(self):
        n_walls = 2 * self.ndim
        n_bands = self.n_bands

        if isinstance(self.scattering, AbsorptionBand):
            self.scattering_band = self.scattering
            self.scattering = np.tile(self.scattering_band.coefficients, (n_walls, 1))
        elif isinstance(self.scattering, (int, float)):
            self.scattering = np.ones((n_walls, n_bands)) * float(self.scattering)
        elif isinstance(self.scattering, (list, np.ndarray)):
            scat_arr = np.asarray(self.scattering, dtype=np.float64)
            if scat_arr.ndim == 1:
                if len(scat_arr) == n_walls:
                    self.scattering = np.tile(scat_arr[:, np.newaxis], (1, n_bands))
                elif len(scat_arr) == n_bands:
                    self.scattering = np.tile(scat_arr[np.newaxis, :], (n_walls, 1))
                else:
                    raise ValueError(
                        f"1D scattering must have {n_walls} walls or {n_bands} bands, got {len(scat_arr)}"
                    )
            elif scat_arr.ndim == 2:
                if scat_arr.shape == (n_walls, n_bands):
                    self.scattering = scat_arr
                else:
                    raise ValueError(
                        f"2D scattering shape must be ({n_walls}, {n_bands}), got {scat_arr.shape}"
                    )
            else:
                raise ValueError(f"Scattering must be 1D or 2D, got {scat_arr.ndim}D")

        self.scattering = np.clip(self.scattering, 0.0, 1.0)

        if not hasattr(self, 'scattering_band'):
            avg_scat = np.mean(self.scattering, axis=0)
            self.scattering_band = AbsorptionBand(self.frequencies, avg_scat)

    def get_specular_coefficient(self, wall_index: int, band_index: int = 0) -> float:
        s = self.scattering[wall_index, band_index]
        return np.sqrt(1 - s)

    def get_scatter_coefficient(self, wall_index: int, band_index: int = 0) -> float:
        return float(np.sqrt(self.scattering[wall_index, band_index]))

    def get_volume(self) -> float:
        return float(np.prod(self.dimensions))

    def get_surface_area(self) -> float:
        if self.ndim == 2:
            return 2 * (self.dimensions[0] + self.dimensions[1])
        elif self.ndim == 3:
            return 2 * (self.dimensions[0] * self.dimensions[1] +
                       self.dimensions[1] * self.dimensions[2] +
                       self.dimensions[0] * self.dimensions[2])
        else:
            raise ValueError(f"Unsupported dimension: {self.ndim}")

    def get_wall_surface_areas(self) -> np.ndarray:
        if self.ndim == 2:
            return np.array([self.dimensions[1], self.dimensions[1],
                           self.dimensions[0], self.dimensions[0]])
        elif self.ndim == 3:
            return np.array([
                self.dimensions[1] * self.dimensions[2],
                self.dimensions[1] * self.dimensions[2],
                self.dimensions[0] * self.dimensions[2],
                self.dimensions[0] * self.dimensions[2],
                self.dimensions[0] * self.dimensions[1],
                self.dimensions[0] * self.dimensions[1],
            ])
        else:
            raise ValueError(f"Unsupported dimension: {self.ndim}")

    def get_absorption_coefficient(self, wall_index: int, band_index: int = 0) -> float:
        return float(self.absorption[wall_index, band_index])

    def get_average_absorption(self, band_index: Optional[int] = None) -> Union[float, np.ndarray]:
        if band_index is not None:
            return float(np.mean(self.absorption[:, band_index]))
        return np.mean(self.absorption, axis=0)

    def get_reflection_coefficient(self, wall_index: int, band_index: int = 0) -> float:
        alpha = self.get_absorption_coefficient(wall_index, band_index)
        return np.sqrt(1 - alpha)

    def compute_adaptive_max_order(self, source_position: np.ndarray,
                                    receiver_position: Optional[np.ndarray] = None) -> int:
        if not self.adaptive_order:
            return self.max_order if self.max_order is not None else 3

        min_dim = np.min(self.dimensions)
        if min_dim <= 0:
            return 3

        if receiver_position is None:
            receiver_position = self.dimensions / 2

        direct_dist = np.linalg.norm(source_position - receiver_position)
        alpha_avg = float(np.mean(self.absorption))
        if alpha_avg >= 1.0:
            alpha_avg = 0.99
        reflection_coeff = np.sqrt(1 - alpha_avg)

        db_threshold = self.adaptive_order_db_threshold
        lin_threshold = 10 ** (-db_threshold / 20.0)

        order = 0
        current_amplitude = 1.0 / (4 * np.pi * direct_dist + 1e-6)

        while True:
            order += 1
            est_dist = direct_dist + 2 * order * min_dim
            est_spreading = 1.0 / (4 * np.pi * est_dist + 1e-6)
            est_reflection = reflection_coeff ** order
            est_amplitude = est_spreading * est_reflection

            if est_amplitude / current_amplitude < lin_threshold or order > 20:
                break

        return max(1, min(order, 20))

    def compute_adaptive_max_order_multi(self, source_positions: np.ndarray,
                                          receiver_positions: np.ndarray) -> int:
        if not self.adaptive_order:
            return self.max_order if self.max_order is not None else 3

        max_order = 1
        for src in source_positions:
            for rec in receiver_positions:
                order = self.compute_adaptive_max_order(src, rec)
                max_order = max(max_order, order)

        return max_order


@dataclass
class Receiver:
    position: np.ndarray
    receiver_id: int = 0

    def __post_init__(self):
        self.position = np.asarray(self.position, dtype=np.float64)


@dataclass
class PrecomputedIR:
    time_points: np.ndarray
    source_positions: np.ndarray
    impulse_responses: np.ndarray
    interpolation_method: str = "linear"
    _interpolators: Optional[List] = None

    def get_ir_at_time(self, t: float) -> np.ndarray:
        t = np.clip(t, self.time_points[0], self.time_points[-1])
        idx = np.clip(np.searchsorted(self.time_points, t) - 1, 0, len(self.time_points) - 2)
        t0, t1 = self.time_points[idx], self.time_points[idx + 1]
        alpha = (t - t0) / (t1 - t0) if t1 > t0 else 0.0

        ir0 = self.impulse_responses[idx]
        ir1 = self.impulse_responses[idx + 1]

        return (1 - alpha) * ir0 + alpha * ir1

    def get_pressure_at_time(self, t: float) -> np.ndarray:
        return self.get_ir_at_time(t)

    def setup_interpolators(self):
        self._interpolators = []
        n_rec, n_src, n_samples = self.impulse_responses[0].shape
        for i in range(n_rec):
            for j in range(n_src):
                for k in range(n_samples):
                    values = self.impulse_responses[:, i, j, k]
                    self._interpolators.append(
                        interpolate.interp1d(self.time_points, values,
                                            kind=self.interpolation_method,
                                            bounds_error=False,
                                            fill_value="extrapolate")
                    )


class AcousticSimulator:
    def __init__(self,
                 room_geometry: RoomGeometry,
                 fs: int = 44100,
                 sound_speed: float = 343.0,
                 use_gpu: bool = True,
                 gpu_backend: str = "auto"):
        self.room = room_geometry
        self.fs = fs
        self.sound_speed = sound_speed
        self.gpu = GPUAccelerator(use_gpu=use_gpu, backend=gpu_backend)
        self.source_manager = SourceManager()
        self.receivers: List[Receiver] = []
        self.pra_room: Optional[pra.room.Room] = None
        self.air_absorption: bool = False
        self.air_absorption_band: Optional[AbsorptionBand] = None
        self._mirror_sources: Optional[np.ndarray] = None
        self._mirror_orders: Optional[np.ndarray] = None
        self._mirror_reflection_counts: Optional[np.ndarray] = None
        self._impulse_responses: Optional[np.ndarray] = None
        self._band_impulse_responses: Optional[np.ndarray] = None
        self._simulation_time: Optional[float] = None
        self._precomputed_static: Optional[Dict] = None
        self._default_air_absorption()

    def _default_air_absorption(self):
        freqs = self.room.frequencies
        air_coeffs = 0.001 * (freqs / 1000) ** 1.5
        self.air_absorption_band = AbsorptionBand(freqs, air_coeffs)

    def set_air_absorption(self, absorption_band: AbsorptionBand):
        self.air_absorption_band = absorption_band
        self.air_absorption = True

    def _estimate_band_rt60(self, band_idx: int) -> float:
        volume = self.room.get_volume()
        surface_areas = self.room.get_wall_surface_areas()
        absorption_coeffs = self.room.absorption[:, band_idx]
        total_surface = np.sum(surface_areas)
        alpha_mean = np.sum(surface_areas * absorption_coeffs) / max(total_surface, 1e-10)

        if alpha_mean <= 0:
            return 5.0
        if alpha_mean >= 1.0:
            return 0.01

        alpha_eyring = -np.log(1 - alpha_mean)
        rt60 = 0.161 * volume / (total_surface * alpha_eyring)
        return float(max(rt60, 0.01))

    def add_source(self, source: Union[SoundSource, DynamicSource]) -> int:
        return self.source_manager.add_source(source)

    def add_receiver(self, position: np.ndarray) -> int:
        rec_id = len(self.receivers)
        self.receivers.append(Receiver(position, rec_id))
        return rec_id

    def add_receivers_grid(self, x_range: Tuple[float, float],
                           y_range: Tuple[float, float],
                           z_range: Optional[Tuple[float, float]] = None,
                           resolution: float = 0.1) -> np.ndarray:
        x = np.arange(x_range[0], x_range[1] + resolution, resolution)
        y = np.arange(y_range[0], y_range[1] + resolution, resolution)

        if z_range is not None and self.room.ndim == 3:
            z = np.arange(z_range[0], z_range[1] + resolution, resolution)
            X, Y, Z = np.meshgrid(x, y, z)
            positions = np.vstack([X.ravel(), Y.ravel(), Z.ravel()]).T
        else:
            X, Y = np.meshgrid(x, y)
            positions = np.vstack([X.ravel(), Y.ravel()]).T

        for pos in positions:
            self.add_receiver(pos)

        return positions

    def compute_mirror_sources(self, max_order: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        source_positions = self.source_manager.get_positions()
        receiver_positions = np.array([rec.position[:self.room.ndim] for rec in self.receivers])

        if max_order is None:
            if self.room.adaptive_order:
                max_order = self.room.compute_adaptive_max_order_multi(
                    source_positions, receiver_positions
                )
                logger.info(f"Adaptive max order determined: {max_order}")
            elif self.room.max_order is not None:
                max_order = self.room.max_order
            else:
                max_order = 3

        self.room.max_order = max_order

        if self.room.use_pra and PRA_AVAILABLE:
            return self._compute_mirror_sources_pra(max_order)
        else:
            if self.room.use_pra and not PRA_AVAILABLE:
                logger.warning("Pyroomacoustics not available, falling back to custom implementation")
            return self._compute_mirror_sources_custom(max_order)

    def _compute_mirror_sources_pra(self, max_order: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        if not PRA_AVAILABLE:
            raise RuntimeError("Pyroomacoustics is not available")
        sources_pos = self.source_manager.get_positions()

        if self.room.ndim == 2:
            self.pra_room = pra.room.ShoeBox(
                p=self.room.dimensions[:2],
                absorption=float(np.mean(self.room.get_average_absorption())),
                fs=self.fs,
                max_order=max_order
            )
        else:
            self.pra_room = pra.room.ShoeBox(
                p=self.room.dimensions,
                absorption=float(np.mean(self.room.get_average_absorption())),
                fs=self.fs,
                max_order=max_order
            )

        for pos in sources_pos:
            self.pra_room.add_source(pos[:self.room.ndim])

        for rec in self.receivers:
            self.pra_room.add_microphone(rec.position[:self.room.ndim])

        self.pra_room.image_source_model()

        mirror_sources = []
        mirror_orders = []
        mirror_reflections = []

        for src_idx, src in enumerate(self.pra_room.sources):
            for img_src in src.images:
                mirror_sources.append(img_src)
                order = int(np.sum(np.abs(src.orders[len(mirror_sources) - 1 - len(sources_pos)]))) if len(sources_pos) > 0 else 0
                mirror_orders.append(order)

        if len(mirror_sources) > 0:
            self._mirror_sources = np.array(mirror_sources)
            self._mirror_orders = np.array(mirror_orders)
            self._mirror_reflection_counts = np.zeros((len(mirror_sources), 2 * self.room.ndim), dtype=np.int32)
        else:
            self._mirror_sources = sources_pos
            self._mirror_orders = np.zeros(len(sources_pos))
            self._mirror_reflection_counts = np.zeros((len(sources_pos), 2 * self.room.ndim), dtype=np.int32)

        return self._mirror_sources, self._mirror_orders, self._mirror_reflection_counts

    def _compute_mirror_sources_custom(self, max_order: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        sources_pos = self.source_manager.get_positions()
        n_sources = len(sources_pos)
        room_dims = self.room.dimensions[:self.room.ndim]
        n_walls = 2 * self.room.ndim

        all_mirror_sources = []
        all_orders = []
        all_reflection_counts = []

        if self.room.ndim == 2:
            for order in range(max_order + 1):
                for nx in range(-order, order + 1):
                    for ny in range(-(order - abs(nx)), order - abs(nx) + 1):
                        if abs(nx) + abs(ny) != order:
                            continue
                        for src_pos in sources_pos:
                            mx = 2 * nx * room_dims[0] + (-1)**nx * src_pos[0]
                            my = 2 * ny * room_dims[1] + (-1)**ny * src_pos[1]
                            all_mirror_sources.append([mx, my])
                            all_orders.append(order)

                            reflections = np.zeros(n_walls, dtype=np.int32)
                            reflections[0] = max(0, nx)
                            reflections[1] = max(0, -nx)
                            reflections[2] = max(0, ny)
                            reflections[3] = max(0, -ny)
                            all_reflection_counts.append(reflections)
        else:
            for order in range(max_order + 1):
                for nx in range(-order, order + 1):
                    for ny in range(-(order - abs(nx)), order - abs(nx) + 1):
                        nz = order - abs(nx) - abs(ny)
                        for sign in [1, -1] if nz != 0 else [1]:
                            nz_signed = sign * nz
                            for src_pos in sources_pos:
                                mx = 2 * nx * room_dims[0] + (-1)**nx * src_pos[0]
                                my = 2 * ny * room_dims[1] + (-1)**ny * src_pos[1]
                                mz = 2 * nz_signed * room_dims[2] + (-1)**nz_signed * src_pos[2]
                                all_mirror_sources.append([mx, my, mz])
                                all_orders.append(order)

                                reflections = np.zeros(n_walls, dtype=np.int32)
                                reflections[0] = max(0, nx)
                                reflections[1] = max(0, -nx)
                                reflections[2] = max(0, ny)
                                reflections[3] = max(0, -ny)
                                reflections[4] = max(0, nz_signed)
                                reflections[5] = max(0, -nz_signed)
                                all_reflection_counts.append(reflections)

        self._mirror_sources = np.array(all_mirror_sources)
        self._mirror_orders = np.array(all_orders)
        self._mirror_reflection_counts = np.array(all_reflection_counts)

        return self._mirror_sources, self._mirror_orders, self._mirror_reflection_counts

    def compute_band_impulse_responses(self, max_order: Optional[int] = None,
                                        duration: Optional[float] = None) -> np.ndarray:
        import time
        start_time = time.time()

        receiver_positions = np.array([rec.position[:self.room.ndim] for rec in self.receivers])
        source_positions = self.source_manager.get_positions()

        if max_order is None:
            if self.room.adaptive_order:
                max_order = self.room.compute_adaptive_max_order_multi(
                    source_positions, receiver_positions
                )
                logger.info(f"Adaptive max order: {max_order}")
            elif self.room.max_order is not None:
                max_order = self.room.max_order
            else:
                max_order = 3

        if duration is None:
            alpha_avg = float(np.mean(self.room.absorption))
            volume = self.room.get_volume()
            surface = self.room.get_surface_area()
            if alpha_avg > 0 and surface > 0:
                rt60_est = 0.161 * volume / (surface * alpha_avg)
                duration = min(max(2 * rt60_est, 0.5), 5.0)
                logger.info(f"Auto duration from RT60 estimate: {duration:.2f}s")
            else:
                duration = 2.0

        n_samples = int(duration * self.fs)
        n_receivers = len(self.receivers)
        n_sources = len(self.source_manager)
        n_bands = self.room.n_bands

        if self._mirror_sources is None:
            self.compute_mirror_sources(max_order)

        n_mirrors = len(self._mirror_sources)

        self._band_impulse_responses = np.zeros(
            (n_receivers, n_sources, n_bands, n_samples), dtype=np.float64
        )

        distances = self.gpu.parallel_distance_calculation(
            self._mirror_sources, receiver_positions
        )

        n_mirrors_per_source = n_mirrors // n_sources

        for band_idx in range(n_bands):
            reflection_coeffs = np.sqrt(1 - self.room.absorption[:, band_idx])
            specular_coeffs = np.sqrt(1 - self.room.scattering[:, band_idx])
            scatter_coeffs = np.sqrt(self.room.scattering[:, band_idx])

            diffuse_decay = np.zeros(n_samples, dtype=np.float64)

            for src_idx in range(n_sources):
                src_start = src_idx * n_mirrors_per_source
                src_end = min(src_start + n_mirrors_per_source, n_mirrors)

                for mirror_idx in range(src_start, src_end):
                    reflections = self._mirror_reflection_counts[mirror_idx]
                    total_reflections = int(np.sum(reflections))

                    specular_amp = 1.0
                    scatter_amp = 1.0
                    for wall_idx in range(2 * self.room.ndim):
                        n_ref = reflections[wall_idx]
                        if n_ref > 0:
                            specular_amp *= (reflection_coeffs[wall_idx] * specular_coeffs[wall_idx]) ** n_ref
                            scatter_amp *= (reflection_coeffs[wall_idx] * scatter_coeffs[wall_idx]) ** n_ref

                    for rec_idx in range(n_receivers):
                        dist = distances[mirror_idx, rec_idx]
                        if dist < 0.001:
                            dist = 0.001

                        time_delay = dist / self.sound_speed
                        sample_delay = int(time_delay * self.fs)

                        if sample_delay < n_samples:
                            spherical_spreading = 1.0 / (4 * np.pi * dist)

                            air_atten = 1.0
                            if self.air_absorption and self.air_absorption_band is not None:
                                air_coeff = self.air_absorption_band.get_absorption_at(
                                    self.room.frequencies[band_idx]
                                )
                                air_atten = np.exp(-air_coeff * dist)

                            base_amp = spherical_spreading * air_atten

                            if total_reflections == 0:
                                total_amplitude = base_amp
                                self._band_impulse_responses[rec_idx, src_idx, band_idx, sample_delay] += total_amplitude
                            else:
                                specular_total = specular_amp * base_amp
                                self._band_impulse_responses[rec_idx, src_idx, band_idx, sample_delay] += specular_total

                                if np.abs(scatter_amp) > 1e-15 and total_reflections > 0:
                                    scatter_total = scatter_amp * base_amp
                                    rt60_band = self._estimate_band_rt60(band_idx)
                                    decay_rate = 6.93 / max(rt60_band, 0.001)
                                    scatter_duration = min(int(rt60_band * self.fs), n_samples - sample_delay)

                                    if scatter_duration > 0:
                                        t_scatter = np.arange(scatter_duration) / self.fs
                                        diffuse_envelope = np.exp(-decay_rate * t_scatter)
                                        diffuse_envelope /= np.sum(diffuse_envelope) + 1e-10
                                        diffuse_envelope *= scatter_total

                                        start_idx = sample_delay
                                        end_idx = min(start_idx + scatter_duration, n_samples)
                                        self._band_impulse_responses[rec_idx, src_idx, band_idx, start_idx:end_idx] += diffuse_envelope[:end_idx - start_idx]

        self._impulse_responses = np.sum(self._band_impulse_responses, axis=2)

        self._simulation_time = time.time() - start_time
        logger.info(f"Band impulse responses computed in {self._simulation_time:.3f}s")

        return self._band_impulse_responses

    def compute_impulse_responses(self, max_order: Optional[int] = None,
                                  duration: Optional[float] = None) -> np.ndarray:
        if self._band_impulse_responses is None:
            self.compute_band_impulse_responses(max_order, duration)
        return self._impulse_responses

    def compute_impulse_responses_pra(self) -> np.ndarray:
        if not PRA_AVAILABLE:
            raise RuntimeError("Pyroomacoustics is not available")
        import time
        start_time = time.time()

        if self.pra_room is None:
            self.compute_mirror_sources()

        signals = self.source_manager.get_signals(self.fs)
        for i, sig in enumerate(signals):
            if i < len(self.pra_room.sources):
                self.pra_room.sources[i].signal = sig

        self.pra_room.simulate()

        n_receivers = len(self.receivers)
        n_sources = len(self.source_manager)
        n_samples = self.pra_room.mic_array.signals.shape[1]

        self._impulse_responses = np.zeros((n_receivers, n_sources, n_samples), dtype=np.float64)

        for rec_idx in range(n_receivers):
            self._impulse_responses[rec_idx, 0, :] = self.pra_room.mic_array.signals[rec_idx, :]

        self._simulation_time = time.time() - start_time
        logger.info(f"Pyroomacoustics impulse response computed in {self._simulation_time:.3f}s")

        return self._impulse_responses

    def precompute_static_part(self, max_order: Optional[int] = None):
        if self._mirror_sources is None:
            self.compute_mirror_sources(max_order)

        receiver_positions = np.array([rec.position[:self.room.ndim] for rec in self.receivers])

        self._precomputed_static = {
            'mirror_sources_base': self._mirror_sources.copy(),
            'mirror_orders': self._mirror_orders.copy(),
            'reflection_counts': self._mirror_reflection_counts.copy(),
            'receiver_positions': receiver_positions,
            'max_order': self.room.max_order,
        }

        logger.info("Static part precomputed successfully")
        return self._precomputed_static

    def simulate_dynamic_source_optimized(self,
                                           dynamic_source: DynamicSource,
                                           time_points: np.ndarray,
                                           max_order: Optional[int] = None,
                                           duration: float = 1.0,
                                           interpolation_points: Optional[int] = None) -> PrecomputedIR:
        import time
        start_time = time.time()

        if interpolation_points is None:
            interpolation_points = max(5, min(len(time_points), 20))

        if len(time_points) > interpolation_points:
            interp_time_indices = np.linspace(0, len(time_points) - 1,
                                             interpolation_points, dtype=int)
            interp_times = time_points[interp_time_indices]
        else:
            interp_times = time_points
            interpolation_points = len(time_points)

        n_interp = len(interp_times)
        n_receivers = len(self.receivers)
        n_bands = self.room.n_bands
        n_samples = int(duration * self.fs)

        if self._precomputed_static is None:
            self.precompute_static_part(max_order)

        static = self._precomputed_static
        base_mirrors = static['mirror_sources_base']
        orders = static['mirror_orders']
        reflections = static['reflection_counts']
        receiver_positions = static['receiver_positions']

        n_mirrors = len(base_mirrors)
        n_sources = len(self.source_manager)
        n_mirrors_per_source = n_mirrors // max(n_sources, 1)

        interpolated_irs = np.zeros((n_interp, n_receivers, 1, n_samples), dtype=np.float64)
        source_positions_interp = np.zeros((n_interp, self.room.ndim))

        for t_idx, t in enumerate(interp_times):
            src_pos = dynamic_source.get_position(t)[:self.room.ndim]
            source_positions_interp[t_idx] = src_pos

            shifted_mirrors = base_mirrors.copy()
            for i in range(n_mirrors_per_source):
                shifted_mirrors[i] = src_pos + (base_mirrors[i] - self.source_manager.get_positions()[0])

            distances = self.gpu.parallel_distance_calculation(
                shifted_mirrors, receiver_positions
            )

            for band_idx in range(n_bands):
                reflection_coeffs = np.sqrt(1 - self.room.absorption[:, band_idx])
                specular_coeffs = np.sqrt(1 - self.room.scattering[:, band_idx])
                scatter_coeffs = np.sqrt(self.room.scattering[:, band_idx])

                for mirror_idx in range(min(n_mirrors_per_source, n_mirrors)):
                    refl_counts = reflections[mirror_idx]
                    total_reflections = int(np.sum(refl_counts))

                    specular_amp = 1.0
                    scatter_amp = 1.0
                    for wall_idx in range(2 * self.room.ndim):
                        n_ref = refl_counts[wall_idx]
                        if n_ref > 0:
                            specular_amp *= (reflection_coeffs[wall_idx] * specular_coeffs[wall_idx]) ** n_ref
                            scatter_amp *= (reflection_coeffs[wall_idx] * scatter_coeffs[wall_idx]) ** n_ref

                    for rec_idx in range(n_receivers):
                        dist = distances[mirror_idx, rec_idx]
                        if dist < 0.001:
                            dist = 0.001

                        time_delay = dist / self.sound_speed
                        sample_delay = int(time_delay * self.fs)

                        if sample_delay < n_samples:
                            spherical = 1.0 / (4 * np.pi * dist)

                            if total_reflections == 0:
                                total_amp = spherical
                                interpolated_irs[t_idx, rec_idx, 0, sample_delay] += total_amp
                            else:
                                specular_total = specular_amp * spherical
                                interpolated_irs[t_idx, rec_idx, 0, sample_delay] += specular_total

                                if np.abs(scatter_amp) > 1e-15 and total_reflections > 0:
                                    scatter_total = scatter_amp * spherical
                                    rt60_band = self._estimate_band_rt60(band_idx)
                                    decay_rate = 6.93 / max(rt60_band, 0.001)
                                    scatter_duration = min(int(rt60_band * self.fs), n_samples - sample_delay)

                                    if scatter_duration > 0:
                                        t_scatter = np.arange(scatter_duration) / self.fs
                                        diffuse_envelope = np.exp(-decay_rate * t_scatter)
                                        diffuse_envelope /= np.sum(diffuse_envelope) + 1e-10
                                        diffuse_envelope *= scatter_total

                                        start_idx = sample_delay
                                        end_idx = min(start_idx + scatter_duration, n_samples)
                                        interpolated_irs[t_idx, rec_idx, 0, start_idx:end_idx] += diffuse_envelope[:end_idx - start_idx]

        precomputed = PrecomputedIR(
            time_points=interp_times,
            source_positions=source_positions_interp,
            impulse_responses=interpolated_irs,
            interpolation_method="linear"
        )

        logger.info(f"Optimized dynamic simulation completed in {time.time() - start_time:.3f}s")
        logger.info(f"Precomputed {n_interp} interpolation points for {len(time_points)} time steps")

        return precomputed

    def simulate_dynamic_source(self, source: DynamicSource,
                                time_points: np.ndarray,
                                use_optimized: bool = True,
                                max_order: Optional[int] = None,
                                duration: float = 1.0) -> Dict[str, np.ndarray]:
        if use_optimized and len(self.source_manager) == 1:
            precomputed = self.simulate_dynamic_source_optimized(
                source, time_points, max_order=max_order, duration=duration
            )

            results = {
                'time_points': time_points,
                'source_positions': np.zeros((len(time_points), self.room.ndim)),
                'impulse_responses': [],
                'pressure_levels': []
            }

            frequencies = np.array([1000.0])

            for t_idx, t in enumerate(time_points):
                results['source_positions'][t_idx] = source.get_position(t)[:self.room.ndim]
                ir = precomputed.get_ir_at_time(t)
                results['impulse_responses'].append(ir)

                pressure = self.compute_sound_pressure_from_ir(ir, frequencies)
                spl = 20 * np.log10(np.abs(pressure) + 1e-10)
                results['pressure_levels'].append(spl)

            results['impulse_responses'] = np.array(results['impulse_responses'])
            results['pressure_levels'] = np.array(results['pressure_levels'])
            results['precomputed_ir'] = precomputed

            return results
        else:
            return self._simulate_dynamic_source_original(source, time_points)

    def _simulate_dynamic_source_original(self, source: DynamicSource,
                                           time_points: np.ndarray) -> Dict[str, np.ndarray]:
        results = {
            'time_points': time_points,
            'source_positions': np.zeros((len(time_points), self.room.ndim)),
            'impulse_responses': [],
            'pressure_levels': []
        }

        frequencies = np.array([1000.0])

        for t_idx, t in enumerate(time_points):
            pos = source.get_position(t)
            results['source_positions'][t_idx] = pos[:self.room.ndim]

            temp_source = SoundSource(position=pos, amplitude=source.amplitude,
                                     signal=source.signal, delay=source.delay)

            temp_sim = AcousticSimulator(
                self.room, self.fs, self.sound_speed,
                use_gpu=self.gpu.use_gpu, gpu_backend=self.gpu.backend
            )
            temp_sim.add_source(temp_source)
            for rec in self.receivers:
                temp_sim.add_receiver(rec.position)

            ir = temp_sim.compute_impulse_responses(max_order=2, duration=1.0)
            results['impulse_responses'].append(ir)

            pressure = temp_sim.compute_sound_pressure(frequencies)
            spl = 20 * np.log10(np.abs(pressure) + 1e-10)
            results['pressure_levels'].append(spl)

        results['impulse_responses'] = np.array(results['impulse_responses'])
        results['pressure_levels'] = np.array(results['pressure_levels'])

        return results

    def compute_sound_pressure_from_ir(self, ir: np.ndarray,
                                        frequencies: np.ndarray) -> np.ndarray:
        n_receivers, n_sources, n_samples = ir.shape
        n_freq = len(frequencies)

        pressure = np.zeros((n_freq, n_sources, n_receivers), dtype=np.complex128)

        for rec_idx in range(n_receivers):
            for src_idx in range(n_sources):
                ir_fft = np.fft.fft(ir[rec_idx, src_idx, :])
                freq_bins = np.fft.fftfreq(n_samples, d=1.0 / self.fs)

                for f_idx, freq in enumerate(frequencies):
                    closest_idx = np.argmin(np.abs(freq_bins - freq))
                    pressure[f_idx, src_idx, rec_idx] = ir_fft[closest_idx]

        return pressure

    def compute_sound_pressure(self, frequencies: np.ndarray,
                               time: Optional[float] = None) -> np.ndarray:
        sources_pos = self.source_manager.get_positions(time)
        receiver_positions = np.array([rec.position[:self.room.ndim] for rec in self.receivers])

        distances = self.gpu.parallel_distance_calculation(sources_pos, receiver_positions)

        pressure = np.zeros((len(frequencies), len(sources_pos), len(receiver_positions)), dtype=np.complex128)

        for f_idx, freq in enumerate(frequencies):
            alpha = self.room.absorption_band.interp_absorption(freq)
            band_pressure = self.gpu.parallel_pressure_calculation(
                distances, np.array([freq]), alpha, self.sound_speed
            )
            pressure[f_idx] = band_pressure[0]

        source_signals = self.source_manager.get_signals(self.fs)
        for i, sig in enumerate(source_signals):
            n_fft = len(sig)
            sig_fft = np.abs(np.fft.fft(sig))
            freq_bins = np.fft.fftfreq(n_fft, d=1.0 / self.fs)

            sig_spectrum = np.zeros(len(frequencies))
            for f_idx, freq in enumerate(frequencies):
                closest_idx = np.argmin(np.abs(freq_bins - freq))
                sig_spectrum[f_idx] = sig_fft[closest_idx]

            pressure[:, i, :] *= sig_spectrum[:, np.newaxis]

        return pressure

    def get_impulse_response(self, receiver_idx: int = 0, source_idx: int = 0,
                              band_idx: Optional[int] = None) -> np.ndarray:
        if band_idx is not None:
            if self._band_impulse_responses is None:
                raise RuntimeError("No band impulse responses computed. Call compute_band_impulse_responses first.")
            return self._band_impulse_responses[receiver_idx, source_idx, band_idx, :]
        else:
            if self._impulse_responses is None:
                raise RuntimeError("No impulse responses computed. Call compute_impulse_responses first.")
            return self._impulse_responses[receiver_idx, source_idx, :]

    def get_band_impulse_responses(self) -> np.ndarray:
        if self._band_impulse_responses is None:
            raise RuntimeError("No band impulse responses computed. Call compute_band_impulse_responses first.")
        return self._band_impulse_responses

    def get_time_axis(self, duration: Optional[float] = None) -> np.ndarray:
        if duration is None and self._impulse_responses is not None:
            n_samples = self._impulse_responses.shape[-1]
        elif duration is not None:
            n_samples = int(duration * self.fs)
        else:
            n_samples = int(self.fs)
        return np.arange(n_samples) / self.fs

    def reset(self):
        self.source_manager = SourceManager()
        self.receivers = []
        self.pra_room = None
        self._mirror_sources = None
        self._mirror_orders = None
        self._mirror_reflection_counts = None
        self._impulse_responses = None
        self._band_impulse_responses = None
        self._simulation_time = None
        self._precomputed_static = None

    @property
    def simulation_time(self) -> float:
        return self._simulation_time if self._simulation_time else 0.0

    @property
    def impulse_responses(self) -> np.ndarray:
        return self._impulse_responses

    @property
    def band_impulse_responses(self) -> np.ndarray:
        return self._band_impulse_responses

    @property
    def mirror_sources(self) -> np.ndarray:
        return self._mirror_sources
