import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict


class PeakAligner:
    def __init__(self, tolerance: float = 0.01, tolerance_type: str = "absolute"):
        self.tolerance = tolerance
        self.tolerance_type = tolerance_type
        self.aligned_peaks = None
        self.peak_groups = None
    
    def align(self, peaks_list: List[List[Dict]], method: str = "single_linkage") -> List[Dict]:
        if len(peaks_list) == 0:
            return []
        
        all_peaks = []
        for spectrum_idx, peaks in enumerate(peaks_list):
            for peak in peaks:
                all_peaks.append({
                    "mz": peak["mz"],
                    "intensity": peak["intensity"],
                    "spectrum_idx": spectrum_idx,
                    "original_peak": peak
                })
        
        all_peaks.sort(key=lambda x: x["mz"])
        
        if method == "single_linkage":
            peak_groups = self._single_linkage_clustering(all_peaks)
        elif method == "greedy":
            peak_groups = self._group_peaks(all_peaks)
        else:
            raise ValueError(f"Unknown alignment method: {method}")
        
        aligned_peaks = []
        for group in peak_groups:
            group_mz = np.mean([p["mz"] for p in group])
            group_intensities = {}
            for p in group:
                group_intensities[p["spectrum_idx"]] = p["intensity"]
            
            aligned_peaks.append({
                "mz": group_mz,
                "intensities": group_intensities,
                "peak_count": len(group),
                "peaks": group,
                "spectra_count": len(set(p["spectrum_idx"] for p in group))
            })
        
        self.peak_groups = peak_groups
        self.aligned_peaks = aligned_peaks
        return aligned_peaks
    
    def _single_linkage_clustering(self, all_peaks: List[Dict]) -> List[List[Dict]]:
        if not all_peaks:
            return []
        
        n = len(all_peaks)
        parent = list(range(n))
        rank = [0] * n
        
        def find(u):
            while parent[u] != u:
                parent[u] = parent[parent[u]]
                u = parent[u]
            return u
        
        def union(u, v):
            u_root = find(u)
            v_root = find(v)
            if u_root == v_root:
                return
            if rank[u_root] < rank[v_root]:
                parent[u_root] = v_root
            else:
                parent[v_root] = u_root
                if rank[u_root] == rank[v_root]:
                    rank[u_root] += 1
        
        window_size = self._get_window_size()
        j_start = 0
        
        for i in range(n):
            current_mz = all_peaks[i]["mz"]
            
            while j_start < i and current_mz - all_peaks[j_start]["mz"] > window_size:
                j_start += 1
            
            for j in range(j_start, i):
                if self._is_within_tolerance(current_mz, all_peaks[j]["mz"]):
                    union(i, j)
        
        clusters = defaultdict(list)
        for i in range(n):
            root = find(i)
            clusters[root].append(all_peaks[i])
        
        return list(clusters.values())
    
    def _get_window_size(self) -> float:
        if self.tolerance_type == "absolute":
            return self.tolerance * 2
        else:
            return 10.0
    
    def _group_peaks(self, all_peaks: List[Dict]) -> List[List[Dict]]:
        if not all_peaks:
            return []
        
        groups = []
        current_group = [all_peaks[0]]
        
        for peak in all_peaks[1:]:
            current_mz = np.mean([p["mz"] for p in current_group])
            
            if self._is_within_tolerance(current_mz, peak["mz"]):
                current_group.append(peak)
            else:
                groups.append(current_group)
                current_group = [peak]
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _is_within_tolerance(self, mz1: float, mz2: float) -> bool:
        diff = abs(mz1 - mz2)
        
        if self.tolerance_type == "absolute":
            return diff <= self.tolerance
        elif self.tolerance_type == "ppm":
            mean_mz = (mz1 + mz2) / 2.0
            ppm_diff = (diff / mean_mz) * 1e6
            return ppm_diff <= self.tolerance
        else:
            raise ValueError(f"Unknown tolerance type: {self.tolerance_type}")
    
    def get_consensus_peaks(self, min_spectra: int = 1) -> List[Dict]:
        if self.aligned_peaks is None:
            raise ValueError("Peaks not aligned. Run align() first.")
        
        return [p for p in self.aligned_peaks if p["spectra_count"] >= min_spectra]
    
    def get_intensity_matrix(self) -> Tuple[np.ndarray, np.ndarray]:
        if self.aligned_peaks is None:
            raise ValueError("Peaks not aligned. Run align() first.")
        
        num_spectra = max([max(p["intensities"].keys()) for p in self.aligned_peaks], default=-1) + 1
        num_peaks = len(self.aligned_peaks)
        
        mz_array = np.array([p["mz"] for p in self.aligned_peaks])
        intensity_matrix = np.zeros((num_spectra, num_peaks))
        
        for peak_idx, peak in enumerate(self.aligned_peaks):
            for spec_idx, intensity in peak["intensities"].items():
                intensity_matrix[spec_idx, peak_idx] = intensity
        
        return mz_array, intensity_matrix
    
    def align_single_spectrum(self, peaks: List[Dict], reference_mz: np.ndarray) -> Dict:
        aligned = {}
        
        for peak in peaks:
            peak_mz = peak["mz"]
            diffs = np.abs(reference_mz - peak_mz)
            
            if self.tolerance_type == "ppm":
                mean_mz = (reference_mz + peak_mz) / 2.0
                ppm_diffs = (diffs / mean_mz) * 1e6
                within_tolerance = ppm_diffs <= self.tolerance
            else:
                within_tolerance = diffs <= self.tolerance
            
            if np.any(within_tolerance):
                closest_idx = np.argmin(diffs)
                aligned[closest_idx] = peak
        
        return aligned


class SpectrumAligner:
    def __init__(self, method: str = "single_linkage", tolerance: float = 0.01):
        self.method = method
        self.tolerance = tolerance
    
    def align_spectra(self, mz_list: List[np.ndarray], intensity_list: List[np.ndarray]) -> Tuple[np.ndarray, List[np.ndarray]]:
        if len(mz_list) == 0:
            return np.array([]), []
        
        if self.method == "single_linkage":
            return self._single_linkage_alignment(mz_list, intensity_list)
        elif self.method == "reference":
            return self._reference_based_alignment(mz_list, intensity_list, 0)
        else:
            raise ValueError(f"Unknown alignment method: {self.method}")
    
    def _single_linkage_alignment(self, mz_list: List[np.ndarray], 
                                   intensity_list: List[np.ndarray]) -> Tuple[np.ndarray, List[np.ndarray]]:
        all_points = []
        for spec_idx, (mz, intensity) in enumerate(zip(mz_list, intensity_list)):
            for i in range(len(mz)):
                all_points.append({
                    "mz": mz[i],
                    "intensity": intensity[i],
                    "spec_idx": spec_idx,
                    "point_idx": i
                })
        
        all_points.sort(key=lambda x: x["mz"])
        n = len(all_points)
        
        if n == 0:
            return np.array([]), []
        
        parent = list(range(n))
        rank = [0] * n
        
        def find(u):
            while parent[u] != u:
                parent[u] = parent[parent[u]]
                u = parent[u]
            return u
        
        def union(u, v):
            u_root = find(u)
            v_root = find(v)
            if u_root == v_root:
                return
            if rank[u_root] < rank[v_root]:
                parent[u_root] = v_root
            else:
                parent[v_root] = u_root
                if rank[u_root] == rank[v_root]:
                    rank[u_root] += 1
        
        window_size = self.tolerance * 2
        j_start = 0
        
        for i in range(n):
            current_mz = all_points[i]["mz"]
            
            while j_start < i and current_mz - all_points[j_start]["mz"] > window_size:
                j_start += 1
            
            for j in range(j_start, i):
                if abs(current_mz - all_points[j]["mz"]) <= self.tolerance:
                    union(i, j)
        
        clusters = defaultdict(list)
        for i in range(n):
            root = find(i)
            clusters[root].append(all_points[i])
        
        aligned_mz = []
        for cluster in clusters.values():
            aligned_mz.append(np.mean([p["mz"] for p in cluster]))
        aligned_mz = np.sort(aligned_mz)
        
        aligned_intensities = []
        for spec_idx in range(len(mz_list)):
            aligned = np.zeros_like(aligned_mz)
            for peak_idx, target_mz in enumerate(aligned_mz):
                best_intensity = 0.0
                for cluster in clusters.values():
                    cluster_mz = np.mean([p["mz"] for p in cluster])
                    if abs(cluster_mz - target_mz) < 1e-6:
                        for p in cluster:
                            if p["spec_idx"] == spec_idx:
                                best_intensity = max(best_intensity, p["intensity"])
                aligned[peak_idx] = best_intensity
            aligned_intensities.append(aligned)
        
        return aligned_mz, aligned_intensities
    
    def _reference_based_alignment(self, mz_list: List[np.ndarray], intensity_list: List[np.ndarray], reference_idx: int) -> Tuple[np.ndarray, List[np.ndarray]]:
        ref_mz = mz_list[reference_idx]
        ref_intensity = intensity_list[reference_idx]
        
        aligned_intensities = []
        
        for mz, intensity in zip(mz_list, intensity_list):
            aligned = np.zeros_like(ref_mz)
            
            for i, target_mz in enumerate(ref_mz):
                diffs = np.abs(mz - target_mz)
                closest_idx = np.argmin(diffs)
                if diffs[closest_idx] <= self.tolerance:
                    aligned[i] = intensity[closest_idx]
            
            aligned_intensities.append(aligned)
        
        return ref_mz, aligned_intensities
