# SeisProcessor - 地震波形处理工具包

基于 ObsPy 和 Matplotlib 的 Python 地震波形处理科学计算库。

## 功能特性

### 1. 波形滤波 (WaveformFilter)
- **带通滤波**: 自定义频率范围的巴特沃斯带通滤波
- **低通滤波**: 去除高频噪声的低通滤波
- **高通滤波**: 去除低频漂移的高通滤波
- **去趋势**: 线性去趋势处理
- **仪器响应移除**: 移除仪器响应的预处理功能

### 2. 震相拾取 (PhasePicker)
- **STA/LTA 方法**: 经典的长短时平均比方法
- **AIC 方法**: 赤池信息准则自动拾取
- **峰度法 (Kurtosis)**: 基于统计特性的拾取
- **P波拾取**: 初至波自动检测
- **S波拾取**: 横波自动检测（在P波之后）

### 3. 频谱分析 (SpectrumAnalyzer)
- **FFT 频谱**: 快速傅里叶变换频谱计算
- **PSD 功率谱密度**: Welch 方法计算功率谱密度
- **谱图 (Spectrogram)**: 时频联合分析
- **主频计算**: 信号的主导频率
- **峰值频率**: 指定频段内的峰值频率
- **带宽分析**: -3dB 带宽计算
- **中心频率**: 能量加权中心频率
- **谱比分析**: 两个信号的频谱比

### 4. 波形绘图 (WaveformPlotter)
- **单波形绘制**: 单道地震波形绘制
- **多道波形绘制**: 台阵数据的多道显示
- **频谱图**: FFT/PSD 频谱可视化
- **谱图**: 时频联合分析的彩色显示
- **震相拾取标注**: P/S波拾取结果标注
- **滤波对比图**: 滤波前后波形对比
- **综合分析图**: 波形+频谱+谱图+震相标注

## 安装

### 依赖安装
```bash
pip install -r requirements.txt
```

### 包安装
```bash
pip install -e .
```

## 快速开始

### 1. 基本使用示例
```python
from seisprocessor import WaveformFilter, PhasePicker, SpectrumAnalyzer, WaveformPlotter
from obspy import read

# 读取地震数据
stream = read("your_waveform_data.mseed")
trace = stream[0]

# 1. 波形滤波
filter_processor = WaveformFilter()
filtered_trace = filter_processor.filter_trace(
    trace, 
    filter_type="bandpass", 
    lowcut=0.5, 
    highcut=10.0,
    order=4
)

# 2. 震相拾取
picker = PhasePicker()
picks = picker.pick_both_phases(
    trace, 
    method="sta_lta",
    sta_window=1.0,
    lta_window=10.0,
    threshold=3.0
)
print(f"P波到达时间: {picks['P']['time']}")
print(f"S波到达时间: {picks['S']['time']}")

# 3. 频谱分析
analyzer = SpectrumAnalyzer()
fft_result = analyzer.compute_fft(trace)
psd_result = analyzer.compute_psd(trace)
dominant_freq = analyzer.dominant_frequency(trace)
print(f"主频: {dominant_freq['dominant_frequency']:.2f} Hz")

# 4. 绘图
plotter = WaveformPlotter()
plotter.plot_waveform(trace, title="原始波形")
plotter.plot_phase_picks(trace, picks, title="震相拾取结果")
plotter.plot_spectrum(fft_result, title="FFT频谱")
```

### 2. 运行示例代码
```bash
python example.py
```

## 详细使用说明

### WaveformFilter 类

#### 初始化
```python
filter_processor = WaveformFilter(sampling_rate=None)
```

#### 主要方法
```python
# 带通滤波
filtered = filter_processor.filter_trace(
    trace, 
    filter_type="bandpass",
    lowcut=0.5,
    highcut=10.0,
    order=4
)

# 低通滤波
filtered = filter_processor.filter_trace(
    trace, 
    filter_type="lowpass",
    cutoff=5.0,
    order=4
)

# 高通滤波
filtered = filter_processor.filter_trace(
    trace, 
    filter_type="highpass",
    cutoff=0.1,
    order=4
)

# 去趋势
detrended = filter_processor.detrend(trace, type="linear")

# 移除仪器响应
resp_removed = filter_processor.remove_response(trace)
```

### PhasePicker 类

#### 初始化
```python
picker = PhasePicker(sampling_rate=None)
```

#### 主要方法
```python
# STA/LTA 方法拾取P波
p_pick = picker.pick_p_wave(
    trace,
    method="sta_lta",
    sta_window=1.0,
    lta_window=10.0,
    threshold=3.0
)

# AIC 方法拾取P波
p_pick = picker.pick_p_wave(trace, method="aic")

# 峰度法拾取P波
p_pick = picker.pick_p_wave(
    trace,
    method="kurtosis",
    window=2.0,
    threshold=5.0
)

# 拾取S波（需要P波拾取结果作为参考）
s_pick = picker.pick_s_wave(trace, p_pick)

# 同时拾取P和S波
picks = picker.pick_both_phases(trace, method="sta_lta")

# 对整个Stream进行拾取
results = picker.pick_stream(stream, method="sta_lta")
```

### SpectrumAnalyzer 类

#### 初始化
```python
analyzer = SpectrumAnalyzer(sampling_rate=None)
```

#### 主要方法
```python
# FFT频谱
fft_result = analyzer.compute_fft(trace)

# PSD功率谱密度
psd_result = analyzer.compute_psd(
    trace,
    nperseg=256,
    noverlap=128,
    window="hann"
)

# 谱图
spec_result = analyzer.compute_spectrogram(
    trace,
    nperseg=128,
    noverlap=64
)

# 主频
dominant = analyzer.dominant_frequency(trace)

# 峰值频率（指定频段内）
peak_freq = analyzer.peak_frequency(trace, freq_range=(1.0, 10.0))

# 带宽计算
bandwidth = analyzer.bandwidth(trace, level=-3)

# 中心频率
central_freq = analyzer.central_frequency(trace)
```

### WaveformPlotter 类

#### 初始化
```python
plotter = WaveformPlotter(figsize=(12, 8), dpi=100)
```

#### 主要方法
```python
# 绘制单波形
fig, ax = plotter.plot_waveform(
    trace,
    title="地震波形",
    show=True,
    save_path="waveform.png"
)

# 绘制多道波形
fig, axes = plotter.plot_stream(stream, title="台阵波形")

# 绘制频谱
fig, ax = plotter.plot_spectrum(fft_result, title="FFT频谱")

# 绘制谱图
fig, ax = plotter.plot_spectrogram(spec_result, title="时频分析")

# 绘制震相拾取结果
fig, ax = plotter.plot_phase_picks(trace, picks, title="震相拾取")

# 绘制滤波对比图
fig, axes = plotter.plot_filter_comparison(
    original_trace,
    filtered_trace,
    title="滤波前后对比"
)

# 综合分析图
fig, axes = plotter.plot_comprehensive(
    trace,
    picks=picks,
    spectrum_data=fft_result,
    spec_data=spec_result,
    title="综合分析"
)
```

## 项目结构
```
seisprocessor/
├── __init__.py          # 包入口
├── filter.py            # 波形滤波模块
├── picker.py            # 震相拾取模块
├── spectrum.py          # 频谱分析模块
└── plotter.py           # 绘图模块
setup.py                 # 安装配置
requirements.txt         # 依赖列表
example.py               # 示例代码
README.md                # 说明文档
```

## 技术栈
- **ObsPy**: 地震数据处理核心库
- **Matplotlib**: 数据可视化
- **NumPy**: 数值计算
- **SciPy**: 信号处理（滤波、FFT、谱分析等）

## 许可证
MIT License
