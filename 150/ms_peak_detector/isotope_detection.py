import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict


class IsotopeDetector:
    def __init__(self, tolerance: float = 0.01, tolerance_type: str = "absolute"):
        self.tolerance = tolerance
        self.tolerance_type = tolerance_type
        self.isotope_patterns = None
        
        self.C13_MASS_DIFF = 1.0033548378
        self.N15_MASS_DIFF = 0.997034886
        self.O18_MASS_DIFF = 2.004244986
        self.S34_MASS_DIFF = 1.995795886
        
        self.theoretical_c13_ratio = 0.0108  # 理论C13/C12比值
    
    def detect_isotopes(self, peaks: List[Dict], 
                        min_charge: int = 1, 
                        max_charge: int = 5,
                        min_score: float = 0.3) -> List[Dict]:
        if len(peaks) == 0:
            return []
        
        peaks_sorted = sorted(peaks, key=lambda x: x["mz"])
        
        all_candidates = []
        used_indices = set()
        
        for charge in range(min_charge, max_charge + 1):
            for i, peak in enumerate(peaks_sorted):
                if i in used_indices:
                    continue
                
                cluster = self._find_isotope_cluster(peaks_sorted, i, charge)
                
                if cluster["size"] >= 2:
                    cluster = self._score_isotope_cluster(cluster)
                    all_candidates.append(cluster)
        
        all_candidates.sort(key=lambda x: x["score"], reverse=True)
        
        final_clusters = []
        for candidate in all_candidates:
            if candidate["score"] >= min_score:
                overlap = False
                for idx in candidate["indices"]:
                    if idx in used_indices:
                        overlap = True
                        break
                
                if not overlap:
                    for idx in candidate["indices"]:
                        used_indices.add(idx)
                    final_clusters.append(candidate)
        
        self.isotope_patterns = final_clusters
        return final_clusters
    
    def _find_isotope_cluster(self, peaks: List[Dict], start_idx: int, charge: int) -> Dict:
        base_peak = peaks[start_idx]
        base_mz = base_peak["mz"]
        base_intensity = base_peak["intensity"]
        
        cluster = {
            "monoisotopic_mz": base_mz,
            "monoisotopic_intensity": base_intensity,
            "charge": charge,
            "peaks": [base_peak],
            "indices": [start_idx],
            "isotope_ratios": {},
            "isotope_types": []
        }
        
        expected_diffs = [
            (self.C13_MASS_DIFF / charge, "C13"),
            (self.N15_MASS_DIFF / charge, "N15"),
            (self.O18_MASS_DIFF / charge, "O18"),
            (self.S34_MASS_DIFF / charge, "S34"),
        ]
        
        i = start_idx + 1
        while i < len(peaks):
            current_mz = peaks[i]["mz"]
            diff = current_mz - base_mz
            
            if diff > self._get_max_expected_diff(charge):
                break
            
            matched_isotope = None
            min_error = float('inf')
            
            for expected_diff, isotope_name in expected_diffs:
                if self._is_within_tolerance(diff, expected_diff):
                    error = abs(diff - expected_diff)
                    if error < min_error:
                        min_error = error
                        matched_isotope = isotope_name
            
            if matched_isotope:
                cluster["peaks"].append(peaks[i])
                cluster["indices"].append(i)
                ratio = peaks[i]["intensity"] / base_intensity
                cluster["isotope_ratios"][matched_isotope] = ratio
                cluster["isotope_types"].append(matched_isotope)
            
            i += 1
        
        cluster["size"] = len(cluster["peaks"])
        
        return cluster
    
    def _score_isotope_cluster(self, cluster: Dict) -> Dict:
        score = 0.0
        
        size_score = min(cluster["size"] / 5.0, 1.0)
        score += 0.3 * size_score
        
        charge = cluster["charge"]
        charge_penalty = max(0, 1.0 - (charge - 1) * 0.1)
        score += 0.2 * charge_penalty
        
        ratio_score = 0.0
        if "C13" in cluster["isotope_ratios"]:
            actual_ratio = cluster["isotope_ratios"]["C13"]
            expected_ratio = charge * self.theoretical_c13_ratio
            ratio_error = abs(actual_ratio - expected_ratio) / expected_ratio
            ratio_score = max(0, 1.0 - ratio_error)
        score += 0.3 * ratio_score
        
        intensity_decrease_score = 1.0
        if cluster["size"] > 2:
            intensities = [p["intensity"] for p in cluster["peaks"]]
            for i in range(1, len(intensities)):
                if intensities[i] > intensities[i-1]:
                    intensity_decrease_score -= 0.2
        intensity_decrease_score = max(0, intensity_decrease_score)
        score += 0.2 * intensity_decrease_score
        
        cluster["score"] = score
        cluster["score_components"] = {
            "size_score": size_score,
            "charge_penalty": charge_penalty,
            "ratio_score": ratio_score,
            "intensity_decrease_score": intensity_decrease_score
        }
        
        return cluster
    
    def validate_charge_state(self, cluster: Dict, expected_max_charge: int = 5) -> bool:
        charge = cluster["charge"]
        
        if charge < 1 or charge > expected_max_charge:
            return False
        
        if "C13" in cluster["isotope_ratios"]:
            ratio = cluster["isotope_ratios"]["C13"]
            max_expected_ratio = charge * self.theoretical_c13_ratio * 2.0
            min_expected_ratio = charge * self.theoretical_c13_ratio * 0.5
            
            if ratio < min_expected_ratio or ratio > max_expected_ratio:
                return False
        
        mz = cluster["monoisotopic_mz"]
        if mz < 100 and charge > 2:
            return False
        if mz < 200 and charge > 3:
            return False
        
        return True
    
    def filter_by_score(self, min_score: float) -> List[Dict]:
        if self.isotope_patterns is None:
            raise ValueError("Isotope patterns not detected. Run detect_isotopes() first.")
        
        return [c for c in self.isotope_patterns if c["score"] >= min_score]
    
    def _is_within_tolerance(self, diff: float, expected_diff: float) -> bool:
        actual_diff = abs(diff - expected_diff)
        
        if self.tolerance_type == "absolute":
            return actual_diff <= self.tolerance
        elif self.tolerance_type == "ppm":
            mean_mz = (diff + expected_diff) / 2.0
            ppm_diff = (actual_diff / mean_mz) * 1e6
            return ppm_diff <= self.tolerance
        else:
            raise ValueError(f"Unknown tolerance type: {self.tolerance_type}")
    
    def _get_max_expected_diff(self, charge: int) -> float:
        max_diff = max(self.C13_MASS_DIFF, self.N15_MASS_DIFF, self.O18_MASS_DIFF, self.S34_MASS_DIFF)
        return (max_diff * 5 / charge) + self.tolerance * 2
    
    def detect_monoisotopic_peaks(self, peaks: List[Dict]) -> List[Dict]:
        peaks_sorted = sorted(peaks, key=lambda x: x["mz"])
        
        monoisotopic = []
        n = len(peaks_sorted)
        
        for i in range(n):
            current_mz = peaks_sorted[i]["mz"]
            current_intensity = peaks_sorted[i]["intensity"]
            
            is_monoisotopic = True
            
            for j in range(max(0, i - 5), i):
                prev_mz = peaks_sorted[j]["mz"]
                prev_intensity = peaks_sorted[j]["intensity"]
                diff = current_mz - prev_mz
                
                if abs(diff - self.C13_MASS_DIFF) < self.tolerance:
                    if prev_intensity > current_intensity * 0.5:
                        is_monoisotopic = False
                        break
            
            if is_monoisotopic:
                monoisotopic.append(peaks_sorted[i])
        
        return monoisotopic
    
    def calculate_theoretical_isotope_distribution(self, formula: str) -> Dict:
        element_counts = self._parse_formula(formula)
        
        distribution = {0: 1.0}
        
        for element, count in element_counts.items():
            element_isotopes = self._get_element_isotopes(element)
            if element_isotopes and count > 0:
                distribution = self._convolve_distributions(distribution, element_isotopes, count)
        
        total = sum(distribution.values())
        normalized = {k: v / total for k, v in distribution.items()}
        
        return {
            "distribution": normalized,
            "masses": [k * self.C13_MASS_DIFF for k in normalized.keys()],
            "abundances": list(normalized.values())
        }
    
    def _parse_formula(self, formula: str) -> Dict[str, int]:
        counts = defaultdict(int)
        
        i = 0
        n = len(formula)
        
        while i < n:
            if formula[i].isupper():
                element = formula[i]
                i += 1
                
                while i < n and formula[i].islower():
                    element += formula[i]
                    i += 1
                
                num_str = ""
                while i < n and formula[i].isdigit():
                    num_str += formula[i]
                    i += 1
                
                count = int(num_str) if num_str else 1
                counts[element] += count
            else:
                i += 1
        
        return dict(counts)
    
    def _get_element_isotopes(self, element: str) -> Optional[Dict[int, float]]:
        isotope_data = {
            "C": {0: 0.9893, 1: 0.0107},
            "H": {0: 0.999885, 1: 0.000115},
            "N": {0: 0.99632, 1: 0.00368},
            "O": {0: 0.99757, 1: 0.00038, 2: 0.00205},
            "S": {0: 0.9493, 1: 0.0076, 2: 0.0429, 4: 0.0002},
            "P": {0: 1.0},
            "Cl": {0: 0.7577, 2: 0.2423},
            "Br": {0: 0.5069, 2: 0.4931},
        }
        
        return isotope_data.get(element)
    
    def _convolve_distributions(self, dist1: Dict[int, float], dist2: Dict[int, float], count: int) -> Dict[int, float]:
        result = dist1.copy()
        
        for _ in range(count):
            new_dist = defaultdict(float)
            for k1, v1 in result.items():
                for k2, v2 in dist2.items():
                    new_dist[k1 + k2] += v1 * v2
            result = dict(new_dist)
        
        return result
    
    def get_isotope_clusters(self) -> List[Dict]:
        if self.isotope_patterns is None:
            raise ValueError("Isotope patterns not detected. Run detect_isotopes() first.")
        
        return self.isotope_patterns
    
    def filter_clusters_by_size(self, min_size: int = 2) -> List[Dict]:
        if self.isotope_patterns is None:
            raise ValueError("Isotope patterns not detected. Run detect_isotopes() first.")
        
        return [c for c in self.isotope_patterns if c["size"] >= min_size]
    
    def filter_valid_clusters(self, min_score: float = 0.3, expected_max_charge: int = 5) -> List[Dict]:
        if self.isotope_patterns is None:
            raise ValueError("Isotope patterns not detected. Run detect_isotopes() first.")
        
        valid_clusters = []
        for cluster in self.isotope_patterns:
            if cluster["score"] >= min_score and self.validate_charge_state(cluster, expected_max_charge):
                valid_clusters.append(cluster)
        
        return valid_clusters
