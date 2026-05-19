import numpy as np
from obspy import Stream, Trace
from scipy.signal import find_peaks
from scipy.stats import kurtosis


class AdaptiveSTALTAPicker:
    def __init__(self, fs):
        self.fs = fs
        
    def compute_noise_level(self, data, noise_window_ratio=0.3):
        n_noise = int(len(data) * noise_window_ratio)
        noise_segment = data[:n_noise]
        noise_std = np.std(noise_segment)
        noise_mean = np.mean(noise_segment)
        return noise_mean, noise_std
    
    def compute_adaptive_threshold(self, sta_lta_ratio, method='median_abs', **kwargs):
        if method == 'median_abs':
            median_val = np.median(sta_lta_ratio)
            mad = np.median(np.abs(sta_lta_ratio - median_val))
            threshold = median_val + kwargs.get('k', 3.0) * mad
            
        elif method == 'percentile':
            percentile = kwargs.get('percentile', 95)
            threshold = np.percentile(sta_lta_ratio, percentile)
            
        elif method == 'mean_std':
            mean_val = np.mean(sta_lta_ratio)
            std_val = np.std(sta_lta_ratio)
            threshold = mean_val + kwargs.get('n_std', 2.5) * std_val
            
        elif method == 'noise_based':
            noise_ratio = kwargs.get('noise_ratio', 0.3)
            n_noise = int(len(sta_lta_ratio) * noise_ratio)
            noise_segment = sta_lta_ratio[:n_noise]
            noise_mean = np.mean(noise_segment)
            noise_std = np.std(noise_segment)
            threshold = noise_mean + kwargs.get('snr_threshold', 3.0) * noise_std
            
        else:
            threshold = kwargs.get('default_threshold', 3.0)
            
        return max(threshold, 1.5)
    
    def recursive_threshold_adjust(self, sta_lta_ratio, initial_threshold, 
                                   max_iterations=3, peak_distance=0.5):
        threshold = initial_threshold
        fs = self.fs
        
        for i in range(max_iterations):
            peaks, _ = find_peaks(sta_lta_ratio, height=threshold, 
                                  distance=int(peak_distance * fs))
            
            if len(peaks) == 0:
                threshold *= 0.8
            elif len(peaks) > 5:
                threshold *= 1.2
            else:
                break
                
        return threshold
    
    def validate_picks(self, data, picks, fs, min_amplitude_ratio=2.0):
        validated = []
        noise_std = np.std(data[:int(fs * 2)])
        
        for pick in picks:
            idx = pick['index']
            if idx + int(fs * 0.5) < len(data):
                signal_amp = np.max(np.abs(data[idx:idx + int(fs * 0.5)]))
                if signal_amp / noise_std >= min_amplitude_ratio:
                    validated.append(pick)
                    
        return validated


class PhasePicker:
    def __init__(self, sampling_rate=None):
        self.sampling_rate = sampling_rate
        self.adaptive_picker = None

    def _get_sampling_rate(self, trace):
        if self.sampling_rate is not None:
            return self.sampling_rate
        return trace.stats.sampling_rate

    def sta_lta(self, data, fs, sta_window=1.0, lta_window=10.0, recursive=True):
        n_sta = int(sta_window * fs)
        n_lta = int(lta_window * fs)
        
        if n_sta < 1:
            n_sta = 1
        if n_lta < n_sta:
            n_lta = n_sta * 2

        data_envelope = np.abs(data)
        data_squared = data_envelope ** 2
        
        sta = np.convolve(data_squared, np.ones(n_sta) / n_sta, mode="same")
        lta = np.convolve(data_squared, np.ones(n_lta) / n_lta, mode="same")
        
        lta[lta == 0] = 1e-10
        sta_lta_ratio = sta / lta
        
        if recursive:
            for i in range(n_lta, len(sta_lta_ratio)):
                if sta_lta_ratio[i] < 1.5:
                    lta[i] = 0.99 * lta[i-1] + 0.01 * data_squared[i]
                    sta_lta_ratio[i] = sta[i] / lta[i] if lta[i] > 0 else 0
        
        return sta_lta_ratio

    def aic_picker(self, data, fs):
        n = len(data)
        aic = np.zeros(n)
        
        for k in range(1, n - 1):
            var1 = np.var(data[:k]) if k > 1 else 1e-10
            var2 = np.var(data[k:]) if (n - k) > 1 else 1e-10
            
            if var1 <= 0:
                var1 = 1e-10
            if var2 <= 0:
                var2 = 1e-10
                
            aic[k] = k * np.log(var1) + (n - k - 1) * np.log(var2)
        
        aic[0] = aic[1] if n > 1 else 0
        aic[-1] = aic[-2] if n > 1 else 0
        return aic

    def kurtosis_picker(self, data, fs, window=2.0):
        n_window = int(window * fs)
        if n_window < 3:
            n_window = 3
            
        kurt = np.zeros_like(data)
        
        for i in range(n_window // 2, len(data) - n_window // 2):
            kurt[i] = kurtosis(data[i - n_window // 2:i + n_window // 2])
        
        return kurt

    def pick_p_wave(self, trace, method="sta_lta", **kwargs):
        fs = self._get_sampling_rate(trace)
        data = trace.data.copy()
        
        if method == "sta_lta" or method == "sta_lta_adaptive":
            sta_window = kwargs.get("sta_window", 1.0)
            lta_window = kwargs.get("lta_window", 10.0)
            recursive = kwargs.get("recursive", True)
            
            sta_lta_ratio = self.sta_lta(data, fs, sta_window, lta_window, recursive)
            
            if method == "sta_lta_adaptive":
                if self.adaptive_picker is None or self.adaptive_picker.fs != fs:
                    self.adaptive_picker = AdaptiveSTALTAPicker(fs)
                
                adaptive_method = kwargs.get("adaptive_method", "median_abs")
                initial_threshold = self.adaptive_picker.compute_adaptive_threshold(
                    sta_lta_ratio, method=adaptive_method, **kwargs)
                
                adjust_iterations = kwargs.get("adjust_iterations", 0)
                if adjust_iterations > 0:
                    threshold = self.adaptive_picker.recursive_threshold_adjust(
                        sta_lta_ratio, initial_threshold, max_iterations=adjust_iterations)
                else:
                    threshold = initial_threshold
            else:
                threshold = kwargs.get("threshold", 3.0)
            
            min_dist = kwargs.get("min_distance", 0.5)
            peaks, properties = find_peaks(sta_lta_ratio, height=threshold, 
                                           distance=int(fs * min_dist))
            
            if len(peaks) > 0:
                peak_heights = properties['peak_heights']
                valid_picks = []
                for i, (p_idx, confidence) in enumerate(zip(peaks, peak_heights)):
                    p_time = trace.stats.starttime + p_idx / fs
                    valid_picks.append({
                        "time": p_time, 
                        "index": p_idx, 
                        "confidence": confidence,
                        "threshold_used": threshold
                    })
                
                if kwargs.get("validate_picks", False) and self.adaptive_picker:
                    valid_picks = self.adaptive_picker.validate_picks(
                        data, valid_picks, fs, 
                        min_amplitude_ratio=kwargs.get("min_amplitude_ratio", 2.0))
                
                if valid_picks:
                    return valid_picks[0]
                
        elif method == "aic":
            aic_values = self.aic_picker(data, fs)
            p_idx = np.argmin(aic_values)
            p_time = trace.stats.starttime + p_idx / fs
            return {"time": p_time, "index": p_idx, "confidence": -aic_values[p_idx]}
        
        elif method == "kurtosis":
            window = kwargs.get("window", 2.0)
            threshold = kwargs.get("threshold", 5.0)
            
            kurt_values = self.kurtosis_picker(data, fs, window)
            peaks, properties = find_peaks(kurt_values, height=threshold, 
                                           distance=int(fs * 0.5))
            
            if len(peaks) > 0:
                peak_heights = properties['peak_heights']
                p_idx = peaks[0]
                p_time = trace.stats.starttime + p_idx / fs
                return {"time": p_time, "index": p_idx, "confidence": peak_heights[0]}
        
        return None

    def pick_s_wave(self, trace, p_pick=None, **kwargs):
        fs = self._get_sampling_rate(trace)
        data = trace.data.copy()
        
        start_idx = 0
        if p_pick is not None:
            start_idx = p_pick.get("index", 0) + int(fs * 0.5)
        
        if start_idx >= len(data):
            return None
        
        window_data = data[start_idx:]
        sta_window = kwargs.get("sta_window", 0.5)
        lta_window = kwargs.get("lta_window", 5.0)
        recursive = kwargs.get("recursive", True)
        
        adaptive = kwargs.get("adaptive", False)
        sta_lta_ratio = self.sta_lta(window_data, fs, sta_window, lta_window, recursive)
        
        if adaptive:
            if self.adaptive_picker is None or self.adaptive_picker.fs != fs:
                self.adaptive_picker = AdaptiveSTALTAPicker(fs)
            
            adaptive_method = kwargs.get("adaptive_method", "mean_std")
            threshold = self.adaptive_picker.compute_adaptive_threshold(
                sta_lta_ratio, method=adaptive_method, n_std=2.0, **kwargs)
        else:
            threshold = kwargs.get("threshold", 2.5)
        
        min_dist = kwargs.get("min_distance", 0.3)
        peaks, properties = find_peaks(sta_lta_ratio, height=threshold, 
                                       distance=int(fs * min_dist))
        
        if len(peaks) > 0:
            peak_heights = properties['peak_heights']
            s_idx = start_idx + peaks[0]
            s_time = trace.stats.starttime + s_idx / fs
            return {"time": s_time, "index": s_idx, 
                    "confidence": peak_heights[0], "threshold_used": threshold}
        
        return None

    def pick_both_phases(self, trace, **kwargs):
        p_pick = self.pick_p_wave(trace, **kwargs)
        s_pick = self.pick_s_wave(trace, p_pick, **kwargs)
        return {"P": p_pick, "S": s_pick}

    def pick_stream(self, stream, **kwargs):
        results = {}
        for trace in stream:
            trace_id = trace.id
            results[trace_id] = self.pick_both_phases(trace, **kwargs)
        return results
