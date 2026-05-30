# 深度学习图像修复工具 (Deep Learning Image Inpainting)

基于PyTorch实现的图像修复算法，使用Partial Convolution和Edge-Connect等深度学习模型，可用于修复水印、划痕、文字遮挡等图像缺损区域。

## 功能特性

- 🎨 **多种深度学习模型**: Partial Conv UNet、Edge-Connect
- 🎭 **不规则掩膜支持**: 支持多种掩膜类型（笔触、矩形框、水印、文字、划痕）
- 📦 **批量处理**: 支持批量图像修复
- 📊 **质量评估**: PSNR、SSIM、LPIPS、MAE、MSE、FID等指标
- 🔧 **灵活配置**: 可自定义图像尺寸、模型参数等
- 🖼️ **可视化**: 自动生成修复结果对比图

## 项目结构

```
image_inpainting/
├── src/
│   ├── __init__.py          # 包初始化
│   ├── models.py            # 深度学习模型 (PartialConv, Edge-Connect)
│   ├── mask_generator.py    # 不规则掩膜生成器
│   ├── inpainter.py         # 图像修复主类
│   ├── metrics.py           # 质量评估指标
│   └── utils.py             # 工具函数
├── examples/
│   ├── __init__.py
│   └── example_usage.py     # 使用示例
├── main.py                  # 命令行主程序
├── requirements.txt         # 依赖包
└── README.md                # 说明文档
```

## 安装依赖

```bash
pip install -r requirements.txt
```

### 依赖包说明

- **torch**: PyTorch深度学习框架
- **torchvision**: PyTorch视觉工具库
- **opencv-python**: 图像处理
- **numpy**: 数值计算
- **matplotlib**: 可视化
- **Pillow**: 图像处理
- **scikit-image**: 图像质量评估
- **tqdm**: 进度条
- **lpips**: LPIPS感知相似度指标

## 快速开始

### 1. 命令行使用

#### 单张图像修复
```bash
python main.py --mode single --input path/to/image.jpg --output output_dir \
    --model partialconv --mask_type watermark --evaluate --save_viz
```

#### 批量图像修复
```bash
python main.py --mode batch --input path/to/images/ --output output_dir \
    --model partialconv --mask_type scratch --evaluate --save_viz
```

#### 运行演示
```bash
python main.py --mode demo --output demo_output
```

#### 模型对比
```bash
python main.py --mode compare --input path/to/image.jpg --output compare_dir \
    --mask_type watermark
```

### 2. Python API 使用

#### 基本使用
```python
from src.inpainter import ImageInpainter

# 初始化修复器
inpainter = ImageInpainter(
    model_name='partialconv',  # 或 'edgeconnect'
    image_size=(256, 256)
)

# 加载预训练权重 (可选)
# inpainter.load_checkpoint('path/to/checkpoint.pth')

# 修复图像 (自动生成掩膜)
image, mask, result = inpainter.inpaint_watermark(
    'path/to/image.jpg',
    text='WATERMARK',
    font_scale=1.5,
    rotation=15
)

# 评估修复质量
metrics = inpainter.evaluate_inpainting(
    image, result, mask, only_masked_region=True
)
inpainter.print_evaluation(metrics)
```

#### 不同掩膜类型
```python
# 水印去除
image, mask, result = inpainter.inpaint_watermark('image.jpg')

# 划痕修复
image, mask, result = inpainter.inpaint_scratch('image.jpg', num_scratches=5)

# 文字遮挡修复
image, mask, result = inpainter.inpaint_text('image.jpg', text='SAMPLE')

# 自定义掩膜类型
image, mask, result = inpainter.inpaint_with_auto_mask(
    'image.jpg', mask_type='irregular'
)
```

#### 批量处理
```python
results = inpainter.batch_inpaint(
    input_dir='path/to/images/',
    output_dir='output/',
    mask_type='watermark',
    save_visualization=True,
    evaluate=True
)

print(f"处理了 {results['num_processed']} 张图像")
```

### 3. 运行示例脚本

```bash
python examples/example_usage.py
```

## 支持的掩膜类型

| 掩膜类型 | 说明 | 适用场景 |
|---------|------|---------|
| `stroke` | 随机笔触形状 | 通用不规则缺损 |
| `bbox` | 矩形框 | 方块遮挡 |
| `watermark` | 旋转文字水印 | 水印去除 |
| `text` | 水平文字 | 文字遮挡 |
| `scratch` | 曲线划痕 | 照片划痕修复 |
| `irregular` | 不规则多边形 | 复杂形状缺损 |
| `random` | 随机选择以上类型 | 数据增强 |

## 质量评估指标

| 指标 | 说明 | 最优值 |
|-----|------|-------|
| **PSNR** | 峰值信噪比 (dB) | 越高越好 |
| **SSIM** | 结构相似性 | 1.0 |
| **LPIPS** | 感知相似度 | 0.0 |
| **MAE** | 平均绝对误差 | 0.0 |
| **MSE** | 均方误差 | 0.0 |
| **FID** | Fréchet Inception距离 | 越低越好 |

## 深度学习模型

### Partial Convolution UNet
- 基于部分卷积的UNet架构
- 编码器-解码器结构带跳跃连接
- 适用于各种不规则掩膜的图像修复

### Edge-Connect
- 两阶段架构：边缘生成 + 图像修复
- 首先预测缺损区域的边缘
- 然后基于边缘信息完成图像修复
- 在结构保持方面表现更好

## 预训练模型

当前实现包含完整的网络结构定义。要使用预训练权重：

1. 下载或训练模型权重
2. 使用 `load_checkpoint()` 方法加载：

```python
inpainter.load_checkpoint('path/to/weights.pth')
```

## API 参考

### ImageInpainter 类

```python
class ImageInpainter:
    def __init__(self, model_name='partialconv', device=None, image_size=(256, 256))
    
    def inpaint(self, image, mask, return_numpy=True)
    def inpaint_with_auto_mask(self, image_path, mask_type='random', **kwargs)
    def inpaint_watermark(self, image_path, text=None, font_scale=None, ...)
    def inpaint_scratch(self, image_path, num_scratches=None)
    def inpaint_text(self, image_path, text=None)
    def batch_inpaint(self, input_dir, output_dir, ...)
    def evaluate_inpainting(self, original, inpainted, mask=None, ...)
    def load_checkpoint(self, checkpoint_path)
    def print_evaluation(self, results)
```

### MaskGenerator 类

```python
class MaskGenerator:
    def __init__(self, height=256, width=256)
    
    def generate_mask(self, mask_type='random', **kwargs)
    def stroke_mask(self, **kwargs)
    def bbox_mask(self, **kwargs)
    def watermark_mask(self, **kwargs)
    def text_mask(self, **kwargs)
    def scratch_mask(self, **kwargs)
    def irregular_mask(self, **kwargs)
    def load_mask_from_file(self, mask_path, threshold=127, invert=False)
    def apply_mask_to_image(self, image, mask, fill_value=255)
```

### QualityEvaluator 类

```python
class QualityEvaluator:
    def __init__(self, device='cpu', use_lpips=True)
    
    def calculate_psnr(self, img1, img2)
    def calculate_ssim(self, img1, img2)
    def calculate_lpips(self, img1, img2)
    def calculate_mae(self, img1, img2)
    def calculate_mse(self, img1, img2)
    def evaluate_all(self, original, inpainted, mask=None, ...)
    def evaluate_batch(self, originals, inpainteds, ...)
    def print_results(self, results)
```

## 常见问题

### Q: 如何使用自己的掩膜文件？
A: 使用 `mask_generator.load_mask_from_file()` 加载自定义掩膜：
```python
mask = inpainter.mask_generator.load_mask_from_file('path/to/mask.png')
result = inpainter.inpaint(image, mask)
```

### Q: 如何提高修复质量？
A: 
1. 使用更大的图像尺寸 (如512x512)
2. 加载在相关数据集上预训练的权重
3. 根据缺损类型选择合适的模型
4. 对于大区域缺损，可以尝试多次修复

### Q: 支持哪些图像格式？
A: 支持 JPG、PNG、BMP 等常见格式，由 OpenCV 后端自动处理。

## 许可证

MIT License

## 参考文献

- **Partial Convolution**: [Image Inpainting for Irregular Holes Using Partial Convolutions](https://arxiv.org/abs/1804.07723)
- **Edge-Connect**: [EdgeConnect: Generative Image Inpainting with Adversarial Edge Learning](https://arxiv.org/abs/1901.00212)
- **LPIPS**: [The Unreasonable Effectiveness of Deep Features as a Perceptual Metric](https://arxiv.org/abs/1801.03924)
