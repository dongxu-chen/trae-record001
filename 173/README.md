# 晶体材料声子谱计算程序

基于ASE + Phonopy + matplotlib + seekpath实现的晶体材料声子谱计算工具。

## 功能特性

- **晶体结构输入与处理**：支持多种格式（VASP、CIF、XYZ等）
- **力常数矩阵输入与处理**：支持从文件加载或自动生成
- **密度泛函微扰理论（DFPT）框架**：基于Phonopy的声子计算
- **Seekpath自动布里渊区路径**：自动识别晶体对称性，生成标准高对称点路径
- **声子色散关系计算**：沿高对称路径计算声子频率
- **声子态密度（DOS）计算**：全BZ积分计算声子态密度
- **声子谱插值平滑**：默认使用三次样条插值，保证曲线光滑
- **力常数稳定性检查**：自动检测负本征值，虚频预警
- **高质量可视化输出**：色散关系 + 态密度联合图，虚频高亮显示

## 新增功能（v2.0）

### 1. Seekpath自动路径生成
- 自动识别晶体对称性（通过spglib）
- 生成标准的不可约布里渊区高对称路径
- 支持所有常见晶格类型（FCC、BCC、SC、六角、正交等）
- 自动格式化高对称点标签（Γ, X, L, K等）

### 2. 三次样条插值平滑
- 默认使用三次样条（cubic spline）插值
- 可调节插值因子（factor）控制平滑程度
- 插值失败时自动降级为线性插值
- 保持曲线二阶导数连续，视觉效果更平滑

### 3. 力常数本征值检查与虚频预警
- 设置力常数时自动计算本征值谱
- 检测负本征值数量和最小值
- 声子谱计算后检测虚频模式
- 虚频在图中用红色虚线高亮显示
- 提供可能的原因分析和建议

## 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install numpy matplotlib ase phonopy scipy pyyaml seekpath
```

## 快速开始

### 方法1：运行示例

```bash
# 运行FCC硅的示例（使用Seekpath自动路径）
python phonon_calculator.py --example fcc

# 运行BCC铁的示例
python phonon_calculator.py --example bcc

# 运行不稳定结构示例（演示虚频检测）
python phonon_calculator.py --example unstable

# 运行插值方法对比示例
python phonon_calculator.py --example interp

# 运行所有示例
python example_usage.py
```

### 方法2：使用自定义结构

```bash
# 从结构文件计算（自动生成示例力常数，使用Seekpath）
python phonon_calculator.py --structure POSCAR --supercell 2 --mesh 20

# 使用自定义力常数文件
python phonon_calculator.py --structure POSCAR --force_constants force_constants.npy

# 禁用Seekpath，使用默认路径
python phonon_calculator.py --structure POSCAR --no-seekpath

# 禁用力常数稳定性检查
python phonon_calculator.py --structure POSCAR --no-check
```

### 方法3：Python API调用

```python
import numpy as np
from ase import Atoms
from phonon_calculator import PhononCalculator

# 1. 创建晶体结构
a = 5.431
atoms = Atoms(
    symbols=['Si', 'Si'],
    cell=[[0, a/2, a/2], [a/2, 0, a/2], [a/2, a/2, 0]],
    scaled_positions=[[0, 0, 0], [0.25, 0.25, 0.25]],
    pbc=True
)

# 2. 初始化计算器
supercell_matrix = np.eye(3, dtype=int) * 2
calculator = PhononCalculator(atoms, supercell_matrix=supercell_matrix)

# 3. 设置力常数（自动进行稳定性检查）
force_constants = np.load('force_constants.npy')
calculator.set_force_constants(force_constants, check_stability=True)

# 4. 计算声子色散关系（使用Seekpath自动路径）
calculator.calculate_band_structure(use_seekpath=True)

# 5. 计算声子态密度
calculator.calculate_dos(mesh=(20, 20, 20))

# 6. 可视化并保存结果（默认使用三次样条插值）
calculator.plot_band_and_dos(
    save_path='phonon_result.png',
    interpolate=True,
    interpolation_method='cubic',  # 三次样条
    interpolation_factor=3
)
calculator.save_results(prefix='si_phonon')
```

## 主要类和方法

### PhononCalculator 类

| 方法 | 说明 |
|------|------|
| `__init__(atoms, supercell_matrix)` | 初始化计算器 |
| `set_force_constants(fc, check_stability)` | 设置力常数，可选稳定性检查 |
| `_check_force_constants_stability(fc)` | 力常数矩阵本征值分析 |
| `generate_displacements(distance)` | 生成位移超胞（用于DFT计算） |
| `set_forces(forces_list, check_stability)` | 从DFT力自动生成力常数 |
| `calculate_band_structure(path, labels, npoints, use_seekpath)` | 计算声子能带结构 |
| `_get_seekpath_path()` | 使用Seekpath自动生成高对称路径 |
| `calculate_dos(mesh, sigma, freq_range)` | 计算声子态密度 |
| `interpolate_bands(qpoints, frequencies, factor, method)` | 声子谱插值（默认三次样条） |
| `plot_band_structure(interpolate, highlight_imaginary)` | 绘制声子色散关系 |
| `plot_dos()` | 绘制声子态密度 |
| `plot_band_and_dos()` | 联合绘制色散关系和态密度 |
| `save_results(prefix)` | 保存所有结果 |
| `from_file(filename, supercell_matrix)` | 从文件创建计算器 |
| `generate_example_force_constants()` | 生成示例力常数（稳定） |
| `generate_unstable_force_constants()` | 生成不稳定力常数（用于测试） |

## 输入格式

### 晶体结构文件

支持ASE可读取的所有格式：
- VASP POSCAR/CONTCAR
- CIF
- XYZ
- PDB
- 等等

### 力常数矩阵

力常数矩阵格式：`(n_supercell_atoms, n_supercell_atoms, 3, 3)` 的numpy数组

可以通过以下方式获得：
1. 从Phonopy的FORCE_CONSTANTS文件加载
2. 从DFT计算的力自动生成（使用`set_forces`方法）
3. 使用示例生成器（`generate_example_force_constants`）

## 输出文件

- `*.png`: 声子谱图像（虚频用红色虚线标记）
- `*_frequencies.npy`: 声子频率数组
- `*_qpoints.npy`: q点坐标数组
- `*_dos.npy`: 态密度数组
- `*_dos_frequencies.npy`: 态密度频率数组
- `*_band.yaml`: 声子能带结构YAML文件
- `*_dos.yaml`: 态密度YAML文件

## 布里渊区路径

### Seekpath自动识别（推荐）

程序会自动识别晶体的空间群，并生成标准的高对称点路径：
- **FCC**: Γ → X → U | K → Γ → L → W → X
- **BCC**: Γ → H → N → Γ → P → H|P → N
- **简单立方**: Γ → X → M → Γ → R → X|M → R
- **六角**: Γ → M → K → Γ → A → L → H → A
- 等等...

### 自定义路径

也可以自定义路径，格式为：
```python
path = [
    (start_q1, end_q1, npoints1),
    (start_q2, end_q2, npoints2),
    ...
]
```

## 插值方法

默认使用**三次样条插值（cubic）**，保证曲线二阶导数连续。

支持的插值方法（scipy.interpolate.interp1d）：
- `linear`: 线性插值（一阶连续）
- `nearest`: 最近邻插值
- `zero`: 零阶样条
- `slinear`: 一阶样条
- `quadratic`: 二阶样条
- `cubic`: 三阶样条（默认，推荐，二阶连续）
- `previous`: 前向插值
- `next`: 后向插值

### 插值参数

```python
calculator.plot_band_structure(
    interpolate=True,
    interpolation_factor=3,      # 插值倍数（点数增加倍数）
    interpolation_method='cubic' # 插值方法
)
```

## 稳定性检查与虚频处理

### 力常数检查

```python
# 设置力常数时自动检查
calculator.set_force_constants(force_constants, check_stability=True)

# 输出示例：
# ✅ 力常数矩阵稳定性检查通过：最小本征值 = 1.234567e-02
# 或
# ⚠️  检测到力常数矩阵存在 5 个负本征值！
# 最小本征值: -1.234567e-01
# 这可能导致声子谱出现虚频...
```

### 虚频可视化

- 虚频模式（频率 < 0）在图中用**红色虚线**标记
- 实频模式用**蓝色实线**显示
- 标题中会显示⚠️警告标识

### 虚频常见原因

1. 晶体结构未充分弛豫（力不为零）
2. 超胞大小不足（短程相互作用未收敛）
3. DFT计算参数未收敛（截断能、k点等）
4. 位移大小不合适（过大或过小）
5. 该结构本身就是动力学不稳定的

## 命令行参数

```bash
python phonon_calculator.py [options]

选项：
  --structure STR       结构文件路径
  --force_constants STR 力常数文件路径 (.npy)
  --example {fcc,bcc,unstable,interp}  运行示例
  --supercell INT       超胞大小 (默认: 2)
  --mesh INT            DOS计算的k点网格 (默认: 20)
  --npoints INT         每段路径的q点数 (默认: 101)
  --no-seekpath         禁用Seekpath自动路径
  --no-check            禁用力常数稳定性检查
```

## 示例说明

1. **FCC Silicon**: 面心立方硅的声子谱计算（Seekpath自动路径）
2. **BCC Iron**: 体心立方铁的声子谱计算
3. **Unstable Structure**: 不稳定结构示例，演示虚频检测和高亮显示
4. **Interpolation Comparison**: 插值方法对比，展示三次样条的优势

## 注意事项

1. 力常数矩阵需要与超胞大小匹配
2. 对于二维材料，设置`pbc=[True, True, False]`并在DOS计算时使用单层k点网格
3. 插值因子（factor）越大，曲线越平滑，但计算时间也会增加
4. DOS计算的mesh大小影响结果精度，建议使用15×15×15或更大
5. Seekpath依赖于spglib的对称性识别，确保结构已标准化

## 参考文献

- Phonopy: https://phonopy.github.io/phonopy/
- ASE: https://wiki.fysik.dtu.dk/ase/
- Seekpath: https://seekpath.readthedocs.io/
- Togo et al., "First principles phonon calculations in materials science", Scr. Mater. 108, 1-5 (2015)
- Togo et al., "Spglib: a software library for crystal symmetry search", arXiv:1808.01590 (2018)
