# 3D人脸重建系统 (3D Face Reconstruction)

基于PyTorch实现的单张图像3D人脸重建算法，使用3DMM参数回归方法。

## 功能特性

- **3DMM人脸建模**: 使用Basel Face Model (BFM) 进行人脸形状和纹理建模
- **表情参数估计**: 支持29维表情参数回归
- **形状参数估计**: 支持199维形状参数回归
- **姿态估计**: 6维姿态参数（3维旋转 + 3维平移）
- **光照估计**: 27维球谐光照参数（9个系数 × 3颜色通道）
- **人脸检测**: OpenCV Haar级联检测器
- **关键点检测**: 68个人脸关键点
- **3D渲染**: 支持深度图、纹理渲染
- **可视化**: Matplotlib 3D可视化

## 项目结构

```
.
├── config.py              # 配置文件
├── bfm_model.py           # BFM 3DMM模型定义
├── face_detection.py      # 人脸检测和关键点检测
├── pose_estimation.py     # 姿态和光照估计
├── param_regression.py    # 参数回归网络
├── renderer.py            # 3D渲染和可视化
├── face_recon.py          # 主程序入口
├── requirements.txt       # 依赖包
├── data/                  # 输入数据目录
├── output/                # 输出结果目录
├── models/                # 模型文件目录
└── checkpoints/           # 训练检查点目录
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 快速开始

```bash
python face_recon.py
```

### 在代码中使用

```python
from face_recon import FaceReconstructor

reconstructor = FaceReconstructor(device='cuda')  # 或 'cpu'
results = reconstructor.reconstruct('path/to/your/image.jpg')

# 访问结果
vertices = results['vertices']       # 3D顶点坐标
texture = results['texture']         # 纹理颜色
params = results['params']           # 所有参数
rendered_image = results['rendered_image']
depth_map = results['depth_map']
```

## 技术细节

### 3DMM模型

- **形状模型**: `S = S_mean + S_id * α + S_exp * β`
  - `S_mean`: 平均人脸形状
  - `S_id`: 身份基向量矩阵 (35709×3 × 199)
  - `S_exp`: 表情基向量矩阵 (35709×3 × 29)
  - `α`: 身份参数 (199维)
  - `β`: 表情参数 (29维)

- **纹理模型**: `T = T_mean + T_tex * γ`
  - `T_mean`: 平均人脸纹理
  - `T_tex`: 纹理基向量矩阵 (35709×3 × 199)
  - `γ`: 纹理参数 (199维)

### 姿态参数

- 3个欧拉角 (pitch, yaw, roll) 用于旋转
- 3个平移参数 (tx, ty, tz) 用于位移

### 光照模型

- 球谐函数 (Spherical Harmonics) 9阶 × 3颜色通道 = 27维参数

### 网络架构

- Backbone: ResNet-50 (可选择ResNet-18/34/50, MobileNetV2)
- 输出层: 全连接层回归所有参数
- 总参数维度: 199+29+199+6+27 = 460维

## 输出文件

运行后会在 `output/` 目录生成以下文件：

- `original_image.jpg` - 原始图像
- `aligned_face.jpg` - 对齐后的人脸
- `face_detection.jpg` - 带检测框的图像
- `landmarks.jpg` - 带关键点的图像
- `rendered_face.jpg` - 渲染的3D人脸
- `depth_map.jpg` - 深度图
- `face_mesh.obj` - OBJ格式的3D模型
- `face_mesh.ply` - PLY格式的3D模型
- `3d_face_plot.png` - 3D可视化图
- `results_comparison.png` - 结果对比图
- `parameters.png` - 参数分布图
- `params.npz` - 所有参数的numpy文件

## 参考资料

- Basel Face Model (BFM): https://faces.dmi.unibas.ch/bfm/
- 3DDFA: https://github.com/cleardusk/3DDFA
- 3DDFA_V2: https://github.com/cleardusk/3DDFA_V2
