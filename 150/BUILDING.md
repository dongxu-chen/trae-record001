# MS Peak Detector - 构建说明

## 项目架构

```
MS Peak Detector v0.2.0
┌─────────────────────────────────────────────────────────────┐
│                    Python API Layer                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ms_peak_detector/ (纯Python实现，完全可用)            │  │
│  │  - baseline_correction.py                              │  │
│  │  - peak_detection.py                                   │  │
│  │  - peak_alignment.py                                   │  │
│  │  - isotope_detection.py                                │  │
│  │  - spectral_library.py                                 │  │
│  │  - ptm_identification.py                               │  │
│  │  - quantitation.py                                     │  │
│  │  - file_io.py                                          │  │
│  └───────────────────────────────────────────────────────┘  │
│                              ↓                                │
├─────────────────────────────────────────────────────────────┤
│                PyO3 Python Bindings (Rust)                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  rust_ffi/src/lib.rs                                   │  │
│  │  - FFI 安全绑定                                        │  │
│  │  - Python 类封装                                       │  │
│  │  - 自动类型转换                                        │  │
│  └───────────────────────────────────────────────────────┘  │
│                              ↓                                │
├─────────────────────────────────────────────────────────────┤
│              C++ Core Implementation                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  cpp_core/include/ms_peak_detector.h                  │  │
│  │  cpp_core/src/ms_peak_detector.cpp                    │  │
│  │  - 分段ASLS基线校正                                    │  │
│  │  - 局部最大值峰检测 + 相邻峰合并                       │  │
│  │  - C++ 原生多线程支持                                  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 前置要求

### 构建高性能版本（必需）

1. **C++ 编译器**
   - Windows: Visual Studio 2019+ 或 MSVC
   - Linux: GCC 7+ 或 Clang 5+
   - macOS: Xcode Command Line Tools

2. **Rust 工具链**
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   # 或从 https://rustup.rs/ 下载安装
   ```

3. **Python 3.7+** (用于 PyO3 绑定)

### 仅使用纯Python版本

只需 Python 3.7+ 和依赖包：
```bash
pip install numpy scipy
```

## 构建步骤

### Windows

```powershell
# 1. 进入 Rust FFI 目录
cd rust_ffi

# 2. 构建 Release 版本
cargo build --release

# 3. 复制编译好的库到 Python 包目录
# 注意: 实际文件名可能有前缀 lib 和 .pyd 后缀
copy target\release\ms_peak_detector_core.dll ..\ms_peak_detector\ms_peak_detector_core.pyd

# 或者使用更通用的方式:
if (Test-Path target\release\ms_peak_detector_core.dll) {
    copy target\release\ms_peak_detector_core.dll ..\ms_peak_detector\ms_peak_detector_core.pyd
} elseif (Test-Path target\release\libms_peak_detector_core.dll) {
    copy target\release\libms_peak_detector_core.dll ..\ms_peak_detector\ms_peak_detector_core.pyd
}
```

### Linux / macOS

```bash
# 1. 进入 Rust FFI 目录
cd rust_ffi

# 2. 构建 Release 版本
cargo build --release

# 3. 复制编译好的库到 Python 包目录
# Linux
cp target/release/libms_peak_detector_core.so ../ms_peak_detector/ms_peak_detector_core.so

# macOS
cp target/release/libms_peak_detector_core.dylib ../ms_peak_detector/ms_peak_detector_core.so
```

## 验证安装

```python
import ms_peak_detector as msd

print(f"版本: {msd.__version__}")
print(f"高性能核心可用: {msd.__core_available__}")

if msd.__core_available__:
    print("✓ 使用 C++/Rust 高性能实现")
else:
    print("⚠  使用纯 Python 实现")
```

## 构建选项

### 优化编译

```bash
# 最大优化（针对本地 CPU）
RUSTFLAGS="-C target-cpu=native" cargo build --release

# 更小的二进制（启用 LTO）
# 在 Cargo.toml 中添加:
[profile.release]
lto = true
codegen-units = 1
```

### 只编译 C++ 部分

```bash
# 使用 CMake 单独编译 C++ 库
cd cpp_core
mkdir build && cd build
cmake ..
make
```

## 预期性能提升

| 功能 | Python | C++/Rust | 加速比 |
|------|--------|----------|--------|
| 基线校正 (5万点) | ~500ms | ~20ms | ~25x |
| 峰检测 (5万点) | ~300ms | ~15ms | ~20x |
| 批量处理 (20谱图) | ~16s | ~0.4s | ~40x |

*实际性能取决于硬件和编译器优化设置

## 故障排除

### Windows 下找不到 C++ 编译器

```
error: linker `link.exe` not found
```

解决方法:
1. 安装 [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/)
2. 选择 "使用 C++ 的桌面开发" 工作负载
3. 重新打开 PowerShell/CMD

### 找不到 Python 开发库

```
error: could not find native static library `pythonXY`
```

解决方法:
```bash
# 确保安装了 Python 开发包
# Ubuntu/Debian:
sudo apt-get install python3-dev

# CentOS/RHEL:
sudo yum install python3-devel
```

### 导入时找不到模块

```
ImportError: cannot import name 'ms_peak_detector_core'
```

解决方法:
1. 检查 .pyd/.so 文件是否复制到了正确位置
2. 确认文件名是 `ms_peak_detector_core.pyd` (Windows) 或 `ms_peak_detector_core.so` (Linux/macOS)
3. 检查文件权限

## 开发模式

### 快速迭代（Debug 模式）

```bash
cargo build
# 复制 debug 版本的库进行测试
cp target/debug/libms_peak_detector_core.so ../ms_peak_detector/
```

### 运行测试

```bash
# Python 测试
cd ..
python example_fast.py

# Rust 单元测试
cd rust_ffi
cargo test
```

## 依赖说明

### Cargo 依赖 (自动安装)

- **pyo3**: Python Rust 绑定
- **numpy**: NumPy 数组支持
- **rayon**: 数据并行库
- **cc**: C/C++ 编译构建工具

### Python 运行时依赖

- **numpy**: 数值计算
- **scipy**: 信号处理 (纯 Python 版本)
