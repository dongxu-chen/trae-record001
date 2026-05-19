import numpy as np
from typing import Optional, Tuple, Dict, List, Set
from collections import defaultdict
from .trajectory_reader import TrajectoryReader


class HydrogenBondAnalyzer:
    def __init__(self, trajectory_reader: TrajectoryReader):
        self.trajectory_reader = trajectory_reader
        self.hbond_counts = None
        self.time_array = None
        self.hbond_details = []
        self.hbond_lifetime = {}

    @staticmethod
    def _calculate_distance(p1: np.ndarray, p2: np.ndarray) -> float:
        return np.linalg.norm(p1 - p2)

    @staticmethod
    def _calculate_angle(donor_pos: np.ndarray, 
                        hydrogen_pos: np.ndarray, 
                        acceptor_pos: np.ndarray) -> float:
        v1 = hydrogen_pos - donor_pos
        v2 = acceptor_pos - hydrogen_pos
        
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle = np.arccos(cos_angle) * 180.0 / np.pi
        
        return angle

    @staticmethod
    def _is_hbond(donor_pos: np.ndarray, 
                  hydrogen_pos: np.ndarray, 
                  acceptor_pos: np.ndarray,
                  distance_cutoff: float = 3.5,
                  angle_cutoff: float = 120.0) -> bool:
        distance = np.linalg.norm(acceptor_pos - hydrogen_pos)
        
        if distance > distance_cutoff:
            return False
        
        v1 = hydrogen_pos - donor_pos
        v2 = acceptor_pos - hydrogen_pos
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle = np.arccos(cos_angle) * 180.0 / np.pi
        
        return angle >= angle_cutoff

    def find_donors_acceptors(self, 
                              donor_sel: str = "name N O and backbone",
                              acceptor_sel: str = "name N O and backbone",
                              hydrogen_sel: str = "name H* HN*") -> Tuple[Dict, Dict]:
        if self.trajectory_reader.universe is None:
            raise ValueError("Trajectory not loaded. Call load() first.")
        
        u = self.trajectory_reader.universe
        donors = u.select_atoms(donor_sel)
        acceptors = u.select_atoms(acceptor_sel)
        hydrogens = u.select_atoms(hydrogen_sel)
        
        donor_hydrogen_map = {}
        for donor in donors:
            bonded_h = []
            for h in hydrogens:
                if donor in h.bonded_atoms:
                    bonded_h.append(h)
            if bonded_h:
                donor_hydrogen_map[donor] = bonded_h
        
        acceptor_dict = {acc: acc for acc in acceptors}
        
        return donor_hydrogen_map, acceptor_dict

    def calculate(self,
                  donor_sel: str = "name N O",
                  acceptor_sel: str = "name N O",
                  hydrogen_sel: str = "name H* HN*",
                  distance_cutoff: float = 3.5,
                  angle_cutoff: float = 120.0,
                  start: int = 0,
                  stop: Optional[int] = None,
                  step: int = 1,
                  track_lifetime: bool = False) -> dict:
        if self.trajectory_reader.universe is None:
            raise ValueError("Trajectory not loaded. Call load() first.")
        
        u = self.trajectory_reader.universe
        
        donor_hydrogen_map, acceptor_dict = self.find_donors_acceptors(
            donor_sel, acceptor_sel, hydrogen_sel
        )
        
        donors = list(donor_hydrogen_map.keys())
        acceptors = list(acceptor_dict.keys())
        
        if stop is None:
            stop = len(u.trajectory)
        
        self.time_array = []
        self.hbond_counts = []
        self.hbond_details = []
        
        if track_lifetime:
            previous_hbonds = set()
            hbond_start_frames = {}
        
        for frame_idx in range(start, stop, step):
            ts = u.trajectory[frame_idx]
            self.time_array.append(ts.time)
            
            current_hbonds = set()
            frame_hbonds = []
            
            for donor in donors:
                donor_pos = donor.position
                
                for hydrogen in donor_hydrogen_map[donor]:
                    hydrogen_pos = hydrogen.position
                    
                    for acceptor in acceptors:
                        if donor == acceptor:
                            continue
                        
                        acceptor_pos = acceptor.position
                        
                        if self._is_hbond(donor_pos, hydrogen_pos, acceptor_pos,
                                         distance_cutoff, angle_cutoff):
                            hbond_key = (donor.index, hydrogen.index, acceptor.index)
                            current_hbonds.add(hbond_key)
                            
                            distance = np.linalg.norm(acceptor_pos - hydrogen_pos)
                            angle = self._calculate_angle(donor_pos, hydrogen_pos, acceptor_pos)
                            
                            frame_hbonds.append({
                                "donor_idx": donor.index,
                                "donor_name": donor.name,
                                "donor_resname": donor.resname,
                                "donor_resid": donor.resid,
                                "hydrogen_idx": hydrogen.index,
                                "hydrogen_name": hydrogen.name,
                                "acceptor_idx": acceptor.index,
                                "acceptor_name": acceptor.name,
                                "acceptor_resname": acceptor.resname,
                                "acceptor_resid": acceptor.resid,
                                "distance": float(distance),
                                "angle": float(angle)
                            })
            
            self.hbond_counts.append(len(frame_hbonds))
            self.hbond_details.append(frame_hbonds)
            
            if track_lifetime:
                for hbond_key in current_hbonds - previous_hbonds:
                    hbond_start_frames[hbond_key] = frame_idx
                
                for hbond_key in previous_hbonds - current_hbonds:
                    if hbond_key in hbond_start_frames:
                        start_frame = hbond_start_frames.pop(hbond_key)
                        lifetime = frame_idx - start_frame
                        if hbond_key not in self.hbond_lifetime:
                            self.hbond_lifetime[hbond_key] = []
                        self.hbond_lifetime[hbond_key].append(lifetime)
                
                previous_hbonds = current_hbonds.copy()
        
        self.time_array = np.array(self.time_array)
        self.hbond_counts = np.array(self.hbond_counts)
        
        return {
            "time": self.time_array,
            "hbond_counts": self.hbond_counts,
            "distance_cutoff": distance_cutoff,
            "angle_cutoff": angle_cutoff
        }

    def calculate_streaming(self,
                           donor_sel: str = "name N O",
                           acceptor_sel: str = "name N O",
                           hydrogen_sel: str = "name H* HN*",
                           distance_cutoff: float = 3.5,
                           angle_cutoff: float = 120.0,
                           chunk_size: int = 100) -> dict:
        if self.trajectory_reader.universe is None:
            raise ValueError("Trajectory not loaded. Call load() first.")
        
        u = self.trajectory_reader.universe
        n_frames = len(u.trajectory)
        
        donor_hydrogen_map, acceptor_dict = self.find_donors_acceptors(
            donor_sel, acceptor_sel, hydrogen_sel
        )
        
        donors = list(donor_hydrogen_map.keys())
        acceptors = list(acceptor_dict.keys())
        
        all_times = []
        all_counts = []
        
        for chunk_start in range(0, n_frames, chunk_size):
            chunk_end = min(chunk_start + chunk_size, n_frames)
            chunk_times = []
            chunk_counts = []
            
            for frame_idx in range(chunk_start, chunk_end):
                ts = u.trajectory[frame_idx]
                chunk_times.append(ts.time)
                
                count = 0
                for donor in donors:
                    donor_pos = donor.position
                    
                    for hydrogen in donor_hydrogen_map[donor]:
                        hydrogen_pos = hydrogen.position
                        
                        for acceptor in acceptors:
                            if donor == acceptor:
                                continue
                            
                            acceptor_pos = acceptor.position
                            
                            if self._is_hbond(donor_pos, hydrogen_pos, acceptor_pos,
                                             distance_cutoff, angle_cutoff):
                                count += 1
                
                chunk_counts.append(count)
            
            all_times.extend(chunk_times)
            all_counts.extend(chunk_counts)
        
        self.time_array = np.array(all_times)
        self.hbond_counts = np.array(all_counts)
        
        return {
            "time": self.time_array,
            "hbond_counts": self.hbond_counts,
            "distance_cutoff": distance_cutoff,
            "angle_cutoff": angle_cutoff
        }

    def get_hbond_frequency(self) -> Dict[Tuple, float]:
        if not self.hbond_details:
            raise ValueError("Hbond analysis not run. Call calculate() first.")
        
        hbond_counts = defaultdict(int)
        total_frames = len(self.hbond_details)
        
        for frame_hbonds in self.hbond_details:
            for hbond in frame_hbonds:
                hbond_id = (
                    hbond["donor_resid"], hbond["donor_name"],
                    hbond["acceptor_resid"], hbond["acceptor_name"]
                )
                hbond_counts[hbond_id] += 1
        
        hbond_frequencies = {}
        for hbond_id, count in hbond_counts.items():
            hbond_frequencies[hbond_id] = count / total_frames
        
        return dict(sorted(hbond_frequencies.items(), key=lambda x: x[1], reverse=True))

    def get_statistics(self) -> dict:
        if self.hbond_counts is None:
            raise ValueError("Hbond analysis not run. Call calculate() first.")
        
        return {
            "mean": float(np.mean(self.hbond_counts)),
            "std": float(np.std(self.hbond_counts)),
            "min": int(np.min(self.hbond_counts)),
            "max": int(np.max(self.hbond_counts)),
            "median": float(np.median(self.hbond_counts))
        }

    def get_lifetime_statistics(self) -> dict:
        if not self.hbond_lifetime:
            raise ValueError("Lifetime tracking not enabled. Call calculate() with track_lifetime=True.")
        
        all_lifetimes = []
        for lifetimes in self.hbond_lifetime.values():
            all_lifetimes.extend(lifetimes)
        
        if not all_lifetimes:
            return {"mean": 0, "std": 0, "min": 0, "max": 0, "total_count": 0}
        
        return {
            "mean": float(np.mean(all_lifetimes)),
            "std": float(np.std(all_lifetimes)),
            "min": int(np.min(all_lifetimes)),
            "max": int(np.max(all_lifetimes)),
            "total_count": len(all_lifetimes)
        }

    def get_hbond_array(self) -> Tuple[np.ndarray, np.ndarray]:
        if self.hbond_counts is None or self.time_array is None:
            raise ValueError("Hbond analysis not run. Call calculate() first.")
        return self.time_array, self.hbond_counts
