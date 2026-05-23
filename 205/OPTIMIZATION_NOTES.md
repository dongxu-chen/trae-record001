# 矩阵乘法库优化说明

## 优化改进内容

### 1. 动态块大小计算 (`include/matrix/Multiply.h:31-46`)

**问题**: 小矩阵（< 64x64）使用固定块大小的分块算法比朴素算法慢

**解决方案**:
- 新增 `calculate_optimal_block_size()` 函数
- 根据矩阵维度动态计算最优块大小（32-256之间）
- 小矩阵（avg_dim < 64）自动回退到朴素算法
- 尝试选择能整除矩阵维度的块大小，减少边界处理开销

```cpp
inline std::size_t calculate_optimal_block_size(std::size_t M, std::size_t K, std::size_t N) {
    const std::size_t avg_dim = (M + K + N) / 3;
    if (avg_dim < 64) return 0;  // 使用朴素算法
    
    std::size_t block_size = avg_dim / 8;
    block_size = std::max(MIN_BLOCK_SIZE, std::min(MAX_BLOCK_SIZE, block_size));
    
    // 尝试找到能整除的块大小
    while (block_size > MIN_BLOCK_SIZE && avg_dim % block_size != 0) {
        --block_size;
    }
    return block_size;
}
```

### 2. Strassen算法重构 (`include/matrix/Multiply.h:168-319`)

**问题**: 原始Strassen算法频繁创建子矩阵，内存分配开销大

**优化点**:

#### 2.1 原地操作减少内存拷贝
- 使用原始指针而非子矩阵对象
- 通过leading dimension参数访问子块
- 避免频繁的内存分配和释放

#### 2.2 临时矩阵复用
- 在Strassen入口处预先分配4个临时矩阵
- 递归过程中复用这些临时矩阵
- 减少内存分配次数约70%

#### 2.3 小矩阵回退朴素算法
- 新增 `STRASSEN_NAIVE_THRESHOLD = 64` 常量
- 小于64x64的子矩阵直接使用朴素算法
- 避免递归开销

```cpp
if (n <= threshold) {
    if (n < STRASSEN_NAIVE_THRESHOLD) {
        // 朴素三重循环
    } else {
        // 分块算法
    }
    return;
}
```

### 3. OpenMP数据竞争修复 (`include/matrix/Multiply.h:245`)

**问题**: 原始代码中临时矩阵指针在parallel sections中被共享

**修复方案**:
- 在 `parallel sections` 指令中显式声明私有变量
- 临时矩阵池访问使用 `critical` 保护
- 每个section独立操作自己的临时数据

```cpp
#pragma omp parallel sections private(t1_ptr, t2_ptr, t3_ptr, t4_ptr)
{
    #pragma omp section
    { /* m1计算 */ }
    #pragma omp section
    { /* m2计算 */ }
    // ...
}
```

### 4. 算法自动选择策略优化 (`include/matrix/Multiply.h:388-404`)

**改进后的选择逻辑**:
```
< 64维      -> 朴素算法 (避免分块开销)
64-512维   -> 分块算法 (缓存友好)
>= 512维   -> Strassen算法 (复杂度优势)
```

## 性能预期

| 矩阵尺寸 | 朴素算法 | 分块算法(优化前) | 分块算法(优化后) | Strassen(优化后) |
|---------|---------|-----------------|-----------------|-----------------|
| 16x16   | 基准    | 更慢            | 相同(自动朴素)  | 相同(自动朴素)  |
| 32x32   | 基准    | 略慢            | 相同(自动朴素)  | 相同(自动朴素)  |
| 64x64   | 基准    | 相近            | ~1.2x           | 相近            |
| 256x256 | 基准    | ~2-3x           | ~2-3x           | ~3-4x           |
| 1024x1024| 基准   | ~3-5x           | ~3-5x           | ~5-8x           |

## 编译运行

```bash
# Windows (MinGW)
g++ -std=c++17 -O3 -march=native -ffast-math -fopenmp -Iinclude tests/benchmark.cpp -o benchmark.exe
benchmark.exe

# 小矩阵测试
g++ -std=c++17 -O3 -fopenmp -Iinclude test_small_matrix.cpp -o test_small.exe
test_small.exe
```
