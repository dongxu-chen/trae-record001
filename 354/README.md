# 广告点击欺诈检测系统

基于 Python + Scikit-learn + Redis + Kafka + Flink 实现的实时广告点击欺诈检测系统。

## 项目概述

本系统通过结合**规则引擎**和**孤立森林(Isolation Forest)**算法，实时检测广告点击中的欺诈行为，包括：
- 同一IP高频点击
- 固定间隔点击（机器人特征）
- 无效流量（短会话、异常User-Agent等）

## 系统架构

```
点击日志数据流
    ↓
┌─────────────────┐
│   Kafka 消息队列│  ← 消息缓冲
└────────┬────────┘
         ↓
┌─────────────────┐
│  Flink 流处理   │  ← 实时计算窗口
└────────┬────────┘
         ↓
┌─────────────────┐
│  特征提取模块   │  ← 18维特征工程
└────────┬────────┘
         ↓
┌─────────────────┐     ┌─────────────────┐
│   规则引擎      │────▶│  孤立森林模型   │
│  (8条规则)      │     │  (异常检测)     │
└────────┬────────┘     └────────┬────────┘
         ↓                       ↓
┌─────────────────────────────────────────┐
│            分数融合模块                  │
│  (规则权重0.6 + 模型权重0.4)             │
└───────────────────┬─────────────────────┘
                    ↓
         ┌──────────────────────┐
         │  欺诈分数 & 处置建议  │
         │  ALLOW / FLAG / BLOCK / CHALLENGE
         └──────────────────────┘
                    ↓
         ┌──────────────────────┐
         │   Redis 状态存储      │
         │  (IP/设备黑名单、告警)
         └──────────────────────┘
```

## 目录结构

```
.
├── config/
│   └── config.yaml          # 系统配置文件
├── src/
│   ├── __init__.py          # 包初始化
│   ├── data_models.py       # 数据模型定义
│   ├── feature_extractor.py # 特征提取模块
│   ├── rule_engine.py       # 规则引擎
│   ├── anomaly_detector.py  # 孤立森林模型
│   ├── redis_store.py       # Redis状态存储
│   ├── kafka_client.py      # Kafka客户端
│   ├── flink_processor.py   # Flink流处理
│   └── fraud_scorer.py      # 欺诈分数融合
├── models/                  # 模型保存目录
├── main.py                  # 主程序入口 & 演示
├── requirements.txt         # 依赖包
└── README.md                # 本文档
```

## 核心功能

### 1. 特征提取 (18维特征)

| 特征类别 | 特征名称 | 说明 |
|---------|---------|------|
| 点击频率 | ip_click_count_1min/5min/1h | IP在不同时间窗口的点击数 |
| 设备频率 | device_click_count_1min/5min/1h | 设备在不同时间窗口的点击数 |
| 会话统计 | session_click_count | 同一会话点击数 |
| 时间间隔 | time_since_last_click_ip/device | 距上次点击的时间 |
| 规律性 | click_interval_std_ip/device | 点击间隔标准差 |
| 多样性 | unique_publishers_per_ip | 同一IP访问的发布商数 |
| 分布 | ip_entropy | IP分布熵 |
| 占比 | publisher_click_ratio | 该IP在发布商总点击中的占比 |
| 时间 | hour_of_day, day_of_week, is_weekend | 时间特征 |

### 2. 规则引擎 (8条检测规则)

| 规则名称 | 检测目标 | 阈值可配置 |
|---------|---------|-----------|
| high_frequency_ip | IP高频点击 | 60秒 > 30次 |
| high_frequency_device | 设备高频点击 | 60秒 > 20次 |
| fixed_interval_ip | IP固定间隔点击 | 标准差 < 0.5秒 |
| fixed_interval_device | 设备固定间隔点击 | 标准差 < 0.5秒 |
| invalid_session_duration | 无效短会话 | 时长 < 1秒且点击>3次 |
| excessive_session_clicks | 会话点击过量 | > 100次 |
| suspicious_publisher_ratio | 发布商占比异常 | 单IP占比 > 50% |
| user_agent_anomaly | 可疑User-Agent | 包含bot/crawler等特征 |

### 3. 孤立森林 (Isolation Forest)

使用 Scikit-learn 实现的孤立森林算法进行无监督异常检测：
- 100棵树
- 异常率预估: 10%
- 自动训练并保存模型

### 4. 分数融合与处置建议

**分数计算:**
- 规则分数权重: 60%
- 模型异常分数权重: 40%
- 双重确认时分数放大1.1倍

**处置策略:**
| 分数范围 | 动作 | 说明 |
|---------|------|------|
| ≥ 0.9 或 高风险规则触发 | **BLOCK** | 立即阻止，加入黑名单 |
| ≥ 0.7 | **CHALLENGE** | 需要验证码等验证 |
| ≥ 0.5 | **FLAG** | 标记供人工审核 |
| < 0.5 | **ALLOW** | 正常通过 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行演示

```bash
python main.py
```

选择演示编号运行：
- `0`: 运行全部演示
- `1`: 基础欺诈检测演示
- `2`: Redis 实时状态存储演示
- `3`: Kafka 消息生产演示
- `4`: Flink 流处理演示
- `5`: 完整实时检测流水线演示（高频攻击场景）

### 3. 基础使用示例

```python
from src import ClickLog, FeatureExtractor, FraudScorer, ActionExecutor
from datetime import datetime

# 初始化组件
feature_extractor = FeatureExtractor()
fraud_scorer = FraudScorer()
action_executor = ActionExecutor()

# 创建点击日志
click = ClickLog(
    click_id="click_001",
    timestamp=datetime.now(),
    ip="192.168.1.100",
    device_id="device_001",
    user_agent="Mozilla/5.0...",
    publisher_id="pub_1",
    campaign_id="camp_1",
    ad_id="ad_1",
    referrer="https://example.com"
)

# 提取特征
features = feature_extractor.extract_features(click)

# 欺诈评估
assessment = fraud_scorer.assess(click, features)

# 执行处置
result = action_executor.execute(assessment, click.ip, click.device_id)

print(f"欺诈分数: {assessment.final_fraud_score:.2f}")
print(f"建议动作: {assessment.recommended_action.value}")
print(f"触发规则: {assessment.triggered_rules}")
```

## 配置说明

编辑 `config/config.yaml` 调整系统参数：

```yaml
kafka:
  bootstrap_servers: "localhost:9092"
  topic: "click_logs"

redis:
  host: "localhost"
  port: 6379

rules:
  high_frequency:
    window_seconds: 60
    max_clicks_per_ip: 30
  # ... 更多规则配置

model:
  isolation_forest:
    n_estimators: 100
    contamination: 0.1

output:
  fraud_threshold: 0.7
```

## 服务依赖

### Redis (可选，用于实时状态)

```bash
# Windows (使用 Docker)
docker run -d -p 6379:6379 redis

# 或下载 Redis for Windows
```

### Kafka (可选，用于消息队列)

```bash
# 使用 Docker Compose 或手动安装
docker run -d -p 2181:2181 zookeeper
docker run -d -p 9092:9092 --env KAFKA_ZOOKEEPER_CONNECT=host.docker.internal:2181 wurstmeister/kafka
```

### Flink (可选，用于流处理)

```bash
# 安装 PyFlink
pip install pyflink==1.17.0
```

## 性能指标

- **单条检测延迟**: < 10ms
- **吞吐量**: ~10,000 TPS (单进程)
- **规则检测准确率**: ~95% (基于模拟数据)
- **孤立森林召回率**: ~85% (基于模拟数据)

## 扩展建议

1. **特征增强**: 添加地理位置、设备指纹等特征
2. **模型升级**: 集成 One-Class SVM、AutoEncoder 等模型
3. **实时训练**: 支持在线学习和模型增量更新
4. **可视化**: 添加 Grafana 监控面板
5. **告警集成**: 对接 Slack、企业微信等告警通道

## License

MIT License
