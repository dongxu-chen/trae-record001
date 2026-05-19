import numpy as np
from obspy import Stream, Trace
from scipy.signal import welch, spectrogram, get_window
from scipy.fft import fft, fftfreq


class SpectrumAnalyzer:
    def __init__(self, sampling_rate=None):
        self.sampling_rate = sampling_rate

    def _get_sampling_rate(self, trace):
        if self.sampling_rate is not None:
            return self.sampling_rate
        return trace.stats.sampling_rate
    
    def detrend_data(self, data, method='linear'):
        if method == 'linear':
            x = np.arange(len(data))
            coeffs = np.polyfit(x, data, 1)
            trend = np.polyval(coeffs, x)
            return data - trend
        elif method == 'mean':
            return data - np.mean(data)
        elif method == 'constant':
            return data - np.mean(data)
        else:
            return data
    
    def apply_window(self, data, window_type='hann'):
        n = len(data)
        window = get_window(window_type, n)
        return data * window, window

    def compute_fft(self, trace, **kwargs):
        fs = self._get_sampling_rate(trace)
        data = trace.data.copy()
        
        detrend = kwargs.get("detrend", "linear")
        if detrend:
            data = self.detrend_data(data, method=detrend)
        
        window_type = kwargs.get("window", "hann")
        if window_type:
            data, window_func = self.apply_window(data, window_type)
        else:
            window_func = np.ones(len(data))
        
        n = len(data)
        yf = fft(data)
        xf = fftfreq(n, 1 / fs)[:n // 2]
        
        window_correction = np.sum(window_func) / n
        amplitude = 2.0 / (n * window_correction) * np.abs(yf[0:n // 2])
        
        return {"freq": xf, "amplitude": amplitude}

    def compute_psd(self, trace, **kwargs):
        fs = self._get_sampling_rate(trace)
        data = trace.data.copy()
        
        detrend = kwargs.get("detrend", "linear")
        if detrend:
            data = self.detrend_data(data, method=detrend)
        
        nperseg = kwargs.get("nperseg", int(fs * 2))
        noverlap = kwargs.get("noverlap", int(nperseg / 2))
        window = kwargs.get("window", "hann")
        
        f, Pxx = welch(data, fs=fs, nperseg=nperseg, noverlap=noverlap, 
                       window=window, detrend=False)
        
        return {"freq": f, "psd": Pxx}

    def compute_spectrogram(self, trace, **kwargs):
        fs = self._get_sampling_rate(trace)
        data = trace.data.copy()
        
        detrend = kwargs.get("detrend", "linear")
        if detrend:
            data = self.detrend_data(data, method=detrend)
        
        nperseg = kwargs.get("nperseg", int(fs * 1))
        noverlap = kwargs.get("noverlap", int(nperseg / 2))
        window = kwargs.get("window", "hann")
        
        f, t, Sxx = spectrogram(data, fs=fs, nperseg=nperseg, noverlap=noverlap, 
                               window=window, detrend=False)
        
        return {"freq": f, "time": t, "spectrogram": Sxx}

    def dominant_frequency(self, trace, **kwargs):
        spectrum = self.compute_fft(trace, **kwargs)
        max_idx = np.argmax(spectrum["amplitude"])
        dom_freq = spectrum["freq"][max_idx]
        return {"dominant_frequency": dom_freq, "amplitude": spectrum["amplitude"][max_idx]}

    def spectral_ratio(self, trace1, trace2, **kwargs):
        spec1 = self.compute_fft(trace1, **kwargs)
        spec2 = self.compute_fft(trace2, **kwargs)
        
        freq = spec1["freq"]
        ratio = spec1["amplitude"] / (spec2["amplitude"] + 1e-10)
        
        return {"freq": freq, "ratio": ratio}

    def peak_frequency(self, trace, freq_range=None, **kwargs):
        spectrum = self.compute_psd(trace, **kwargs)
        freq = spectrum["freq"]
        psd = spectrum["psd"]
        
        if freq_range is not None:
            mask = (freq >= freq_range[0]) & (freq <= freq_range[1])
            freq = freq[mask]
            psd = psd[mask]
        
        max_idx = np.argmax(psd)
        return {"peak_frequency": freq[max_idx], "psd": psd[max_idx]}

    def bandwidth(self, trace, level=-3, **kwargs):
        spectrum = self.compute_psd(trace, **kwargs)
        freq = spectrum["freq"]
        psd = spectrum["psd"]
        
        max_psd = np.max(psd)
        threshold = max_psd * (10 ** (level / 10))
        
        above_threshold = psd >= threshold
        
        if np.any(above_threshold):
            indices = np.where(above_threshold)[0]
            low_freq = freq[indices[0]]
            high_freq = freq[indices[-1]]
            return {"low_freq": low_freq, "high_freq": high_freq, "bandwidth": high_freq - low_freq}
        
        return {"low_freq": 0, "high_freq": 0, "bandwidth": 0}

    def central_frequency(self, trace, **kwargs):
        spectrum = self.compute_psd(trace, **kwargs)
        freq = spectrum["freq"]
        psd = spectrum["psd"]
        
        total_power = np.sum(psd)
        if total_power == 0:
            return 0
        
        cf = np.sum(freq * psd) / total_power
        return {"central_frequency": cf}
