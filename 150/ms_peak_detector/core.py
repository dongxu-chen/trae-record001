import numpy as np
from pyopenms import MSExperiment, MSSpectrum


class MSPeakProcessor:
    def __init__(self):
        self.experiment = MSExperiment()
    
    def load_mzml(self, filepath: str) -> None:
        from pyopenms import MzMLFile
        file = MzMLFile()
        file.load(filepath, self.experiment)
    
    def get_spectrum(self, index: int = 0) -> MSSpectrum:
        return self.experiment[index]
    
    def get_spectrum_count(self) -> int:
        return self.experiment.size()
    
    def get_spectrum_data(self, index: int = 0) -> tuple:
        spectrum = self.get_spectrum(index)
        mz = np.array(spectrum.get_peaks()[0])
        intensity = np.array(spectrum.get_peaks()[1])
        return mz, intensity
    
    def get_ms_level_spectra(self, ms_level: int = 1) -> list:
        spectra = []
        for i in range(self.experiment.size()):
            spec = self.experiment[i]
            if spec.getMSLevel() == ms_level:
                spectra.append(spec)
        return spectra
