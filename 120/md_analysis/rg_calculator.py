import numpy as np
from typing import Optional, Tuple, Dict
from .trajectory_reader import TrajectoryReader


class RgCalculator:
    def __init__(self, trajectory_reader: TrajectoryReader):
        self.trajectory_reader = trajectory_reader
        self.rg_values = None
        self.time_array = None

    @staticmethod
    def _calculate_rg(positions: np.ndarray, masses: Optional[np.ndarray] = None) -> float:
        if masses is None:
            masses = np.ones(positions.shape[0])
        
        total_mass = np.sum(masses)
        center_of_mass = np.sum(masses[:, np.newaxis] * positions, axis=0) / total_mass
        
        squared_distances = np.sum((positions - center_of_mass) ** 2, axis=1)
        weighted_sq_dist = np.sum(masses * squared_distances) / total_mass
        
        return np.sqrt(weighted_sq_dist)

    def calculate(self,
                  selection: str = "protein",
                  use_masses: bool = True,
                  group_selections: Optional[Dict[str, str]] = None) -> dict:
        if self.trajectory_reader.universe is None:
            raise ValueError("Trajectory not loaded. Call load() first.")
        
        u = self.trajectory_reader.universe
        atoms = u.select_atoms(selection)
        
        self.time_array = self.trajectory_reader.get_time_array()
        self.rg_values = []
        
        masses = atoms.masses if use_masses else None
        
        for ts in u.trajectory:
            rg = self._calculate_rg(atoms.positions, masses)
            self.rg_values.append(rg)
        
        self.rg_values = np.array(self.rg_values)
        
        results = {
            "time": self.time_array,
            "rg": self.rg_values,
            "selection": selection,
            "use_masses": use_masses
        }
        
        if group_selections:
            group_results = {}
            for group_name, group_sel in group_selections.items():
                group_rg = self._calculate_group_rg(group_sel, use_masses)
                group_results[group_name] = group_rg
            results["groups"] = group_results
        
        return results

    def _calculate_group_rg(self,
                           selection: str,
                           use_masses: bool) -> np.ndarray:
        u = self.trajectory_reader.universe
        atoms = u.select_atoms(selection)
        masses = atoms.masses if use_masses else None
        
        rg_values = []
        for ts in u.trajectory:
            rg = self._calculate_rg(atoms.positions, masses)
            rg_values.append(rg)
        
        return np.array(rg_values)

    def get_statistics(self) -> dict:
        if self.rg_values is None:
            raise ValueError("Rg not calculated. Call calculate() first.")
        return {
            "mean": np.mean(self.rg_values),
            "std": np.std(self.rg_values),
            "min": np.min(self.rg_values),
            "max": np.max(self.rg_values),
            "median": np.median(self.rg_values)
        }

    def get_rg_array(self) -> Tuple[np.ndarray, np.ndarray]:
        if self.rg_values is None or self.time_array is None:
            raise ValueError("Rg not calculated. Call calculate() first.")
        return self.time_array, self.rg_values

    def calculate_asphericity(self, selection: str = "protein") -> dict:
        if self.trajectory_reader.universe is None:
            raise ValueError("Trajectory not loaded. Call load() first.")
        
        u = self.trajectory_reader.universe
        atoms = u.select_atoms(selection)
        
        time_array = self.trajectory_reader.get_time_array()
        asphericity_values = []
        acylindricity_values = []
        anisotropy_values = []
        
        for ts in u.trajectory:
            positions = atoms.positions
            center = np.mean(positions, axis=0)
            centered = positions - center
            
            tensor = np.dot(centered.T, centered) / len(positions)
            eigenvalues = np.linalg.eigvalsh(tensor)
            eigenvalues.sort()
            
            lambda1, lambda2, lambda3 = eigenvalues
            asphericity = lambda3 - 0.5 * (lambda1 + lambda2)
            acylindricity = lambda2 - lambda1
            anisotropy = 1.5 * (lambda1**2 + lambda2**2 + lambda3**2) / (lambda1 + lambda2 + lambda3)**2 - 0.5
            
            asphericity_values.append(asphericity)
            acylindricity_values.append(acylindricity)
            anisotropy_values.append(anisotropy)
        
        return {
            "time": time_array,
            "asphericity": np.array(asphericity_values),
            "acylindricity": np.array(acylindricity_values),
            "anisotropy": np.array(anisotropy_values)
        }
