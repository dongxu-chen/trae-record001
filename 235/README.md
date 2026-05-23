# ESPCN 超分辨率重建模型

基于 PyTorch 实现的 ESPCN (Efficient Sub-Pixel Convolutional Neural Network) 轻量级超分辨率模型，支持 2倍 和 4倍 图像放大。

## 项目特性

- ✅ 轻量级 ESPCN 模型架构
- ✅ 支持 2x / 4x 图像放大
- ✅ 单张图像和批量处理
- ✅ PSNR / SSIM 评估指标
- ✅ DIV2K 数据集训练支持
- ✅ ONNX 模型导出
- ✅ C++ 推理接口 (ONNX Runtime)
- ✅ 预训练权重支持

## 项目结构

```
.
├── models/              # 模型定义
│   ├── __init__.py
│   └── espcn.py        # ESPCN 模型架构
├── data/               # 数据加载模块
│   ├── __init__.py
│   └── dataset.py     # DIV2K 数据集
├── utils/              # 工具函数
│   ├── __init__.py
│   └── metrics.py     # PSNR/SSIM 指标
├── cpp/                # C++ 推理代码
│   ├── CMakeLists.txt
│   ├── include/
│   │   └── ESPCN.h
│   └── src/
│       ├── ESPCN.cpp
│       └── main.cpp
├── config.yaml         # 配置文件
├── requirements.txt    # Python 依赖
├── train.py           # 训练脚本
├── inference.py       # Python 推理脚本
├── export_onnx.py     # ONNX 导出脚本
└── download_data.py   # 数据集下载脚本
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 下载数据集

```bash
# 下载训练集和验证集
python download_data.py --download_all

# 或分别下载
python download_data.py --download_train
python download_data.py --download_valid
```

### 3. 训练模型

```bash
# 使用默认配置训练 4x 模型
python train.py --config config.yaml

# 训练 2x 模型
python train.py --config config.yaml --scale 2

# 从断点继续训练
python train.py --config config.yaml --resume checkpoints/espcn_x4_latest.pth
```

### 4. 模型推理

```bash
# 单张图像推理
python inference.py \
    --input test_image.png \
    --output results \
    --checkpoint checkpoints/espcn_x4_best.pth \
    --scale 4

# 批量处理
python inference.py \
    --input input_images/ \
    --output results/ \
    --checkpoint checkpoints/espcn_x4_best.pth \
    --scale 4

# 带参考图评估（输出 PSNR/SSIM）
python inference.py \
    --input lr_images/ \
    --output results/ \
    --checkpoint checkpoints/espcn_x4_best.pth \
    --scale 4 \
    --reference hr_images/
```

### 5. 导出 ONNX 模型

```bash
python export_onnx.py \
    --checkpoint checkpoints/espcn_x4_best.pth \
    --output checkpoints \
    --scale 4 \
    --simplify
```

## C++ 推理

### 编译要求

- CMake >= 3.15
- OpenCV >= 4.0
- ONNX Runtime >= 1.15

### 编译步骤

```bash
cd cpp
mkdir build && cd build
cmake .. -DONNXRUNTIME_DIR=/path/to/onnxruntime
make -j4
```

### C++ 推理使用

```bash
# 单张图像
./espcn_infer \
    --model ../checkpoints/espcn_x4_best.onnx \
    --input test_image.png \
    --output results \
    --scale 4

# 批量处理
./espcn_infer \
    --model ../checkpoints/espcn_x4_best.onnx \
    --input input_dir/ \
    --output results/ \
    --scale 4

# GPU 加速
./espcn_infer --model model.onnx --input image.png --gpu

# 性能基准测试
./espcn_infer --model model.onnx --benchmark
```

## 模型架构

ESPCN 使用亚像素卷积 (Sub-Pixel Convolution) 实现高效上采样：

```
Input (H, W, 3)
    ↓
Conv2d(5x5, 64) + Tanh
    ↓
Conv2d(3x3, 64) + Tanh
    ↓
Conv2d(3x3, 64) + Tanh
    ↓
Conv2d(3x3, 3×r²)  # r = scale factor
    ↓
PixelShuffle(r)
    ↓
Output (H×r, W×r, 3)
```

### 模型参数量

- Scale x2: ~85K 参数
- Scale x4: ~103K 参数

## 性能指标

在 DIV2K 验证集上的典型表现：

| 模型 | 缩放 | PSNR (dB) | SSIM |
|------|------|-----------|------|
| Bicubic | x4 | 28.5 | 0.81 |
| ESPCN | x4 | 30.2 | 0.86 |

## 配置说明

编辑 `config.yaml` 调整训练参数：

```yaml
model:
  scale_factor: 4
  num_channels: 3
  num_features: 64

training:
  batch_size: 16
  num_epochs: 100
  learning_rate: 1e-4
  lr_decay_step: 20
  lr_decay_gamma: 0.5
  weight_decay: 1e-4

data:
  div2k_train_dir: ./data/DIV2K/DIV2K_train_HR
  div2k_valid_dir: ./data/DIV2K/DIV2K_valid_HR
  patch_size: 96
  num_workers: 4
```

## 预训练权重

你可以通过以下方式获取预训练权重：

1. 使用本项目训练脚本自行训练
2. 或下载官方预训练权重放置于 `checkpoints/` 目录

## 引用

```bibtex
@article{shi2016real,
  title={Real-time single image and video super-resolution using an efficient sub-pixel convolutional neural network},
  author={Shi, Wenzhe and Caballero, Jose and Husz{\'a}r, Ferenc and Totz, Johannes and Aitken, Andrew P and Bishop, Rob and Rueckert, Daniel and Wang, Zehan},
  journal={CVPR},
  year={2016}
}

@inproceedings{wang2021realesrgan,
  title={Real-ESRGAN: Training Real-World Blind Super-Resolution with Pure Synthetic Data},
  author={Wang, Xintao and Xie, Liangbin and Dong, Chao and Shan, Ying},
  booktitle={ICCVW},
  year={2021}
}

@inproceedings{hinton2015distilling,
  title={Distilling the knowledge in a neural network},
  author={Hinton, Geoffrey and Vinyals, Oriol and Dean, Jeff},
  booktitle={NeurIPS Workshop},
  year={2015}
}
```

## 许可证

MIT License
