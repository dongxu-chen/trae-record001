import numpy as np
from typing import Optional, Tuple, Dict, List
import warnings


class PCAAnalyzer:
    def __init__(self, trajectory_reader):
        self.reader = trajectory_reader
        self.covariance_matrix = None
        self.eigenvalues = None
        self.eigenvectors = None
        self.variance_ratio = None
        self.cumulative_variance = None
        self.projections = None
        self.mean_coords = None
        self.atom_masses = None
        
    def fit(self, 
            selection: str = "name CA", 
            fit: bool = True,
            start: int = 0,
            stop: Optional[int] = None,
            step: int = 1) -> Dict:
        """执行PCA分析"""
        if self.reader.universe is None:
            raise ValueError("Trajectory not loaded. Call load() first.")
        
        u = self.reader.universe
        atoms = u.select_atoms(selection)
        n_atoms = len(atoms)
        
        print(f"  选择原子: {n_atoms} 个 ({selection})")
        
        if stop is None:
            stop = len(u.trajectory)
        
        n_frames = len(range(start, stop, step))
        coords_all = np.zeros((n_frames, n_atoms, 3), dtype=np.float32)
        
        print(f"  提取坐标数据... ({n_frames} 帧)")
        for i, ts in enumerate(u.trajectory[start:stop:step]):
            coords_all[i] = atoms.positions
        
        if fit:
            print(f"  进行平动转动对齐...")
            coords_all = self._align_trajectory(coords_all)
        
        print(f"  计算协方差矩阵...")
        self.mean_coords = np.mean(coords_all, axis=0)
        coords_centered = coords_all - self.mean_coords
        coords_flat = coords_centered.reshape(n_frames, -1)
        
        self.covariance_matrix = np.cov(coords_flat.T)
        
        print(f"  特征值分解...")
        self.eigenvalues, self.eigenvectors = np.linalg.eigh(self.covariance_matrix)
        
        sort_idx = np.argsort(self.eigenvalues)[::-1]
        self.eigenvalues = self.eigenvalues[sort_idx]
        self.eigenvectors = self.eigenvectors[:, sort_idx]
        
        total_var = np.sum(self.eigenvalues)
        self.variance_ratio = self.eigenvalues / total_var
        self.cumulative_variance = np.cumsum(self.variance_ratio)
        
        print(f"  计算轨迹投影...")
        self.projections = coords_flat @ self.eigenvectors
        
        return {
            "eigenvalues": self.eigenvalues,
            "variance_ratio": self.variance_ratio,
            "cumulative_variance": self.cumulative_variance,
            "projections": self.projections,
            "n_atoms": n_atoms,
            "n_frames": n_frames
        }
    
    def _align_trajectory(self, coords: np.ndarray) -> np.ndarray:
        """使用Kabsch算法对齐整个轨迹"""
        n_frames, n_atoms, _ = coords.shape
        reference = coords[0].copy()
        ref_centered = reference - np.mean(reference, axis=0)
        
        aligned_coords = np.zeros_like(coords)
        
        for i in range(n_frames):
            mobile = coords[i]
            mob_centered = mobile - np.mean(mobile, axis=0)
            
            H = mob_centered.T @ ref_centered
            U, S, Vt = np.linalg.svd(H)
            
            if np.linalg.det(Vt.T @ U.T) < 0:
                Vt[-1, :] *= -1
            
            R = Vt.T @ U.T
            aligned = (R @ mob_centered.T).T + np.mean(reference, axis=0)
            aligned_coords[i] = aligned
        
        return aligned_coords
    
    def get_projections(self, n_components: int = 2) -> np.ndarray:
        """获取前N个主成分的投影"""
        if self.projections is None:
            raise ValueError("PCA not fitted. Call fit() first.")
        return self.projections[:, :n_components]
    
    def get_explained_variance(self, n_components: int = 10) -> Dict:
        """获取解释方差信息"""
        if self.variance_ratio is None:
            raise ValueError("PCA not fitted. Call fit() first.")
        
        return {
            "component": np.arange(1, n_components + 1),
            "variance_ratio": self.variance_ratio[:n_components],
            "cumulative_variance": self.cumulative_variance[:n_components]
        }
    
    def get_residue_contributions(self, 
                                  selection: str = "name CA",
                                  n_components: int = 2) -> Dict:
        """计算每个残基对主成分的贡献"""
        if self.eigenvectors is None:
            raise ValueError("PCA not fitted. Call fit() first.")
        
        u = self.reader.universe
        atoms = u.select_atoms(selection)
        residues = atoms.residues
        
        contributions = np.zeros((len(residues), n_components))
        
        for comp in range(n_components):
            eigenvector = self.eigenvectors[:, comp].reshape(-1, 3)
            for i, _ in enumerate(residues):
                atom_slice = slice(i * 1, (i + 1) * 1)
                contributions[i, comp] = np.sum(eigenvector[atom_slice] ** 2)
        
        contributions = contributions / np.sum(contributions, axis=0, keepdims=True)
        
        return {
            "resids": [res.resid for res in residues],
            "resnames": [res.resname for res in residues],
            "contributions": contributions,
            "n_components": n_components
        }


class FreeEnergySurface:
    def __init__(self, x: np.ndarray, y: np.ndarray):
        self.x = x
        self.y = y
        self.fes = None
        self.x_grid = None
        self.y_grid = None
        self.min_energy = None
        
    def calculate(self, 
                  bins: int = 100, 
                  temperature: float = 300.0,
                  method: str = "histogram") -> Dict:
        """计算自由能形貌图"""
        kB = 0.008314  # kJ/(mol·K)
        RT = kB * temperature
        
        if method == "histogram":
            hist, x_edges, y_edges = np.histogram2d(
                self.x, self.y, bins=bins, density=True
            )
            
            self.x_grid = (x_edges[:-1] + x_edges[1:]) / 2
            self.y_grid = (y_edges[:-1] + y_edges[1:]) / 2
            
            prob = hist / np.sum(hist)
            prob[prob == 0] = np.min(prob[prob > 0]) * 0.1
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.fes = -RT * np.log(prob)
            
            self.min_energy = np.min(self.fes)
            self.fes = self.fes - self.min_energy
            
            if self.min_energy != 0:
                print(f"  警告: 最小自由能不为零 ({self.min_energy:.2f} kJ/mol)")
                print(f"  已减去最小值，范围: 0 到 {np.max(self.fes):.2f} kJ/mol")
            else:
                print(f"  自由能范围: 0 到 {np.max(self.fes):.2f} kJ/mol")
            
        elif method == "kde":
            try:
                from scipy.stats import gaussian_kde
                
                self.x_grid = np.linspace(np.min(self.x), np.max(self.x), bins)
                self.y_grid = np.linspace(np.min(self.y), np.max(self.y), bins)
                X, Y = np.meshgrid(self.x_grid, self.y_grid)
                
                positions = np.vstack([X.ravel(), Y.ravel()])
                values = np.vstack([self.x, self.y])
                
                kde = gaussian_kde(values)
                prob = kde(positions).reshape(bins, bins)
                
                prob[prob == 0] = np.min(prob[prob > 0]) * 0.1
                
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    self.fes = -RT * np.log(prob)
                
                self.min_energy = np.min(self.fes)
                self.fes = self.fes - self.min_energy
                
            except ImportError:
                print("  scipy未安装，使用histogram方法替代")
                return self.calculate(bins, temperature, method="histogram")
        
        return {
            "x_grid": self.x_grid,
            "y_grid": self.y_grid,
            "fes": self.fes,
            "min_energy": self.min_energy,
            "temperature": temperature,
            "method": method
        }
    
    def find_minima(self, n_minima: int = 3) -> List[Tuple[float, float, float]]:
        """寻找自由能极小值"""
        if self.fes is None:
            raise ValueError("FES not calculated. Call calculate() first.")
        
        minima = []
        fes_copy = self.fes.copy()
        
        for _ in range(n_minima):
            idx = np.unravel_index(np.argmin(fes_copy), fes_copy.shape)
            x_min = self.x_grid[idx[0]]
            y_min = self.y_grid[idx[1]]
            energy = fes_copy[idx]
            
            minima.append((x_min, y_min, energy))
            
            mask_size = max(1, len(fes_copy) // 20)
            i_min = max(0, idx[0] - mask_size)
            i_max = min(fes_copy.shape[0], idx[0] + mask_size + 1)
            j_min = max(0, idx[1] - mask_size)
            j_max = min(fes_copy.shape[1], idx[1] + mask_size + 1)
            fes_copy[i_min:i_max, j_min:j_max] = np.inf
        
        return minima
    
    def get_free_energy_levels(self, levels: List[float] = None) -> List[float]:
        """获取自由能等高线级别"""
        if self.fes is None:
            raise ValueError("FES not calculated. Call calculate() first.")
        
        if levels is None:
            max_e = np.max(self.fes)
            levels = np.arange(0, min(max_e, 50), 5)
        
        return list(levels)


def compute_rmsf(coords: np.ndarray) -> np.ndarray:
    """计算均方根波动(RMSF)"""
    mean_coords = np.mean(coords, axis=0)
    fluctuations = np.mean(np.sum((coords - mean_coords) ** 2, axis=-1), axis=0)
    return np.sqrt(fluctuations)


def compute_correlation_matrix(coords: np.ndarray) -> np.ndarray:
    """计算动态相关矩阵"""
    n_frames, n_atoms, _ = coords.shape
    coords_centered = coords - np.mean(coords, axis=0)
    
    correlation = np.zeros((n_atoms, n_atoms))
    
    for i in range(n_atoms):
        for j in range(n_atoms):
            ci = coords_centered[:, i, :].flatten()
            cj = coords_centered[:, j, :].flatten()
            correlation[i, j] = np.corrcoef(ci, cj)[0, 1]
    
    return correlation
