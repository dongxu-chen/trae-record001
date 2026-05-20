# MS Peak Detector

一个基于PyOpenMS和NumPy的质谱数据峰检测Python科学计算工具库。

## 功能特性

### 1. 基线校正 (Baseline Correction)
- **ASLS (Asymmetric Least Squares)**: 非对称最小二乘法
- **Rolling Min**: 滚动最小值法
- **TopHat**: TopHat滤波
- **SNIP**: 统计非线性迭代峰值算法

### 2. 峰检测 (Peak Detection)
- **CWT (Continuous Wavelet Transform)**: 连续小波变换
- **Local Maxima**: 局部最大值检测
- **PyOpenMS集成**: 支持PyOpenMS算法
- 峰属性计算：m/z、强度、FWHM、峰面积、SNR

### 3. 峰对齐 (Peak Alignment)
- 多谱图峰匹配
- 绝对/PPM容差支持
- 共识峰提取
- 强度矩阵生成

### 4. 同位素检测 (Isotope Detection)
- 同位素模式识别 (C13, N15, O18, S34)
- 单同位素峰检测
- 理论同位素分布计算
- 支持分子式解析

## 安装依赖

```bash
pip install -r requirements.txt
```

依赖包:
- pyopenms >= 2.7.0
- numpy >= 1.21.0
- scipy >= 1.7.0
- matplotlib >= 3.4.0

## 快速开始

### 1. 单个谱图处理

```python
import numpy as np
from ms_peak_detector import MSPeakAnalysisPipeline

pipeline = MSPeakAnalysisPipeline()

# 生成测试谱图
mz, intensity = pipeline.generate_test_spectrum(
    num_peaks=10,
    mz_range=(100, 1000)
)

# 完整分析流程
results = pipeline.process_spectrum(mz, intensity)

print(f"检测到 {len(results['peaks'])} 个峰")
print(f"发现 {len(results['isotope_clusters'])} 个同位素簇")
```

### 2. 基线校正

```python
from ms_peak_detector import BaselineCorrector

corrector = BaselineCorrector(method="asls")
corrected_intensity = corrector.correct(mz, intensity)
baseline = corrector.get_baseline()
```

### 3. 峰检测

```python
from ms_peak_detector import PeakDetector

detector = PeakDetector(method="cwt")
peaks = detector.detect(mz, intensity)

for peak in peaks:
    print(f"m/z: {peak['mz']:.2f}, 强度: {peak['intensity']:.3f}")
```

### 4. 同位素检测

```python
from ms_peak_detector import IsotopeDetector

isotope_detector = IsotopeDetector()
clusters = isotope_detector.detect_isotopes(peaks, charge=1)

# 计算理论同位素分布
theoretical = isotope_detector.calculate_theoretical_isotope_distribution("C6H12O6")
```

### 5. 多谱图峰对齐

```python
from ms_peak_detector import PeakAligner

# peaks_list 是多个谱图的峰列表
aligner = PeakAligner(tolerance=0.05, tolerance_type="absolute")
aligned = aligner.align(peaks_list)

# 获取共识峰（出现在至少3个谱图中）
consensus = aligner.get_consensus_peaks(min_spectra=3)

# 获取强度矩阵
mz_array, intensity_matrix = aligner.get_intensity_matrix()
```

## 运行示例

```bash
python example.py
```

## 模块说明

### core.py - 核心数据处理
- `MSPeakProcessor`: mzML文件加载和谱图数据获取

### baseline_correction.py - 基线校正
- `BaselineCorrector`: 多种基线校正算法

### peak_detection.py - 峰检测
- `PeakDetector`: 峰检测与属性计算

### peak_alignment.py - 峰对齐
- `PeakAligner`: 多谱图峰对齐
- `SpectrumAligner`: 完整谱图对齐

### isotope_detection.py - 同位素检测
- `IsotopeDetector`: 同位素模式识别与理论计算

### processor.py - 完整分析流程
- `MSPeakAnalysisPipeline`: 整合所有模块的完整处理流程

## 可视化功能

库中内置了matplotlib可视化功能：

```python
# 绘制谱图
pipeline.plot_spectrum(mz, intensity, corrected_intensity, peaks)

# 绘制同位素簇
pipeline.plot_isotope_clusters(mz, intensity, clusters)

# 绘制对齐峰热图
pipeline.plot_aligned_peaks_heatmap()
```

## 数据格式

### 峰数据结构
```python
{
    "mz": float,           # 质荷比
    "intensity": float,    # 强度
    "index": int,          # 在数组中的索引
    "left_index": int,     # 左边界索引
    "right_index": int,    # 右边界索引
    "fwhm": float,         # 半高峰宽
    "area": float,         # 峰面积
    "snr": float           # 信噪比
}
```

### 同位素簇数据结构
```python
{
    "monoisotopic_mz": float,
    "monoisotopic_intensity": float,
    "charge": int,
    "peaks": List[Dict],
    "indices": List[int],
    "isotope_ratios": Dict[str, float],
    "size": int
}
```

## 许可证

MIT License
