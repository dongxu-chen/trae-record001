# 矩阵特征值并行计算库 v3.0

一个支持多种后端的高性能特征值求解库，采用模块化设计，支持多种计算后端和特征值算法。

## ✨ 主要特性

### 🔌 **多后端支持**
- **NumPy CPU后端** - 通用CPU计算
- **CuPy CUDA后端** - GPU加速（可选）
- 运行时自动检测和切换
- 统一的接口抽象

### 📊 **多种特征值算法**
- **幂法 (Power Method)** - 求最大模特征值
- **QR算法** - 求全部特征值
- **Jacobi方法** - 对称矩阵专用
- **Arnoldi迭代** - 求前k个特征值（适合大型稀疏矩阵）

### 🤖 **智能算法选择**
- 自动检测矩阵类型（稠密/稀疏）
- 根据矩阵规模自动选择合适算法
- 统一的`eig()`接口

### 📈 **性能基准测试**
- 内置benchmark模块
- 跨后端性能对比
- 详细的统计信息

## 📁 项目结构

```
eigenvalue_solver/
├── __init__.py              # 包入口
├── backends/                # 后端模块
│   ├── __init__.py
│   ├── base.py             # 后端抽象基类
│   ├── numpy_backend.py    # NumPy CPU后端
│   └── cupy_backend.py     # CuPy CUDA后端
├── solvers/                # 求解器模块
│   ├── __init__.py
│   └── eigenvalue.py       # 特征值算法
├── benchmark.py             # 性能基准测试
├── examples.py              # 使用示例
├── verify_improvements.py # 改进验证
└── test_*.py             # 测试文件
```

## 🚀 快速开始

### 安装依赖

```bash
# 基础依赖
pip install numpy

# GPU支持（可选）
pip install cupy-cuda12x  # 根据CUDA 12.x
```

### 基本使用

```python
import numpy as np
from eigenvalue_solver import eig, power_method, get_backend

# 创建测试矩阵
A = np.random.randn(1000, 1000)

# 1. 自动后端选择 - 自动选择算法
eigvals, eigvecs = eig(A, k=10)  # 自动用Arnoldi

# 2. 显式指定后端
backend = get_backend('numpy')  # 或 'cupy'
eigval, eigvec = power_method(A, backend=backend)

# 3. QR算法求全部特征值
eigvals_all = qr_algorithm(A)
```

### 后端管理

```python
from eigenvalue_solver import (
    list_available_backends,
    get_backend,
    set_default_backend,
    auto_select_backend
)

# 查看可用后端
print(list_available_backends())  # ['numpy', 'cupy']

# 获取后端
numpy_backend = get_backend('numpy')
cupy_backend = get_backend('cupy')

# 设置默认后端
set_default_backend('cupy')

# 根据数组类型自动选择
backend = auto_select_backend(array)
```

### 性能基准测试

```python
from eigenvalue_solver import benchmark

# 运行所有基准测试
results = benchmark.run_all_benchmarks()

# 单项测试
result = benchmark.benchmark_power_method(sizes=[100, 500, 1000])
result.print_summary()
```

## 📚 API参考

### 后端接口

| 函数 | 说明 |
|------|------|
| `LinearAlgebraBackend` | 后端抽象基类 |
| `get_backend(name)` | 获取指定后端 |
| `list_available_backends()` | 列出可用后端 |
| `set_default_backend(name)` | 设置默认后端 |
| `auto_select_backend(array)` | 自动选择后端 |

### 特征值求解器

| 函数 | 说明 |
|------|------|
| `power_method(A, max_iter, tol, backend)` | 幂法求最大特征值 |
| `qr_algorithm(A, max_iter, tol, backend)` | QR算法求全部特征值 |
| `jacobi_method(A, max_iter, tol, threshold, backend)` | Jacobi方法 |
| `arnoldi_iteration(A, k, max_iter, tol, reortho, backend)` | Arnoldi迭代 |
| `eig(A, k, which, max_iter, tol, backend)` | 统一接口 |

### BenchmarkResult类

| 方法 | 说明 |
|------|------|
| `add_time(backend, time)` | 添加时间记录 |
| `add_error(backend, error)` | 添加误差记录 |
| `get_stats(backend)` | 获取统计信息 |
| `print_summary()` | 打印总结 |

## 🔧 扩展开发

### 添加新后端

1. 继承`LinearAlgebraBackend`
2. 实现所有抽象方法
3. 在`backends/__init__.py`中注册

```python
from .base import LinearAlgebraBackend

class MyBackend(LinearAlgebraBackend):
    @property
    def name(self):
        return 'my-backend'
    
    @property
    def xp(self):
        return my_array_module
    
    # ... 实现其他方法
```

## 📊 性能特点

| 算法 | 时间复杂度 | 适用场景 |
|------|------------|----------|
| 幂法 | O(n²) | 大型矩阵求主导特征值 |
| QR | O(n³) | 中小型矩阵求全部特征值 |
| Jacobi | O(n³) | 对称矩阵高精度求解 |
| Arnoldi | O(kn²) | 大型矩阵求前k个特征值 |

## 📝 版本历史

### v3.0 (当前)
- ✅ 模块化后端架构重构
- ✅ NumPy CPU后端实现
- ✅ CuPy CUDA后端实现
- ✅ 自动后端选择逻辑
- ✅ 性能基准测试模块

### v2.0
- ✅ 稀疏矩阵支持
- ✅ SciPy稀疏格式支持
- ✅ Arnoldi迭代算法

### v1.0
- ✅ 基础特征值算法
- ✅ 收敛性改进

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request!
