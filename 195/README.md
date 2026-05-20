# 高光谱图像分类 - 3D-CNN

使用3D卷积神经网络（3D-CNN）对高光谱图像进行像素级分类，以Indian Pines数据集为例。

## 功能特性

- **PCA降维预处理**: 减少高光谱数据的维度，保留主要信息
- **数据增强**: 随机翻转、旋转、高斯噪声、亮度调整等
- **3D-CNN模型**: 多种3D卷积神经网络架构
- **评价指标**: 总体精度(OA)、平均精度(AA)、Kappa系数
- **可视化**: 混淆矩阵、训练曲线、类别精度分布图

## 安装依赖

```bash
pip install -r requirements.txt
```

## 项目结构

```
.
├── data_loader.py      # 数据加载和预处理（PCA降维、数据划分）
├── model.py            # 3D-CNN模型定义
├── augmentation.py     # 数据增强模块
├── train.py            # 训练和评估流程
├── visualization.py    # 可视化工具
├── main.py             # 主程序入口
├── test_imports.py     # 环境检测脚本
└── requirements.txt    # 依赖列表
```

## 使用方法

### 1. 环境检测

```bash
python test_imports.py
```

### 2. 运行主程序

```bash
python main.py
```

程序将自动：
- 下载Indian Pines数据集（首次运行）
- 进行PCA降维预处理
- 创建训练/验证/测试集
- 训练3D-CNN模型
- 评估模型性能
- 生成可视化结果

## 数据集

Indian Pines数据集包含:
- 145×145像素
- 200个光谱波段（0.4-2.5 μm）
- 16个地物类别
- 10249个标注像素

## 模型架构

提供3种3D-CNN模型：

1. **CNN3D**: 标准3D-CNN，3层3D卷积
2. **CNN3D_Light**: 轻量级3D-CNN，更快的训练速度
3. **HybridSN**: 混合3D-2D CNN架构

## 配置参数

在`main.py`中可以调整：
- `patch_size`: 图像块大小（默认：5）
- `n_components`: PCA降维后的波段数（默认：30）
- `batch_size`: 批量大小（默认：64）
- `learning_rate`: 学习率（默认：0.001）
- `num_epochs`: 训练轮数（默认：100）
- `use_augmentation`: 是否使用数据增强（默认：True）

## 输出结果

运行完成后，结果保存在`./results/`目录：
- `metrics.npy`: 评估指标
- `results.npy`: 完整结果
- `model_weights.pth`: 训练好的模型权重
- `summary.txt`: 结果摘要
- `figures/`: 可视化图表

## 引用

如果使用本代码，请参考相关文献。
