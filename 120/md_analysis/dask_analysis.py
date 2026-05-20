import numpy as np
import dask.array as da
import dask.dataframe as dd
from dask.distributed import Client, LocalCluster, get_task_stream
from dask import delayed, compute
from typing import Optional, Tuple, Dict, List, Union
import os
import warnings
from pathlib import Path


class MemoryMappedTrajectory:
    """内存映射轨迹读取器 - 支持TB级数据"""
    
    def __init__(self, topology_file: str, trajectory_file: str, 
                 chunk_size: int = 1000):
        self.topology_file = topology_file
        self.trajectory_file = trajectory_file
        self.chunk_size = chunk_size
        self.n_atoms = None
        self.n_frames = None
        self.atom_masses = None
        self._initialize()
    
    def _initialize(self):
        """初始化，使用MDAnalysis读取基本信息"""
        import MDAnalysis as mda
        
        u = mda.Universe(self.topology_file, self.trajectory_file)
        self.n_atoms = u.atoms.n_atoms
        self.n_frames = len(u.trajectory)
        self.atom_masses = u.atoms.masses.copy()
        
        try:
            self.dt = u.trajectory.dt
        except:
            self.dt = 1.0
    
    def read_frame(self, frame_idx: int, selection: str = "all") -> np.ndarray:
        """读取单个帧（延迟执行）"""
        import MDAnalysis as mda
        
        u = mda.Universe(self.topology_file, self.trajectory_file)
        atoms = u.select_atoms(selection)
        u.trajectory[frame_idx]
        return atoms.positions.copy()
    
    def read_chunk(self, start: int, stop: int, 
                   selection: str = "all") -> Tuple[np.ndarray, np.ndarray]:
        """读取数据块"""
        import MDAnalysis as mda
        
        u = mda.Universe(self.topology_file, self.trajectory_file)
        atoms = u.select_atoms(selection)
        n_sel_atoms = len(atoms)
        
        n_frames_chunk = stop - start
        positions = np.zeros((n_frames_chunk, n_sel_atoms, 3), dtype=np.float32)
        times = np.zeros(n_frames_chunk, dtype=np.float32)
        
        for i, frame_idx in enumerate(range(start, stop)):
            u.trajectory[frame_idx]
            positions[i] = atoms.positions
            times[i] = u.trajectory.time
        
        return times, positions
    
    def to_dask_array(self, selection: str = "all") -> Tuple[da.Array, da.Array]:
        """转换为Dask数组"""
        import MDAnalysis as mda
        u = mda.Universe(self.topology_file, self.trajectory_file)
        atoms = u.select_atoms(selection)
        n_sel_atoms = len(atoms)
        
        chunks = []
        time_chunks = []
        
        for start in range(0, self.n_frames, self.chunk_size):
            stop = min(start + self.chunk_size, self.n_frames)
            chunk = da.from_delayed(
                delayed(self.read_chunk)(start, stop, selection)[1],
                shape=(stop - start, n_sel_atoms, 3),
                dtype=np.float32
            )
            chunks.append(chunk)
            
            time_chunk = da.from_delayed(
                delayed(self.read_chunk)(start, stop, selection)[0],
                shape=(stop - start,),
                dtype=np.float32
            )
            time_chunks.append(time_chunk)
        
        positions_dask = da.concatenate(chunks, axis=0)
        times_dask = da.concatenate(time_chunks, axis=0)
        
        return times_dask, positions_dask


class DistributedAnalyzer:
    """分布式轨迹分析器 - 基于Dask"""
    
    def __init__(self, client: Optional[Client] = None):
        self.client = client
        self.ref_positions = None
        self.ref_center = None
    
    def setup_local_cluster(self, n_workers: int = None, 
                           threads_per_worker: int = 2,
                           memory_limit: str = "auto") -> Client:
        """设置本地Dask集群"""
        if self.client is not None:
            self.client.close()
        
        cluster = LocalCluster(
            n_workers=n_workers,
            threads_per_worker=threads_per_worker,
            memory_limit=memory_limit
        )
        
        self.client = Client(cluster)
        print(f"✓ Dask集群已启动: {self.client.dashboard_link}")
        return self.client
    
    def connect_to_cluster(self, scheduler_address: str) -> Client:
        """连接到远程Dask集群"""
        if self.client is not None:
            self.client.close()
        
        self.client = Client(scheduler_address)
        print(f"✓ 已连接到集群: {scheduler_address}")
        return self.client
    
    def set_reference(self, ref_positions: np.ndarray):
        """设置参考结构"""
        self.ref_positions = ref_positions.astype(np.float32)
        self.ref_center = np.mean(ref_positions, axis=0)
    
    @staticmethod
    def _kabsch_align(mobile: np.ndarray, ref: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Kabsch算法对齐（单帧）"""
        mob_center = np.mean(mobile, axis=0)
        ref_center = np.mean(ref, axis=0)
        
        mob_centered = mobile - mob_center
        ref_centered = ref - ref_center
        
        H = mob_centered.T @ ref_centered
        
        U, S, Vt = np.linalg.svd(H)
        
        if np.linalg.det(Vt.T @ U.T) < 0:
            Vt[-1, :] *= -1
        
        R = Vt.T @ U.T
        mob_aligned = (R @ mob_centered.T).T + ref_center
        
        return mob_aligned, R
    
    @staticmethod
    def _compute_rmsd_chunk(chunk: np.ndarray, ref: np.ndarray) -> np.ndarray:
        """计算一个数据块的RMSD"""
        ref_center = np.mean(ref, axis=0)
        ref_centered = ref - ref_center
        
        rmsd_values = np.zeros(chunk.shape[0], dtype=np.float32)
        
        for i in range(chunk.shape[0]):
            mobile = chunk[i]
            mob_center = np.mean(mobile, axis=0)
            mob_centered = mobile - mob_center
            
            H = mob_centered.T @ ref_centered
            U, S, Vt = np.linalg.svd(H)
            
            if np.linalg.det(Vt.T @ U.T) < 0:
                Vt[-1, :] *= -1
            
            R = Vt.T @ U.T
            mob_aligned = (R @ mob_centered.T).T + ref_center
            
            diff = mob_aligned - ref
            rmsd_values[i] = np.sqrt(np.mean(np.sum(diff ** 2, axis=1)))
        
        return rmsd_values
    
    def compute_rmsd_distributed(self, 
                                 positions_dask: da.Array,
                                 ref_positions: np.ndarray,
                                 compute_now: bool = True) -> Union[da.Array, np.ndarray]:
        """分布式计算RMSD"""
        if self.ref_positions is None:
            self.set_reference(ref_positions)
        
        rmsd_dask = positions_dask.map_blocks(
            self._compute_rmsd_chunk,
            ref=self.ref_positions,
            drop_axis=[1, 2],
            dtype=np.float32
        )
        
        if compute_now:
            with get_task_stream(plot='save', filename='rmsd_computation.html'):
                result = rmsd_dask.compute()
            print("✓ RMSD计算完成")
            return result
        
        return rmsd_dask
    
    @staticmethod
    def _compute_rg_chunk(chunk: np.ndarray, masses: np.ndarray = None) -> np.ndarray:
        """计算一个数据块的Rg"""
        n_frames = chunk.shape[0]
        rg_values = np.zeros(n_frames, dtype=np.float32)
        
        if masses is None:
            masses = np.ones(chunk.shape[1], dtype=np.float32)
        
        total_mass = np.sum(masses)
        
        for i in range(n_frames):
            positions = chunk[i]
            center = np.sum(positions * masses[:, np.newaxis], axis=0) / total_mass
            centered = positions - center
            sq_dist = np.sum(centered ** 2, axis=1)
            rg_values[i] = np.sqrt(np.sum(sq_dist * masses) / total_mass)
        
        return rg_values
    
    def compute_rg_distributed(self,
                              positions_dask: da.Array,
                              masses: np.ndarray = None,
                              compute_now: bool = True) -> Union[da.Array, np.ndarray]:
        """分布式计算回旋半径Rg"""
        if masses is None:
            masses = np.ones(positions_dask.shape[1], dtype=np.float32)
        
        rg_dask = positions_dask.map_blocks(
            self._compute_rg_chunk,
            masses=masses.astype(np.float32),
            drop_axis=[1, 2],
            dtype=np.float32
        )
        
        if compute_now:
            with get_task_stream(plot='save', filename='rg_computation.html'):
                result = rg_dask.compute()
            print("✓ Rg计算完成")
            return result
        
        return rg_dask
    
    def compute_batch_statistics(self, data_dask: da.Array) -> Dict[str, float]:
        """批量计算统计量（均值、标准差、最小值、最大值等）"""
        mean_val = da.mean(data_dask)
        std_val = da.std(data_dask)
        min_val = da.min(data_dask)
        max_val = da.max(data_dask)
        
        results = compute(mean_val, std_val, min_val, max_val)
        
        return {
            "mean": float(results[0]),
            "std": float(results[1]),
            "min": float(results[2]),
            "max": float(results[3])
        }
    
    def to_dask_dataframe(self, 
                          times: da.Array, 
                          rmsd: da.Array, 
                          rg: da.Array = None) -> dd.DataFrame:
        """转换为Dask DataFrame进行后续分析"""
        data_dict = {
            "time_ps": times,
            "rmsd_angstrom": rmsd
        }
        
        if rg is not None:
            data_dict["rg_angstrom"] = rg
        
        df = dd.concat([da.from_delayed(d, shape=(times.shape[0],), dtype=np.float32).to_dask_dataframe() 
                        for d in data_dict.values()], axis=1)
        
        df.columns = list(data_dict.keys())
        return df
    
    def close(self):
        """关闭Dask客户端"""
        if self.client is not None:
            self.client.close()
            print("✓ Dask客户端已关闭")


class DaskPCA:
    """基于Dask的分布式PCA分析"""
    
    def __init__(self, n_components: int = 10):
        self.n_components = n_components
        self.mean_ = None
        self.components_ = None
        self.explained_variance_ = None
        self.explained_variance_ratio_ = None
    
    def fit(self, X_dask: da.Array, compute_now: bool = True):
        """分布式PCA拟合"""
        n_samples, n_features = X_dask.shape
        
        mean_vec = da.mean(X_dask, axis=0)
        X_centered = X_dask - mean_vec
        
        cov_matrix = (X_centered.T @ X_centered) / (n_samples - 1)
        
        if compute_now:
            cov_np = cov_matrix.compute()
            mean_np = mean_vec.compute()
            
            eigenvalues, eigenvectors = np.linalg.eigh(cov_np)
            
            idx = np.argsort(eigenvalues)[::-1]
            eigenvalues = eigenvalues[idx]
            eigenvectors = eigenvectors[:, idx]
            
            self.mean_ = mean_np
            self.components_ = eigenvectors[:, :self.n_components]
            self.explained_variance_ = eigenvalues[:self.n_components]
            
            total_var = np.sum(eigenvalues)
            self.explained_variance_ratio_ = eigenvalues[:self.n_components] / total_var
            
            print("✓ PCA计算完成")
            print(f"  前2个主成分解释方差: {np.sum(self.explained_variance_ratio_[:2])*100:.2f}%")
        
        return self
    
    def transform(self, X_dask: da.Array) -> da.Array:
        """投影数据"""
        if self.mean_ is None or self.components_ is None:
            raise ValueError("PCA模型未拟合")
        
        X_centered = X_dask - self.mean_
        projections = X_centered @ self.components_
        
        return projections
    
    def fit_transform(self, X_dask: da.Array) -> da.Array:
        """拟合并转换"""
        self.fit(X_dask, compute_now=True)
        return self.transform(X_dask)


def estimate_memory_usage(n_frames: int, n_atoms: int, precision: str = "float32") -> Dict[str, str]:
    """估算内存使用"""
    bytes_per_element = 4 if precision == "float32" else 8
    
    coords_memory = n_frames * n_atoms * 3 * bytes_per_element
    rmsd_memory = n_frames * bytes_per_element
    rg_memory = n_frames * bytes_per_element
    
    total_memory = coords_memory + rmsd_memory + rg_memory
    
    return {
        "coordinates": f"{coords_memory / (1024**3):.2f} GB",
        "rmsd": f"{rmsd_memory / (1024**3):.2f} GB",
        "rg": f"{rg_memory / (1024**3):.2f} GB",
        "total": f"{total_memory / (1024**3):.2f} GB"
    }


def create_dask_cluster_info(client: Client) -> Dict:
    """获取Dask集群信息"""
    info = client.scheduler_info()
    
    return {
        "n_workers": len(info["workers"]),
        "total_cores": sum(w["nthreads"] for w in info["workers"].values()),
        "total_memory_gb": sum(w["memory_limit"] for w in info["workers"].values()) / (1024**3),
        "dashboard_link": client.dashboard_link
    }
