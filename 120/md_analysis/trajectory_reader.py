import MDAnalysis as mda
import numpy as np
from typing import Optional, Tuple, Iterator, Callable, Any


class TrajectoryReader:
    def __init__(self, topology_file: str, trajectory_file: str):
        self.topology_file = topology_file
        self.trajectory_file = trajectory_file
        self.universe = None
        self._n_frames = None
        self._n_atoms = None
        self._dt = None
        self._totaltime = None

    def load(self, in_memory: bool = False) -> None:
        if in_memory:
            self.universe = mda.Universe(self.topology_file, self.trajectory_file, in_memory=True)
        else:
            self.universe = mda.Universe(self.topology_file, self.trajectory_file)
        
        self._n_frames = len(self.universe.trajectory)
        self._n_atoms = self.universe.atoms.n_atoms
        
        try:
            self._dt = self.universe.trajectory.dt
            self._totaltime = self.universe.trajectory.totaltime
        except (AttributeError, NotImplementedError):
            if self._n_frames > 1:
                t0 = self.universe.trajectory[0].time
                t1 = self.universe.trajectory[1].time
                self._dt = t1 - t0
                self._totaltime = t0 + self._dt * (self._n_frames - 1)
            else:
                self._dt = 0.0
                self._totaltime = 0.0

    @property
    def n_frames(self) -> int:
        return self._n_frames

    @property
    def n_atoms(self) -> int:
        return self._n_atoms

    def get_frame(self, frame_index: int) -> np.ndarray:
        if self.universe is None:
            raise ValueError("Trajectory not loaded. Call load() first.")
        self.universe.trajectory[frame_index]
        return self.universe.atoms.positions.copy()

    def iterate_frames(self, 
                       start: int = 0,
                       stop: Optional[int] = None,
                       step: int = 1,
                       selection: str = "all") -> Iterator[Tuple[int, float, np.ndarray]]:
        if self.universe is None:
            raise ValueError("Trajectory not loaded. Call load() first.")
        
        atoms = self.universe.select_atoms(selection)
        trajectory = self.universe.trajectory
        
        if stop is None:
            stop = len(trajectory)
        
        for i in range(start, stop, step):
            ts = trajectory[i]
            yield i, ts.time, atoms.positions.copy()

    def process_frames(self,
                       callback: Callable[[int, float, np.ndarray], Any],
                       start: int = 0,
                       stop: Optional[int] = None,
                       step: int = 1,
                       selection: str = "all") -> list:
        if self.universe is None:
            raise ValueError("Trajectory not loaded. Call load() first.")
        
        results = []
        for frame_idx, time, positions in self.iterate_frames(start, stop, step, selection):
            result = callback(frame_idx, time, positions)
            results.append(result)
        return results

    def get_coordinates_stream(self, 
                               selection: str = "all",
                               chunk_size: int = 100) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        if self.universe is None:
            raise ValueError("Trajectory not loaded. Call load() first.")
        
        atoms = self.universe.select_atoms(selection)
        trajectory = self.universe.trajectory
        n_frames = len(trajectory)
        
        for chunk_start in range(0, n_frames, chunk_size):
            chunk_end = min(chunk_start + chunk_size, n_frames)
            chunk_times = []
            chunk_coords = []
            
            for i in range(chunk_start, chunk_end):
                ts = trajectory[i]
                chunk_times.append(ts.time)
                chunk_coords.append(atoms.positions.copy())
            
            yield np.array(chunk_times), np.array(chunk_coords)

    def get_selection(self, selection: str = "all"):
        if self.universe is None:
            raise ValueError("Trajectory not loaded. Call load() first.")
        return self.universe.select_atoms(selection)

    def get_time_array(self) -> np.ndarray:
        if self.universe is None:
            raise ValueError("Trajectory not loaded. Call load() first.")
        
        times = []
        for ts in self.universe.trajectory:
            times.append(ts.time)
        return np.array(times)

    def get_box_dimensions(self) -> np.ndarray:
        if self.universe is None:
            raise ValueError("Trajectory not loaded. Call load() first.")
        
        boxes = []
        for ts in self.universe.trajectory:
            boxes.append(ts.dimensions[:3])
        return np.array(boxes)

    def summary(self) -> dict:
        return {
            "topology_file": self.topology_file,
            "trajectory_file": self.trajectory_file,
            "n_frames": self._n_frames,
            "n_atoms": self._n_atoms,
            "time_step": self._dt,
            "total_time": self._totaltime,
            "in_memory": getattr(self.universe.trajectory, 'in_memory', False)
        }
