import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import find_peaks


class SleepFeatureExtractor:
    def __init__(self, window_size=30, step_size=30, sampling_rate=1):
        self.window_size = window_size
        self.step_size = step_size
        self.sampling_rate = sampling_rate

    def extract_window_features(self, window_data, prefix=''):
        if len(window_data) == 0:
            return {}
        features = {
            f'{prefix}mean': np.mean(window_data),
            f'{prefix}std': np.std(window_data),
            f'{prefix}min': np.min(window_data),
            f'{prefix}max': np.max(window_data),
            f'{prefix}median': np.median(window_data),
            f'{prefix}range': np.max(window_data) - np.min(window_data),
            f'{prefix}skewness': stats.skew(window_data),
            f'{prefix}kurtosis': stats.kurtosis(window_data),
            f'{prefix}energy': np.sum(window_data ** 2),
            f'{prefix}rms': np.sqrt(np.mean(window_data ** 2))
        }
        features[f'{prefix}cv'] = features[f'{prefix}std'] / features[f'{prefix}mean'] if features[f'{prefix}mean'] != 0 else 0
        return features

    def extract_hrv_features(self, hr_window):
        if len(hr_window) < 2:
            return {}
        rr_intervals = 60000 / hr_window
        rr_diff = np.diff(rr_intervals)
        features = {
            'hrv_sdnn': np.std(rr_intervals),
            'hrv_rmssd': np.sqrt(np.mean(rr_diff ** 2)),
            'hrv_mean_nni': np.mean(rr_intervals),
            'hrv_cvnni': np.std(rr_intervals) / np.mean(rr_intervals)
        }
        return features

    def extract_activity_features(self, act_window):
        if len(act_window) == 0:
            return {}
        peaks, _ = find_peaks(act_window, height=0.5)
        zero_crossings = np.sum(np.diff(np.sign(act_window - np.mean(act_window))) != 0)
        features = {
            'act_mean': np.mean(act_window),
            'act_std': np.std(act_window),
            'act_max': np.max(act_window),
            'act_zero_crossings': zero_crossings,
            'act_peak_count': len(peaks),
            'act_motion_intensity': np.sum(np.abs(np.diff(act_window)))
        }
        return features

    def extract_resp_features(self, resp_window):
        if len(resp_window) == 0:
            return {}
        peaks, _ = find_peaks(resp_window, distance=self.sampling_rate * 2)
        features = {
            'resp_mean': np.mean(resp_window),
            'resp_std': np.std(resp_window),
            'resp_peak_count': len(peaks),
            'resp_rate': len(peaks) / (len(resp_window) / self.sampling_rate) * 60
        }
        return features

    def extract_all_features(self, hr_data, resp_data, act_data):
        n_samples = len(hr_data)
        features_list = []
        timestamps = []
        for start in range(0, n_samples - self.window_size + 1, self.step_size):
            end = start + self.window_size
            hr_window = hr_data[start:end]
            resp_window = resp_data[start:end]
            act_window = act_data[start:end]
            features = {}
            features.update(self.extract_window_features(hr_window, prefix='hr_'))
            features.update(self.extract_window_features(resp_window, prefix='resp_'))
            features.update(self.extract_window_features(act_window, prefix='act_'))
            features.update(self.extract_hrv_features(hr_window))
            features.update(self.extract_activity_features(act_window))
            features.update(self.extract_resp_features(resp_window))
            features_list.append(features)
            timestamps.append(start)
        features_df = pd.DataFrame(features_list)
        features_df = features_df.fillna(features_df.mean())
        features_df = features_df.replace([np.inf, -np.inf], 0)
        return features_df, timestamps


class SleepDataGenerator:
    def __init__(self, n_subjects=10, n_nights=5, n_epochs=720, history_days=3):
        self.n_subjects = n_subjects
        self.n_nights = n_nights
        self.n_epochs = n_epochs
        self.history_days = history_days

    def generate_subject_data(self, subject_id, night_id, history_factors=None):
        np.random.seed(subject_id * 100 + night_id)
        sleep_stages = self._generate_sleep_stages()
        hr_data = self._generate_hr_data(sleep_stages)
        resp_data = self._generate_resp_data(sleep_stages)
        act_data = self._generate_act_data(sleep_stages)
        factors = self._generate_lifestyle_factors()
        if history_factors is None:
            history_factors = self._generate_history_factors(subject_id, night_id)
        data = {
            'subject_id': subject_id,
            'night_id': night_id,
            'sleep_stages': sleep_stages,
            'heart_rate': hr_data,
            'respiration': resp_data,
            'activity': act_data,
            'lifestyle_factors': factors,
            'history_factors': history_factors
        }
        return data

    def _generate_sleep_stages(self):
        stages = []
        current_stage = 0
        for epoch in range(self.n_epochs):
            cycle_pos = (epoch % 90) / 90
            if cycle_pos < 0.1:
                transition_probs = [0.3, 0.4, 0.2, 0.1]
            elif cycle_pos < 0.4:
                transition_probs = [0.1, 0.2, 0.6, 0.1]
            elif cycle_pos < 0.7:
                transition_probs = [0.05, 0.15, 0.1, 0.7]
            else:
                transition_probs = [0.2, 0.5, 0.1, 0.2]
            current_stage = np.random.choice([0, 1, 2, 3], p=transition_probs)
            stages.append(current_stage)
        return np.array(stages)

    def _generate_hr_data(self, sleep_stages):
        stage_means = {0: 75, 1: 65, 2: 55, 3: 60}
        stage_stds = {0: 8, 1: 6, 2: 4, 3: 5}
        hr = []
        for stage in sleep_stages:
            base_hr = stage_means[stage]
            noise = np.random.normal(0, stage_stds[stage], 30)
            hr_30s = base_hr + np.cumsum(noise) * 0.1
            hr.extend(hr_30s.tolist())
        return np.array(hr)

    def _generate_resp_data(self, sleep_stages):
        stage_means = {0: 16, 1: 14, 2: 12, 3: 15}
        stage_stds = {0: 3, 1: 2, 2: 1.5, 3: 2.5}
        resp = []
        for stage in sleep_stages:
            base_resp = stage_means[stage]
            noise = np.random.normal(0, stage_stds[stage], 30)
            resp_30s = base_resp + np.cumsum(noise) * 0.05
            resp.extend(resp_30s.tolist())
        return np.array(resp)

    def _generate_act_data(self, sleep_stages):
        stage_means = {0: 50, 1: 20, 2: 5, 3: 15}
        stage_stds = {0: 30, 1: 15, 2: 3, 3: 10}
        act = []
        for stage in sleep_stages:
            base_act = stage_means[stage]
            noise = np.abs(np.random.normal(0, stage_stds[stage], 30))
            act_30s = base_act + noise
            act.extend(act_30s.tolist())
        return np.array(act)

    def _generate_lifestyle_factors(self):
        return {
            'exercise_minutes': np.random.randint(0, 120),
            'exercise_intensity': np.random.choice(['low', 'moderate', 'high']),
            'caffeine_intake': np.random.choice([0, 1, 2, 3]),
            'alcohol_intake': np.random.choice([0, 1, 2]),
            'stress_level': np.random.randint(1, 11),
            'sleep_duration_goal': np.random.randint(7, 10),
            'bedtime_consistency': np.random.randint(1, 11)
        }

    def _generate_history_factors(self, subject_id, night_id):
        np.random.seed(subject_id * 1000 + night_id * 10)
        history = {
            'exercise_minutes_1d': np.random.randint(0, 120),
            'exercise_minutes_2d': np.random.randint(0, 120),
            'exercise_minutes_3d': np.random.randint(0, 120),
            'stress_level_1d': np.random.randint(1, 11),
            'stress_level_2d': np.random.randint(1, 11),
            'stress_level_3d': np.random.randint(1, 11),
            'caffeine_intake_1d': np.random.choice([0, 1, 2, 3]),
            'caffeine_intake_2d': np.random.choice([0, 1, 2, 3]),
            'caffeine_intake_3d': np.random.choice([0, 1, 2, 3]),
            'alcohol_intake_1d': np.random.choice([0, 1, 2]),
            'alcohol_intake_2d': np.random.choice([0, 1, 2]),
            'alcohol_intake_3d': np.random.choice([0, 1, 2]),
            'bedtime_hour_1d': np.random.normal(23, 1.5),
            'bedtime_hour_2d': np.random.normal(23, 1.5),
            'bedtime_hour_3d': np.random.normal(23, 1.5),
            'sleep_duration_1d': np.random.normal(7.5, 1.5),
            'sleep_duration_2d': np.random.normal(7.5, 1.5),
            'sleep_duration_3d': np.random.normal(7.5, 1.5),
        }
        return history

    def generate_all_data(self):
        all_data = []
        for subject in range(self.n_subjects):
            for night in range(self.n_nights):
                data = self.generate_subject_data(subject, night)
                all_data.append(data)
        return all_data
