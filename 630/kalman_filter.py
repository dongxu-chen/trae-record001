import numpy as np
from collections import deque


class KalmanFilter:
    def __init__(self, initial_state, initial_covariance, process_noise, measurement_noise):
        self.state = np.array(initial_state, dtype=np.float64)
        self.covariance = np.array(initial_covariance, dtype=np.float64)
        self.process_noise = np.array(process_noise, dtype=np.float64)
        self.measurement_noise = np.array(measurement_noise, dtype=np.float64)
        self.base_process_noise = self.process_noise.copy()
        self.base_measurement_noise = self.measurement_noise.copy()
        self.transition_matrix = np.array([[1, 1], [0, 1]], dtype=np.float64)
        self.measurement_matrix = np.array([[1, 0]], dtype=np.float64)
        self.adaptation_rate = 0.1

    def predict(self):
        self.state = self.transition_matrix @ self.state
        self.covariance = (
            self.transition_matrix @ self.covariance @ self.transition_matrix.T
            + self.process_noise
        )

    def update(self, measurement):
        innovation = measurement - self.measurement_matrix @ self.state
        innovation_covariance = (
            self.measurement_matrix @ self.covariance @ self.measurement_matrix.T
            + self.measurement_noise
        )
        kalman_gain = (
            self.covariance @ self.measurement_matrix.T @ np.linalg.inv(innovation_covariance)
        )
        self.state = self.state + kalman_gain @ innovation
        self.covariance = (
            np.eye(2) - kalman_gain @ self.measurement_matrix
        ) @ self.covariance
        return innovation

    def adapt_noise(self, bpm_change_rate, measurement_uncertainty=0.0):
        process_scale = 1.0 + abs(bpm_change_rate) * 0.5
        process_scale = min(max(process_scale, 0.5), 3.0)

        measurement_scale = 1.0 + measurement_uncertainty * 2.0
        measurement_scale = min(max(measurement_scale, 0.5), 4.0)

        self.process_noise = self.base_process_noise * process_scale
        self.measurement_noise = self.base_measurement_noise * measurement_scale

    def reset_noise(self):
        self.process_noise = self.base_process_noise.copy()
        self.measurement_noise = self.base_measurement_noise.copy()

    def get_state(self):
        return self.state.copy()

    def get_covariance(self):
        return self.covariance.copy()


class AdaptiveBPMKalmanFilter:
    def __init__(
        self,
        initial_bpm=120.0,
        process_noise_std=0.5,
        measurement_noise_std=5.0,
        adaptation_window=10,
        max_process_scale=3.0,
    ):
        initial_state = np.array([initial_bpm, 0.0], dtype=np.float64)
        initial_covariance = np.diag([100.0, 10.0])
        process_noise = np.diag([process_noise_std**2, 0.01])
        measurement_noise = np.array([[measurement_noise_std**2]])

        self.kf = KalmanFilter(
            initial_state, initial_covariance, process_noise, measurement_noise
        )

        self.bpm_history = deque(maxlen=30)
        self.innovation_history = deque(maxlen=20)
        self.confidence = 0.0
        self.adaptation_window = adaptation_window
        self.max_process_scale = max_process_scale

        self.bpm_velocity = 0.0
        self.bpm_acceleration = 0.0
        self.last_bpm = initial_bpm

        self.speed_change_detected = False
        self.speed_change_magnitude = 0.0

    def _detect_speed_change(self, measured_bpm):
        if len(self.bpm_history) < self.adaptation_window:
            return False, 0.0

        recent_bpms = list(self.bpm_history)[-self.adaptation_window:]
        bpm_mean = np.mean(recent_bpms)
        bpm_std = np.std(recent_bpms)

        deviation = abs(measured_bpm - bpm_mean)
        z_score = deviation / (bpm_std + 1e-6) if bpm_std > 0 else 0

        if len(recent_bpms) >= 5:
            slope = np.polyfit(range(len(recent_bpms)), recent_bpms, 1)[0]
            trend_magnitude = abs(slope) * len(recent_bpms)
        else:
            trend_magnitude = 0.0

        is_change = z_score > 2.0 or trend_magnitude > 5.0
        magnitude = min(max(z_score * 0.3 + trend_magnitude * 0.02, 0), 1.0)

        return is_change, magnitude

    def _adapt_parameters(self, measured_bpm, measurement_confidence):
        is_change, change_mag = self._detect_speed_change(measured_bpm)
        self.speed_change_detected = is_change
        self.speed_change_magnitude = change_mag

        if len(self.bpm_history) >= 2:
            self.bpm_velocity = measured_bpm - self.last_bpm
            if len(self.bpm_history) >= 3:
                prev_velocity = self.bpm_history[-1] - self.bpm_history[-2]
                self.bpm_acceleration = self.bpm_velocity - prev_velocity

        bpm_change_rate = abs(self.bpm_velocity) / 5.0 + abs(self.bpm_acceleration) / 2.0
        measurement_uncertainty = 1.0 - measurement_confidence

        if is_change:
            bpm_change_rate += change_mag * 2.0

        self.kf.adapt_noise(bpm_change_rate, measurement_uncertainty)

        self.last_bpm = measured_bpm

    def update(self, measured_bpm, measurement_confidence=1.0):
        self._adapt_parameters(measured_bpm, measurement_confidence)

        self.kf.predict()
        innovation = self.kf.update(measured_bpm)
        self.innovation_history.append(abs(innovation))

        current_bpm = self.kf.get_state()[0]
        self.bpm_history.append(current_bpm)

        if len(self.bpm_history) > 5:
            recent_bpms = list(self.bpm_history)[-10:]
            bpm_std = np.std(recent_bpms)
            base_confidence = max(0.0, min(1.0, 1.0 - bpm_std / 20.0))

            if len(self.innovation_history) > 3:
                innovation_mean = np.mean(list(self.innovation_history)[-5:])
                innovation_penalty = min(innovation_mean / 10.0, 0.5)
                base_confidence = max(0.0, base_confidence - innovation_penalty)

            self.confidence = base_confidence * measurement_confidence

        if self.speed_change_detected:
            self.confidence *= 0.7

        return current_bpm, self.confidence

    def get_bpm(self):
        return self.kf.get_state()[0]

    def get_bpm_trend(self):
        return self.kf.get_state()[1]

    def get_bpm_velocity(self):
        return self.bpm_velocity

    def get_bpm_acceleration(self):
        return self.bpm_acceleration

    def get_confidence(self):
        return self.confidence

    def is_speed_changing(self):
        return self.speed_change_detected

    def get_speed_change_magnitude(self):
        return self.speed_change_magnitude

    def reset(self, initial_bpm=120.0):
        self.kf.state = np.array([initial_bpm, 0.0], dtype=np.float64)
        self.kf.covariance = np.diag([100.0, 10.0])
        self.kf.reset_noise()
        self.bpm_history.clear()
        self.innovation_history.clear()
        self.confidence = 0.0
        self.bpm_velocity = 0.0
        self.bpm_acceleration = 0.0
        self.last_bpm = initial_bpm
        self.speed_change_detected = False
        self.speed_change_magnitude = 0.0


class BPMKalmanFilter(AdaptiveBPMKalmanFilter):
    def __init__(self, initial_bpm=120.0, process_noise_std=0.5, measurement_noise_std=5.0):
        super().__init__(
            initial_bpm=initial_bpm,
            process_noise_std=process_noise_std,
            measurement_noise_std=measurement_noise_std,
        )
