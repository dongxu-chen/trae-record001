# Rust 加速版本构建指南

## 前置要求

### 1. 安装 Rust
访问 https://rustup.rs/ 安装 Rust 工具链：

```bash
# Linux/macOS
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Windows (PowerShell)
# 访问 https://rustup.rs/ 下载并运行安装程序
```

验证安装：
```bash
rustc --version
cargo --version
```

### 2. 安装 Maturin
```bash
pip install maturin
```

## 构建步骤

### 开发模式构建（推荐）
在项目根目录运行：
```bash
maturin develop --release
```

这将：
1. 编译 Rust 代码为优化的 Python 扩展
2. 直接安装到当前 Python 环境中
3. 立即可供导入使用

### 构建 wheel 包
```bash
maturin build --release
```

生成的 wheel 包将在 `target/wheels/` 目录中。

### 安装 wheel 包
```bash
pip install target/wheels/seqalign_rs-*.whl
```

## 验证安装

```python
import seqalign

print(f"Version: {seqalign.__version__}")
print(f"Rust available: {seqalign.has_rust()}")

if seqalign.has_rust():
    from seqalign import NeedlemanWunschRust
    
    nw = NeedlemanWunschRust(
        match_score=2,
        mismatch_score=-1,
        gap_open=-5,
        gap_extend=-1,
        use_affine=True
    )
    
    result = nw.align("MVLSPADKTN", "MVLSAADKTN")
    print(f"Score: {result.score}")
    print(f"Aligned 1: {result.aligned_seq1}")
    print(f"Aligned 2: {result.aligned_seq2}")
```

## 性能优化选项

### 1. CPU 特定优化
在 `Cargo.toml` 中配置：
```toml
[profile.release]
opt-level = 3
lto = "fat"
codegen-units = 1
target-cpu = "native"  # 使用当前 CPU 的所有指令集
```

### 2. 交叉编译（针对其他 CPU）
```bash
# 编译针对通用 x86-64 CPU
RUSTFLAGS="-C target-cpu=x86-64-v2" maturin build --release
```

### 3. 启用更多 SIMD 特性
```bash
RUSTFLAGS="-C target-feature=+avx2,+avx512f" maturin build --release
```

## 运行性能测试

```bash
# 运行完整性能对比
python test_rust_performance.py

# 运行简单示例
python example_rust.py
```

## 预期性能提升

| 算法 | 序列长度 | Python | Rust | 加速比 |
|------|---------|--------|------|-------|
| Needleman-Wunsch | 100 | ~10 ms | ~0.5 ms | ~20x |
| Needleman-Wunsch | 500 | ~250 ms | ~12 ms | ~20x |
| Smith-Waterman | 100 | ~15 ms | ~0.8 ms | ~18x |
| 批量比对 (50x200) | | ~30 s | ~1-2 s | ~15-30x |

*实际性能取决于 CPU 和具体场景*

## 故障排除

### 1. 编译错误: linker `cc` not found
```bash
# Ubuntu/Debian
sudo apt-get install build-essential

# macOS (安装 Xcode command line tools)
xcode-select --install

# Windows (安装 Visual Studio Build Tools)
```

### 2. Python 头文件缺失
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev

# CentOS/RHEL
sudo yum install python3-devel
```

### 3. Maturin 找不到 Python
```bash
# 指定 Python 解释器
maturin develop --release -i python3
# 或者
python -m maturin develop --release
```

## 开发 Rust 代码

### 项目结构
```
.
├── src/
│   ├── lib.rs                 # PyO3 模块导出
│   ├── alignment.rs           # 结果类型和参数定义
│   ├── needleman_wunsch.rs    # Needleman-Wunsch 实现
│   ├── smith_waterman.rs      # Smith-Waterman 实现
│   ├── parallel.rs            # 多线程并行处理
│   └── simd.rs                # SIMD 优化工具
├── seqalign/                  # Python 包装层
│   └── rust_bindings.py
├── Cargo.toml                 # Rust 项目配置
└── pyproject.toml             # Python 包配置
```

### 添加新功能
1. 在 `src/` 下添加 Rust 实现
2. 在 `lib.rs` 中通过 PyO3 导出
3. 在 `seqalign/rust_bindings.py` 中添加 Python 包装
4. 在 `seqalign/__init__.py` 中导出

### 运行 Rust 单元测试
```bash
cargo test
cargo test --release  # 优化模式运行测试
```

## 技术栈

- **Rust**: 高性能系统编程语言
- **PyO3**: Rust ↔ Python 绑定
- **Rayon**: 数据并行计算
- **Ndarray**: 多维数组（NumPy 类似）
- **Maturin**: Python 包构建工具
