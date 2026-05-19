import numpy as np
from typing import List, Dict, Optional, Tuple
import matplotlib.pyplot as plt

from .core import MSPeakProcessor
from .baseline_correction import BaselineCorrector
from .peak_detection import PeakDetector
from .peak_alignment import PeakAligner
from .isotope_detection import IsotopeDetector


class MSPeakAnalysisPipeline:
    def __init__(self):
        self.processor = MSPeakProcessor()
        self.baseline_corrector = BaselineCorrector()
        self.peak_detector = PeakDetector()
        self.peak_aligner = PeakAligner()
        self.isotope_detector = IsotopeDetector()
        
        self.corrected_intensity = None
        self.detected_peaks = None
        self.aligned_peaks = None
        self.isotope_clusters = None
    
    def process_spectrum(self, mz: np.ndarray, intensity: np.ndarray, 
                        baseline_method: str = "segmented_asls",
                        peak_detection_method: str = "local_max",
                        merge_distance: float = 0.5,
                        min_isotope_score: float = 0.3,
                        min_charge: int = 1,
                        max_charge: int = 5,
                        **kwargs) -> Dict:
        corrected_intensity = self.baseline_corrector.correct(mz, intensity, method=baseline_method, **kwargs)
        self.corrected_intensity = corrected_intensity
        
        peaks = self.peak_detector.detect(mz, corrected_intensity, method=peak_detection_method, 
                                          merge_distance=merge_distance, **kwargs)
        self.detected_peaks = peaks
        
        isotope_clusters = self.isotope_detector.detect_isotopes(peaks, 
                                                                 min_charge=min_charge, 
                                                                 max_charge=max_charge,
                                                                 min_score=min_isotope_score)
        self.isotope_clusters = isotope_clusters
        
        return {
            "mz": mz,
            "original_intensity": intensity,
            "corrected_intensity": corrected_intensity,
            "baseline": self.baseline_corrector.get_baseline(),
            "peaks": peaks,
            "isotope_clusters": isotope_clusters
        }
    
    def process_multiple_spectra(self, mz_list: List[np.ndarray], 
                                 intensity_list: List[np.ndarray],
                                 alignment_method: str = "single_linkage",
                                 **kwargs) -> Dict:
        all_peaks = []
        
        for mz, intensity in zip(mz_list, intensity_list):
            corrected = self.baseline_corrector.correct(mz, intensity, **kwargs)
            peaks = self.peak_detector.detect(mz, corrected, **kwargs)
            all_peaks.append(peaks)
        
        aligned = self.peak_aligner.align(all_peaks, method=alignment_method)
        self.aligned_peaks = aligned
        
        mz_array, intensity_matrix = self.peak_aligner.get_intensity_matrix()
        
        return {
            "aligned_peaks": aligned,
            "mz_array": mz_array,
            "intensity_matrix": intensity_matrix,
            "all_peaks": all_peaks
        }
    
    def generate_test_spectrum(self, num_peaks: int = 10, 
                               mz_range: Tuple[float, float] = (100, 1000),
                               noise_level: float = 0.05,
                               baseline_slope: float = 0.001) -> Tuple[np.ndarray, np.ndarray]:
        mz = np.linspace(mz_range[0], mz_range[1], 1000)
        intensity = np.zeros_like(mz)
        
        peak_positions = np.random.uniform(mz_range[0], mz_range[1], num_peaks)
        peak_heights = np.random.uniform(0.1, 1.0, num_peaks)
        peak_widths = np.random.uniform(0.5, 2.0, num_peaks)
        
        for pos, height, width in zip(peak_positions, peak_heights, peak_widths):
            intensity += height * np.exp(-(mz - pos)**2 / (2 * width**2))
        
        baseline = baseline_slope * (mz - mz_range[0]) + 0.1
        intensity += baseline
        
        noise = np.random.normal(0, noise_level, size=len(mz))
        intensity += noise
        
        return mz, intensity
    
    def generate_isotope_pattern(self, base_mz: float, base_intensity: float,
                                  num_isotopes: int = 3, charge: int = 1) -> Tuple[np.ndarray, np.ndarray]:
        mz_points = []
        intensity_points = []
        
        for i in range(num_isotopes):
            mz = base_mz + i * self.isotope_detector.C13_MASS_DIFF / charge
            intensity = base_intensity * (0.5 ** i)
            mz_points.append(mz)
            intensity_points.append(intensity)
        
        mz = np.linspace(base_mz - 2, base_mz + num_isotopes * 1.5, 500)
        intensity = np.zeros_like(mz)
        
        for m, i in zip(mz_points, intensity_points):
            width = 0.3
            intensity += i * np.exp(-(mz - m)**2 / (2 * width**2))
        
        return mz, intensity
    
    def plot_spectrum(self, mz: np.ndarray, intensity: np.ndarray,
                      corrected_intensity: Optional[np.ndarray] = None,
                      peaks: Optional[List[Dict]] = None,
                      show_baseline: bool = True,
                      title: str = "Mass Spectrum") -> None:
        plt.figure(figsize=(12, 6))
        
        plt.plot(mz, intensity, label='Original', alpha=0.7, color='gray')
        
        if corrected_intensity is not None:
            plt.plot(mz, corrected_intensity, label='Baseline Corrected', 
                    color='blue', linewidth=1.5)
        
        if show_baseline and self.baseline_corrector.baseline is not None:
            plt.plot(mz, self.baseline_corrector.get_baseline(), 
                    label='Baseline', color='red', linestyle='--')
        
        if peaks is not None:
            peak_mz = [p["mz"] for p in peaks]
            peak_int = [p["intensity"] for p in peaks]
            plt.scatter(peak_mz, peak_int, color='green', s=50, zorder=5,
                       label=f'Peaks ({len(peaks)})')
        
        plt.xlabel('m/z')
        plt.ylabel('Intensity')
        plt.title(title)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()
    
    def plot_isotope_clusters(self, mz: np.ndarray, intensity: np.ndarray,
                               clusters: List[Dict]) -> None:
        plt.figure(figsize=(12, 6))
        plt.plot(mz, intensity, 'b-', alpha=0.6, linewidth=1)
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(clusters)))
        
        for idx, cluster in enumerate(clusters):
            cluster_mz = [p["mz"] for p in cluster["peaks"]]
            cluster_int = [p["intensity"] for p in cluster["peaks"]]
            
            plt.scatter(cluster_mz, cluster_int, color=colors[idx], s=100,
                       edgecolor='black', zorder=5,
                       label=f'Cluster {idx+1} (z={cluster["charge"]})')
            
            for i, (m, inte) in enumerate(zip(cluster_mz, cluster_int)):
                if i == 0:
                    label = f'Mono ({cluster["monoisotopic_mz"]:.2f})'
                else:
                    label = f'+{i}'
                plt.annotate(label, (m, inte), xytext=(5, 5),
                            textcoords='offset points', fontsize=8)
        
        plt.xlabel('m/z')
        plt.ylabel('Intensity')
        plt.title('Isotope Clusters')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()
    
    def plot_aligned_peaks_heatmap(self) -> None:
        if self.aligned_peaks is None:
            raise ValueError("No aligned peaks available. Run process_multiple_spectra() first.")
        
        mz_array, intensity_matrix = self.peak_aligner.get_intensity_matrix()
        
        plt.figure(figsize=(12, 8))
        plt.imshow(intensity_matrix, aspect='auto', cmap='viridis',
                  extent=[mz_array[0], mz_array[-1], 0, intensity_matrix.shape[0]])
        plt.colorbar(label='Intensity')
        plt.xlabel('m/z')
        plt.ylabel('Spectrum Index')
        plt.title('Aligned Peaks Heatmap')
        plt.tight_layout()
        plt.show()
