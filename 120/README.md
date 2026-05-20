# 分子动力学轨迹分析工具 (MDAnalysis + NumPy)

一个基于MDAnalysis和NumPy的Python科学计算库，用于分子动力学轨迹分析。

## 功能特性

1. **轨迹文件读取** - 支持xtc/trr等常见轨迹格式
2. **RMSD计算** - 均方根偏差，使用Kabsch算法进行结构对齐
3. **回旋半径Rg计算** - 支持质量加权计算
4. **完整报告输出** - 文本报告、CSV数据、可视化图表

## 安装依赖

```bash
pip install -r requirements.txt
```

依赖包:
- MDAnalysis >= 2.0.0
- NumPy >= 1.21.0
- matplotlib >= 3.4.0
- pandas >= 1.3.0

## 快速开始

### 命令行使用

```bash
# 基本用法
python md_analysis_cli.py -t topology.pdb -x trajectory.xtc

# 指定原子选择
python md_analysis_cli.py -t topology.pdb -x trajectory.xtc --rmsd-sel "backbone"

# 只计算Rg，不使用质量加权
python md_analysis_cli.py -t topology.pdb -x trajectory.xtc --no-rmsd --rg-sel "protein" --no-masses

# 指定输出目录
python md_analysis_cli.py -t topology.pdb -x trajectory.xtc -o my_results -p run1
```

### Python API使用

```python
from md_analysis import TrajectoryReader, RMSDCalculator, RgCalculator, ReportGenerator

# 1. 加载轨迹
reader = TrajectoryReader("topology.pdb", "trajectory.xtc")
reader.load()

# 2. 计算RMSD
rmsd_calc = RMSDCalculator(reader)
rmsd_results = rmsd_calc.calculate(
    reference_frame=0,
    selection="backbone"
)
rmsd_stats = rmsd_calc.get_statistics()

# 3. 计算回旋半径Rg
rg_calc = RgCalculator(reader)
rg_results = rg_calc.calculate(
    selection="protein",
    use_masses=True
)
rg_stats = rg_calc.get_statistics()

# 4. 生成完整报告
reporter = ReportGenerator(
    trajectory_summary=reader.summary(),
    rmsd_results=rmsd_results,
    rg_results=rg_results
)
reporter.generate_full_report(
    output_dir="analysis_results",
    output_prefix="md_analysis"
)
```

## API说明

### TrajectoryReader (轨迹读取器)

| 方法 | 说明 |
|------|------|
| `load()` | 加载拓扑和轨迹文件 |
| `get_frame(frame_index)` | 获取指定帧的坐标 |
| `get_all_coordinates(selection)` | 获取所选原子的所有帧坐标 |
| `get_selection(selection)` | 获取原子选择对象 |
| `get_time_array()` | 获取时间数组 |
| `summary()` | 获取轨迹摘要信息 |

### RMSDCalculator (RMSD计算器)

| 方法 | 说明 |
|------|------|
| `calculate(reference_frame, selection, group_selections)` | 计算RMSD |
| `get_statistics()` | 获取RMSD统计信息 (mean, std, min, max, median) |
| `get_rmsd_array()` | 获取时间和RMSD数组 |

### RgCalculator (回旋半径计算器)

| 方法 | 说明 |
|------|------|
| `calculate(selection, use_masses, group_selections)` | 计算Rg |
| `get_statistics()` | 获取Rg统计信息 |
| `get_rg_array()` | 获取时间和Rg数组 |
| `calculate_asphericity(selection)` | 计算形状参数 (非球形度、圆柱度、各向异性) |

### ReportGenerator (报告生成器)

| 方法 | 说明 |
|------|------|
| `generate_text_report(output_file)` | 生成文本报告 |
| `generate_csv_data(output_prefix)` | 生成CSV数据文件 |
| `generate_plots(output_prefix, dpi)` | 生成可视化图表 |
| `generate_full_report(output_dir, output_prefix)` | 生成完整报告 |

## 输出文件说明

生成的报告包含以下文件：

```
analysis_results/
├── md_analysis_report.txt     # 文本分析报告
├── md_analysis_rmsd.csv       # RMSD数据CSV
├── md_analysis_rg.csv         # Rg数据CSV
├── md_analysis_rmsd.png       # RMSD曲线图
├── md_analysis_rg.png         # Rg曲线图
└── md_analysis_combined.png   # RMSD+Rg组合图
```

## 原子选择语法

MDAnalysis支持类似VMD的原子选择语法：

| 选择器 | 示例 |
|--------|------|
| 主链 | `backbone` |
| α碳 | `name CA` |
| 蛋白质 | `protein` |
| 特定残基 | `resid 10 to 50` |
| 特定残基类型 | `resname ALA` |
| 原子名称 | `name N C O CA` |

## 许可证

MIT License
