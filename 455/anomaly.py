import numpy as np
from typing import Dict, List, Optional, Tuple
from collections import deque
from enum import Enum

from config import Config


class AnomalyType(Enum):
    LOITERING = "loitering"
    WRONG_DIRECTION = "wrong_direction"
    SPEED_ANOMALY = "speed_anomaly"
    SUDDEN_STOP = "sudden_stop"
    SUDDEN_ACCELERATION = "sudden_acceleration"


class AnomalyEvent:
    def __init__(
        self,
        track_id: int,
        anomaly_type: AnomalyType,
        confidence: float,
        position: Tuple[float, float],
        frame_index: int,
        details: Optional[Dict] = None,
    ):
        self.track_id = track_id
        self.anomaly_type = anomaly_type
        self.confidence = confidence
        self.position = position
        self.frame_index = frame_index
        self.details = details or {}

    def to_dict(self) -> Dict:
        return {
            "track_id": self.track_id,
            "anomaly_type": self.anomaly_type.value,
            "confidence": round(self.confidence, 3),
            "position": [round(self.position[0], 1), round(self.position[1], 1)],
            "frame_index": self.frame_index,
            "details": self.details,
        }


class TrackStatistics:
    def __init__(self, track_id: int, max_history: int = 200):
        self.track_id = track_id
        self.positions: deque = deque(maxlen=max_history)
        self.velocities: deque = deque(maxlen=max_history)
        self.speeds: deque = deque(maxlen=max_history)
        self.frame_indices: deque = deque(maxlen=max_history)
        self.directions: deque = deque(maxlen=max_history)
        self.mean_speed = 0.0
        self.std_speed = 1.0

    def update(
        self,
        position: Tuple[float, float],
        velocity: Tuple[float, float],
        frame_index: int,
    ):
        speed = np.sqrt(velocity[0] ** 2 + velocity[1] ** 2)
        direction = np.arctan2(velocity[1], velocity[0])

        self.positions.append(position)
        self.velocities.append(velocity)
        self.speeds.append(speed)
        self.frame_indices.append(frame_index)
        self.directions.append(direction)

        if len(self.speeds) >= 3:
            speeds_arr = np.array(list(self.speeds))
            self.mean_speed = np.mean(speeds_arr)
            self.std_speed = np.std(speeds_arr) + 1e-6


class AnomalyDetector:
    def __init__(
        self,
        loitering_dist_threshold: Optional[float] = None,
        loitering_time_threshold: Optional[int] = None,
        wrong_dir_angle_threshold: Optional[float] = None,
        wrong_dir_min_speed: Optional[float] = None,
        speed_anomaly_multiplier: Optional[float] = None,
        trail_min_length: Optional[int] = None,
    ):
        self.loitering_dist_threshold = loitering_dist_threshold or Config.LOITERING_DISTANCE_THRESHOLD
        self.loitering_time_threshold = loitering_time_threshold or Config.LOITERING_TIME_THRESHOLD
        self.wrong_dir_angle_threshold = wrong_dir_angle_threshold or Config.WRONG_DIRECTION_ANGLE_THRESHOLD
        self.wrong_dir_min_speed = wrong_dir_min_speed or Config.WRONG_DIRECTION_MIN_SPEED
        self.speed_anomaly_multiplier = speed_anomaly_multiplier or Config.SPEED_ANOMALY_MULTIPLIER
        self.trail_min_length = trail_min_length or Config.ANOMALY_TRAIL_MIN_LENGTH

        self.track_stats: Dict[int, TrackStatistics] = {}
        self.prev_directions: Dict[int, float] = {}
        self.active_anomalies: Dict[int, List[AnomalyType]] = {}
        self.anomaly_events: deque = deque(maxlen=1000)

    def update_track(
        self,
        track_id: int,
        position: Tuple[float, float],
        velocity: Tuple[float, float],
        frame_index: int,
    ) -> List[AnomalyEvent]:
        if track_id not in self.track_stats:
            self.track_stats[track_id] = TrackStatistics(track_id)

        stats = self.track_stats[track_id]
        stats.update(position, velocity, frame_index)

        events = []

        if len(stats.positions) < self.trail_min_length:
            return events

        loitering_event = self._check_loitering(stats, frame_index)
        if loitering_event:
            events.append(loitering_event)

        direction_event = self._check_wrong_direction(stats, frame_index)
        if direction_event:
            events.append(direction_event)

        speed_event = self._check_speed_anomaly(stats, frame_index)
        if speed_event:
            events.append(speed_event)

        stop_event = self._check_sudden_stop(stats, frame_index)
        if stop_event:
            events.append(stop_event)

        accel_event = self._check_sudden_acceleration(stats, frame_index)
        if accel_event:
            events.append(accel_event)

        self.active_anomalies[track_id] = [e.anomaly_type for e in events]

        for event in events:
            self.anomaly_events.append(event)

        return events

    def _check_loitering(
        self,
        stats: TrackStatistics,
        frame_index: int,
    ) -> Optional[AnomalyEvent]:
        positions = list(stats.positions)
        frames = list(stats.frame_indices)

        if len(frames) < self.loitering_time_threshold:
            return None

        recent_positions = positions[-self.loitering_time_threshold:]
        recent_frames = frames[-self.loitering_time_threshold:]

        time_span = recent_frames[-1] - recent_frames[0]
        if time_span < self.loitering_time_threshold * 0.5:
            return None

        positions_arr = np.array(recent_positions)
        centroid = np.mean(positions_arr, axis=0)
        distances = np.sqrt(np.sum((positions_arr - centroid) ** 2, axis=1))
        max_distance = np.max(distances)

        if max_distance < self.loitering_dist_threshold:
            mean_dist = np.mean(distances)
            confidence = 1.0 - (mean_dist / self.loitering_dist_threshold)
            confidence = max(0.0, min(1.0, confidence))

            return AnomalyEvent(
                track_id=stats.track_id,
                anomaly_type=AnomalyType.LOITERING,
                confidence=confidence,
                position=tuple(centroid),
                frame_index=frame_index,
                details={
                    "max_displacement": round(float(max_distance), 2),
                    "time_span": int(time_span),
                    "centroid": [round(float(centroid[0]), 1), round(float(centroid[1]), 1)],
                },
            )

        return None

    def _check_wrong_direction(
        self,
        stats: TrackStatistics,
        frame_index: int,
    ) -> Optional[AnomalyEvent]:
        if len(stats.directions) < 3:
            return None

        current_speed = stats.speeds[-1]
        if current_speed < self.wrong_dir_min_speed:
            return None

        recent_directions = list(stats.directions)
        prev_dir = recent_directions[-2]
        curr_dir = recent_directions[-1]

        angle_diff = np.abs(curr_dir - prev_dir)
        if angle_diff > np.pi:
            angle_diff = 2 * np.pi - angle_diff

        angle_degrees = np.degrees(angle_diff)

        if angle_degrees > self.wrong_dir_angle_threshold:
            confidence = angle_degrees / 180.0
            confidence = max(0.0, min(1.0, confidence))

            return AnomalyEvent(
                track_id=stats.track_id,
                anomaly_type=AnomalyType.WRONG_DIRECTION,
                confidence=confidence,
                position=stats.positions[-1],
                frame_index=frame_index,
                details={
                    "angle_change": round(float(angle_degrees), 1),
                    "prev_direction": round(float(np.degrees(prev_dir)), 1),
                    "curr_direction": round(float(np.degrees(curr_dir)), 1),
                    "speed": round(float(current_speed), 2),
                },
            )

        return None

    def _check_speed_anomaly(
        self,
        stats: TrackStatistics,
        frame_index: int,
    ) -> Optional[AnomalyEvent]:
        if len(stats.speeds) < 5:
            return None

        current_speed = stats.speeds[-1]
        expected_max = stats.mean_speed + self.speed_anomaly_multiplier * stats.std_speed

        if current_speed > expected_max and stats.mean_speed > 1.0:
            confidence = min(1.0, (current_speed - expected_max) / (expected_max + 1e-6))

            return AnomalyEvent(
                track_id=stats.track_id,
                anomaly_type=AnomalyType.SPEED_ANOMALY,
                confidence=confidence,
                position=stats.positions[-1],
                frame_index=frame_index,
                details={
                    "current_speed": round(float(current_speed), 2),
                    "mean_speed": round(float(stats.mean_speed), 2),
                    "expected_max": round(float(expected_max), 2),
                },
            )

        return None

    def _check_sudden_stop(
        self,
        stats: TrackStatistics,
        frame_index: int,
    ) -> Optional[AnomalyEvent]:
        if len(stats.speeds) < 5:
            return None

        prev_speed = stats.speeds[-2]
        curr_speed = stats.speeds[-1]

        if prev_speed > stats.mean_speed * 0.8 and curr_speed < 0.5:
            speed_ratio = prev_speed / (curr_speed + 1e-6)
            confidence = min(1.0, speed_ratio / 10.0)

            return AnomalyEvent(
                track_id=stats.track_id,
                anomaly_type=AnomalyType.SUDDEN_STOP,
                confidence=confidence,
                position=stats.positions[-1],
                frame_index=frame_index,
                details={
                    "prev_speed": round(float(prev_speed), 2),
                    "curr_speed": round(float(curr_speed), 2),
                    "speed_ratio": round(float(speed_ratio), 2),
                },
            )

        return None

    def _check_sudden_acceleration(
        self,
        stats: TrackStatistics,
        frame_index: int,
    ) -> Optional[AnomalyEvent]:
        if len(stats.speeds) < 5:
            return None

        prev_speed = stats.speeds[-2]
        curr_speed = stats.speeds[-1]

        if prev_speed < 1.0 and curr_speed > stats.mean_speed * 2.0 and curr_speed > 5.0:
            accel_ratio = curr_speed / (prev_speed + 1e-6)
            confidence = min(1.0, accel_ratio / 10.0)

            return AnomalyEvent(
                track_id=stats.track_id,
                anomaly_type=AnomalyType.SUDDEN_ACCELERATION,
                confidence=confidence,
                position=stats.positions[-1],
                frame_index=frame_index,
                details={
                    "prev_speed": round(float(prev_speed), 2),
                    "curr_speed": round(float(curr_speed), 2),
                    "accel_ratio": round(float(accel_ratio), 2),
                },
            )

        return None

    def get_track_anomalies(self, track_id: int) -> List[AnomalyType]:
        return self.active_anomalies.get(track_id, [])

    def remove_track(self, track_id: int):
        self.track_stats.pop(track_id, None)
        self.prev_directions.pop(track_id, None)
        self.active_anomalies.pop(track_id, None)

    def get_recent_events(self, n: int = 20) -> List[Dict]:
        events = list(self.anomaly_events)[-n:]
        return [e.to_dict() for e in events]

    def reset(self):
        self.track_stats.clear()
        self.prev_directions.clear()
        self.active_anomalies.clear()
        self.anomaly_events.clear()
