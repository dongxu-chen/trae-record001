# 视频点击率预测模型 (Video CTR Prediction) v2.0

基于 DeepFM 模型的视频点击率预测系统，支持预训练嵌入层、冷启动处理和多版本灰度发布。

## 新增功能 v2.0

### 1. 两阶段训练 (FM预训练 + DeepFM联合训练)
- **Stage 1**: 单独训练 FM 模型学习特征嵌入
- **Stage 2**: 使用预训练嵌入初始化 DeepFM，分两阶段联合训练
  - Phase 1: 冻结 FM 层，训练 DNN
  - Phase 2: 微调整个网络
- **优势**: 加速收敛，提升最终效果

### 2. 冷启动处理
- **多级降级策略**:
  - 用户历史数据充足 → 使用用户历史均值
  - 新用户/少数据 → 使用分类平均 CTR
  - 完全新用户 → 使用全局平均 CTR
- **置信度加权**: 根据数据量动态调整冷启动预测权重

### 3. 模型版本路由与灰度发布
- **多版本共存**: 支持同时加载多个模型版本
- **流量灰度**: 按比例分配流量到不同模型版本
- **用户一致性**: 同一用户始终路由到同一版本
- **动态调整**: 运行时可更新流量比例
- **版本管理**: 支持热添加新版本

## 技术栈

- **模型**: DeepFM（深度分解机）+ FM 预训练
- **框架**: TensorFlow 2.x
- **特征处理**: Keras Preprocessing + Scikit-learn
- **API 服务**: Flask
- **灰度路由**: 自定义 ModelRouter

## 项目结构

```
.
├── config.py                   # 配置文件（含灰度路由配置）
├── requirements.txt            # 依赖包
├── train.py                  # 训练脚本（支持两阶段训练）
├── test_api.py               # 基础 API 测试
├── test_advanced_features.py # 高级功能测试
├── README.md                 # 项目说明
├── data/                     # 数据目录
├── models/
│   ├── v1/                   # 模型版本 v1
│   └── v2/                   # 模型版本 v2
├── logs/                     # 日志目录
└── src/
    ├── __init__.py
    ├── data/
    │   ├── __init__.py
    │   ├── preprocess.py     # 数据预处理
    │   ├── data_generator.py # 样本生成
    │   └── cold_start.py     # 冷启动处理
    ├── models/
    │   ├── __init__.py
    │   └── deepfm.py         # DeepFM + FMOnlyModel
    └── api/
        ├── __init__.py
        ├── app.py            # Flask API v2.0
        └── model_router.py   # 模型版本路由器
```

## 配置说明 (config.py)

```python
# FM 预训练配置
FM_PRETRAIN_EPOCHS = 5
FM_LEARNING_RATE = 0.01

# 冷启动配置
COLD_START_THRESHOLD = 5       # 用户数据少于5条视为冷启动
GLOBAL_AVERAGE_CTR = 0.35       # 全局平均 CTR 兜底

# 模型版本配置
MODEL_VERSIONS = {
    'v1': {'path': 'models/v1', 'traffic_ratio': 0.7, 'default': True},
    'v2': {'path': 'models/v2', 'traffic_ratio': 0.3, 'default': False}
}

GRAYSCALE_ENABLED = True
ROUTING_STRATEGY = 'ratio'      # 'ratio' 或 'user_hash'
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 两阶段训练

```bash
# 训练两阶段模型 (v1)
python train.py twostage v1

# 训练基线模型 (v2)
python train.py baseline v2

# 默认：训练 v1 + v2 两个版本
python train.py
```

### 3. 启动 API 服务

```bash
python -m src.api.app
```

### 4. 测试高级功能

```bash
# 基础测试
python test_api.py

# 高级功能测试（灰度路由、冷启动、版本管理）
python test_advanced_features.py
```

## API 接口 v2.0

### 预测接口
- **POST** `/predict`
- 请求体可添加 `model_version` 字段指定版本

```json
{
  "user_id": "user_123",
  "video_id": "video_456",
  "title": "Python机器学习入门",
  "tags": "Python,机器学习",
  "category": "科技",
  "duration": 300,
  "user_history": "video_100,video_200",
  "model_version": "v1"
}
```

响应包含：
- `model_version`: 实际使用的模型版本
- `model_ctr`: 模型原始预测值
- `predicted_ctr`: 融合冷启动后的最终值
- `cold_start_info`: 冷启动信息

### 路由管理接口

| 接口 | 方法 | 功能 |
|------|------|------|
| `/router/stats` | GET | 获取路由统计 |
| `/router/update_ratio` | POST | 更新流量比例 |
| `/router/add_version` | POST | 添加新版本 |

更新流量比例示例：
```json
{
  "version": "v2",
  "traffic_ratio": 0.5
}
```

## 两阶段训练流程

```
训练数据
    ↓
┌─────────────────────────────────┐
│  Stage 1: FM 预训练            │
│  - 学习一阶 + 二阶特征交互      │
│  - 输出预训练嵌入权重         │
└─────────────────────────────────┘
    ↓ 预训练嵌入
┌─────────────────────────────────┐
│  Stage 2: DeepFM 联合训练    │
│  Phase 1: 冻结FM层，训练DNN │
│  Phase 2: 微调整个网络          │
└─────────────────────────────────┘
    ↓
最终模型
```

## 冷启动降级策略

```
用户请求
    ↓
有足够历史数据?
    ├─ 是 → 使用用户历史均值 (高置信度)
    └─ 否
        ↓
    有分类信息?
        ├─ 是 → 使用分类平均 CTR (中置信度)
        └─ 否 → 使用全局平均 CTR (低置信度)
```

## 灰度路由策略

### 按比例路由
- 根据配置的 `traffic_ratio` 随机分配
- 支持用户哈希确保一致性

```
用户请求
    ↓
计算用户哈希值
    ↓
按累计比例匹配版本
    ↓
路由到对应模型
```

### 动态灰度发布流程

```
初始: v1 (100%)
    ↓
发布 v2: v1(90%), v2(10%)
    ↓
观察指标稳定: v1(70%), v2(30%)
    ↓
全量发布: v1(0%), v2(100%)
```

## 新增文件说明

| 文件 | 说明 |
|------|------|
| [cold_start.py](file:///d:/Trae/project/record001/294/src/data/cold_start.py) | 冷启动处理器 |
| [model_router.py](file:///d:/Trae/project/record001/294/src/api/model_router.py) | 模型版本路由器 |
| [test_advanced_features.py](file:///d:/Trae/project/record001/294/test_advanced_features.py) | 高级功能测试脚本 |

## 使用示例

### Python 客户端调用灰度发布

```python
import requests

# 自动按比例路由
response = requests.post('http://localhost:5000/predict', json={
    'user_id': 'user_123',
    'title': '测试视频',
    'tags': '测试',
    'category': '科技',
    'duration': 300,
    'user_history': 'video_1'
})
print(f"使用版本: {response.json()['model_version']}")

# 指定版本调用
response = requests.post('http://localhost:5000/predict', json={
    ...,
    'model_version': 'v2'  # 强制使用 v2
})

# 动态调整流量
requests.post('http://localhost:5000/router/update_ratio', json={
    'version': 'v2',
    'traffic_ratio': 0.5
})
```
