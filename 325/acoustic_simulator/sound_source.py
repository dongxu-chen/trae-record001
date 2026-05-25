import numpy as np
from typing import List, Tuple, Optional, Union, Callable
from dataclasses import dataclass, field


@dataclass
class SoundSource:
    position: np.ndarray
    signal: Optional[np.ndarray] = None
    delay: float = 0.0
    amplitude: float = 1.0
    source_id: int = field(default_factory=lambda: SoundSource._next_id())
    frequency: Optional[float] = None

    _id_counter = 0

    @classmethod
    def _next_id(cls) -> int:
        cls._id_counter += 1
        return cls._id_counter - 1

    def __post_init__(self):
        self.position = np.asarray(self.position, dtype=np.float64)
        if self.signal is not None:
            self.signal = np.asarray(self.signal, dtype=np.float64)

    def generate_tone(self, frequency: float, duration: float, fs: int,
                      amplitude: float = 1.0, phase: float = 0.0) -> np.ndarray:
        self.frequency = frequency
        t = np.arange(int(duration * fs)) / fs
        self.signal = amplitude * np.sin(2 * np.pi * frequency * t + phase)
        return self.signal

    def generate_impulse(self, fs: int, amplitude: float = 1.0) -> np.ndarray:
        self.signal = np.zeros(1)
        self.signal[0] = amplitude
        return self.signal

    def generate_noise(self, duration: float, fs: int,
                       amplitude: float = 1.0, noise_type: str = "white") -> np.ndarray:
        n_samples = int(duration * fs)
        if noise_type == "white":
            self.signal = amplitude * np.random.randn(n_samples)
        elif noise_type == "pink":
            self.signal = amplitude * self._pink_noise(n_samples)
        else:
            raise ValueError(f"Unknown noise type: {noise_type}")
        return self.signal

    @staticmethod
    def _pink_noise(n_samples: int) -> np.ndarray:
        b0 = b1 = b2 = b3 = b4 = b5 = b6 = 0.0
        out = np.zeros(n_samples)
        for i in range(n_samples):
            white = np.random.randn()
            b0 = 0.99886 * b0 + white * 0.0555179
            b1 = 0.99332 * b1 + white * 0.0750759
            b2 = 0.96900 * b2 + white * 0.1538520
            b3 = 0.86650 * b3 + white * 0.3104856
            b4 = 0.55000 * b4 + white * 0.5329522
            b5 = -0.7616 * b5 - white * 0.0168980
            out[i] = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362
            b6 = white * 0.115926
        return out

    def copy(self) -> 'SoundSource':
        return SoundSource(
            position=self.position.copy(),
            signal=self.signal.copy() if self.signal is not None else None,
            delay=self.delay,
            amplitude=self.amplitude,
            frequency=self.frequency
        )


@dataclass
class DynamicSource(SoundSource):
    trajectory: Optional[Callable[[float], np.ndarray]] = None
    velocity: Optional[np.ndarray] = None
    start_time: float = 0.0
    end_time: float = 1.0

    def __post_init__(self):
        super().__post_init__()
        if self.trajectory is None and self.velocity is not None:
            self.velocity = np.asarray(self.velocity, dtype=np.float64)
            self.trajectory = lambda t: self.position + self.velocity * (t - self.start_time)

    def get_position(self, time: float) -> np.ndarray:
        if self.trajectory is None:
            return self.position
        if self.velocity is not None:
            t = np.clip(time, self.start_time, self.end_time)
        else:
            t = time
        return np.asarray(self.trajectory(t), dtype=np.float64)

    def set_linear_trajectory(self, start_pos: np.ndarray, end_pos: np.ndarray,
                              duration: float, start_time: float = 0.0):
        start_pos = np.asarray(start_pos, dtype=np.float64)
        end_pos = np.asarray(end_pos, dtype=np.float64)
        self.start_time = start_time
        self.end_time = start_time + duration
        self.position = start_pos

        def linear_traj(t):
            alpha = (t - start_time) / duration if duration > 0 else 0.0
            alpha = np.clip(alpha, 0.0, 1.0)
            return start_pos + alpha * (end_pos - start_pos)

        self.trajectory = linear_traj
        self.velocity = (end_pos - start_pos) / duration if duration > 0 else np.zeros_like(start_pos)

    def set_circular_trajectory(self, center: np.ndarray, radius: float,
                                angular_velocity: float, start_time: float = 0.0,
                                duration: float = 10.0, start_angle: float = 0.0):
        center = np.asarray(center, dtype=np.float64)
        self.start_time = start_time
        self.end_time = start_time + duration

        def circular_traj(t):
            theta = start_angle + angular_velocity * (t - start_time)
            pos = center.copy()
            pos[0] += radius * np.cos(theta)
            pos[1] += radius * np.sin(theta)
            return pos

        self.trajectory = circular_traj

    def set_sinusoidal_trajectory(self, center: np.ndarray, amplitude: np.ndarray,
                                  frequency: float, start_time: float = 0.0,
                                  duration: float = 10.0, phase: float = 0.0):
        center = np.asarray(center, dtype=np.float64)
        amplitude = np.asarray(amplitude, dtype=np.float64)
        self.start_time = start_time
        self.end_time = start_time + duration

        def sinusoidal_traj(t):
            t_rel = t - start_time
            return center + amplitude * np.sin(2 * np.pi * frequency * t_rel + phase)

        self.trajectory = sinusoidal_traj

    def copy(self) -> 'DynamicSource':
        new_source = DynamicSource(
            position=self.position.copy(),
            signal=self.signal.copy() if self.signal is not None else None,
            delay=self.delay,
            amplitude=self.amplitude,
            trajectory=self.trajectory,
            velocity=self.velocity.copy() if self.velocity is not None else None,
            start_time=self.start_time,
            end_time=self.end_time,
            frequency=self.frequency
        )
        return new_source


class SourceManager:
    def __init__(self):
        self._sources: List[Union[SoundSource, DynamicSource]] = []

    def add_source(self, source: Union[SoundSource, DynamicSource]) -> int:
        self._sources.append(source)
        return source.source_id

    def remove_source(self, source_id: int) -> bool:
        for i, src in enumerate(self._sources):
            if src.source_id == source_id:
                del self._sources[i]
                return True
        return False

    def get_source(self, source_id: int) -> Optional[Union[SoundSource, DynamicSource]]:
        for src in self._sources:
            if src.source_id == source_id:
                return src
        return None

    def get_all_sources(self) -> List[Union[SoundSource, DynamicSource]]:
        return self._sources.copy()

    def get_positions(self, time: Optional[float] = None) -> np.ndarray:
        positions = []
        for src in self._sources:
            if time is not None and isinstance(src, DynamicSource):
                positions.append(src.get_position(time))
            else:
                positions.append(src.position)
        return np.array(positions)

    def get_signals(self, fs: Optional[int] = None, default_duration: float = 1.0) -> List[np.ndarray]:
        signals = []
        for src in self._sources:
            if src.signal is not None:
                signals.append(src.signal * src.amplitude)
            elif fs is not None:
                sig = src.generate_impulse(fs, src.amplitude)
                signals.append(sig)
            else:
                raise ValueError(f"Source {src.source_id} has no signal and fs not provided")
        return signals

    def __len__(self) -> int:
        return len(self._sources)

    def __iter__(self):
        return iter(self._sources)

    def __getitem__(self, idx: int) -> Union[SoundSource, DynamicSource]:
        return self._sources[idx]
