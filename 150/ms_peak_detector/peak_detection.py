import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter1d, minimum_filter1d
from typing import List, Dict, Tuple


class PeakDetector:
    def __init__(self, method: str = "cwt"):
        self.method = method
        self.peaks = None
    
    def detect(self, mz: np.ndarray, intensity: np.ndarray, 
               merge_distance: float = 0.5, **kwargs) -> List[Dict]:
        if self.method == "cwt":
            peaks = self._cwt_detection(mz, intensity, **kwargs)
        elif self.method == "local_max":
            peaks = self._local_max_detection(mz, intensity, **kwargs)
        elif self.method == "pyopenms":
            peaks = self._pyopenms_detection(mz, intensity, **kwargs)
        else:
            raise ValueError(f"Unknown method: {self.method}")
        
        if merge_distance > 0:
            peaks = self._merge_adjacent_peaks(peaks, mz, intensity, merge_distance)
        
        self.peaks = peaks
        return peaks
    
    def _merge_adjacent_peaks(self, peaks: List[Dict], mz: np.ndarray, 
                              intensity: np.ndarray, merge_distance: float) -> List[Dict]:
        if len(peaks) <= 1:
            return peaks
        
        peaks_sorted = sorted(peaks, key=lambda x: x["mz"])
        merged = []
        current_group = [peaks_sorted[0]]
        
        for peak in peaks_sorted[1:]:
            current_mz = current_group[-1]["mz"]
            peak_mz = peak["mz"]
            
            if abs(peak_mz - current_mz) <= merge_distance:
                current_group.append(peak)
            else:
                merged_peak = self._merge_peak_group(current_group, mz, intensity)
                merged.append(merged_peak)
                current_group = [peak]
        
        if current_group:
            merged_peak = self._merge_peak_group(current_group, mz, intensity)
            merged.append(merged_peak)
        
        return merged
    
    def _merge_peak_group(self, peak_group: List[Dict], mz: np.ndarray, 
                          intensity: np.ndarray) -> Dict:
        if len(peak_group) == 1:
            return peak_group[0]
        
        total_intensity = sum(p["intensity"] for p in peak_group)
        weighted_mz = sum(p["mz"] * p["intensity"] for p in peak_group) / total_intensity
        
        left_idx = min(p["left_index"] for p in peak_group)
        right_idx = max(p["right_index"] for p in peak_group)
        
        peak_idx = np.argmin(np.abs(mz - weighted_mz))
        
        fwhm = mz[right_idx] - mz[left_idx]
        area = np.trapz(intensity[left_idx:right_idx+1], mz[left_idx:right_idx+1])
        
        snr = self._calculate_snr(intensity, peak_idx, left_idx, right_idx)
        
        return {
            "mz": weighted_mz,
            "intensity": total_intensity,
            "index": peak_idx,
            "left_index": left_idx,
            "right_index": right_idx,
            "fwhm": fwhm,
            "area": area,
            "snr": snr,
            "merged_count": len(peak_group)
        }
    
    def _cwt_detection(self, mz: np.ndarray, intensity: np.ndarray, widths: np.ndarray = None, snr_threshold: float = 3.0, min_snr: float = 2.0) -> List[Dict]:
        if widths is None:
            widths = np.arange(1, 31)
        
        peak_indices = signal.find_peaks_cwt(intensity, widths, snr_threshold=snr_threshold)
        peaks = []
        
        for idx in peak_indices:
            peak_mz = mz[idx]
            peak_intensity = intensity[idx]
            left_idx, right_idx = self._get_peak_boundaries(intensity, idx)
            
            fwhm = mz[right_idx] - mz[left_idx]
            area = np.trapz(intensity[left_idx:right_idx+1], mz[left_idx:right_idx+1])
            
            snr = self._calculate_snr(intensity, idx, left_idx, right_idx)
            
            if snr >= min_snr:
                peaks.append({
                    "mz": peak_mz,
                    "intensity": peak_intensity,
                    "index": idx,
                    "left_index": left_idx,
                    "right_index": right_idx,
                    "fwhm": fwhm,
                    "area": area,
                    "snr": snr
                })
        
        return peaks
    
    def _local_max_detection(self, mz: np.ndarray, intensity: np.ndarray, threshold: float = 0.01, min_distance: int = 5) -> List[Dict]:
        max_intensity = np.max(intensity)
        height = threshold * max_intensity
        
        peak_indices, _ = signal.find_peaks(intensity, height=height, distance=min_distance)
        
        peaks = []
        for idx in peak_indices:
            peak_mz = mz[idx]
            peak_intensity = intensity[idx]
            left_idx, right_idx = self._get_peak_boundaries(intensity, idx)
            
            fwhm = mz[right_idx] - mz[left_idx]
            area = np.trapz(intensity[left_idx:right_idx+1], mz[left_idx:right_idx+1])
            
            snr = self._calculate_snr(intensity, idx, left_idx, right_idx)
            
            peaks.append({
                "mz": peak_mz,
                "intensity": peak_intensity,
                "index": idx,
                "left_index": left_idx,
                "right_index": right_idx,
                "fwhm": fwhm,
                "area": area,
                "snr": snr
            })
        
        return peaks
    
    def _pyopenms_detection(self, mz: np.ndarray, intensity: np.ndarray, **kwargs) -> List[Dict]:
        from pyopenms import PeakFinder
        
        peaks = []
        peak_indices = signal.find_peaks(intensity, distance=5)[0]
        
        for idx in peak_indices:
            peak_mz = mz[idx]
            peak_intensity = intensity[idx]
            left_idx, right_idx = self._get_peak_boundaries(intensity, idx)
            
            fwhm = mz[right_idx] - mz[left_idx]
            area = np.trapz(intensity[left_idx:right_idx+1], mz[left_idx:right_idx+1])
            
            snr = self._calculate_snr(intensity, idx, left_idx, right_idx)
            
            peaks.append({
                "mz": peak_mz,
                "intensity": peak_intensity,
                "index": idx,
                "left_index": left_idx,
                "right_index": right_idx,
                "fwhm": fwhm,
                "area": area,
                "snr": snr
            })
        
        return peaks
    
    def _get_peak_boundaries(self, intensity: np.ndarray, peak_idx: int) -> Tuple[int, int]:
        half_max = intensity[peak_idx] / 2.0
        
        left_idx = peak_idx
        while left_idx > 0 and intensity[left_idx] > half_max:
            left_idx -= 1
        
        right_idx = peak_idx
        while right_idx < len(intensity) - 1 and intensity[right_idx] > half_max:
            right_idx += 1
        
        return left_idx, right_idx
    
    def _calculate_snr(self, intensity: np.ndarray, peak_idx: int, left_idx: int, right_idx: int, window_size: int = 20) -> float:
        peak_intensity = intensity[peak_idx]
        
        noise_window = []
        start = max(0, left_idx - window_size)
        end = min(len(intensity), right_idx + window_size)
        
        for i in range(start, left_idx):
            noise_window.append(intensity[i])
        for i in range(right_idx, end):
            noise_window.append(intensity[i])
        
        if len(noise_window) == 0:
            noise_window = intensity[max(0, peak_idx - window_size):min(len(intensity), peak_idx + window_size)]
        
        noise_std = np.std(noise_window) if len(noise_window) > 1 else 1.0
        
        return peak_intensity / (noise_std + 1e-10)
    
    def get_peaks_array(self) -> np.ndarray:
        if self.peaks is None:
            raise ValueError("Peaks not detected. Run detect() first.")
        
        return np.array([(p["mz"], p["intensity"]) for p in self.peaks])
    
    def filter_peaks_by_intensity(self, min_intensity: float = None, max_intensity: float = None) -> List[Dict]:
        if self.peaks is None:
            raise ValueError("Peaks not detected. Run detect() first.")
        
        filtered = self.peaks
        if min_intensity is not None:
            filtered = [p for p in filtered if p["intensity"] >= min_intensity]
        if max_intensity is not None:
            filtered = [p for p in filtered if p["intensity"] <= max_intensity]
        
        return filtered
    
    def filter_peaks_by_snr(self, min_snr: float) -> List[Dict]:
        if self.peaks is None:
            raise ValueError("Peaks not detected. Run detect() first.")
        
        return [p for p in self.peaks if p["snr"] >= min_snr]
