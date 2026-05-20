import numpy as np
from obspy import Stream, Trace
from scipy.signal import convolve, windows


class ResponseDeconvolution:
    def __init__(self, sampling_rate=None):
        self.sampling_rate = sampling_rate
    
    def _get_sampling_rate(self, trace):
        if self.sampling_rate is not None:
            return self.sampling_rate
        return trace.stats.sampling_rate
    
    def water_level_deconvolution(self, data, response_data, water_level=0.01, 
                                 pre_filt=None, smooth_spectrum=False):
        n = len(data)
        n_pow2 = 2**int(np.ceil(np.log2(n)))
        
        data_fft = np.fft.fft(data, n_pow2)
        resp_fft = np.fft.fft(response_data, n_pow2)
        
        freq = np.fft.fftfreq(n_pow2, 1.0 / self.sampling_rate)
        
        if pre_filt is not None:
            f1, f2, f3, f4 = pre_filt
            freq_abs = np.abs(freq)
            butter_filter = np.ones_like(freq_abs, dtype=float)
            
            idx1 = np.where(freq_abs < f1)[0]
            idx2 = np.where((freq_abs >= f1) & (freq_abs < f2))[0]
            idx3 = np.where((freq_abs >= f3) & (freq_abs < f4))[0]
            idx4 = np.where(freq_abs >= f4)[0]
            
            if len(idx2) > 0:
                x = (freq_abs[idx2] - f1) / (f2 - f1)
                butter_filter[idx2] = 0.5 * (1 - np.cos(np.pi * x))
            if len(idx3) > 0:
                x = (freq_abs[idx3] - f3) / (f4 - f3)
                butter_filter[idx3] = 0.5 * (1 + np.cos(np.pi * x))
            butter_filter[idx4] = 0
            
            data_fft *= butter_filter
            resp_fft *= butter_filter
        
        resp_abs = np.abs(resp_fft)
        max_resp = np.max(resp_abs)
        threshold = max_resp * water_level
        
        resp_safe = resp_fft.copy()
        below_threshold = resp_abs < threshold
        resp_safe[below_threshold] = threshold * np.exp(1j * np.angle(resp_safe[below_threshold]))
        
        deconv_fft = data_fft / resp_safe
        
        if smooth_spectrum:
            smooth_window = 5
            deconv_fft = self._smooth_complex_spectrum(deconv_fft, smooth_window)
        
        deconv_data = np.fft.ifft(deconv_fft).real[:n]
        
        return deconv_data
    
    def _smooth_complex_spectrum(self, spectrum, window_size):
        n = len(spectrum)
        smoothed = np.zeros_like(spectrum, dtype=complex)
        half_window = window_size // 2
        
        for i in range(n):
            start = max(0, i - half_window)
            end = min(n, i + half_window + 1)
            smoothed[i] = np.mean(spectrum[start:end])
        
        return smoothed
    
    def iterative_deconvolution(self, data, source_wavelet, n_iterations=100, 
                               mu=0.001, spike_threshold=1e-6):
        n = len(data)
        reflectivity = np.zeros(n)
        residual = data.copy()
        
        wavelet_corr = np.correlate(source_wavelet, source_wavelet, mode='valid')[0]
        
        for _ in range(n_iterations):
            correlation = np.correlate(residual, source_wavelet, mode='same')
            
            max_idx = np.argmax(np.abs(correlation))
            max_val = correlation[max_idx]
            
            if np.abs(max_val) < spike_threshold:
                break
            
            reflectivity[max_idx] += mu * max_val / wavelet_corr
            
            residual -= mu * max_val / wavelet_corr * np.roll(
                source_wavelet, max_idx - len(source_wavelet) // 2
            )
        
        return reflectivity, residual
    
    def create_instrument_response(self, response_type='displacement', 
                                  damping=0.707, natural_freq=1.0, 
                                  gain=1.0, n_samples=1024):
        dt = 1.0 / self.sampling_rate
        t = np.arange(n_samples) * dt
        
        if response_type == 'displacement':
            omega0 = 2 * np.pi * natural_freq
            h = damping
            
            response = (gain * omega0 / np.sqrt(1 - h**2) * 
                       np.exp(-h * omega0 * t) * 
                       np.sin(omega0 * np.sqrt(1 - h**2) * t))
            response = response * dt
        elif response_type == 'velocity':
            omega0 = 2 * np.pi * natural_freq
            h = damping
            
            response = (gain * (omega0**2) / np.sqrt(1 - h**2) * 
                       np.exp(-h * omega0 * t) * 
                       np.cos(omega0 * np.sqrt(1 - h**2) * t - np.arctan2(np.sqrt(1 - h**2), h)))
            response = response * dt
        elif response_type == 'acceleration':
            omega0 = 2 * np.pi * natural_freq
            h = damping
            
            response = (gain * (omega0**3) * 
                       np.exp(-h * omega0 * t) * 
                       (np.cos(omega0 * np.sqrt(1 - h**2) * t) - 
                        2 * h / np.sqrt(1 - h**2) * np.sin(omega0 * np.sqrt(1 - h**2) * t)))
            response = response * dt
        else:
            raise ValueError(f"Unknown response type: {response_type}")
        
        return response
    
    def deconvolve_trace(self, trace, response_data, method='water_level', 
                        **kwargs):
        self.sampling_rate = self._get_sampling_rate(trace)
        data = trace.data.copy()
        
        if method == 'water_level':
            deconv_data = self.water_level_deconvolution(
                data, response_data,
                water_level=kwargs.get('water_level', 0.01),
                pre_filt=kwargs.get('pre_filt', None),
                smooth_spectrum=kwargs.get('smooth_spectrum', False)
            )
        elif method == 'iterative':
            deconv_data, _ = self.iterative_deconvolution(
                data, response_data,
                n_iterations=kwargs.get('n_iterations', 100),
                mu=kwargs.get('mu', 0.001),
                spike_threshold=kwargs.get('spike_threshold', 1e-6)
            )
        else:
            raise ValueError(f"Unknown deconvolution method: {method}")
        
        deconv_trace = trace.copy()
        deconv_trace.data = deconv_data
        
        return deconv_trace
    
    def deconvolve_stream(self, stream, response_dict, method='water_level', **kwargs):
        deconv_stream = Stream()
        
        for trace in stream:
            chan = trace.stats.channel
            if chan in response_dict:
                deconv_trace = self.deconvolve_trace(
                    trace, response_dict[chan], method, **kwargs
                )
                deconv_stream.append(deconv_trace)
            else:
                deconv_stream.append(trace.copy())
        
        return deconv_stream


class SourceDeconvolution:
    def __init__(self, sampling_rate=None):
        self.sampling_rate = sampling_rate
    
    def _get_sampling_rate(self, trace):
        if self.sampling_rate is not None:
            return self.sampling_rate
        return trace.stats.sampling_rate
    
    def estimate_source_wavelet(self, stream, method='spectral_averaging', 
                               window_length=2.0):
        if len(stream) == 0:
            return None
        
        self.sampling_rate = self._get_sampling_rate(stream[0])
        n_window = int(window_length * self.sampling_rate)
        
        if method == 'spectral_averaging':
            all_spectra = []
            
            for trace in stream:
                data = trace.data[:n_window] if len(trace.data) > n_window else trace.data
                spectrum = np.fft.fft(data)
                all_spectra.append(spectrum)
            
            min_len = min(len(s) for s in all_spectra)
            avg_spectrum = np.mean([s[:min_len] for s in all_spectra], axis=0)
            wavelet = np.fft.ifft(avg_spectrum).real
            
        elif method == ' kurtosis_max':
            from scipy.stats import kurtosis
            
            best_wavelet = None
            best_kurt = -np.inf
            
            for trace in stream:
                for start in range(0, len(trace.data) - n_window, n_window // 4):
                    segment = trace.data[start:start + n_window]
                    current_kurt = kurtosis(segment)
                    if current_kurt > best_kurt:
                        best_kurt = current_kurt
                        best_wavelet = segment
            
            wavelet = best_wavelet if best_wavelet is not None else np.zeros(n_window)
        
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return wavelet
    
    def cross_correlation_deconvolution(self, data, wavelet, normalize=True):
        corr = np.correlate(data, wavelet, mode='same')
        
        if normalize:
            wavelet_energy = np.sum(wavelet**2)
            if wavelet_energy > 0:
                corr /= wavelet_energy
        
        return corr
    
    def wiener_deconvolution(self, data, wavelet, noise_sigma=0.01):
        n = len(data)
        n_pow2 = 2**int(np.ceil(np.log2(n)))
        
        data_fft = np.fft.fft(data, n_pow2)
        wavelet_fft = np.fft.fft(wavelet, n_pow2)
        
        wiener_filter = np.conj(wavelet_fft) / (np.abs(wavelet_fft)**2 + noise_sigma**2)
        deconv_fft = data_fft * wiener_filter
        
        deconv_data = np.fft.ifft(deconv_fft).real[:n]
        
        return deconv_data
