import numpy as np
from collections import deque
import time


class BeatLock:
    def __init__(
        self,
        sr=44100,
        lock_confidence_threshold=0.7,
        unlock_confidence_threshold=0.3,
        max_history=50,
    ):
        self.sr = sr
        self.lock_confidence_threshold = lock_confidence_threshold
        self.unlock_confidence_threshold = unlock_confidence_threshold
        self.max_history = max_history

        self.is_locked = False
        self.locked_bpm = 0.0
        self.locked_beat_time = 0.0
        self.lock_start_time = 0.0

        self.beat_times = deque(maxlen=max_history)
        self.bpm_history = deque(maxlen=max_history)
        self.confidence_history = deque(maxlen=max_history)

        self.next_predicted_beat = 0.0
        self.beat_interval = 0.5

        self.lock_counter = 0
        self.unlock_counter = 0
        self.lock_requirement = 5

    def update(self, beat_times, bpm, confidence, current_time):
        self.beat_times.extend(beat_times)
        self.bpm_history.append(bpm)
        self.confidence_history.append(confidence)

        if len(self.bpm_history) < 3:
            return self.is_locked, bpm

        if not self.is_locked:
            if confidence >= self.lock_confidence_threshold:
                self.lock_counter += 1
                self.unlock_counter = 0
                if self.lock_counter >= self.lock_requirement:
                    self._lock(bpm, current_time)
            else:
                self.lock_counter = max(0, self.lock_counter - 1)
        else:
            if confidence < self.unlock_confidence_threshold:
                self.unlock_counter += 1
                if self.unlock_counter >= 3:
                    self._unlock()
            else:
                self.unlock_counter = 0
                self._update_lock(bpm, current_time)

        if self.is_locked:
            self._predict_next_beat(current_time)
            return True, self.locked_bpm
        else:
            return False, bpm

    def _lock(self, bpm, current_time):
        self.is_locked = True
        self.locked_bpm = bpm
        self.beat_interval = 60.0 / bpm
        self.lock_start_time = current_time
        self.locked_beat_time = current_time
        self.lock_counter = 0
        self.unlock_counter = 0

        if len(self.beat_times) > 0:
            recent_beats = list(self.beat_times)[-10:]
            self.locked_beat_time = recent_beats[-1]

        self.next_predicted_beat = self.locked_beat_time + self.beat_interval

    def _unlock(self):
        self.is_locked = False
        self.locked_bpm = 0.0
        self.lock_counter = 0
        self.unlock_counter = 0

    def _update_lock(self, bpm, current_time):
        alpha = 0.1
        self.locked_bpm = (1 - alpha) * self.locked_bpm + alpha * bpm
        self.beat_interval = 60.0 / self.locked_bpm

        if len(self.beat_times) > 0:
            recent_beats = list(self.beat_times)[-5:]
            for bt in recent_beats:
                if bt > self.locked_beat_time + self.beat_interval * 0.5:
                    time_diff = bt - self.next_predicted_beat
                    if abs(time_diff) < self.beat_interval * 0.3:
                        self.locked_beat_time = bt
                        break

    def _predict_next_beat(self, current_time):
        while self.next_predicted_beat <= current_time:
            self.next_predicted_beat += self.beat_interval

    def get_next_beat_time(self, current_time):
        if not self.is_locked:
            return None

        while self.next_predicted_beat <= current_time:
            self.next_predicted_beat += self.beat_interval

        return self.next_predicted_beat

    def get_beat_phase(self, current_time):
        if not self.is_locked:
            return 0.0

        time_since_last = current_time - self.locked_beat_time
        phase = (time_since_last % self.beat_interval) / self.beat_interval
        return phase

    def is_beat_soon(self, current_time, threshold=0.05):
        if not self.is_locked:
            return False

        next_beat = self.get_next_beat_time(current_time)
        if next_beat is None:
            return False

        time_until = next_beat - current_time
        return 0 <= time_until < threshold

    def get_lock_status(self):
        return {
            'is_locked': self.is_locked,
            'locked_bpm': self.locked_bpm,
            'beat_interval': self.beat_interval,
            'lock_duration': time.time() - self.lock_start_time if self.is_locked else 0,
            'next_beat': self.next_predicted_beat,
        }

    def reset(self):
        self.is_locked = False
        self.locked_bpm = 0.0
        self.locked_beat_time = 0.0
        self.lock_start_time = 0.0
        self.beat_times.clear()
        self.bpm_history.clear()
        self.confidence_history.clear()
        self.next_predicted_beat = 0.0
        self.beat_interval = 0.5
        self.lock_counter = 0
        self.unlock_counter = 0

    def force_lock(self, bpm, current_time):
        self._lock(bpm, current_time)

    def force_unlock(self):
        self._unlock()


class AdaptiveBeatLock(BeatLock):
    def __init__(
        self,
        sr=44100,
        lock_confidence_threshold=0.7,
        unlock_confidence_threshold=0.3,
        max_history=50,
    ):
        super().__init__(
            sr=sr,
            lock_confidence_threshold=lock_confidence_threshold,
            unlock_confidence_threshold=unlock_confidence_threshold,
            max_history=max_history,
        )
        self.style_patterns = {}
        self.current_style = 'generic'

    def update(self, beat_times, bpm, confidence, current_time, style='generic'):
        self.current_style = style

        if style in self.style_patterns:
            pattern = self.style_patterns[style]
            adjusted_bpm = bpm * pattern.get('bpm_scale', 1.0)
        else:
            adjusted_bpm = bpm

        return super().update(beat_times, adjusted_bpm, confidence, current_time)

    def register_style_pattern(self, style_name, bpm_scale=1.0, lock_threshold=None):
        self.style_patterns[style_name] = {
            'bpm_scale': bpm_scale,
            'lock_threshold': lock_threshold,
        }

    def get_stable_bpm(self, window=10):
        if len(self.bpm_history) < window:
            window = len(self.bpm_history)

        if window == 0:
            return 0.0

        recent_bpms = list(self.bpm_history)[-window:]
        return np.median(recent_bpms)

    def get_bpm_variability(self, window=10):
        if len(self.bpm_history) < window:
            window = len(self.bpm_history)

        if window < 2:
            return 0.0

        recent_bpms = list(self.bpm_history)[-window:]
        return np.std(recent_bpms) / np.mean(recent_bpms) if np.mean(recent_bpms) > 0 else 0
