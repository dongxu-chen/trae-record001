import numpy as np

try:
    import cupy as cp
    CUPY_AVAILABLE = True
except ImportError:
    CUPY_AVAILABLE = False
    import numpy as cp

from cuda_utils import get_array_module, synchronize, to_cpu


class NeighborList:
    """
    邻居列表类，基于晶格方法 (Cell List) 构建邻居列表
    支持 CPU 和 GPU 两种实现
    """

    def __init__(self, rc, skin=0.3, use_gpu=False):
        """
        初始化邻居列表

        Args:
            rc (float): 截断距离
            skin (float): 邻居列表更新的安全层厚度
            use_gpu (bool): 是否使用 GPU 加速
        """
        self.rc = rc
        self.skin = skin
        self.rc_skin = rc + skin
        self.neighbors = None
        self.last_positions = None
        self.use_gpu = use_gpu and CUPY_AVAILABLE

    def need_rebuild(self, positions, box):
        """
        检查是否需要重建邻居列表

        Args:
            positions: 当前粒子位置
            box: 模拟盒子

        Returns:
            bool: 是否需要重建
        """
        if self.last_positions is None:
            return True

        xp = get_array_module(positions)
        box_size = box[:, 1] - box[:, 0]
        disp = positions - self.last_positions
        disp -= box_size * xp.round(disp / box_size)
        max_disp = xp.max(xp.sqrt(xp.sum(disp ** 2, axis=1)))

        if xp is cp:
            max_disp = float(max_disp)

        return max_disp > self.skin / 2.0

    def build_verlet(self, positions, box):
        """
        使用晶格方法构建 Verlet 邻居列表

        Args:
            positions: 粒子位置
            box: 模拟盒子
        """
        if self.use_gpu and CUPY_AVAILABLE:
            self._build_verlet_gpu(positions, box)
        else:
            self._build_verlet_cpu(positions, box)

    def _build_verlet_cpu(self, positions, box):
        """
        CPU 版本：晶格方法构建 Verlet 邻居列表

        Args:
            positions (np.ndarray): 粒子位置 (Nx3)
            box (np.ndarray): 模拟盒子
        """
        n = positions.shape[0]
        box_size = box[:, 1] - box[:, 0]
        r_cut = self.rc_skin

        n_cells = np.maximum(1, np.floor(box_size / r_cut).astype(int))
        cell_size = box_size / n_cells

        cell_assignment = np.floor((positions - box[:, 0]) / cell_size)
        cell_assignment = cell_assignment.astype(int)
        cell_assignment = np.clip(cell_assignment, 0, n_cells - 1)

        cell_map = {}
        for idx in range(n):
            key = (int(cell_assignment[idx, 0]), int(cell_assignment[idx, 1]), int(cell_assignment[idx, 2]))
            if key not in cell_map:
                cell_map[key] = []
            cell_map[key].append(idx)

        self.neighbors = [[] for _ in range(n)]

        for i in range(n):
            ic = cell_assignment[i]
            for dcx in range(-1, 2):
                for dcy in range(-1, 2):
                    for dcz in range(-1, 2):
                        jc = (int(ic[0] + dcx), int(ic[1] + dcy), int(ic[2] + dcz))
                        jc = tuple(
                            (jc[d] % n_cells[d]) for d in range(3)
                        )

                        if jc not in cell_map:
                            continue

                        for j in cell_map[jc]:
                            if j <= i:
                                continue

                            r_vec = positions[i] - positions[j]
                            r_vec -= box_size * np.round(r_vec / box_size)
                            r2 = np.dot(r_vec, r_vec)

                            if r2 <= r_cut * r_cut:
                                self.neighbors[i].append(j)
                                self.neighbors[j].append(i)

        self.last_positions = positions.copy()

    def _build_verlet_gpu(self, positions, box):
        """
        GPU 版本：晶格方法构建 Verlet 邻居列表

        Args:
            positions (cp.ndarray): GPU 上的粒子位置 (Nx3)
            box: 模拟盒子
        """
        if not CUPY_AVAILABLE:
            self._build_verlet_cpu(to_cpu(positions), to_cpu(box))
            return

        n = positions.shape[0]
        box_size = cp.asarray(box[:, 1] - box[:, 0], dtype=cp.float64)
        box_np = to_cpu(box_size)
        r_cut = self.rc_skin
        r_cut2 = r_cut * r_cut

        n_cells = np.maximum(1, np.floor(box_np / r_cut).astype(int))
        cell_size = box_np / n_cells
        cell_size_gpu = cp.asarray(cell_size, dtype=cp.float64)

        box_min = cp.asarray(box[:, 0], dtype=cp.float64)
        cell_assignment = cp.floor((positions - box_min) / cell_size_gpu)
        cell_assignment = cell_assignment.astype(cp.int32)
        cell_assignment = cp.clip(cell_assignment, 0,
                                  cp.asarray([n_cells[0] - 1, n_cells[1] - 1, n_cells[2] - 1], dtype=cp.int32))

        cell_assignment_cpu = to_cpu(cell_assignment)

        cell_map = {}
        for idx in range(n):
            key = (int(cell_assignment_cpu[idx, 0]),
                   int(cell_assignment_cpu[idx, 1]),
                   int(cell_assignment_cpu[idx, 2]))
            if key not in cell_map:
                cell_map[key] = []
            cell_map[key].append(idx)

        neighbors_cpu = [[] for _ in range(n)]
        positions_cpu = to_cpu(positions)

        for i in range(n):
            ic = cell_assignment_cpu[i]
            for dcx in range(-1, 2):
                for dcy in range(-1, 2):
                    for dcz in range(-1, 2):
                        jc = (int(ic[0] + dcx), int(ic[1] + dcy), int(ic[2] + dcz))
                        jc = tuple(
                            (jc[d] % n_cells[d]) for d in range(3)
                        )

                        if jc not in cell_map:
                            continue

                        for j in cell_map[jc]:
                            if j <= i:
                                continue

                            r_vec = positions_cpu[i] - positions_cpu[j]
                            r_vec -= box_np * np.round(r_vec / box_np)
                            r2 = np.dot(r_vec, r_vec)

                            if r2 <= r_cut2:
                                neighbors_cpu[i].append(j)
                                neighbors_cpu[j].append(i)

        self.neighbors = neighbors_cpu
        self.last_positions = positions.copy()

    def get_neighbors(self):
        """返回邻居列表"""
        return self.neighbors
