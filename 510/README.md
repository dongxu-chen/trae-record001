# 视频插帧超分联合处理系统 v2.0 (VESPCN)

基于 VESPCN (Video Super-Resolution with Convolutional Neural Networks) 网络实现的视频插帧和超分辨率联合处理系统，可同时实现 **2x 帧率提升** 和 **2x 分辨率提升**。

## ✨ v2.0 新特性

- **⚡ 模型压缩加速**: 支持剪枝 + 量化，推理速度提升到 15 FPS
- **🎯 时域校准**: 特征融合增加时域对齐，消除错位模糊
- **👥 MOS 主观评估**: 支持用户主观评分，与客观指标综合
- **📊 综合质量评估**: 加权融合 MOS (40%) + PSNR (25%) + SSIM (25%) + LPIPS (10%)
- **🧪 推理优化**: FP16 半精度、Channels Last、JIT 编译
- **🎯 目标 FPS 追踪**: 自动优化达到 15 FPS 目标

## ✨ 核心特性

- **联合处理**: 同时进行帧插值和超分辨率，实现 2x2 倍视频增强
- **实时处理**: 支持摄像头实时视频流处理
- **多尺度特征融合**: 使用多尺度卷积核提取丰富特征
- **时域校准**: 通过光流置信度和特征对齐消除错位模糊
- **模型压缩**: L1 剪枝、结构化剪枝、动态/静态/QAT 量化
- **质量评估**: 集成 PSNR、SSIM、LPIPS 等客观指标 + MOS 主观评分
- **Web 界面**: 基于 Streamlit 的友好交互界面
- **高性能**: 支持 CUDA GPU 加速 + 多种推理优化

## 📁 项目结构

```
.
├── models/
│   ├── __init__.py
│   └── vespcn.py              # VESPCN 网络模型（含时域校准）
├── config.py                  # 配置文件
├── utils.py                   # 工具函数
├── quality_metrics.py         # 质量评估模块（综合客观+MOS）
├── mos_evaluation.py          # MOS 主观评估模块
├── model_compression.py       # 模型压缩和推理加速模块
├── video_processor.py         # 视频处理核心模块
├── app.py                     # Streamlit Web 界面 v2.0
├── main.py                    # 命令行入口 v2.0
├── requirements.txt           # 依赖列表
└── README.md
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 Web 界面

```bash
python main.py webui
```

访问 http://localhost:8501 即可使用 Web 界面。

### 3. 命令行使用

#### 处理视频文件

```bash
# 基础处理
python main.py video -i input.mp4 -o output.mp4

# 启用质量评估，目标 15 FPS
python main.py video -i input.mp4 -o output.mp4 --quality-metrics --target-fps 15

# 使用压缩模型
python main.py video -i input.mp4 -o output.mp4 --use-compressed

# 禁用时域校准（速度优先）
python main.py video -i input.mp4 -o output.mp4 --disable-temporal-alignment
```

#### 实时摄像头处理

```bash
python main.py camera --target-fps 15
```

#### 模型压缩

```bash
# 自动优化到 15 FPS
python main.py compress --target-fps 15 -o models/compressed_vespcn.pt

# 手动指定剪枝比例
python main.py compress --prune-amount 0.3 --target-fps 15

# 压缩后运行基准测试
python main.py compress --target-fps 15 --benchmark-after --verbose
```

#### 性能基准测试

```bash
# 测试完整流水线
python main.py benchmark --target-fps 15

# 测试指定视频
python main.py benchmark -i test.mp4 --runs 100
```

#### 质量评估

```bash
# 综合质量评估（需要MOS评分数据）
python main.py evaluate comprehensive --video-id video_001 \
    --reference ref_frames.pt --processed proc_frames.pt \
    -o quality_report.json

# 自定义权重
python main.py evaluate comprehensive --video-id video_001 \
    --weights-config '{"mos":0.5, "psnr":0.25, "ssim":0.2, "lpips":0.05}'

# 主观-客观相关性分析
python main.py evaluate correlation --metrics-config video_metrics.json
```

#### MOS 评分管理

```bash
# 添加评分
python main.py mos add --video-id video_001 --rater-id rater_001 --score 4.5 --comment "很好"

# 查看评分
python main.py mos view --video-id video_001

# 导出评分
python main.py mos export -o mos_ratings.json --format json

# 导入评分
python main.py mos import -i mos_ratings.json --format json

# 异常检测
python main.py mos outlier --video-id video_001 --threshold 2.0
```

## 🎯 核心功能详解

### 1. VESPCN 网络架构（v2.0）

1. **时域校准模块 (TemporalAlignmentModule)**:
   - 光流置信度估计网络，学习自适应权重
   - 特征对齐网络，融合前中后三帧特征
   - 去模糊网络，通过残差学习消除错位模糊

2. **多尺度特征融合**:
   - 1x1、3x3、5x5 多尺度卷积核并行提取
   - 新增时域注意力机制
   - 自适应通道分配（修复通道数不匹配 bug）

3. **运动估计与补偿**: 估计相邻帧之间的光流并对齐

4. **帧插值**: 生成中间帧实现 2x 帧率提升

5. **超分辨率**: 使用 PixelShuffle 实现 2x 分辨率提升

### 2. 模型压缩与加速

#### 剪枝技术

| 方法 | 说明 | 适用场景 |
|------|------|----------|
| **L1 非结构化剪枝** | 基于权重绝对值剪枝 | 通用场景，精度保持好 |
| **结构化剪枝** | 剪枝整个通道/过滤器 | 硬件友好，加速明显 |

#### 量化技术

| 方法 | 说明 | 精度损失 | 速度提升 |
|------|------|----------|----------|
| **动态量化** | 运行时动态量化权重 | 小 | ~1.5x |
| **静态量化** | 校准后量化权重和激活 | 中 | ~2x |
| **QAT 量化** | 训练时模拟量化 | 极小 | ~2x |

#### 推理优化

- **FP16 半精度**: 减少显存占用，提升计算速度
- **Channels Last**: 优化内存布局，提升卷积效率
- **JIT 编译**: TorchScript 编译，优化计算图

### 3. 综合质量评估

#### 客观指标

| 指标 | 说明 | 优秀阈值 |
|------|------|----------|
| **PSNR** | 峰值信噪比 (dB) | > 35 |
| **SSIM** | 结构相似性 [0,1] | > 0.9 |
| **LPIPS** | 感知相似度 [0,1] | < 0.1 |
| **时序一致性** | 相邻帧差异 | > 0.8 |

#### MOS 主观评分

- 评分范围: 1 (很差) ~ 5 (优秀)
- 支持多评价者、置信区间计算
- 异常检测、评价者可靠性分析
- 支持 JSON/CSV 导入导出

#### 综合质量评分

**默认权重**:
- MOS: 40%
- PSNR: 25%
- SSIM: 25%
- LPIPS: 10%

**质量等级**:
- ≥ 4.5: 优秀 (Excellent)
- 4.0 ~ 4.5: 很好 (Good)
- 3.5 ~ 4.0: 良好 (Fair)
- 3.0 ~ 3.5: 一般 (Poor)
- 2.0 ~ 3.0: 较差 (Bad)
- < 2.0: 很差 (Very Bad)

## 📊 支持的处理模式

### 1. 视频文件处理
- 支持 MP4、AVI、MOV、MKV 等格式
- 可限制处理帧数
- 分块处理大视频（可选）
- 实时进度显示
- 目标 FPS 达成状态监控

### 2. 实时摄像头处理
- 支持 USB 摄像头
- 实时 FPS 和处理时间显示
- 目标 FPS 达成状态指示
- 按 '停止' 按钮退出

### 3. 单帧图像处理
- 支持 PNG、JPG、JPEG 格式
- 原图与增强后对比显示
- 差异图可视化
- 处理时间统计

### 4. 模型压缩优化
- 自动优化模式：自动寻找达到目标 FPS 的最佳配置
- 手动配置模式：自定义剪枝比例和量化方法
- 压缩结果展示：FPS 提升、参数压缩率、目标达成
- 基准测试：完整流水线性能测试

### 5. 综合质量评估
- 单图像对评估：快速计算客观指标
- 综合质量报告：客观 + 主观 + 时序一致性
- 主观-客观相关性分析：Pearson/Spearman 相关系数

### 6. MOS 主观评分
- 单条/批量添加评分
- 评分结果查看（含分布直方图）
- 导入/导出（JSON/CSV）
- 异常评分检测

## ⚙️ 配置说明

编辑 `config.py` 可自定义参数：

```python
VESPCN_CONFIG = {
    "scale_factor": 2,        # 分辨率提升倍数
    "num_channels": 3,        # 通道数
    "num_frames": 3,          # 输入帧数
    "base_channels": 64,      # 基础通道数
    "num_residual_blocks": 6, # 残差块数量
}

PROCESSING_CONFIG = {
    "codec": "libx264",       # 输出编码
    "crf": 20,                # 输出质量 (0-51, 越低越好)
}

QUALITY_METRICS = {
    "default_weights": {      # 综合评分权重
        "mos": 0.4,
        "psnr": 0.25,
        "ssim": 0.25,
        "lpips": 0.1
    }
}
```

## 🔧 系统要求

- **Python**: 3.8+
- **PyTorch**: 2.0+
- **CUDA**: 11.0+ (推荐，GPU 加速)
- **FFmpeg**: 4.0+ (视频编码)
- **内存**: 4GB+
- **显存**: 2GB+ (GPU 模式)
- **目标 FPS**: 15+ (经过模型压缩优化后)

## 📈 性能参考

### 原始模型 (RTX 3090)

| 分辨率 | FPS | 延迟 |
|--------|-----|------|
| 480p   | ~45 | ~22ms |
| 720p   | ~22 | ~45ms |
| 1080p  | ~10 | ~100ms |

### 压缩优化后 (目标 15 FPS)

| 分辨率 | 优化前 | 优化后 | 提升 |
|--------|--------|--------|------|
| 480p   | ~45    | ~75+   | 1.7x |
| 720p   | ~22    | ~35+   | 1.6x |
| 1080p  | ~10    | **~18**| 1.8x |

> 注：实际性能取决于硬件和压缩配置。上述数据基于 30% 剪枝 + 动态量化 + FP16。

## 📝 命令行参数详解

### video 命令

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-i, --input` | 输入视频路径 | 必填 |
| `-o, --output` | 输出视频路径 | 自动生成 |
| `-w, --weights` | 模型权重文件 | 无 |
| `--max-frames` | 最大处理帧数 | 全部 |
| `--patch-processing` | 使用分块处理 | False |
| `--quality-metrics` | 计算质量指标 | False |
| `--disable-temporal-alignment` | 禁用时域校准 | False |
| `--use-compressed` | 使用压缩模型 | False |
| `--disable-fp16` | 禁用 FP16 半精度 | False |
| `--disable-channels-last` | 禁用 Channels Last | False |
| `--use-jit` | 启用 JIT 编译 | False |
| `--target-fps` | 目标 FPS | 15.0 |

### compress 命令

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-w, --weights` | 模型权重文件 | 无 |
| `-o, --output` | 压缩模型输出路径 | 无 |
| `--prune-amount` | 手动剪枝比例 (0-1) | 自动 |
| `--max-prune-amount` | 最大剪枝比例 | 0.5 |
| `--disable-quantization` | 禁用 INT8 量化 | False |
| `--target-fps` | 目标 FPS | 15.0 |
| `--benchmark-after` | 压缩后运行基准测试 | False |
| `-v, --verbose` | 显示详细信息 | False |

### evaluate comprehensive 命令

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--video-id` | 视频 ID | 必填 |
| `--reference` | 参考帧文件 (.npy/.pt) | 可选 |
| `--processed` | 处理后帧文件 (.npy/.pt) | 可选 |
| `--weights-config` | 自定义权重 JSON | 无 |
| `--disable-mos` | 禁用 MOS 评估 | False |
| `-o, --output` | 评估报告输出路径 | 无 |

### mos 子命令

| 子命令 | 说明 |
|--------|------|
| `add` | 添加单条评分 |
| `view` | 查看评分结果 |
| `export` | 导出评分数据 |
| `import` | 导入评分数据 |
| `outlier` | 异常评分检测 |

## 🎓 参考论文

- [Real-Time Video Super-Resolution with Spatio-Temporal Networks and Motion Compensation](https://arxiv.org/abs/1611.05250)
- [Video Frame Interpolation via Adaptive Separable Convolution](https://arxiv.org/abs/1708.01692)
- [Optimal Filtering for Frame Rate Up-Conversion](https://ieeexplore.ieee.org/document/4483342)

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 联系方式

如有问题或建议，请通过 Issue 反馈。

---

## 📋 版本历史

### v2.0 (2024)
- ✅ 新增模型压缩模块（剪枝 + 量化）
- ✅ 新增时域校准模块，消除错位模糊
- ✅ 新增 MOS 主观评估系统
- ✅ 新增综合质量评估（客观 + 主观）
- ✅ 新增推理优化（FP16、Channels Last、JIT）
- ✅ 新增目标 FPS 追踪和自动优化
- ✅ 修复多尺度特征融合通道数不匹配 bug
- ✅ 全面升级 Web 界面和命令行工具

### v1.0 (2024)
- ✅ 基础 VESPCN 网络实现
- ✅ 2x 帧率 + 2x 分辨率联合处理
- ✅ 多尺度特征融合
- ✅ 客观质量评估 (PSNR/SSIM/LPIPS)
- ✅ Streamlit Web 界面
- ✅ 命令行工具
