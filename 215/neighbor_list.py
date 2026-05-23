import importlib.util

if importlib.util.find_spec("cupy") is not None:
    import cupy as np
    GPU_AVAILABLE = True
else:
    import numpy as np
    GPU_AVAILABLE = False


class NeighborList:
    """
    邻居列表类，用于优化分子动力学中的力计算
    
    使用Verlet列表方案：
    - r_skin: 皮肤层厚度，用于减少列表重建频率
    - 当粒子移动超过 r_skin/2 时重建列表
    """
    
    def __init__(self, r_cut, r_skin=0.3, box_length=None, use_gpu=False):
        """
        初始化邻居列表
        
        参数:
            r_cut: 截断半径
            r_skin: 皮肤层厚度
            box_length: 周期性盒子边长
            use_gpu: 是否使用GPU加速
        """
        self.r_cut = r_cut
        self.r_skin = r_skin
        self.r_list = r_cut + r_skin
        self.r_list2 = self.r_list ** 2
        self.box_length = box_length
        self.use_gpu = use_gpu and GPU_AVAILABLE
        
        self.last_positions = None
        self.neighbors = None
        self.n_updates = 0
        self.displacement_threshold = r_skin / 2.0
        self.max_displacement = 0.0
        
    def set_box(self, box_length):
        """设置盒子大小"""
        self.box_length = box_length
        
    def _pbc_distance(self, positions, i, j):
        """计算PBC下的距离矢量"""
        dr = positions[j] - positions[i]
        if self.box_length is not None:
            dr -= self.box_length * np.round(dr / self.box_length)
        return dr
    
    def build(self, positions):
        """
        构建邻居列表
        
        参数:
            positions: 粒子位置 (N, dim)
        """
        n_particles = positions.shape[0]
        
        self.last_positions = positions.copy()
        self.n_updates += 1
        
        if self.use_gpu:
            return self._build_gpu(positions)
        else:
            return self._build_cpu(positions)
    
    def _build_cpu(self, positions):
        """CPU版本的邻居列表构建"""
        n_particles = positions.shape[0]
        neighbors = [[] for _ in range(n_particles)]
        
        for i in range(n_particles - 1):
            for j in range(i + 1, n_particles):
                dr = positions[j] - positions[i]
                if self.box_length is not None:
                    dr -= self.box_length * np.round(dr / self.box_length)
                r2 = np.sum(dr ** 2)
                
                if r2 < self.r_list2:
                    neighbors[i].append(j)
                    neighbors[j].append(i)
        
        self.neighbors = [np.array(nb, dtype=np.int64) for nb in neighbors]
        return self.neighbors
    
    def _build_gpu(self, positions):
        """GPU版本的邻居列表构建"""
        n_particles = positions.shape[0]
        dim = positions.shape[1]
        
        # 展开计算所有粒子对
        idx_i, idx_j = np.triu_indices(n_particles, k=1)
        
        dr = positions[idx_j] - positions[idx_i]
        if self.box_length is not None:
            dr -= self.box_length * np.round(dr / self.box_length)
        
        r2 = np.sum(dr ** 2, axis=1)
        mask = r2 < self.r_list2
        
        valid_i = idx_i[mask]
        valid_j = idx_j[mask]
        
        neighbors = [[] for _ in range(n_particles)]
        for i, j in zip(valid_i.get(), valid_j.get()):
            neighbors[i].append(j)
            neighbors[j].append(i)
        
        self.neighbors = [np.array(nb, dtype=np.int64) for nb in neighbors]
        return self.neighbors
    
    def need_update(self, positions, force_check=False):
        """
        检查是否需要重建邻居列表
        当任意两个粒子的相对位移超过皮肤层厚度的一半时需要重建
        
        参数:
            positions: 当前粒子位置
            force_check: 强制执行完整检查
        
        返回:
            bool: 是否需要重建
        """
        if self.last_positions is None:
            return True
        
        dr = positions - self.last_positions
        if self.box_length is not None:
            dr = pbc_distance(dr, self.box_length)
        
        displacements = np.sqrt(np.sum(dr ** 2, axis=1))
        self.max_displacement = float(np.max(displacements))
        
        if self.max_displacement > self.displacement_threshold:
            return True
        
        if force_check:
            max_relative_displacement = self.max_displacement * 2.0
            if max_relative_displacement > self.r_skin:
                return True
        
        return False
    
    def get_max_displacement(self):
        """获取上次检查的最大位移"""
        return self.max_displacement
    
    def reset_displacement(self):
        """重置位移追踪"""
        self.max_displacement = 0.0
    
    def get_neighbors(self, i):
        """获取粒子i的邻居列表"""
        return self.neighbors[i]
    
    def __getitem__(self, i):
        """通过索引访问邻居"""
        return self.neighbors[i]
    
    def __len__(self):
        return len(self.neighbors)


class CellList:
    """
    元胞列表类，进一步优化大系统的邻居搜索
    
    将模拟盒子划分为网格元胞，只搜索相邻元胞中的粒子
    """
    
    def __init__(self, r_cut, box_length, use_gpu=False):
        """
        初始化元胞列表
        
        参数:
            r_cut: 截断半径
            box_length: 盒子边长
            use_gpu: 是否使用GPU
        """
        self.r_cut = r_cut
        self.box_length = box_length
        self.use_gpu = use_gpu and GPU_AVAILABLE
        
        self.n_cells = int(box_length // r_cut)
        self.cell_size = box_length / self.n_cells
        
        if self.n_cells < 3:
            self.n_cells = 3
            self.cell_size = box_length / self.n_cells
        
        self.cells = None
        
    def build(self, positions):
        """
        构建元胞列表
        
        参数:
            positions: 粒子位置
        """
        n_particles = positions.shape[0]
        
        cell_indices = np.floor(positions / self.cell_size).astype(np.int32)
        cell_indices = np.mod(cell_indices, self.n_cells)
        
        self.cells = {}
        for i in range(n_particles):
            key = tuple(cell_indices[i].tolist())
            if key not in self.cells:
                self.cells[key] = []
            self.cells[key].append(i)
        
        for key in self.cells:
            self.cells[key] = np.array(self.cells[key], dtype=np.int64)
        
        return self.cells
    
    def get_neighbor_cells(self, cell_idx):
        """获取相邻元胞的索引（含自身）"""
        dim = len(cell_idx)
        neighbors = []
        
        offsets = np.array(np.meshgrid(*[[-1, 0, 1]] * dim)).T.reshape(-1, dim)
        
        for offset in offsets:
            neighbor = tuple(np.mod(cell_idx + offset, self.n_cells).tolist())
            neighbors.append(neighbor)
        
        return neighbors
    
    def get_particles_in_cell(self, cell_idx):
        """获取指定元胞中的粒子"""
        key = tuple(cell_idx) if not isinstance(cell_idx, tuple) else cell_idx
        return self.cells.get(key, np.array([], dtype=np.int64))
    
    def get_nearby_particles(self, position):
        """获取位置附近的所有粒子（来自相邻元胞）"""
        cell_idx = tuple(np.floor(position / self.cell_size).astype(np.int32))
        cell_idx = tuple(np.mod(np.array(cell_idx), self.n_cells).tolist())
        
        nearby = []
        for neighbor_cell in self.get_neighbor_cells(cell_idx):
            nearby.extend(self.cells.get(neighbor_cell, []))
        
        return np.array(nearby, dtype=np.int64)


def build_neighbor_list_simple(positions, r_cut, box_length=None, use_gpu=False):
    """
    简单的邻居列表构建函数（用于测试）
    
    参数:
        positions: 粒子位置 (N, dim)
        r_cut: 截断半径
        box_length: 盒子边长
        use_gpu: 是否使用GPU
    
    返回:
        neighbors: 邻居列表
    """
    nl = NeighborList(r_cut, r_skin=0.0, box_length=box_length, use_gpu=use_gpu)
    return nl.build(positions)
