import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict


class SpectralLibrary:
    def __init__(self, tolerance: float = 0.02, tolerance_type: str = "Da"):
        self.tolerance = tolerance
        self.tolerance_type = tolerance_type
        self.library: Dict[str, List[Dict]] = defaultdict(list)
        self.entries: List[Dict] = []
    
    def add_entry(self, name: str, precursor_mz: float, peaks: List[Tuple[float, float]],
                  charge: int = 1, protein: str = "", sequence: str = "", modifications: str = "") -> None:
        entry = {
            "name": name,
            "precursor_mz": precursor_mz,
            "peaks": sorted(peaks, key=lambda x: x[0]),
            "charge": charge,
            "protein": protein,
            "sequence": sequence,
            "modifications": modifications
        }
        self.entries.append(entry)
        self.library[name].append(entry)
    
    def add_peptide_library(self, entries: List[Dict]) -> None:
        for entry in entries:
            self.add_entry(**entry)
    
    def search_spectrum(self, mz: np.ndarray, intensity: np.ndarray,
                        precursor_mz: Optional[float] = None,
                        precursor_charge: Optional[int] = None,
                        top_n: int = 5) -> List[Dict]:
        spectrum_peaks = list(zip(mz, intensity))
        spectrum_peaks = sorted(spectrum_peaks, key=lambda x: x[1], reverse=True)[:200]
        spectrum_peaks = sorted(spectrum_peaks, key=lambda x: x[0])
        
        candidates = self._filter_candidates(precursor_mz, precursor_charge)
        scores = []
        
        for i, entry in enumerate(candidates):
            score = self._calculate_similarity(spectrum_peaks, entry["peaks"])
            scores.append({
                "entry": entry,
                "score": score,
                "rank": 0
            })
        
        scores.sort(key=lambda x: x["score"], reverse=True)
        for i, s in enumerate(scores):
            s["rank"] = i + 1
        
        return scores[:top_n]
    
    def _filter_candidates(self, precursor_mz: Optional[float], 
                           precursor_charge: Optional[int]) -> List[Dict]:
        candidates = self.entries
        
        if precursor_charge is not None:
            candidates = [c for c in candidates if c["charge"] == precursor_charge]
        
        if precursor_mz is not None:
            window = 10.0 if self.tolerance_type == "Da" else 50.0
            if self.tolerance_type == "Da":
                candidates = [c for c in candidates 
                             if abs(c["precursor_mz"] - precursor_mz) < window]
            else:
                candidates = [c for c in candidates 
                             if abs((c["precursor_mz"] - precursor_mz) / precursor_mz * 1e6) < window]
        
        return candidates
    
    def _calculate_similarity(self, peaks1: List[Tuple[float, float]], 
                               peaks2: List[Tuple[float, float]]) -> float:
        if not peaks1 or not peaks2:
            return 0.0
        
        mz1 = np.array([p[0] for p in peaks1])
        int1 = np.array([p[1] for p in peaks1])
        mz2 = np.array([p[0] for p in peaks2])
        int2 = np.array([p[1] for p in peaks2])
        
        if np.sum(int1) > 0:
            int1 = int1 / np.max(int1)
        if np.sum(int2) > 0:
            int2 = int2 / np.max(int2)
        
        matching_intensity = 0.0
        used_indices = set()
        
        for i, mz in enumerate(mz1):
            diffs = np.abs(mz2 - mz)
            if self.tolerance_type == "ppm":
                diffs = diffs / mz * 1e6
            
            min_idx = np.argmin(diffs)
            if diffs[min_idx] < self.tolerance and min_idx not in used_indices:
                matching_intensity += int1[i] * int2[min_idx]
                used_indices.add(min_idx)
        
        dot_product = matching_intensity
        norm1 = np.sqrt(np.sum(int1 ** 2))
        norm2 = np.sqrt(np.sum(int2 ** 2))
        
        if norm1 > 0 and norm2 > 0:
            cosine_score = dot_product / (norm1 * norm2)
        else:
            cosine_score = 0.0
        
        return cosine_score
    
    def get_library_stats(self) -> Dict:
        if not self.entries:
            return {"total_entries": 0}
        
        proteins = set(e["protein"] for e in self.entries if e["protein"])
        sequences = set(e["sequence"] for e in self.entries if e["sequence"])
        
        return {
            "total_entries": len(self.entries),
            "num_proteins": len(proteins),
            "num_sequences": len(sequences),
            "charge_distribution": self._get_charge_distribution()
        }
    
    def _get_charge_distribution(self) -> Dict[int, int]:
        dist = defaultdict(int)
        for e in self.entries:
            dist[e["charge"]] += 1
        return dict(dist)


class SpectralMatcher:
    def __init__(self, library: SpectralLibrary):
        self.library = library
    
    def match_ms2_spectrum(self, mz: np.ndarray, intensity: np.ndarray,
                           precursor_mz: float, precursor_charge: int,
                           score_threshold: float = 0.5) -> Dict:
        results = self.library.search_spectrum(mz, intensity, precursor_mz, precursor_charge, top_n=10)
        
        filtered = [r for r in results if r["score"] >= score_threshold]
        
        best_match = filtered[0] if filtered else None
        
        return {
            "best_match": best_match,
            "all_matches": filtered,
            "num_matches": len(filtered),
            "precursor_mz": precursor_mz,
            "precursor_charge": precursor_charge
        }
    
    def batch_match(self, spectra_list: List[Dict], score_threshold: float = 0.5) -> List[Dict]:
        results = []
        for spectrum in spectra_list:
            result = self.match_ms2_spectrum(
                spectrum["mz"], spectrum["intensity"],
                spectrum["precursor_mz"], spectrum["precursor_charge"],
                score_threshold
            )
            results.append(result)
        return results


def create_example_library() -> SpectralLibrary:
    lib = SpectralLibrary(tolerance=0.02)
    
    example_peptides = [
        {
            "name": "ACDK_2+",
            "precursor_mz": 246.1145,
            "charge": 2,
            "protein": "P01234",
            "sequence": "ACDK",
            "modifications": "",
            "peaks": [(50.5, 100), (103.05, 200), (205.1, 150), (246.11, 50)]
        },
        {
            "name": "VVLDTK_2+",
            "precursor_mz": 330.2025,
            "charge": 2,
            "protein": "P01234",
            "sequence": "VVLDTK",
            "modifications": "",
            "peaks": [(72.04, 80), (171.11, 150), (286.17, 200), (330.20, 60)]
        },
        {
            "name": "VVLDTK_3+",
            "precursor_mz": 220.4700,
            "charge": 3,
            "protein": "P01234",
            "sequence": "VVLDTK",
            "modifications": "",
            "peaks": [(72.04, 70), (114.58, 100), (220.47, 180)]
        },
        {
            "name": "DLTDYLMK_2+",
            "precursor_mz": 507.2450,
            "charge": 2,
            "protein": "Q9Y2W1",
            "sequence": "DLTDYLMK",
            "modifications": "",
            "peaks": [(133.06, 90), (248.12, 120), (363.18, 160), (507.25, 70)]
        },
        {
            "name": "EAEAELR_2+",
            "precursor_mz": 387.2080,
            "charge": 2,
            "protein": "P12345",
            "sequence": "EAEAELR",
            "modifications": "",
            "peaks": [(102.05, 85), (203.10, 110), (304.16, 140), (387.21, 65)]
        },
        {
            "name": "ACDK_pS_2+",
            "precursor_mz": 286.0915,
            "charge": 2,
            "protein": "P01234",
            "sequence": "ACDK",
            "modifications": "S(phospho)",
            "peaks": [(50.5, 90), (103.05, 180), (245.08, 130), (286.09, 45)]
        },
        {
            "name": "VVLDTK_acK_2+",
            "precursor_mz": 351.2188,
            "charge": 2,
            "protein": "P01234",
            "sequence": "VVLDTK",
            "modifications": "K(acetyl)",
            "peaks": [(72.04, 75), (171.11, 140), (307.19, 190), (351.22, 55)]
        }
    ]
    
    for peptide in example_peptides:
        lib.add_entry(**peptide)
    
    return lib
