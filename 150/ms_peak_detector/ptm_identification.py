import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict


class PTMDatabase:
    def __init__(self):
        self.modifications = self._get_standard_modifications()
    
    def _get_standard_modifications(self) -> Dict[str, Dict]:
        return {
            "phosphorylation": {
                "mass_shift": 79.966331,
                "amino_acids": ["S", "T", "Y"],
                "symbol": "p",
                "name": "Phosphorylation"
            },
            "acetylation": {
                "mass_shift": 42.010565,
                "amino_acids": ["K", "N-term"],
                "symbol": "ac",
                "name": "Acetylation"
            },
            "methylation": {
                "mass_shift": 14.015650,
                "amino_acids": ["K", "R"],
                "symbol": "me",
                "name": "Methylation"
            },
            "dimethylation": {
                "mass_shift": 28.031300,
                "amino_acids": ["K", "R"],
                "symbol": "me2",
                "name": "Dimethylation"
            },
            "trimethylation": {
                "mass_shift": 42.046950,
                "amino_acids": ["K"],
                "symbol": "me3",
                "name": "Trimethylation"
            },
            "ubiquitination": {
                "mass_shift": 114.042927,
                "amino_acids": ["K"],
                "symbol": "ub",
                "name": "Ubiquitination"
            },
            "sumoylation": {
                "mass_shift": 485.215550,
                "amino_acids": ["K"],
                "symbol": "sumo",
                "name": "Sumoylation"
            },
            "glycosylation_N": {
                "mass_shift": 203.079373,
                "amino_acids": ["N"],
                "symbol": "glycN",
                "name": "N-linked Glycosylation"
            },
            "glycosylation_O": {
                "mass_shift": 162.052824,
                "amino_acids": ["S", "T"],
                "symbol": "glycO",
                "name": "O-linked Glycosylation"
            },
            "oxidation": {
                "mass_shift": 15.994915,
                "amino_acids": ["M", "C"],
                "symbol": "ox",
                "name": "Oxidation"
            },
            "nitrosylation": {
                "mass_shift": 29.994441,
                "amino_acids": ["C"],
                "symbol": "no",
                "name": "Nitrosylation"
            },
            "palmitoylation": {
                "mass_shift": 238.229666,
                "amino_acids": ["C"],
                "symbol": "palm",
                "name": "Palmitoylation"
            },
            "myristoylation": {
                "mass_shift": 210.198366,
                "amino_acids": ["N-term"],
                "symbol": "myr",
                "name": "Myristoylation"
            },
            "hydroxylation": {
                "mass_shift": 15.994915,
                "amino_acids": ["P", "K", "D", "N"],
                "symbol": "oh",
                "name": "Hydroxylation"
            },
            "carboxylation": {
                "mass_shift": 43.989829,
                "amino_acids": ["E"],
                "symbol": "co2",
                "name": "Carboxylation"
            },
            "amidation": {
                "mass_shift": -0.984016,
                "amino_acids": ["C-term"],
                "symbol": "am",
                "name": "Amidation"
            }
        }
    
    def get_modification(self, name: str) -> Optional[Dict]:
        return self.modifications.get(name)
    
    def search_modifications_by_mass(self, mass_shift: float, tolerance: float = 0.02) -> List[Dict]:
        matches = []
        for name, mod in self.modifications.items():
            if abs(mod["mass_shift"] - mass_shift) <= tolerance:
                matches.append({
                    "name": name,
                    "mass_shift": mod["mass_shift"],
                    "amino_acids": mod["amino_acids"],
                    "symbol": mod["symbol"]
                })
        return matches
    
    def get_all_modifications(self) -> List[Dict]:
        return [{"name": k, **v} for k, v in self.modifications.items()]


class PeptideFragmenter:
    def __init__(self):
        self.aa_masses = self._get_amino_acid_masses()
    
    def _get_amino_acid_masses(self) -> Dict[str, float]:
        return {
            'A': 71.037114, 'R': 156.101111, 'N': 114.042927,
            'D': 115.026943, 'C': 103.009185, 'E': 129.042593,
            'Q': 128.058578, 'G': 57.021464, 'H': 137.058942,
            'I': 113.084064, 'L': 113.084064, 'K': 128.094963,
            'M': 131.040485, 'F': 147.068414, 'P': 97.052764,
            'S': 87.032028, 'T': 101.047679, 'W': 186.079313,
            'Y': 163.063329, 'V': 99.068414
        }
    
    def fragment_peptide(self, sequence: str, charge: int = 1, 
                         modifications: Optional[List[Dict]] = None) -> Dict:
        if modifications is None:
            modifications = []
        
        seq_masses = [self.aa_masses.get(aa, 0.0) for aa in sequence]
        
        for mod in modifications:
            pos = mod.get("position", -1)
            if 0 <= pos < len(seq_masses):
                seq_masses[pos] += mod.get("mass_shift", 0.0)
        
        n_term_mass = 1.007825
        c_term_mass = 17.002740
        proton_mass = 1.007825
        
        b_ions = []
        cumulative = n_term_mass
        for i in range(len(seq_masses)):
            cumulative += seq_masses[i]
            for z in range(1, charge + 1):
                b_ions.append({
                    "type": "b",
                    "position": i + 1,
                    "charge": z,
                    "mz": (cumulative + z * proton_mass) / z
                })
        
        y_ions = []
        cumulative = c_term_mass
        for i in range(len(seq_masses) - 1, -1, -1):
            cumulative += seq_masses[i]
            for z in range(1, charge + 1):
                y_ions.append({
                    "type": "y",
                    "position": len(seq_masses) - i,
                    "charge": z,
                    "mz": (cumulative + z * proton_mass) / z
                })
        
        precursor_mass = n_term_mass + sum(seq_masses) + c_term_mass
        precursor_mz = (precursor_mass + charge * proton_mass) / charge
        
        return {
            "sequence": sequence,
            "charge": charge,
            "precursor_mz": precursor_mz,
            "precursor_mass": precursor_mass,
            "b_ions": b_ions,
            "y_ions": y_ions,
            "modifications": modifications
        }


class PTMIdentifier:
    def __init__(self, tolerance: float = 0.02):
        self.tolerance = tolerance
        self.ptm_db = PTMDatabase()
        self.fragmenter = PeptideFragmenter()
    
    def identify_ptms(self, mz: np.ndarray, intensity: np.ndarray,
                      sequence: str, charge: int = 2,
                      mods_to_check: Optional[List[str]] = None) -> List[Dict]:
        if mods_to_check is None:
            mods_to_check = list(self.ptm_db.modifications.keys())
        
        unmodified_fragments = self.fragmenter.fragment_peptide(sequence, charge)
        unmodified_score = self._score_match(mz, intensity, unmodified_fragments)
        
        ptm_results = []
        
        for mod_name in mods_to_check:
            mod_info = self.ptm_db.get_modification(mod_name)
            if not mod_info:
                continue
            
            for aa in mod_info["amino_acids"]:
                if aa in ["N-term", "C-term"]:
                    continue
                
                positions = [i for i, char in enumerate(sequence) if char == aa]
                
                for pos in positions:
                    modification = {
                        "name": mod_name,
                        "position": pos,
                        "amino_acid": aa,
                        "mass_shift": mod_info["mass_shift"],
                        "symbol": mod_info["symbol"]
                    }
                    
                    modified_fragments = self.fragmenter.fragment_peptide(
                        sequence, charge, [modification]
                    )
                    modified_score = self._score_match(mz, intensity, modified_fragments)
                    
                    delta_score = modified_score - unmodified_score
                    
                    ptm_results.append({
                        "modification": modification,
                        "unmodified_score": unmodified_score,
                        "modified_score": modified_score,
                        "delta_score": delta_score,
                        "score_ratio": modified_score / (unmodified_score + 1e-10),
                        "fragments": modified_fragments
                    })
        
        ptm_results.sort(key=lambda x: x["delta_score"], reverse=True)
        
        return ptm_results
    
    def _score_match(self, mz: np.ndarray, intensity: np.ndarray, 
                     fragments: Dict) -> float:
        all_ions = fragments["b_ions"] + fragments["y_ions"]
        ion_mz_list = [ion["mz"] for ion in all_ions]
        
        if np.max(intensity) > 0:
            intensity_norm = intensity / np.max(intensity)
        else:
            intensity_norm = intensity
        
        score = 0.0
        for i, m in enumerate(mz):
            diffs = np.abs(np.array(ion_mz_list) - m)
            min_diff = np.min(diffs)
            if min_diff <= self.tolerance:
                score += intensity_norm[i]
        
        return score
    
    def search_delta_mass(self, mz: np.ndarray, intensity: np.ndarray,
                          theoretical_mz: np.ndarray, min_intensity_ratio: float = 0.1) -> List[Dict]:
        delta_masses = []
        
        max_intensity = np.max(intensity)
        significant_peaks = [(m, i) for m, i in zip(mz, intensity) 
                           if i >= max_intensity * min_intensity_ratio]
        
        for exp_mz, exp_int in significant_peaks:
            for theo_mz in theoretical_mz:
                delta = exp_mz - theo_mz
                if abs(delta) > 10.0:
                    matching_mods = self.ptm_db.search_modifications_by_mass(
                        abs(delta), self.tolerance
                    )
                    if matching_mods:
                        delta_masses.append({
                            "delta_mass": delta,
                            "intensity": exp_int,
                            "matching_modifications": matching_mods
                        })
        
        delta_masses.sort(key=lambda x: x["intensity"], reverse=True)
        return delta_masses
    
    def get_localization_score(self, sequence: str, position: int,
                               mz: np.ndarray, intensity: np.ndarray,
                               mod_mass: float, charge: int = 2) -> Dict:
        mod_info = {"position": position, "mass_shift": mod_mass}
        fragments = self.fragmenter.fragment_peptide(sequence, charge, [mod_info])
        
        expected_modified_ions = []
        for ion in fragments["b_ions"]:
            if ion["position"] > position:
                expected_modified_ions.append(ion)
        
        for ion in fragments["y_ions"]:
            if ion["position"] > len(sequence) - position - 1:
                expected_modified_ions.append(ion)
        
        matched = 0
        matched_intensity = 0.0
        for ion in expected_modified_ions:
            diffs = np.abs(mz - ion["mz"])
            min_idx = np.argmin(diffs)
            if diffs[min_idx] <= self.tolerance:
                matched += 1
                matched_intensity += intensity[min_idx]
        
        localization_score = matched / len(expected_modified_ions) if expected_modified_ions else 0.0
        
        return {
            "localization_score": localization_score,
            "matched_ions": matched,
            "total_expected_ions": len(expected_modified_ions),
            "matched_intensity": matched_intensity
        }
