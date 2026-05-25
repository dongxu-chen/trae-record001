import numpy as np
from typing import Tuple, Optional, Dict
from datetime import datetime, timedelta
from collections import deque


class SegmentNoiseProfile:
    def __init__(self, max_history: int = 100):
        self.position_errors = deque(maxlen=max_history)
        self.velocity_errors = deque(maxlen=max_history)
        self.residuals = deque(maxlen=max_history)
    
    def update(self, position_error: float, velocity_error: float, residual: np.ndarray):
        self.position_errors.append(position_error)
        self.velocity_errors.append(velocity_error)
        self.residuals.append(residual)
    
    def get_variances(self) -> Tuple[float, float, np.ndarray]:
        if len(self.position_errors) < 10:
            return 5.0, 2.0, np.eye(4)
        
        pos_var = np.var(self.position_errors)
        vel_var = np.var(self.velocity_errors)
        
        if len(self.residuals) >= 10:
            residual_matrix = np.array(self.residuals[-10:])
            residual_cov = np.cov(residual_matrix.T)
            if residual_cov.shape == (4, 4):
                R = residual_cov + np.eye(4) * 0.1
            else:
                R = np.eye(4)
        else:
            R = np.eye(4)
        
        return max(1.0, pos_var), max(0.5, vel_var), R


class KalmanFilter:
    def __init__(self, dt: float = 1.0, segment_id: str = 'default'):
        self.dt = dt
        self.segment_id = segment_id
        
        self.state_dim = 6
        self.measurement_dim = 4
        
        self.x = np.zeros((self.state_dim, 1))
        
        self.F = np.eye(self.state_dim)
        self.F[0, 2] = dt
        self.F[1, 3] = dt
        self.F[2, 4] = dt
        self.F[3, 5] = dt
        
        self.H = np.zeros((self.measurement_dim, self.state_dim))
        self.H[0, 0] = 1
        self.H[1, 1] = 1
        self.H[2, 2] = 1
        self.H[3, 3] = 1
        
        self.P = np.eye(self.state_dim) * 1000
        
        self.base_Q = np.eye(self.state_dim) * 0.1
        self.base_Q[4, 4] = 0.5
        self.base_Q[5, 5] = 0.5
        
        self.Q = self.base_Q.copy()
        self.R = np.eye(self.measurement_dim)
        self.R[0, 0] = 5
        self.R[1, 1] = 5
        self.R[2, 2] = 2
        self.R[3, 3] = 2
        
        self.noise_profile = SegmentNoiseProfile()
        self.last_measurement = None
        self.initialized = False
        
        self.traffic_factor = 1.0
        self.stop_light_factor = 1.0
    
    def initialize(self, lat: float, lon: float, speed: float, heading: float):
        vx = speed * np.cos(np.radians(heading))
        vy = speed * np.sin(np.radians(heading))
        
        self.x[0, 0] = lat
        self.x[1, 0] = lon
        self.x[2, 0] = vx
        self.x[3, 0] = vy
        self.x[4, 0] = 0
        self.x[5, 0] = 0
        
        self.initialized = True
    
    def predict(self) -> np.ndarray:
        if not self.initialized:
            return np.zeros((self.state_dim, 1))
        
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        
        return self.x
    
    def set_segment_factors(self, traffic_level: int, stop_light_density: float):
        self.traffic_factor = 1.0 + traffic_level * 0.3
        self.stop_light_factor = 1.0 + stop_light_density * 0.5
        
        self.Q = self.base_Q.copy()
        self.Q[2, 2] *= self.traffic_factor
        self.Q[3, 3] *= self.traffic_factor
        self.Q[4, 4] *= self.stop_light_factor
        self.Q[5, 5] *= self.stop_light_factor
    
    def update(self, lat: float, lon: float, speed: float, heading: float):
        if not self.initialized:
            self.initialize(lat, lon, speed, heading)
            self.last_measurement = np.array([[lat], [lon], [speed * np.cos(np.radians(heading))], [speed * np.sin(np.radians(heading))]])
            return self.x
        
        vx = speed * np.cos(np.radians(heading))
        vy = speed * np.sin(np.radians(heading))
        
        z = np.array([[lat], [lon], [vx], [vy]])
        
        if self.last_measurement is not None:
            pos_error = np.sqrt((lat - self.last_measurement[0, 0])**2 + (lon - self.last_measurement[1, 0])**2)
            vel_error = np.sqrt((vx - self.last_measurement[2, 0])**2 + (vy - self.last_measurement[3, 0])**2)
        
        y = z - self.H @ self.x
        
        if self.last_measurement is not None:
            self.noise_profile.update(pos_error, vel_error, y.flatten())
        
        pos_var, vel_var, R_dynamic = self.noise_profile.get_variances()
        self.R = R_dynamic.copy()
        self.R[0, 0] = max(self.R[0, 0], pos_var)
        self.R[1, 1] = max(self.R[1, 1], pos_var)
        self.R[2, 2] = max(self.R[2, 2], vel_var)
        self.R[3, 3] = max(self.R[3, 3], vel_var)
        
        S = self.H @ self.P @ self.H.T + self.R
        
        K = self.P @ self.H.T @ np.linalg.inv(S)
        
        self.x = self.x + K @ y
        
        self.P = (np.eye(self.state_dim) - K @ self.H) @ self.P
        
        self.last_measurement = z.copy()
        
        return self.x
    
    def get_state(self) -> Tuple[float, float, float, float]:
        lat = float(self.x[0, 0])
        lon = float(self.x[1, 0])
        vx = float(self.x[2, 0])
        vy = float(self.x[3, 0])
        speed = np.sqrt(vx**2 + vy**2)
        heading = np.degrees(np.arctan2(vy, vx))
        
        return lat, lon, speed, heading
    
    def predict_position(self, seconds: float) -> Tuple[float, float]:
        if not self.initialized:
            return 0.0, 0.0
        
        steps = int(seconds / self.dt)
        x_pred = self.x.copy()
        F = self.F.copy()
        
        for _ in range(steps):
            x_pred = F @ x_pred
        
        return float(x_pred[0, 0]), float(x_pred[1, 0])
    
    def get_uncertainty(self) -> Tuple[float, float]:
        lat_uncertainty = float(np.sqrt(self.P[0, 0]))
        lon_uncertainty = float(np.sqrt(self.P[1, 0]))
        
        return lat_uncertainty, lon_uncertainty


class BusKalmanTracker:
    def __init__(self):
        self.trackers: Dict[str, Dict[str, KalmanFilter]] = {}
        self.segment_noise_profiles: Dict[str, SegmentNoiseProfile] = {}
    
    def _get_segment_id(self, route_id: str, segment_idx: int) -> str:
        return f"{route_id}_seg_{segment_idx}"
    
    def update_bus(self, bus_id: str, lat: float, lon: float, speed: float, heading: float,
                   route_id: str = None, segment_idx: int = None, 
                   traffic_level: int = 0, stop_light_density: float = 0.0):
        if bus_id not in self.trackers:
            self.trackers[bus_id] = {}
        
        segment_id = self._get_segment_id(route_id, segment_idx) if route_id and segment_idx is not None else 'default'
        
        if segment_id not in self.trackers[bus_id]:
            self.trackers[bus_id][segment_id] = KalmanFilter(dt=2.0, segment_id=segment_id)
        
        tracker = self.trackers[bus_id][segment_id]
        tracker.set_segment_factors(traffic_level, stop_light_density)
        
        return tracker.update(lat, lon, speed, heading)
    
    def get_bus_state(self, bus_id: str, route_id: str = None, segment_idx: int = None) -> Optional[Tuple[float, float, float, float]]:
        if bus_id not in self.trackers:
            return None
        
        segment_id = self._get_segment_id(route_id, segment_idx) if route_id and segment_idx is not None else 'default'
        
        if segment_id not in self.trackers[bus_id]:
            if 'default' in self.trackers[bus_id]:
                return self.trackers[bus_id]['default'].get_state()
            return None
        
        return self.trackers[bus_id][segment_id].get_state()
    
    def predict_bus_position(self, bus_id: str, seconds: float, route_id: str = None, segment_idx: int = None) -> Optional[Tuple[float, float]]:
        if bus_id not in self.trackers:
            return None
        
        segment_id = self._get_segment_id(route_id, segment_idx) if route_id and segment_idx is not None else 'default'
        
        if segment_id not in self.trackers[bus_id]:
            if 'default' in self.trackers[bus_id]:
                return self.trackers[bus_id]['default'].predict_position(seconds)
            return None
        
        return self.trackers[bus_id][segment_id].predict_position(seconds)
    
    def estimate_arrival_time(self, bus_id: str, target_lat: float, target_lon: float, 
                              distance_meters: float, route_id: str = None, segment_idx: int = None,
                              stop_light_delay: float = 0.0) -> Optional[float]:
        if bus_id not in self.trackers:
            return None
        
        segment_id = self._get_segment_id(route_id, segment_idx) if route_id and segment_idx is not None else 'default'
        
        if segment_id not in self.trackers[bus_id]:
            if 'default' in self.trackers[bus_id]:
                tracker = self.trackers[bus_id]['default']
            else:
                return None
        else:
            tracker = self.trackers[bus_id][segment_id]
        
        lat, lon, speed, heading = tracker.get_state()
        
        if speed < 0.5:
            speed = 5.0
        
        if distance_meters < 10:
            return 0.0
        
        travel_time = distance_meters / (speed * 1000 / 3600)
        total_time = travel_time + stop_light_delay
        
        return max(0, total_time)
    
    def get_segment_noise_stats(self, route_id: str, segment_idx: int) -> Optional[Dict]:
        segment_id = self._get_segment_id(route_id, segment_idx)
        if segment_id not in self.segment_noise_profiles:
            return None
        
        profile = self.segment_noise_profiles[segment_id]
        pos_var, vel_var, R = profile.get_variances()
        
        return {
            'segment_id': segment_id,
            'position_variance': pos_var,
            'velocity_variance': vel_var,
            'sample_count': len(profile.position_errors)
        }
