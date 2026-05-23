# 矩阵乘法库扩展功能说明

## 新增功能

### 1. 稀疏矩阵支持 (CSR格式)

**文件**: `include/matrix/SparseMatrix.h`

#### SparseMatrixCSR 类

```cpp
template <typename T>
class SparseMatrixCSR {
    // 构造函数
    SparseMatrixCSR(size_t rows, size_t cols, size_t nnz_hint = 0);
    
    // 从稠密矩阵转换
    static SparseMatrixCSR from_dense(const Matrix<T>& dense, T threshold = 0);
    
    // 转换为稠密矩阵
    Matrix<T> to_dense() const;
    
    // 计算稀疏度
    static double calculate_sparsity(const Matrix<T>& dense, T threshold = 0);
    
    // 获取属性
    size_t rows() const;
    size_t cols() const;
    size_t nnz() const;      // 非零元素数量
    double sparsity() const;  // 稀疏度 (0-1)
    
    // CSR数据访问
    const std::vector<size_t>& row_ptr() const;
    const std::vector<int32_t>& col_idx() const;
    const std::vector<T>& values() const;
};
```

#### 稀疏乘法算法

```cpp
// CSR * Dense -> Dense
Matrix<T> sparse::multiply_csr_dense(const SparseMatrixCSR<T>& A, const Matrix<T>& B);

// CSR * CSR -> CSR
SparseMatrixCSR<T> sparse::multiply_csr_csr(const SparseMatrixCSR<T>& A, const SparseMatrixCSR<T>& B);
```

### 2. 自动稀疏检测

**文件**: `include/matrix/MatrixMulExt.h`

```cpp
// 快速估算稀疏度 (采样5%)
double estimate_sparsity_fast(const Matrix<T>& A, double sample_ratio = 0.05);

// 执行配置
struct ExecutionConfig {
    Algorithm algorithm;           // 算法选择
    Device device;                 // 设备选择
    size_t block_size;             // 分块大小
    size_t strassen_threshold;     // Strassen阈值
    double sparsity_threshold;     // 稀疏切换阈值 (默认0.9)
    bool use_sparse;               // 是否强制使用稀疏
    bool sparse_detected;          // 输出: 是否检测到稀疏
};

// 自动选择乘法（包含稀疏检测）
Matrix<T> multiply_auto(const Matrix<T>& A, const Matrix<T>& B, ExecutionConfig<T>& config);
```

**自动选择逻辑**:
- 采样检测矩阵稀疏度
- 稀疏度 >= 90% 时，自动转换为CSR格式并使用稀疏乘法
- 否则使用稠密算法

### 3. CUDA GPU加速

**文件**: 
- `include/matrix/GpuMultiply.h` (头文件/存根实现)
- `src/GpuMultiply.cu` (CUDA内核实现)

#### GPU内核实现

```cpp
// 基础矩阵乘法内核
__global__ void matmul_kernel(float* C, const float* A, const float* B,
                               int M, int K, int N);

// 共享内存分块优化内核
__global__ void matmul_tiled_kernel(float* C, const float* A, const float* B,
                                     int M, int K, int N, int tile_size);

// CPU接口
bool is_cuda_available();
std::string get_cuda_version();

Matrix<T> gpu::multiply_gpu(const Matrix<T>& A, const Matrix<T>& B);
Matrix<T> gpu::multiply_gpu_blocked(const Matrix<T>& A, const Matrix<T>& B, size_t tile_size);
```

**编译时GPU支持**:
- 默认构建：无GPU支持，调用GPU函数会抛出异常
- `cmake -DUSE_CUDA=ON`：启用CUDA支持

### 4. Python绑定 (pybind11)

**文件**: `python/matrix_mul_bindings.cpp`

#### 安装使用

```bash
# 克隆pybind11
mkdir -p third_party
git clone https://github.com/pybind/pybind11.git third_party/pybind11

# 构建Python模块
mkdir build && cd build
cmake .. -DBUILD_PYTHON_BINDINGS=ON -DUSE_CUDA=OFF
make -j
```

#### Python API

```python
import numpy as np
import matrix_mul

# 基本乘法
A = np.random.randn(512, 512).astype(np.float32)
B = np.random.randn(512, 512).astype(np.float32)
C = matrix_mul.multiply(A, B)

# 指定算法
C = matrix_mul.multiply(A, B, algorithm='strassen')  # 'naive', 'blocked', 'strassen', 'auto'

# 指定设备
C = matrix_mul.multiply(A, B, device='gpu')  # 'cpu', 'gpu', 'auto'

# 稀疏阈值配置
C = matrix_mul.multiply(A, B, sparsity_threshold=0.95)

# GPU信息
print(matrix_mul.has_gpu())       # True/False
print(matrix_mul.gpu_info())      # 详细GPU信息

# 稀疏度检测
sparsity = matrix_mul.estimate_sparsity(A)
info = matrix_mul.get_matrix_info(A)  # {'rows', 'cols', 'sparsity', 'nnz'}
```

**支持的数据类型**:
- `numpy.float32` (单精度)
- `numpy.float64` (双精度)

## 完整构建选项

```bash
# 基本构建 (仅CPU)
cmake ..

# 启用CUDA
cmake .. -DUSE_CUDA=ON

# 构建Python绑定
cmake .. -DBUILD_PYTHON_BINDINGS=ON

# 完整构建
cmake .. -DUSE_CUDA=ON -DBUILD_PYTHON_BINDINGS=ON -DUSE_OPENMP=ON
```

## 项目结构

```
205/
├── include/matrix/
│   ├── Matrix.h           # 稠密矩阵类
│   ├── Multiply.h         # 核心乘法算法
│   ├── SparseMatrix.h     # CSR稀疏矩阵
│   ├── MatrixMulExt.h     # 自动选择扩展
│   └── GpuMultiply.h      # GPU接口
├── src/
│   └── GpuMultiply.cu     # CUDA内核
├── python/
│   ├── matrix_mul_bindings.cpp  # pybind11绑定
│   └── example.py               # Python示例
├── tests/
│   └── benchmark.cpp     # C++基准测试
└── CMakeLists.txt
```

## 使用示例

### C++: 自动稀疏检测

```cpp
#include "matrix/MatrixMulExt.h"

using namespace matrix;
using namespace matrix::multiply;

Matrix<float> A = create_sparse_matrix(1024, 1024, 0.95);  // 95%稀疏
Matrix<float> B = Matrix<float>::random(1024, 256);

ExecutionConfig<float> config;
config.sparsity_threshold = 0.90;  // >=90%使用稀疏算法

Matrix<float> C = multiply_auto(A, B, config);

if (config.sparse_detected) {
    std::cout << "Auto-detected sparse matrix, used CSR algorithm" << std::endl;
}
```

### Python: 完整示例

```python
import numpy as np
import matrix_mul

# 大型矩阵自动选择
A = np.random.randn(2048, 2048).astype(np.float32)
B = np.random.randn(2048, 2048).astype(np.float32)

# 自动选择最优算法和设备
C = matrix_mul.multiply(A, B)

# 对比NumPy
import time
start = time.time()
C_np = A @ B
print(f"NumPy time: {time.time() - start:.3f}s")
```
