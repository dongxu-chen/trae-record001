# 运动模糊图像复原系统 (Motion Deblur System)

一个基于 Python 的运动模糊图像复原工具，支持维纳滤波、Richardson-Lucy 反卷积和盲反卷积算法。

## 功能特性

- **运动模糊核生成**：根据运动方向和长度生成精确的模糊核
- **维纳滤波复原**：频域去模糊，速度快，效果好
- **Richardson-Lucy 反卷积**：迭代式反卷积，适合泊松噪声
- **盲反卷积**：无需已知模糊核，自动估计核参数
- **参数自动估计**：基于频谱分析自动估计运动模糊的方向和长度
- **振铃效应抑制**：边缘渐晕 (Edge Taper) 技术减少振铃伪影
- **批量处理**：支持对整个目录的图像进行批量去模糊
- **可视化**：Matplotlib 可视化对比结果

## 依赖库

```
numpy
opencv-python
scipy
matplotlib
```

安装依赖：
```bash
pip install numpy opencv-python scipy matplotlib
```

## 快速开始

### 1. 基本使用

```python
from motion_deblur import MotionDeblur
import cv2

deblur = MotionDeblur()

# 读取模糊图像
blurred_image = cv2.imread('blurred.png')

# 方法1: 已知参数的维纳滤波
kernel = deblur.generate_motion_kernel(length=25, angle=30)
deblurred = deblur.wiener_deblur(blurred_image, kernel, K=0.01)

# 方法2: Richardson-Lucy 反卷积
deblurred_rl = deblur.richardson_lucy_deblur(blurred_image, kernel, iterations=50)

# 方法3: 盲反卷积 (无需已知核)
deblurred_blind, estimated_kernel = deblur.blind_deconvolution(
    blurred_image, 
    iterations=20,
    kernel_size=15
)

# 保存结果
cv2.imwrite('deblurred.png', deblurred)
```

### 2. 参数自动估计

```python
# 自动估计运动模糊参数
est_length, est_angle = deblur.estimate_motion_parameters(blurred_image)
print(f"估计的模糊长度: {est_length}")
print(f"估计的模糊角度: {est_angle}")

# 使用估计的参数进行去模糊
kernel = deblur.generate_motion_kernel(int(est_length), est_angle)
deblurred = deblur.wiener_deblur(blurred_image, kernel)
```

### 3. 振铃效应抑制

```python
# 使用边缘渐晕抑制振铃效应
tapered = deblur.suppress_ringing(blurred_image, kernel, method='edgetaper')
deblurred = deblur.wiener_deblur(tapered, kernel)
```

### 4. 批量处理

```python
# 批量处理目录中的所有图像
processed_files = deblur.batch_process(
    input_dir='input_images',
    output_dir='output_images',
    method='wiener',        # 'wiener', 'rl', 'blind'
    auto_params=True,       # 自动估计参数
    suppress_ringing=True   # 启用振铃抑制
)

print(f"处理了 {len(processed_files)} 张图像")
```

### 5. 可视化结果

```python
# 可视化对比
deblur.visualize_results(
    original=original_image,
    blurred=blurred_image,
    deblurred=deblurred_image,
    kernel=kernel,
    save_path='comparison.png'
)
```

## 运行示例

运行完整的示例：
```bash
python example_usage.py
```

直接运行主程序测试：
```bash
python motion_deblur.py
```

## API 说明

### MotionDeblur 类

#### `generate_motion_kernel(length, angle, size=None)`
生成运动模糊核
- `length`: 运动长度（像素）
- `angle`: 运动角度（度）
- `size`: 核大小，自动计算

#### `apply_motion_blur(image, kernel)`
对图像应用运动模糊

#### `wiener_deblur(image, kernel, K=0.01)`
维纳滤波去模糊
- `K`: 噪声功率与信号功率比，较小值恢复更多细节但可能引入振铃

#### `richardson_lucy_deblur(image, kernel, iterations=50)`
Richardson-Lucy 反卷积
- `iterations`: 迭代次数，更多迭代更清晰但更慢

#### `blind_deconvolution(image, init_kernel=None, iterations=20, kernel_size=15)`
盲反卷积，同时估计图像和模糊核

#### `estimate_motion_parameters(image)`
自动估计运动模糊参数，返回 (length, angle)

#### `suppress_ringing(image, kernel, method='edgetaper')`
振铃效应抑制
- `method`: 'edgetaper' 或 'wiener'

#### `batch_process(input_dir, output_dir, method='wiener', auto_params=True, ...)`
批量处理图像

#### `visualize_results(original, blurred, deblurred, kernel=None, save_path=None)`
可视化结果对比

## 算法原理

### 维纳滤波
维纳滤波在频域中最小化均方误差：
```
G(u,v) = H*(u,v) / (|H(u,v)|² + K)
```
其中 H 是模糊核的傅里叶变换，K 是正则化参数。

### Richardson-Lucy 反卷积
基于贝叶斯估计的迭代方法，假设噪声服从泊松分布：
```
f_{k+1} = f_k * (g / (f_k * h)) * h*
```

### 参数估计
使用频谱分析检测运动模糊：
1. 对图像进行 FFT 变换
2. 分析频谱中与运动方向垂直的条纹
3. 通过条纹间距估计模糊长度

## 注意事项

1. **参数选择**：维纳滤波的 K 值影响恢复质量，建议在 0.001-0.05 之间调整
2. **计算速度**：Richardson-Lucy 和盲反卷积是迭代算法，计算较慢
3. **真实图像**：对于真实拍摄的模糊图像，参数估计可能不够精确，建议手动微调
4. **振铃效应**：强边缘图像容易产生振铃，建议启用振铃抑制

## 示例输出

运行示例后会生成以下图像：
- `original.png` - 原始测试图像
- `blurred.png` - 运动模糊后的图像
- `deblurred_wiener.png` - 维纳滤波恢复结果
- `deblurred_rl.png` - Richardson-Lucy 恢复结果
- `blind_deblurred.png` - 盲反卷积结果
- `ringing_*.png` - 振铃效应对比

## 许可证

MIT License
