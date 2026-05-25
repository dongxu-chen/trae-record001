import numpy as np
from scipy import signal
from typing import Tuple, Optional, List, Dict, Union, TYPE_CHECKING
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .acoustic_simulator import RoomGeometry


class RT60Calculator:
    def __init__(self, fs: int = 44100):
        self.fs = fs

    def calculate_rt60(self, impulse_response: np.ndarray,
                       method: str = "t30",
                       freq_bands: Optional[np.ndarray] = None) -> Dict[str, Union[float, np.ndarray]]:
        results = {}

        if freq_bands is not None:
            rt60_bands = []
            edc_bands = []
            for freq in freq_bands:
                filtered_ir = self._bandpass_filter(impulse_response, freq)
                rt60 = self._calculate_rt60_single(filtered_ir, method)
                rt60_bands.append(rt60)
                edc_bands.append(self._calculate_edc(filtered_ir))
            results['rt60_bands'] = np.array(rt60_bands)
            results['frequencies'] = freq_bands
            results['edc_bands'] = np.array(edc_bands)

        results['rt60'] = self._calculate_rt60_single(impulse_response, method)
        results['method'] = method
        results['edc'] = self._calculate_edc(impulse_response)
        results['t20'], results['t30'] = self._calculate_rt60_variants(impulse_response)

        return results

    def calculate_rt60_from_band_irs(self, band_irs: np.ndarray,
                                     frequencies: np.ndarray,
                                     method: str = "t30") -> Dict[str, Union[float, np.ndarray]]:
        n_bands = len(frequencies)
        if band_irs.ndim == 1:
            band_irs = band_irs.reshape(1, -1)

        rt60_bands = []
        edc_bands = []
        t20_bands = []
        t30_bands = []

        for band_idx in range(n_bands):
            ir = band_irs[band_idx]
            rt60 = self._calculate_rt60_single(ir, method)
            edc = self._calculate_edc(ir)
            t20, t30 = self._calculate_rt60_variants(ir)

            rt60_bands.append(rt60)
            edc_bands.append(edc)
            t20_bands.append(t20)
            t30_bands.append(t30)

        total_ir = np.sum(band_irs, axis=0)
        results = {
            'rt60_bands': np.array(rt60_bands),
            'frequencies': frequencies,
            'edc_bands': np.array(edc_bands),
            't20_bands': np.array(t20_bands),
            't30_bands': np.array(t30_bands),
            'rt60': self._calculate_rt60_single(total_ir, method),
            'edc': self._calculate_edc(total_ir),
            'method': method,
            'band_irs': band_irs,
        }

        return results

    def calculate_rt60_theoretical_bands(self, room: 'RoomGeometry',
                                          method: str = "sabine") -> Dict[str, np.ndarray]:
        frequencies = room.frequencies
        n_bands = len(frequencies)
        rt60_bands = np.zeros(n_bands)

        volume = room.get_volume()
        surface_areas = room.get_wall_surface_areas()

        for band_idx in range(n_bands):
            alphas = room.absorption[:, band_idx]

            if method == "sabine":
                total_absorption = np.sum(surface_areas * alphas)
                if total_absorption > 0:
                    rt60_bands[band_idx] = 0.161 * volume / total_absorption
                else:
                    rt60_bands[band_idx] = float('inf')
            elif method == "eyring":
                alphas_clipped = np.clip(alphas, 0.001, 0.999)
                total_absorption = -np.sum(surface_areas * np.log(1 - alphas_clipped))
                if total_absorption > 0:
                    rt60_bands[band_idx] = 0.161 * volume / total_absorption
                else:
                    rt60_bands[band_idx] = float('inf')
            elif method == "millington_sette":
                alphas_clipped = np.clip(alphas, 0.001, 0.999)
                total_absorption = -np.sum(surface_areas * np.log(1 - alphas_clipped))
                if total_absorption > 0:
                    rt60_bands[band_idx] = 0.161 * volume / total_absorption
                else:
                    rt60_bands[band_idx] = float('inf')
            else:
                raise ValueError(f"Unknown theoretical method: {method}")

        return {
            'rt60_bands': rt60_bands,
            'frequencies': frequencies,
            'method': method,
        }

    def _calculate_rt60_single(self, impulse_response: np.ndarray, method: str = "t30") -> float:
        edc = self._calculate_edc(impulse_response)

        if method == "t30":
            return self._rt60_from_edc(edc, -5, -35)
        elif method == "t20":
            return self._rt60_from_edc(edc, -5, -25)
        elif method == "t10":
            return self._rt60_from_edc(edc, -5, -15)
        elif method == "lundeby":
            return self._rt60_lundeby(impulse_response)
        elif method == "interpolation":
            return self._rt60_interpolation(edc)
        else:
            raise ValueError(f"Unknown RT60 method: {method}")

    def _calculate_edc(self, impulse_response: np.ndarray) -> np.ndarray:
        ir = np.asarray(impulse_response, dtype=np.float64)
        max_val = np.max(np.abs(ir))
        if max_val > 0:
            ir = ir / max_val
        ir_squared = ir ** 2
        edc = np.flip(np.cumsum(np.flip(ir_squared)))
        edc_max = np.max(edc)
        if edc_max > 0:
            edc_db = 10 * np.log10(edc / edc_max + 1e-10)
        else:
            edc_db = np.ones_like(edc) * (-100.0)
        return edc_db

    def _rt60_from_edc(self, edc_db: np.ndarray,
                       start_db: float = -5.0,
                       end_db: float = -35.0) -> float:
        t = np.arange(len(edc_db)) / self.fs

        try:
            start_idx = np.where(edc_db <= start_db)[0][0]
            end_idx = np.where(edc_db <= end_db)[0]
            if len(end_idx) > 0:
                end_idx = end_idx[0]
            else:
                end_idx = len(edc_db) - 1

            if end_idx <= start_idx:
                start_idx = max(0, start_idx - 10)

            t_segment = t[start_idx:end_idx]
            edc_segment = edc_db[start_idx:end_idx]

            if len(t_segment) < 2:
                return 0.0

            slope, intercept = np.polyfit(t_segment, edc_segment, 1)
            rt60 = -60.0 / slope if slope < 0 else 0.0

            return max(0.0, rt60)
        except Exception as e:
            logger.warning(f"RT60 calculation failed: {e}")
            return 0.0

    def _rt60_lundeby(self, impulse_response: np.ndarray) -> float:
        edc_db = self._calculate_edc(impulse_response)
        t = np.arange(len(edc_db)) / self.fs

        noise_level = np.mean(edc_db[-int(0.1 * self.fs):])
        cross_point = noise_level + 10

        try:
            decay_start = np.where(edc_db <= -5)[0][0]
            decay_end = np.where(edc_db <= cross_point)[0]
            if len(decay_end) > 0:
                decay_end = decay_end[0]
            else:
                decay_end = len(edc_db) - 1

            t_segment = t[decay_start:decay_end]
            edc_segment = edc_db[decay_start:decay_end]

            if len(t_segment) < 10:
                return self._rt60_from_edc(edc_db)

            slope, intercept = np.polyfit(t_segment, edc_segment, 1)
            rt60 = -60.0 / slope if slope < 0 else 0.0

            return max(0.0, rt60)
        except Exception as e:
            logger.warning(f"Lundeby RT60 calculation failed, falling back: {e}")
            return self._rt60_from_edc(edc_db)

    def _rt60_interpolation(self, edc_db: np.ndarray) -> float:
        try:
            t = np.arange(len(edc_db)) / self.fs

            idx_5 = np.where(edc_db <= -5)[0][0]
            idx_25 = np.where(edc_db <= -25)[0]
            idx_35 = np.where(edc_db <= -35)[0]

            rt20 = 0.0
            rt30 = 0.0

            if len(idx_25) > 0:
                idx_25 = idx_25[0]
                t_20 = t[idx_5:idx_25]
                edc_20 = edc_db[idx_5:idx_25]
                if len(t_20) > 2:
                    slope_20, _ = np.polyfit(t_20, edc_20, 1)
                    rt20 = -60.0 / slope_20 if slope_20 < 0 else 0.0

            if len(idx_35) > 0:
                idx_35 = idx_35[0]
                t_30 = t[idx_5:idx_35]
                edc_30 = edc_db[idx_5:idx_35]
                if len(t_30) > 2:
                    slope_30, _ = np.polyfit(t_30, edc_30, 1)
                    rt30 = -60.0 / slope_30 if slope_30 < 0 else 0.0

            if rt20 > 0 and rt30 > 0:
                return (rt20 + rt30) / 2
            elif rt30 > 0:
                return rt30
            elif rt20 > 0:
                return rt20
            else:
                return self._rt60_from_edc(edc_db)
        except Exception as e:
            logger.warning(f"Interpolation RT60 calculation failed: {e}")
            return self._rt60_from_edc(edc_db)

    def _calculate_rt60_variants(self, impulse_response: np.ndarray) -> Tuple[float, float]:
        edc_db = self._calculate_edc(impulse_response)
        t20 = self._rt60_from_edc(edc_db, -5, -25)
        t30 = self._rt60_from_edc(edc_db, -5, -35)
        return t20, t30

    def _bandpass_filter(self, signal_in: np.ndarray, center_freq: float,
                         bandwidth: float = 1.0) -> np.ndarray:
        octave_ratio = 2 ** (bandwidth / 2)
        low_freq = center_freq / octave_ratio
        high_freq = center_freq * octave_ratio

        nyquist = self.fs / 2
        low = max(low_freq / nyquist, 0.001)
        high = min(high_freq / nyquist, 0.999)

        if low >= high:
            return signal_in

        b, a = signal.butter(4, [low, high], btype='band')
        return signal.filtfilt(b, a, signal_in)

    def calculate_sabine_rt60(self, volume: float, surface_area: float,
                              absorption_coeff: float) -> float:
        if absorption_coeff <= 0:
            return float('inf')
        return 0.161 * volume / (surface_area * absorption_coeff)

    def calculate_eyring_rt60(self, volume: float, surface_area: float,
                              absorption_coeff: float) -> float:
        if absorption_coeff <= 0:
            return float('inf')
        if absorption_coeff >= 1:
            return 0.0
        return 0.161 * volume / (-surface_area * np.log(1 - absorption_coeff))

    def calculate_millington_sette_rt60(self, volume: float,
                                        surface_areas: List[float],
                                        absorption_coeffs: List[float]) -> float:
        total_absorption = 0.0
        for area, alpha in zip(surface_areas, absorption_coeffs):
            if alpha < 1:
                total_absorption += -area * np.log(1 - alpha)
        if total_absorption <= 0:
            return float('inf')
        return 0.161 * volume / total_absorption

    def calculate_fitzroy_rt60(self, volume: float,
                               surface_areas: List[float],
                               absorption_coeffs: List[float]) -> float:
        if len(surface_areas) != 6 or len(absorption_coeffs) != 6:
            raise ValueError("Fitzroy requires 6 surfaces (3 pairs)")

        Sx = surface_areas[0] + surface_areas[1]
        Sy = surface_areas[2] + surface_areas[3]
        Sz = surface_areas[4] + surface_areas[5]

        ax = (absorption_coeffs[0] + absorption_coeffs[1]) / 2
        ay = (absorption_coeffs[2] + absorption_coeffs[3]) / 2
        az = (absorption_coeffs[4] + absorption_coeffs[5]) / 2

        S_total = Sx + Sy + Sz

        if ax <= 0 or ay <= 0 or az <= 0:
            return float('inf')

        term1 = Sx / (-np.log(1 - ax)) if ax < 1 else Sx / 10
        term2 = Sy / (-np.log(1 - ay)) if ay < 1 else Sy / 10
        term3 = Sz / (-np.log(1 - az)) if az < 1 else Sz / 10

        denominator = (S_total / 8) * (
            1 / term1 + 1 / term2 + 1 / term3
        ) ** 2 * (term1 + term2 + term3)

        if denominator <= 0:
            return float('inf')

        return 0.161 * volume / denominator

    def calculate_arau_puchades_rt60(self, volume: float,
                                      surface_areas: List[float],
                                      absorption_coeffs: List[float]) -> float:
        if len(surface_areas) != 6 or len(absorption_coeffs) != 6:
            raise ValueError("Araú-Puchades requires 6 surfaces")

        S = np.array(surface_areas)
        alpha = np.array(absorption_coeffs)
        alpha_safe = np.clip(alpha, 0.001, 0.999)

        term1 = np.sum(S) / np.sum(S * alpha_safe)
        term2 = np.sum(S) / np.sum(S * (1 - np.log(alpha_safe)))

        t_sabine = self.calculate_sabine_rt60(volume, np.sum(S), np.mean(alpha_safe))
        t_eyring = self.calculate_eyring_rt60(volume, np.sum(S), np.mean(alpha_safe))

        x = np.mean(alpha_safe)
        weight = 1 - np.exp(-10 * x)

        return weight * t_eyring + (1 - weight) * t_sabine

    def analyze_room_modes(self, room_dims: np.ndarray,
                           max_freq: float = 200.0) -> Dict[str, np.ndarray]:
        c = 343.0
        modes = []
        frequencies = []

        Lx, Ly, Lz = room_dims if len(room_dims) == 3 else (room_dims[0], room_dims[1], float('inf'))

        max_nx = int(2 * max_freq * Lx / c) + 1
        max_ny = int(2 * max_freq * Ly / c) + 1
        max_nz = int(2 * max_freq * Lz / c) + 1 if Lz != float('inf') else 0

        for nx in range(max_nx + 1):
            for ny in range(max_ny + 1):
                for nz in range(max_nz + 1):
                    if nx == 0 and ny == 0 and nz == 0:
                        continue
                    if Lz == float('inf') and nz != 0:
                        continue

                    if Lz == float('inf'):
                        freq = (c / 2) * np.sqrt((nx / Lx) ** 2 + (ny / Ly) ** 2)
                    else:
                        freq = (c / 2) * np.sqrt((nx / Lx) ** 2 + (ny / Ly) ** 2 + (nz / Lz) ** 2)

                    if freq <= max_freq:
                        modes.append((nx, ny, nz))
                        frequencies.append(freq)

        sorted_indices = np.argsort(frequencies)
        return {
            'frequencies': np.array(frequencies)[sorted_indices],
            'modes': np.array(modes)[sorted_indices],
            'spacing': np.diff(np.array(frequencies)[sorted_indices])
        }

    def calculate_modal_density(self, freq: float, volume: float,
                                 sound_speed: float = 343.0) -> float:
        return 4 * np.pi * volume * freq ** 2 / sound_speed ** 3 + \
               np.pi * volume * freq / sound_speed ** 2 + \
               volume / (8 * np.pi * sound_speed)

    def calculate_critical_frequency(self, volume: float, rt60: float) -> float:
        if rt60 <= 0:
            return 0.0
        return 2000 * np.sqrt(rt60 / volume)

    def estimate_reverberation_energy(self, impulse_response: np.ndarray,
                                       time_window: float = 0.01) -> np.ndarray:
        ir_squared = np.abs(impulse_response) ** 2
        window_samples = int(time_window * self.fs)
        window = np.ones(window_samples) / window_samples
        return np.convolve(ir_squared, window, mode='same')

    def calculate_clarity(self, impulse_response: np.ndarray,
                          threshold_time: float = 0.05) -> float:
        t = np.arange(len(impulse_response)) / self.fs
        ir_sq = np.abs(impulse_response) ** 2

        early = np.sum(ir_sq[t <= threshold_time])
        late = np.sum(ir_sq[t > threshold_time])

        if late <= 0:
            return float('inf')
        return 10 * np.log10(early / late)

    def calculate_definition(self, impulse_response: np.ndarray,
                             threshold_time: float = 0.05) -> float:
        t = np.arange(len(impulse_response)) / self.fs
        ir_sq = np.abs(impulse_response) ** 2

        early = np.sum(ir_sq[t <= threshold_time])
        total = np.sum(ir_sq)

        if total <= 0:
            return 0.0
        return 100 * early / total

    def calculate_center_time(self, impulse_response: np.ndarray) -> float:
        t = np.arange(len(impulse_response)) / self.fs
        ir_sq = np.abs(impulse_response) ** 2
        total = np.sum(ir_sq)
        if total <= 0:
            return 0.0
        return np.sum(t * ir_sq) / total
