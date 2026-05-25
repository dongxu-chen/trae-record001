# 实时竞价广告出价系统 (RTB Bid Engine)

## 系统架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  广告请求入口   │────▶│  Kafka消息队列  │────▶│  Flink实时处理 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                  │                           │
                                  ▼                           ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  预测模型服务   │◀────│  核心出价引擎  │────▶│   Redis存储    │
│  (XGBoost)      │     └─────────────────┘     └─────────────────┘
└─────────────────┘              │
                                  ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  流量价值分层   │     │  频次控制模块   │     │  预算管理模块   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 技术栈

- **Python 3.8+**: 主开发语言
- **XGBoost**: CTR/CVR预测模型
- **Redis**: 高速数据存储（用户画像、频次控制、预算管理、预测缓存）
- **Apache Kafka**: 消息队列（请求/响应数据流）
- **Apache Flink**: 实时流处理（实时统计、预算节奏控制、频次监控）
- **FastAPI**: API服务接口

## 核心功能

### 1. CTR/CVR预测模型 (`src/prediction_model.py`)

- 特征工程：支持类别特征、数值特征、交叉特征
- 基于XGBoost的CTR（点击率）和CVR（转化率）预测
- 预测结果缓存，提升响应速度
- 支持GPU加速训练

### 2. 流量价值分层 (`src/traffic_layer.py`)

- S/A/B/C四层流量分级
- 基于预测CTR/CVR进行流量价值评估
- 各层级独立预算分配和动态调整
- 实时统计各层级投放效果

### 3. 频次控制 (`src/frequency_control.py`)

- 多时间窗口频次限制（1小时、6小时、24小时、7天）
- 频度过高时的出价衰减机制
- 用户-广告对的频控统计

### 4. 预算平滑消耗 (`src/budget_manager.py`)

- 总预算和日预算管理
- 小时级预算平滑分配
- 动态节奏控制（Pace Control）
- 紧急模式下的出价调整
- 预算消耗速度监控

### 5. 核心出价引擎 (`src/bid_engine.py`)

- 整合预测模型、流量分层、频次控制、预算管理
- 多阶段出价计算流程
- 详细的出价决策日志

### 6. Kafka消息处理 (`src/kafka_handler.py`)

- 出价请求/响应的生产和消费
- 曝光、点击、转化事件处理

### 7. Flink实时处理 (`src/flink_job.py`)

- 实时出价分析（出价量、成功率、CTR/CVR统计）
- 预算消耗节奏动态调整
- 高频用户监控告警

## 快速开始

### 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 启动Redis（需要先安装Redis服务
redis-server

# 启动Kafka（需要先安装Kafka
# 启动ZooKeeper
bin/zookeeper-server-start.sh config/zookeeper.properties
# 启动Kafka Broker
bin/kafka-server-start.sh config/server.properties
```

### 运行演示模式

```bash
# 完整功能演示
python main.py demo
```

### 运行仿真模拟

```bash
# 基础模拟（100个请求，每个请求间隔0.1秒）
python main.py simulate --num-requests 100 --delay 0.1

# 创建模型并保存用户画像
python main.py simulate --create-models --save-profiles --profile-count 100

# 指定活动ID
python main.py simulate --campaign-id my_campaign
```

### 启动API服务

```bash
# 启动API服务（默认端口8000）
python main.py api --port 8000

# 多worker启动
python main.py api --port 8000 --workers 4
```

### API接口

- **POST /bid**: 处理出价请求
- **GET /status**: 获取系统状态
- **POST /click/{bid_id}**: 记录点击事件
- **POST /reset**: 重置引擎状态

### Kafka模式

```bash
# 启动Kafka消费者（处理出价请求）
python main.py kafka-consumer

# 启动Kafka生产者（模拟请求）
python main.py kafka-producer --num-messages 1000 --delay 0.5
```

### Flink实时处理

```bash
# 模拟模式（不需要安装Flink）
python main.py flink --simulate --interval 30

# 真实Flink模式
python main.py flink --job-type analytics
python main.py flink --job-type budget
python main.py flink --job-type frequency
```

## 出价计算流程

```
出价请求
    │
    ▼
前置条件检查
  ├─ 预算检查
  ├─ 频次检查
  └─ 底价检查
    │
    ▼
CTR/CVR预测
  ├─ 特征提取
  ├─ 模型预测
  └─ 结果缓存
    │
    ▼
基础出价计算
  └─ 期望价值 = CTR × CVR × CPA目标 × 0.5
    │
    ▼
流量分层调整
  ├─ S层(高价值流量：×1.5
  ├─ A层：×1.2
  ├─ B层：×1.0
  └─ C层：×0.7
    │
    ▼
频次控制调整
  └─ 频度过高时衰减出价
    │
    ▼
预算节奏调整
  ├─ 消耗过快：降低出价
  ├─ 消耗过慢：提高出价
  └─ 紧急模式：大幅降低出价
    │
    ▼
最终出价确定
  ├─ 出价范围限制（0.01 ~ 10元）
  ├─ 底价检查
  └─ 预算预扣
    │
    ▼
出价响应
```

## 配置说明 (`config.py`)

### Redis配置
```python
RedisConfig(
    host="localhost",
    port=6379,
    max_connections=50,
)
```

### 预算配置
```python
BudgetConfig(
    total_budget=10000.0,      # 总预算
    daily_budget=1000.0,        # 日预算
    smooth_factor=0.8,           # 平滑因子
    emergency_threshold=0.2,    # 紧急阈值
    min_bid=0.01,                # 最低出价
    max_bid=10.0,               # 最高出价
)
```

### 频次配置
```python
FrequencyConfig(
    limits={
        "1h": (3, 3600),      # 1小时最多3次
        "6h": (10, 21600),     # 6小时最多10次
        "24h": (20, 86400),    # 24小时最多20次
        "7d": (50, 604800),     # 7天最多50次
    },
    decay_factor=0.7,              # 衰减因子
)
```

### 流量分层配置
```python
TrafficLayerConfig(
    layers=[
        {"name": "S", "min_ctr": 0.05, "bid_multiplier": 1.5, "budget_share": 0.4},
        {"name": "A", "min_ctr": 0.02, "bid_multiplier": 1.2, "budget_share": 0.3},
        {"name": "B", "min_ctr": 0.01, "bid_multiplier": 1.0, "budget_share": 0.2},
        {"name": "C", "min_ctr": 0.0, "bid_multiplier": 0.7, "budget_share": 0.1},
    ]
)
```

## 项目结构

```
rtb-bid-engine/
├── config.py                 # 系统配置
├── main.py                   # 主入口文件
├── requirements.txt         # 依赖包列表
├── README.md              # 项目说明
├── models/                # 模型文件目录
│   ├── ctr_xgboost.model    # CTR预测模型
│   └── cvr_xgboost.model    # CVR预测模型
└── src/                   # 源代码目录
    ├── __init__.py
    ├── redis_client.py        # Redis客户端
    ├── prediction_model.py   # 预测模型
    ├── traffic_layer.py      # 流量分层
    ├── frequency_control.py   # 频次控制
    ├── budget_manager.py     # 预算管理
    ├── bid_engine.py         # 出价引擎
    ├── kafka_handler.py     # Kafka处理
    ├── flink_job.py          # Flink作业
    └── data_generator.py    # 数据生成器
```

## Redis Key设计

| Key模式 | 说明 | 过期时间 |
|---------|------|----------|
| `user:profile:{user_id}` | 用户画像 | 7天 |
| `freq:{user_id}:{ad_id}:{window}` | 频次计数 | 对应窗口 |
| `budget:{campaign_id}` | 预算信息 | 永久 |
| `budget:hourly:{campaign_id}:{hour}` | 小时预算 | 1天 |
| `traffic:layer:{layer}:{campaign_id}` | 流量分层统计 | 永久 |
| `pred:cache:{hash}` | 预测结果缓存 | 30分钟 |
| `pace:{campaign_id}` | 节奏系数 | 1小时 |
| `bid:history:{bid_id}` | 出价历史 | 1天 |

## 性能优化建议

1. **预测缓存**: 相同特征组合的预测结果缓存30分钟
2. **Redis连接池**: 使用连接池复用Redis连接
3. **批量预测**: 支持批量预测提升吞吐量
4. **Kafka批量发送**: 批量发送消息减少网络开销
5. **Flink窗口聚合**: 实时统计使用窗口聚合减少状态存储

## 监控指标

- **出价相关**: QPS、成功率、平均出价、拒绝原因分布
- **预测相关**: CTR、CVR、预测耗时
- **预算相关**: 预算消耗率、节奏偏差、小时预算使用率
- **流量相关**: 各层级流量占比、各层级CTR/CVR
- **频次相关**: 高频用户数、平均展示频次

## 许可证

MIT License
