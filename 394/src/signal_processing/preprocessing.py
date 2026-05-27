import numpy as np
import pandas as pd
from scipy import signal
from scipy.signal import butter, filtfilt, welch
import pywt


class SignalPreprocessor:
    def __init__(self, sampling_rate=1):
        self.sampling_rate = sampling_rate

    def remove_outliers(self, data, threshold=3):
        z_scores = np.abs((data - np.mean(data)) / (np.std(data) + 1e-10))
        outlier_mask = z_scores >= threshold
        if np.sum(~outlier_mask) < 2:
            return data
        x = np.arange(len(data))
        cleaned_data = np.where(
            ~outlier_mask,
            data,
            np.interp(x, x[~outlier_mask], data[~outlier_mask])
        )
        return cleaned_data

    def butter_lowpass_filter(self, data, cutoff=0.5, order=4):
        nyquist = 0.5 * self.sampling_rate
        normal_cutoff = cutoff / nyquist
        b, a = butter(order, normal_cutoff, btype='low', analog=False)
        return filtfilt(b, a, data)

    def butter_highpass_filter(self, data, cutoff=0.01, order=4):
        nyquist = 0.5 * self.sampling_rate
        normal_cutoff = cutoff / nyquist
        b, a = butter(order, normal_cutoff, btype='high', analog=False)
        return filtfilt(b, a, data)

    def moving_average(self, data, window_size=5):
        return pd.Series(data).rolling(window=window_size, center=True).mean().bfill().ffill().values

    def wavelet_denoise(self, data, wavelet='db4', level=3):
        coeffs = pywt.wavedec(data, wavelet, level=level)
        sigma = np.median(np.abs(coeffs[-1])) / 0.6745
        threshold = sigma * np.sqrt(2 * np.log(len(data)))
        coeffs_thresholded = [pywt.threshold(c, threshold, mode='soft') for c in coeffs]
        return pywt.waverec(coeffs_thresholded, wavelet)

    def process_heart_rate(self, hr_data):
        hr_clean = self.remove_outliers(hr_data)
        hr_smooth = self.moving_average(hr_clean, window_size=10)
        hr_filtered = self.butter_lowpass_filter(hr_smooth, cutoff=0.1)
        return hr_filtered

    def process_respiration(self, resp_data):
        resp_clean = self.remove_outliers(resp_data)
        resp_denoised = self.wavelet_denoise(resp_clean)
        resp_filtered = self.butter_bandpass_filter(resp_denoised, low=0.05, high=0.4)
        return resp_filtered

    def butter_bandpass_filter(self, data, low=0.05, high=0.4, order=4):
        nyquist = 0.5 * self.sampling_rate
        low = low / nyquist
        high = high / nyquist
        b, a = butter(order, [low, high], btype='band')
        return filtfilt(b, a, data)

    def process_activity(self, act_data):
        act_clean = self.remove_outliers(act_data)
        act_smooth = self.moving_average(act_clean, window_size=3)
        return act_smooth

    def normalize_signal(self, data):
        return (data - np.mean(data)) / np.std(data)


class HRVAnalyzer:
    def __init__(self, sampling_rate=1):
        self.sampling_rate = sampling_rate

    def calculate_rr_intervals(self, hr_data):
        rr_intervals = 60000 / hr_data
        return rr_intervals

    def time_domain_features(self, rr_intervals):
        rr_diff = np.diff(rr_intervals)
        features = {
            'hr_mean': np.mean(60000 / rr_intervals),
            'hr_std': np.std(60000 / rr_intervals),
            'sdnn': np.std(rr_intervals),
            'rmssd': np.sqrt(np.mean(rr_diff ** 2)),
            'nn50': np.sum(np.abs(rr_diff) > 50),
            'pnn50': np.sum(np.abs(rr_diff) > 50) / len(rr_diff) * 100
        }
        return features

    def frequency_domain_features(self, rr_intervals):
        f, Pxx = welch(rr_intervals, fs=1 / np.mean(rr_intervals) * 1000,
                       nperseg=min(256, len(rr_intervals)))
        vlf_band = (0.003, 0.04)
        lf_band = (0.04, 0.15)
        hf_band = (0.15, 0.4)
        vlf_power = np.trapz(Pxx[(f >= vlf_band[0]) & (f < vlf_band[1])])
        lf_power = np.trapz(Pxx[(f >= lf_band[0]) & (f < lf_band[1])])
        hf_power = np.trapz(Pxx[(f >= hf_band[0]) & (f < hf_band[1])])
        total_power = vlf_power + lf_power + hf_power
        features = {
            'vlf_power': vlf_power,
            'lf_power': lf_power,
            'hf_power': hf_power,
            'lf_hf_ratio': lf_power / hf_power if hf_power > 0 else 0,
            'lf_norm': lf_power / total_power * 100 if total_power > 0 else 0,
            'hf_norm': hf_power / total_power * 100 if total_power > 0 else 0
        }
        return features


class RespirationAnalyzer:
    def __init__(self, sampling_rate=1):
        self.sampling_rate = sampling_rate

    def extract_respiratory_features(self, resp_data):
        peaks, _ = signal.find_peaks(resp_data, distance=self.sampling_rate * 2)
        if len(peaks) < 2:
            return {
                'resp_rate': 15,
                'resp_rate_variability': 0,
                'resp_depth_mean': np.mean(np.abs(resp_data)),
                'resp_depth_std': np.std(np.abs(resp_data))
            }
        rr_intervals = np.diff(peaks) / self.sampling_rate
        resp_rates = 60 / rr_intervals
        features = {
            'resp_rate': np.mean(resp_rates),
            'resp_rate_variability': np.std(resp_rates),
            'resp_depth_mean': np.mean(np.abs(resp_data[peaks])),
            'resp_depth_std': np.std(np.abs(resp_data[peaks]))
        }
        return features
