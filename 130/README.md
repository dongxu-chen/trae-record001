# 气候模式数据分析库 - Python科学计算工具

基于 Xarray + Dask + NetCDF 的气候模式数据分析工具库。

## 功能特性

### 1. 数据读取与预处理 (`data_reader.py`)
- 支持 NetCDF 和 GRIB 格式数据读取
- 多文件拼接
- 区域选择
- 气候态计算
- 距平计算
- 季节/年平均计算

### 2. EOF经验正交函数分析 (`eof_analysis.py`)
- 纬度加权 EOF 分解
- 主成分 (PC) 提取
- 解释方差计算
- 数据重建
- 结果保存

### 3. 时间序列趋势分析 (`trend_analysis.py`)
- 线性趋势分析
- Mann-Kendall 非参数趋势检验
- Theil-Sen 斜率估计
- 去趋势处理
- 滑动平均
- 标准化
- 显著性检验

### 4. 地理热力图可视化 (`visualization.py`)
- 地理热力图 (支持多种投影)
- 带显著性标记的趋势图
- EOF 模态空间分布图
- 主成分时间序列图
- 解释方差柱状图

## 安装依赖

```bash
pip install -r requirements.txt
```

或

```bash
pip install xarray dask netCDF4 numpy scipy matplotlib cartopy scikit-learn pandas cfgrib
```

## 快速开始

### 1. 生成示例数据

```bash
python generate_sample_data.py
```

### 2. 运行完整示例

```bash
python example_usage.py
```

### 3. 基本使用示例

```python
from climate_analysis import ClimateDataReader, EOFAnalysis, TrendAnalysis, ClimateVisualizer

# 1. 读取数据
reader = ClimateDataReader()
ds = reader.read_netcdf("your_data.nc")

# 2. EOF分析
temp_anomaly = reader.anomaly("temperature")
eof_analysis = EOFAnalysis(temp_anomaly)
eofs, pcs, eigenvalues = eof_analysis.fit(n_modes=10)

# 3. 趋势分析
trend_analysis = TrendAnalysis(ds.temperature)
trend, p_value = trend_analysis.linear_trend()

# 4. 可视化
visualizer = ClimateVisualizer()
visualizer.plot_heatmap(ds.temperature.mean(dim="time"))
```

## 模块说明

### ClimateDataReader

```python
from climate_analysis import ClimateDataReader

reader = ClimateDataReader(chunks={"time": "auto"})

# 读取NetCDF
ds = reader.read_netcdf("data.nc", variables=["temperature"])

# 读取GRIB
ds = reader.read_grib("data.grib")

# 区域选择
subset = reader.select_region(
    "temperature",
    lat_range=(-30, 30),
    lon_range=(100, 140),
    time_range=("2000", "2020")
)

# 气候态与距平
clim = reader.climatology("temperature")
anomaly = reader.anomaly("temperature")
```

### EOFAnalysis

```python
from climate_analysis import EOFAnalysis

eof_analysis = EOFAnalysis(anomaly_data)
eofs, pcs, eigenvalues = eof_analysis.fit(n_modes=10, apply_weights=True)

# 获取结果
explained_var = eof_analysis.get_explained_variance_ratio()
eofs_modes = eof_analysis.get_eofs(modes=[1, 2, 3])

# 重建数据
reconstructed = eof_analysis.reconstruct(modes=[1, 2])
```

### TrendAnalysis

```python
from climate_analysis import TrendAnalysis

trend_analysis = TrendAnalysis(data)

# 线性趋势
trend, p_value = trend_analysis.linear_trend()

# Mann-Kendall检验
z_stat, mk_p_value, slope = trend_analysis.mann_kendall_test()

# 去趋势
detrended = trend_analysis.detrend(order=1)

# 显著性掩膜
significant = trend_analysis.get_significant_mask(alpha=0.05)
```

### ClimateVisualizer

```python
from climate_analysis import ClimateVisualizer

visualizer = ClimateVisualizer(figsize=(12, 8), dpi=100)

# 热力图
visualizer.plot_heatmap(
    data,
    title="Title",
    cmap="RdBu_r",
    projection="PlateCarree",
    output_path="output.png"
)

# 趋势显著性图
visualizer.plot_trend_with_significance(
    trend_data,
    p_value,
    alpha=0.05
)

# EOF模态图
visualizer.plot_eof_modes(eofs, explained_var, n_modes=4)
```

## 项目结构

```
.
├── climate_analysis/
│   ├── __init__.py
│   ├── data_reader.py      # 数据读取模块
│   ├── eof_analysis.py       # EOF分析模块
│   ├── trend_analysis.py     # 趋势分析模块
│   └── visualization.py       # 可视化模块
├── generate_sample_data.py    # 生成示例数据
├── example_usage.py        # 完整示例脚本
├── requirements.txt         # 依赖列表
├── setup.py                # 安装配置
└── README.md               # 项目说明
```

## 技术栈

- **Xarray**: 多维数组处理
- **Dask**: 并行计算
- **NetCDF4**: NetCDF格式读写
- **NumPy/SciPy**: 数值计算与统计
- **Matplotlib/Cartopy**: 地理可视化
- **scikit-learn**: 机器学习工具

## 许可证

MIT License
