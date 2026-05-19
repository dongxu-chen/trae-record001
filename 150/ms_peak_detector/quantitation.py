import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict


class ReporterIonQuantitation:
    def __init__(self, tolerance: float = 0.02):
        self.tolerance = tolerance
        self.reporter_ions = {
            "TMT_6plex": {
                "TMT126": 126.127726,
                "TMT127": 127.124761,
                "TMT128": 128.134436,
                "TMT129": 129.131471,
                "TMT130": 130.141145,
                "TMT131": 131.138180
            },
            "TMT_10plex": {
                "TMT126": 126.127726,
                "TMT127N": 127.124761,
                "TMT127C": 127.131081,
                "TMT128N": 128.128116,
                "TMT128C": 128.134436,
                "TMT129N": 129.131471,
                "TMT129C": 129.137790,
                "TMT130N": 130.134825,
                "TMT130C": 130.141145,
                "TMT131": 131.138180
            },
            "TMT_16plex": {
                "TMT126": 126.127726,
                "TMT127N": 127.124761,
                "TMT127C": 127.131081,
                "TMT128N": 128.128116,
                "TMT128C": 128.134436,
                "TMT129N": 129.131471,
                "TMT129C": 129.137790,
                "TMT130N": 130.134825,
                "TMT130C": 130.141145,
                "TMT131N": 131.138180,
                "TMT131C": 131.144500,
                "TMT132N": 132.141535,
                "TMT132C": 132.147855,
                "TMT133N": 133.144890,
                "TMT133C": 133.151210,
                "TMT134N": 134.148245
            },
            "iTRAQ_4plex": {
                "iTRAQ114": 114.1112,
                "iTRAQ115": 115.1083,
                "iTRAQ116": 116.1116,
                "iTRAQ117": 117.1087
            },
            "iTRAQ_8plex": {
                "iTRAQ113": 113.1078,
                "iTRAQ114": 114.1112,
                "iTRAQ115": 115.1083,
                "iTRAQ116": 116.1116,
                "iTRAQ117": 117.1087,
                "iTRAQ118": 118.1120,
                "iTRAQ119": 119.1091,
                "iTRAQ121": 121.1151
            }
        }
    
    def get_reporter_ions(self, kit: str = "TMT_10plex") -> Dict[str, float]:
        return self.reporter_ions.get(kit, {})
    
    def quantitate_spectrum(self, mz: np.ndarray, intensity: np.ndarray,
                            kit: str = "TMT_10plex",
                            method: str = "max") -> Dict[str, float]:
        reporters = self.get_reporter_ions(kit)
        if not reporters:
            return {}
        
        results = {}
        for name, reporter_mz in reporters.items():
            diffs = np.abs(mz - reporter_mz)
            within_tolerance = diffs <= self.tolerance
            
            if not np.any(within_tolerance):
                results[name] = 0.0
                continue
            
            relevant_intensities = intensity[within_tolerance]
            
            if method == "max":
                results[name] = float(np.max(relevant_intensities))
            elif method == "sum":
                results[name] = float(np.sum(relevant_intensities))
            elif method == "closest":
                closest_idx = np.argmin(diffs)
                results[name] = float(intensity[closest_idx])
            else:
                results[name] = float(np.max(relevant_intensities))
        
        return results
    
    def batch_quantitate(self, spectra: List[Dict], kit: str = "TMT_10plex",
                         method: str = "max") -> List[Dict]:
        quant_results = []
        for spectrum in spectra:
            quant = self.quantitate_spectrum(
                spectrum["mz"], spectrum["intensity"], kit, method
            )
            quant_results.append({
                "spectrum_id": spectrum.get("id", ""),
                "quantitation": quant,
                "precursor_mz": spectrum.get("precursor_mz", 0.0),
                "precursor_charge": spectrum.get("precursor_charge", 0)
            })
        return quant_results


class PeptideQuantitation:
    def __init__(self):
        self.quantitation_results = []
    
    def aggregate_peptide_quantitation(self, psm_results: List[Dict],
                                       peptide_sequence_key: str = "sequence") -> Dict[str, Dict]:
        peptide_quants = defaultdict(list)
        
        for psm in psm_results:
            sequence = psm.get(peptide_sequence_key, "")
            if not sequence:
                continue
            
            quant = psm.get("quantitation", {})
            peptide_quants[sequence].append(quant)
        
        aggregated = {}
        for peptide, quants in peptide_quants.items():
            channels = list(quants[0].keys())
            aggregated[peptide] = {
                "n_psms": len(quants),
                "mean": {ch: np.mean([q[ch] for q in quants]) for ch in channels},
                "median": {ch: np.median([q[ch] for q in quants]) for ch in channels},
                "sum": {ch: np.sum([q[ch] for q in quants]) for ch in channels},
                "std": {ch: np.std([q[ch] for q in quants]) for ch in channels},
                "cv": {ch: np.std([q[ch] for q in quants]) / (np.mean([q[ch] for q in quants]) + 1e-10) 
                       for ch in channels}
            }
        
        return aggregated
    
    def normalize_quantitation(self, quant_data: Dict[str, Dict],
                               method: str = "median") -> Dict[str, Dict]:
        if method == "median":
            all_values = []
            for peptide in quant_data.values():
                all_values.extend(list(peptide["mean"].values()))
            
            median_val = np.median(all_values) if all_values else 1.0
            
            normalized = {}
            for peptide, data in quant_data.items():
                normalized[peptide] = {
                    **data,
                    "normalized_mean": {ch: val / median_val for ch, val in data["mean"].items()},
                    "normalized_median": {ch: val / median_val for ch, val in data["median"].items()}
                }
            return normalized
        
        elif method == "reference_channel":
            first_peptide = list(quant_data.keys())[0]
            first_channel = list(quant_data[first_peptide]["mean"].keys())[0]
            
            ref_values = []
            for peptide in quant_data.values():
                ref_values.append(peptide["mean"][first_channel])
            
            ref_median = np.median(ref_values) if ref_values else 1.0
            
            normalized = {}
            for peptide, data in quant_data.items():
                normalized[peptide] = {
                    **data,
                    "normalized_mean": {ch: val / ref_median for ch, val in data["mean"].items()}
                }
            return normalized
        
        return quant_data


class ProteinQuantitation:
    def __init__(self):
        pass
    
    def rollup_protein_quantitation(self, peptide_quants: Dict[str, Dict],
                                      peptide_to_protein: Dict[str, List[str]]) -> Dict[str, Dict]:
        protein_quants = defaultdict(list)
        
        for peptide, proteins in peptide_to_protein.items():
            if peptide not in peptide_quants:
                continue
            
            peptide_data = peptide_quants[peptide]
            for protein in proteins:
                protein_quants[protein].append(peptide_data)
        
        aggregated = {}
        for protein, peptide_data_list in protein_quants.items():
            channels = list(peptide_data_list[0]["mean"].keys())
            aggregated[protein] = {
                "n_peptides": len(peptide_data_list),
                "mean": {ch: np.mean([pd["mean"][ch] for pd in peptide_data_list]) for ch in channels},
                "median": {ch: np.median([pd["median"][ch] for pd in peptide_data_list]) for ch in channels},
                "sum": {ch: np.sum([pd["sum"][ch] for pd in peptide_data_list]) for ch in channels}
            }
        
        return aggregated


class RatioCalculation:
    def __init__(self):
        pass
    
    def calculate_ratios(self, quant_data: Dict[str, float],
                         reference_channel: str) -> Dict[str, float]:
        if reference_channel not in quant_data:
            return {}
        
        ref_value = quant_data[reference_channel]
        if ref_value <= 0:
            return {}
        
        ratios = {}
        for channel, value in quant_data.items():
            ratios[channel] = value / ref_value
        
        return ratios
    
    def calculate_log2_ratios(self, quant_data: Dict[str, float],
                               reference_channel: str) -> Dict[str, float]:
        ratios = self.calculate_ratios(quant_data, reference_channel)
        log2_ratios = {}
        for channel, ratio in ratios.items():
            if ratio > 0:
                log2_ratios[channel] = np.log2(ratio)
            else:
                log2_ratios[channel] = np.nan
        return log2_ratios
    
    def fold_change(self, condition1: Dict[str, float],
                     condition2: Dict[str, float]) -> Dict[str, float]:
        common_channels = set(condition1.keys()) & set(condition2.keys())
        fc = {}
        for ch in common_channels:
            if condition2[ch] > 0:
                fc[ch] = condition1[ch] / condition2[ch]
            else:
                fc[ch] = np.nan
        return fc


class QuantitationPipeline:
    def __init__(self, tolerance: float = 0.02):
        self.reporter_quant = ReporterIonQuantitation(tolerance)
        self.peptide_quant = PeptideQuantitation()
        self.protein_quant = ProteinQuantitation()
        self.ratio_calc = RatioCalculation()
    
    def run_full_quantitation(self, ms2_spectra: List[Dict],
                               psm_assignments: List[Dict],
                               peptide_to_protein: Dict[str, List[str]],
                               kit: str = "TMT_10plex",
                               reference_channel: Optional[str] = None) -> Dict:
        quantitated_spectra = self.reporter_quant.batch_quantitate(ms2_spectra, kit)
        
        psm_with_quant = []
        for qs, psm in zip(quantitated_spectra, psm_assignments):
            psm_with_quant.append({**psm, **qs})
        
        peptide_quants = self.peptide_quant.aggregate_peptide_quantitation(psm_with_quant)
        peptide_quants = self.peptide_quant.normalize_quantitation(peptide_quants)
        
        protein_quants = self.protein_quant.rollup_protein_quantitation(
            peptide_quants, peptide_to_protein
        )
        
        if reference_channel:
            for peptide in peptide_quants:
                peptide_quants[peptide]["ratios"] = self.ratio_calc.calculate_ratios(
                    peptide_quants[peptide]["mean"], reference_channel
                )
                peptide_quants[peptide]["log2_ratios"] = self.ratio_calc.calculate_log2_ratios(
                    peptide_quants[peptide]["mean"], reference_channel
                )
            
            for protein in protein_quants:
                protein_quants[protein]["ratios"] = self.ratio_calc.calculate_ratios(
                    protein_quants[protein]["mean"], reference_channel
                )
                protein_quants[protein]["log2_ratios"] = self.ratio_calc.calculate_log2_ratios(
                    protein_quants[protein]["mean"], reference_channel
                )
        
        return {
            "peptide_quantitation": peptide_quants,
            "protein_quantitation": protein_quants,
            "psm_quantitation": psm_with_quant,
            "kit": kit,
            "reference_channel": reference_channel
        }
