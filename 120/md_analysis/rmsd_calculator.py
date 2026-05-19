import numpy as np
from MDAnalysis.analysis import align
from MDAnalysis.analysis.rms import RMSD
from typing import Optional, Tuple, Dict
from .trajectory_reader import TrajectoryReader


class RMSDCalculator:
    def __init__(self, trajectory_reader: TrajectoryReader):
        self.trajectory_reader = trajectory_reader
        self.rmsd_values = None
        self.time_array = None
        self._group_results = {}

    @staticmethod
    def _kabsch_align(A: np.ndarray, B: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        centroid_A = np.mean(A, axis=0)
        centroid_B = np.mean(B, axis=0)
        AA = A - centroid_A
        BB = B - centroid_B
        
        H = AA.T @ BB
        U, S, Vt = np.linalg.svd(H)
        
        if np.linalg.det(Vt.T @ U.T) < 0:
            Vt[-1, :] *= -1
        
        R = Vt.T @ U.T
        t = centroid_B - R @ centroid_A
        
        A_aligned = (R @ AA.T).T + centroid_B
        return A_aligned, R

    @staticmethod
    def _calculate_rmsd(A: np.ndarray, B: np.ndarray) -> float:
        diff = A - B
        return np.sqrt(np.mean(np.sum(diff ** 2, axis=1)))

    def calculate(self, 
                  reference_frame: int = 0,
                  selection: str = "backbone",
                  group_selections: Optional[Dict[str, str]] = None,
                  fit_superposition: bool = True,
                  center: bool = True,
                  verbose: bool = False) -> dict:
        if self.trajectory_reader.universe is None:
            raise ValueError("Trajectory not loaded. Call load() first.")
        
        u = self.trajectory_reader.universe
        ref_u = self.trajectory_reader.universe
        
        ref_u.trajectory[reference_frame]
        
        if fit_superposition:
            rmsd_analysis = RMSD(u, ref_u,
                                select=selection,
                                groupselections=list(group_selections.values()) if group_selections else None,
                                ref_frame=reference_frame,
                                center=center,
                                superposition=True,
                                verbose=verbose)
            rmsd_analysis.run()
            
            self.time_array = rmsd_analysis.results[:, 1]
            self.rmsd_values = rmsd_analysis.results[:, 2]
            
            if group_selections:
                for i, (group_name, _) in enumerate(group_selections.items()):
                    self._group_results[group_name] = rmsd_analysis.results[:, 3 + i]
        else:
            self.time_array = self.trajectory_reader.get_time_array()
            self.rmsd_values = []
            
            ref_atoms = ref_u.select_atoms(selection)
            ref_positions = ref_atoms.positions.copy()
            
            mobile_atoms = u.select_atoms(selection)
            
            for ts in u.trajectory:
                mob_positions = mobile_atoms.positions
                if center:
                    mob_centered = mob_positions - np.mean(mob_positions, axis=0)
                    ref_centered = ref_positions - np.mean(ref_positions, axis=0)
                    rmsd = self._calculate_rmsd(mob_centered, ref_centered)
                else:
                    rmsd = self._calculate_rmsd(mob_positions, ref_positions)
                self.rmsd_values.append(rmsd)
            
            self.rmsd_values = np.array(self.rmsd_values)
        
        results = {
            "time": self.time_array,
            "rmsd": self.rmsd_values,
            "selection": selection,
            "reference_frame": reference_frame,
            "fit_superposition": fit_superposition,
            "center": center
        }
        
        if group_selections:
            results["groups"] = self._group_results
        
        return results

    def calculate_streaming(self,
                            reference_frame: int = 0,
                            selection: str = "backbone",
                            start: int = 0,
                            stop: Optional[int] = None,
                            step: int = 1,
                            center: bool = True) -> dict:
        if self.trajectory_reader.universe is None:
            raise ValueError("Trajectory not loaded. Call load() first.")
        
        u = self.trajectory_reader.universe
        ref_u = self.trajectory_reader.universe
        
        ref_u.trajectory[reference_frame]
        ref_atoms = ref_u.select_atoms(selection)
        ref_positions = ref_atoms.positions.copy()
        ref_center = np.mean(ref_positions, axis=0)
        ref_centered = ref_positions - ref_center
        
        mobile_atoms = u.select_atoms(selection)
        
        times = []
        rmsd_values = []
        
        if stop is None:
            stop = len(u.trajectory)
        
        for i in range(start, stop, step):
            ts = u.trajectory[i]
            mob_positions = mobile_atoms.positions
            
            if center:
                mob_center = np.mean(mob_positions, axis=0)
                mob_centered = mob_positions - mob_center
                
                _, R = self._kabsch_align(mob_centered, ref_centered)
                mob_aligned = (R @ mob_centered.T).T
                
                rmsd = self._calculate_rmsd(mob_aligned, ref_centered)
            else:
                rmsd = self._calculate_rmsd(mob_positions, ref_positions)
            
            times.append(ts.time)
            rmsd_values.append(rmsd)
        
        self.time_array = np.array(times)
        self.rmsd_values = np.array(rmsd_values)
        
        return {
            "time": self.time_array,
            "rmsd": self.rmsd_values,
            "selection": selection,
            "reference_frame": reference_frame
        }

    def align_trajectory(self,
                        output_file: str,
                        selection: str = "backbone",
                        reference_frame: int = 0,
                        subselection: Optional[str] = None) -> None:
        if self.trajectory_reader.universe is None:
            raise ValueError("Trajectory not loaded. Call load() first.")
        
        u = self.trajectory_reader.universe
        ref_u = self.trajectory_reader.universe
        
        ref_u.trajectory[reference_frame]
        
        aligner = align.AlignTraj(u, ref_u,
                                 select=selection,
                                 filename=output_file,
                                 in_memory=False)
        aligner.run()

    def get_statistics(self) -> dict:
        if self.rmsd_values is None:
            raise ValueError("RMSD not calculated. Call calculate() first.")
        return {
            "mean": float(np.mean(self.rmsd_values)),
            "std": float(np.std(self.rmsd_values)),
            "min": float(np.min(self.rmsd_values)),
            "max": float(np.max(self.rmsd_values)),
            "median": float(np.median(self.rmsd_values))
        }

    def get_group_statistics(self, group_name: str) -> dict:
        if group_name not in self._group_results:
            raise ValueError(f"Group '{group_name}' not found. Available groups: {list(self._group_results.keys())}")
        
        values = self._group_results[group_name]
        return {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "median": float(np.median(values))
        }

    def get_rmsd_array(self) -> Tuple[np.ndarray, np.ndarray]:
        if self.rmsd_values is None or self.time_array is None:
            raise ValueError("RMSD not calculated. Call calculate() first.")
        return self.time_array, self.rmsd_values
