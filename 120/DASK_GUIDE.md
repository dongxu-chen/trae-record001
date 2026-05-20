# 分子动力学轨迹分布式分析工具 (基于Dask)

## 📦 功能特性

### 1. 内存映射文件读取
- 支持TB级轨迹文件读取，无需一次性加载全部数据到内存
- 分块处理（chunked processing），可自定义分块大小
- 基于MDAnalysis的原子选择语法

### 2. 分布式计算
- **RMSD计算**：均方根偏差的分布式并行计算
- **Rg计算**：回旋半径的分布式并行计算（支持质量加权）
- **PCA主成分分析**：基于Dask数组的协方差矩阵计算

### 3. 实时监控
- Dask Dashboard可视化任务进度
- 内存使用估算
- 计算时间统计

### 4. 交互式分析
- Jupyter Notebook交互式界面
- ipywidgets友好交互
- 实时图表生成

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 命令行使用

#### 1. 内存估算
```bash
python dask_analysis_cli.py -t topology.pdb -x trajectory.xtc --estimate-memory
```

#### 2. 本地集群分析
```bash
# RMSD + Rg分析
python dask_analysis_cli.py -t topology.pdb -x trajectory.xtc \
    --rmsd --rg --workers 4 --memory-limit 8GB

# PCA分析
python dask_analysis_cli.py -t topology.pdb -x trajectory.xtc \
    --pca --pca-sel 'name CA' --n-components 10

# 完整分析
python dask_analysis_cli.py -t topology.pdb -x trajectory.xtc \
    --rmsd --rg --pca -o my_results
```

#### 3. 分布式集群分析
```bash
# 首先启动调度器
dask-scheduler

# 在各节点启动Worker
dask-worker tcp://scheduler-ip:8786 --nthreads 4 --memory-limit 16GB

# 提交任务
python dask_analysis_cli.py -t topology.pdb -x trajectory.xtc \
    --scheduler tcp://scheduler-ip:8786 --rmsd --rg
```

### Jupyter Notebook交互式分析

启动Jupyter Notebook：
```bash
jupyter notebook interactive_analysis.ipynb
```

按照Notebook中的步骤进行交互式分析。

### Python API使用

```python
from md_analysis import (
    MemoryMappedTrajectory,
    DistributedAnalyzer,
    DaskPCA,
    estimate_memory_usage
)

# 1. 初始化Dask集群
analyzer = DistributedAnalyzer()
client = analyzer.setup_local_cluster(
    n_workers=4,
    threads_per_worker=2,
    memory_limit='8GB'
)

# 2. 加载轨迹数据
traj = MemoryMappedTrajectory(
    'topology.pdb',
    'trajectory.xtc',
    chunk_size=1000
)

# 3. 内存估算
memory_est = estimate_memory_usage(traj.n_frames, traj.n_atoms)
print(f"预计内存需求: {memory_est['total']}")

# 4. 转换为Dask数组
times_dask, positions_dask = traj.to_dask_array('name CA')

# 5. 计算RMSD
ref_positions = traj.read_frame(0, 'name CA')
rmsd_values = analyzer.compute_rmsd_distributed(
    positions_dask,
    ref_positions,
    compute_now=True
)

# 6. 计算Rg
rg_values = analyzer.compute_rg_distributed(
    positions_dask,
    masses=traj.atom_masses,
    compute_now=True
)

# 7. PCA分析
positions_flat = positions_dask.reshape(positions_dask.shape[0], -1)
pca = DaskPCA(n_components=10)
pca.fit(positions_flat, compute_now=True)
projections = pca.transform(positions_flat).compute()

# 8. 关闭集群
analyzer.close()
```

## ⚙️  性能优化指南

### 分块大小选择 (chunk_size)
- **小文件** (< 10GB): 1000-2000 帧/块
- **中文件** (10-100GB): 2000-5000 帧/块
- **大文件** (> 100GB): 5000-10000 帧/块

### 集群配置建议

| 轨迹大小 | Worker数量 | 内存/Worker | 线程/Worker |
|---------|-----------|------------|------------|
| < 10GB  | 2-4       | 4-8GB      | 2-4        |
| 10-100GB| 4-8       | 8-16GB     | 4-8        |
| > 100GB | 8-16      | 16-32GB    | 8-16       |

### 原子选择优化
- 使用 `name CA` 代替 `protein` 可减少计算量约70%
- 仅选择需要的原子进行分析
- 避免全原子分析除非必要

## 📊 输出结果说明

### 数值结果
- `analysis_results.csv`: 包含时间、RMSD、Rg等时间序列数据
- `pca_projections.npy`: PCA投影坐标（numpy格式）
- `pca_components.npy`: PCA主成分向量
- `pca_variance_ratio.npy`: 各主成分解释方差

### 图表结果
- `rmsd_plot.png`: RMSD随时间变化曲线
- `rg_plot.png`: Rg随时间变化曲线
- `pca_plots.png`: PCA投影散点图 + 碎石图

## 🔧 高级配置

### 自定义Dask集群

```python
from dask.distributed import LocalCluster, Client

# 自定义集群配置
cluster = LocalCluster(
    n_workers=8,
    threads_per_worker=4,
    memory_limit='16GB',
    processes=True,
    local_directory='/tmp/dask-worker-space'
)

client = Client(cluster)
analyzer = DistributedAnalyzer(client)
```

### 多节点部署

在各节点上启动Worker：
```bash
# 节点1
dask-worker tcp://scheduler-ip:8786 --nthreads 8 --memory-limit 32GB

# 节点2  
dask-worker tcp://scheduler-ip:8786 --nthreads 8 --memory-limit 32GB
```

### SLURM集群支持

使用dask-jobqueue：
```python
from dask_jobqueue import SLURMCluster

cluster = SLURMCluster(
    queue='compute',
    cores=8,
    memory='32GB',
    walltime='02:00:00'
)
cluster.scale(10)  # 启动10个Worker

client = Client(cluster)
```

## ❓ 常见问题

### Q: Dask Dashboard无法访问？
A: 检查防火墙设置，或使用SSH端口转发：
```bash
ssh -L 8787:localhost:8787 user@server
```

### Q: 内存不足怎么办？
A: 
1. 减小 `chunk_size` 参数
2. 增加Worker数量
3. 使用SSD存储提高I/O速度
4. 减少分析的原子范围

### Q: 计算速度慢怎么办？
A:
1. 检查I/O瓶颈（网络存储可能慢）
2. 增加Worker数量
3. 使用 `num_workers` 参数优化
4. 检查Dask Dashboard的任务进度

### Q: 如何中断正在运行的计算？
A: 
```python
client.cancel(futures)  # 取消特定任务
client.shutdown()       # 关闭整个集群
```

## 📚 相关资源

- [Dask官方文档](https://docs.dask.org/)
- [Dask Distributed文档](https://distributed.dask.org/)
- [MDAnalysis用户指南](https://userguide.mdanalysis.org/)
- [Dask Jobqueue](https://jobqueue.dask.org/)

## 📝 版本信息

- **当前版本**: 0.4.0
- **Dask版本**: >= 2023.5.0
- **Python版本**: >= 3.8
