"""
列并行计算模块
支持：
- MPI 多进程列并行
- 自动负载均衡
- 结果收集和汇总
"""

import numpy as np

try:
    from mpi4py import MPI
    MPI_AVAILABLE = True
except ImportError:
    MPI_AVAILABLE = False


class ColumnParallel:
    """
    列并行计算管理器
    """

    def __init__(self, n_columns, use_mpi=True):
        """
        参数:
        - n_columns: 总列数
        - use_mpi: 是否使用 MPI
        """
        self.n_columns = n_columns
        self.use_mpi = use_mpi and MPI_AVAILABLE

        if self.use_mpi:
            self.comm = MPI.COMM_WORLD
            self.rank = self.comm.Get_rank()
            self.size = self.comm.Get_size()
        else:
            self.comm = None
            self.rank = 0
            self.size = 1

        self._calculate_column_distribution()

    def _calculate_column_distribution(self):
        """计算各进程负责的列范围"""
        if self.size == 1:
            self.start_col = 0
            self.end_col = self.n_columns
            self.local_columns = self.n_columns
        else:
            cols_per_proc = self.n_columns // self.size
            remainder = self.n_columns % self.size

            if self.rank < remainder:
                self.start_col = self.rank * (cols_per_proc + 1)
                self.local_columns = cols_per_proc + 1
            else:
                self.start_col = self.rank * cols_per_proc + remainder
                self.local_columns = cols_per_proc

            self.end_col = self.start_col + self.local_columns

    def get_local_columns(self):
        """
        获取当前进程负责的列索引范围

        返回:
        - start, end, count
        """
        return self.start_col, self.end_col, self.local_columns

    def is_root(self):
        """是否是根进程"""
        return self.rank == 0

    def scatter_data(self, data, root=0):
        """
        将数据分散到各进程

        参数:
        - data: 完整数据，形状 (n_columns, ...)
        - root: 根进程号

        返回:
        - 本地数据切片
        """
        if not self.use_mpi or self.size == 1:
            return data

        if self.rank == root:
            data = np.asarray(data)
            sendbuf = []
            for i in range(self.size):
                if i < self.size - 1:
                    chunk = data[i * self.local_columns:(i + 1) * self.local_columns]
                else:
                    chunk = data[i * self.local_columns:]
                sendbuf.append(chunk)
        else:
            sendbuf = None

        local_data = self.comm.scatter(sendbuf, root=root)
        return local_data

    def gather_data(self, local_data, root=0):
        """
        从各进程收集数据

        参数:
        - local_data: 本地数据
        - root: 根进程号

        返回:
        - 完整数据（仅在根进程返回）
        """
        if not self.use_mpi or self.size == 1:
            return local_data

        recvbuf = self.comm.gather(local_data, root=root)

        if self.rank == root:
            if isinstance(recvbuf[0], np.ndarray):
                return np.concatenate(recvbuf, axis=0)
            elif isinstance(recvbuf[0], dict):
                result = {}
                for key in recvbuf[0].keys():
                    arrays = [r[key] for r in recvbuf]
                    if isinstance(arrays[0], np.ndarray):
                        result[key] = np.concatenate(arrays, axis=0)
                    else:
                        result[key] = [a for r in recvbuf for a in r[key]]
                return result
            else:
                return recvbuf
        else:
            return None

    def gather_results(self, local_results, root=0):
        """
        收集辐射计算结果

        参数:
        - local_results: 本地结果字典
        - root: 根进程号

        返回:
        - 完整结果字典
        """
        if not self.use_mpi or self.size == 1:
            return local_results

        all_results = self.comm.gather(local_results, root=root)

        if self.rank == root:
            full_results = {}

            for key in all_results[0].keys():
                if key == 'atmosphere':
                    full_results[key] = all_results[0][key]
                    continue

                first_val = all_results[0][key]
                if first_val is None:
                    full_results[key] = None
                    continue

                if isinstance(first_val, dict):
                    full_results[key] = {}
                    for subkey in first_val.keys():
                        subvals = [r[key][subkey] for r in all_results]
                        if isinstance(subvals[0], np.ndarray):
                            full_results[key][subkey] = np.concatenate(subvals, axis=0)
                        else:
                            full_results[key][subkey] = subvals
                elif isinstance(first_val, np.ndarray):
                    full_results[key] = np.concatenate([r[key] for r in all_results], axis=0)
                else:
                    full_results[key] = [r[key] for r in all_results]

            return full_results
        else:
            return None

    def broadcast(self, data, root=0):
        """
        广播数据到所有进程

        参数:
        - data: 要广播的数据
        - root: 根进程号

        返回:
        - 广播后的数据
        """
        if not self.use_mpi or self.size == 1:
            return data

        if self.rank == root:
            data = np.asarray(data)
        else:
            data = None

        return self.comm.bcast(data, root=root)

    def barrier(self):
        """进程同步屏障"""
        if self.use_mpi and self.size > 1:
            self.comm.Barrier()

    def print_info(self):
        """打印并行信息"""
        if self.is_root():
            print("=" * 60)
            print(f"Column Parallel Configuration")
            print(f"  Total columns: {self.n_columns}")
            print(f"  MPI available: {MPI_AVAILABLE}")
            print(f"  Using MPI: {self.use_mpi}")
            print(f"  Number of processes: {self.size}")
            if self.size > 1:
                print(f"  Columns per process: ~{self.n_columns // self.size}")
            print("=" * 60)


def run_parallel_column_calculation(
    compute_func,
    n_columns,
    profile,
    n_levels=10,
    use_mpi=True,
    **kwargs
):
    """
    执行列并行计算的便捷函数

    参数:
    - compute_func: 计算函数，签名为 compute_func(col_indices, profile, **kwargs)
    - n_columns: 总列数
    - profile: 大气廓线
    - n_levels: 层数
    - use_mpi: 是否使用 MPI
    - **kwargs: 其他参数传递给 compute_func

    返回:
    - 完整结果（仅在根进程返回非 None）
    """
    parallel = ColumnParallel(n_columns, use_mpi=use_mpi)

    if parallel.is_root():
        parallel.print_info()

    start, end, n_local = parallel.get_local_columns()

    if parallel.is_root():
        print(f"Rank {parallel.rank}: Columns {start}-{end-1} (n={n_local})")

    local_indices = np.arange(start, end)

    local_results = compute_func(local_indices, profile, **kwargs)

    full_results = parallel.gather_results(local_results)

    return full_results


class ParallelRadiationDriver:
    """
    并行辐射计算驱动器
    """

    def __init__(self, radiation_model, n_columns, use_mpi=True):
        """
        参数:
        - radiation_model: RadiationModel 实例
        - n_columns: 列数
        - use_mpi: 是否使用 MPI
        """
        self.model = radiation_model
        self.n_columns = n_columns
        self.parallel = ColumnParallel(n_columns, use_mpi=use_mpi)

    def compute_column(self, col_index, profile, **kwargs):
        """
        计算单列辐射

        参数:
        - col_index: 列索引
        - profile: 大气廓线
        - **kwargs: 其他参数

        返回:
        - 单柱结果
        """
        return self.model.compute_radiation_budget(profile, **kwargs)

    def run(self, profile, **kwargs):
        """
        执行并行计算

        参数:
        - profile: 大气廓线
        - **kwargs: 其他参数

        返回:
        - 完整结果（根进程）
        """
        start, end, n_local = self.parallel.get_local_columns()

        if self.parallel.is_root():
            print(f"Parallel computation: {self.n_columns} columns on {self.parallel.size} processes")

        def compute_columns(indices, profile, **kwargs):
            results = None
            for idx in indices:
                col_result = self.compute_column(idx, profile, **kwargs)
                if results is None:
                    results = {k: [] for k in col_result.keys()}
                for key, val in col_result.items():
                    if isinstance(val, dict):
                        if key not in results or not isinstance(results[key], dict):
                            results[key] = {k: [] for k in val.keys()}
                        for subkey, subval in val.items():
                            results[key][subkey].append(subval)
                    else:
                        results[key].append(val)

            final_results = {}
            for key, val in results.items():
                if isinstance(val, dict):
                    final_results[key] = {}
                    for subkey, subvals in val.items():
                        if isinstance(subvals[0], np.ndarray):
                            final_results[key][subkey] = np.stack(subvals, axis=0)
                        else:
                            final_results[key][subkey] = subvals
                elif isinstance(val[0], np.ndarray):
                    final_results[key] = np.stack(val, axis=0)
                else:
                    final_results[key] = val

            return final_results

        return run_parallel_column_calculation(
            compute_columns,
            self.n_columns,
            profile,
            use_mpi=self.parallel.use_mpi,
            **kwargs
        )
