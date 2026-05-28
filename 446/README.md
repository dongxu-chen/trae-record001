# 消息队列延迟监控平台

## 项目简介

消息队列延迟监控平台（MQ Monitor Platform是一个综合性的消息队列监控解决方案，支持Kafka、RabbitMQ、RocketMQ三种主流消息队列的生产消费延迟、积压量、吞吐量等关键指标的实时监控、异常告警、积压趋势预测、消费者组对比等功能。

## 功能特性

### 核心功能
- **多MQ支持**：同时支持Kafka、RabbitMQ、RocketMQ
- **延迟监控**：生产延迟、消费延迟、端到端延迟
- **积压监控**：实时队列积压量、消费者Lag监控
- **吞吐量监控**：生产/消费吞吐量（消息/秒）
- **异常告警**：
  - 延迟阈值告警
  - 延迟异常检测（Z-Score算法）
  - 积压阈值告警
  - 积压增长趋势告警
  - 吞吐量突降告警
  - 支持Webhook通知
- **时序预测**：
  - Holt-Winters指数平滑预测
  - ARIMA模型预测
  - 线性回归预测
  - 未来30分钟积压预测
  - 阈值超限预警
- **消费者组对比**：
  - 多消费者组性能对比
  - 健康度评分
  - Lag趋势分析
- **Prometheus集成**：标准Prometheus指标导出
- **Grafana可视化**：预置专业监控仪表盘

## 技术栈

| 组件 | 技术选型 |
|--------|----------|
| 开发语言 | Java 17 |
| 框架 | Spring Boot 3.2 |
| 构建工具 | Maven 3.9 |
| MQ客户端 | Kafka Clients 3.6、RabbitMQ Client 5.20、RocketMQ Client 5.1 |
| 指标采集 | Micrometer 1.12 |
| 监控系统 | Prometheus |
| 可视化 | Grafana |
| 时序分析 | Apache Commons Math 3.6 |
| 网络请求 | OkHttp 4.12 |
| JSON处理 | Jackson 2.16 |

## 项目结构

```
mq-monitor-platform/
├── mq-monitor-common/          # 公共模块
│   ├── enums/                      # 枚举类型
│   ├── model/                      # 数据模型
│   ├── config/                     # 配置类
│   └── util/                       # 工具类
├── mq-monitor-mq-clients/        # MQ客户端模块
│   ├── mq-monitor-kafka/          # Kafka客户端
│   ├── mq-monitor-rabbitmq/     # RabbitMQ客户端
│   └── mq-monitor-rocketmq/     # RocketMQ客户端
├── mq-monitor-collector/          # 指标采集模块
├── mq-monitor-alert/              # 异常检测告警模块
├── mq-monitor-prediction/         # 时序预测模块
├── mq-monitor-comparison/         # 消费者组对比模块
├── mq-monitor-exporter/           # Prometheus导出模块
├── mq-monitor-api/              # REST API模块
├── mq-monitor-bootstrap/        # 启动模块
└── docker/                         # Docker部署配置
│   ├── prometheus/               # Prometheus配置
│   ├── grafana/                  # Grafana配置
│   ├── alertmanager/             # Alertmanager配置
│   ├── docker-compose.yml         # Docker Compose配置
│   └── Dockerfile               # 应用Dockerfile
└── pom.xml                        # 父POM
```

## 快速开始

### 环境要求
- JDK 17+
- Maven 3.9+
- Docker 20.10+

### 本地构建

```bash
# 克隆项目
git clone <repository-url>
cd mq-monitor-platform

# 构建项目
mvn clean package -DskipTests

# 运行应用
java -jar mq-monitor-bootstrap/target/mq-monitor-bootstrap-1.0.0.jar
```

### Docker部署

```bash
# 使用Docker Compose启动完整监控栈
cd docker
docker-compose up -d
```

### 访问地址
- 应用API: http://localhost:8080
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin123)
- Alertmanager: http://localhost:9093

## API接口

### 指标相关
- `GET /api/metrics` - 获取所有监控指标
- `GET /api/metrics/{cluster}/{topic}` - 获取指定Topic指标
- `GET /api/metrics/history/backlog/{cluster}/{topic}` - 获取积压历史数据
- `GET /api/metrics/history/latency/{cluster}/{topic}` - 获取延迟历史数据
- `GET /api/metrics/summary` - 获取监控摘要

### 告警相关
- `GET /api/alerts` - 获取所有告警
- `GET /api/alerts/active` - 获取活跃告警
- `POST /api/alerts/evaluate` - 手动触发告警评估
- `GET /api/alerts/config` - 获取告警配置
- `PUT /api/alerts/config` - 更新告警配置

### 预测相关
- `GET /api/prediction/{mqType}/{cluster}/{topic}` - 预测指定Topic积压
- `GET /api/prediction/all` - 预测所有Topic积压
- `GET /api/prediction/high-risk` - 获取高风险预测
- `GET /api/prediction/config` - 获取预测配置
- `PUT /api/prediction/config` - 更新预测配置

### 对比相关
- `POST /api/comparison/{mqType}/{cluster}/{topic}` - 对比消费者组
- `GET /api/comparison/{mqType}/{cluster}` - 对比所有Topic的消费者组

### Prometheus指标
- `GET /actuator/prometheus` - Prometheus指标抓取端点

## 监控指标

### 核心指标

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `mq_latency_produce_ms` | Gauge | 生产延迟(毫秒) |
| `mq_latency_consume_ms` | Gauge | 消费延迟(毫秒) |
| `mq_latency_end_to_end_ms` | Gauge | 端到端延迟(毫秒) |
| `mq_backlog_size` | Gauge | 当前积压量 |
| `mq_consumer_lag` | Gauge | 消费者Lag |
| `mq_throughput_produce` | Gauge | 生产吞吐量(消息/秒) |
| `mq_throughput_consume` | Gauge | 消费吞吐量(消息/秒) |
| `mq_messages_produced_total` | Counter | 累计生产消息数 |
| `mq_messages_consumed_total` | Counter | 累计消费消息数 |

### 指标标签
- `mq_type`: MQ类型 (kafka/rabbitmq/rocketmq)
- `cluster`: 集群名称
- `topic`: Topic/队列名称
- `consumer_group`: 消费者组名称

## 告警规则

### 1. **高延迟告警
- 延迟>3000ms持续1分钟 → Warning
- 延迟>10000ms持续30秒 → Critical

### 2. **高积压告警
- 积压>10000持续2分钟 → Warning
- 积压>50000持续1分钟 → Critical

### 3. **消费者Lag告警
- Lag持续增长且>5000 → Warning

### 4. **吞吐量突降告警
- 消费吞吐量<10消息/秒持续5分钟 → Warning

### 5. **连接错误告警
- 5分钟内出现连接错误 → Critical

## 配置说明

### 告警配置

```yaml
alert:
  latencyThresholdMs: 3000              # 延迟阈值(毫秒)
  backlogThreshold: 10000                # 积压阈值
  throughputDropThresholdPercent: 25.0    # 吞吐量下降阈值(%)
  consumerLagThreshold: 5000           # 消费者Lag阈值
  anomalyZScoreThreshold: 2.5               # 异常检测Z-Score阈值
  evaluationIntervalSeconds: 30               # 告警评估间隔(秒)
  webhookEnabled: false                   # 是否启用Webhook通知
  webhookUrl: http://webhook-url          # Webhook地址
```

### 预测配置

```yaml
prediction:
  predictionHorizonMinutes: 30               # 预测时间范围(分钟)
  minDataPointsForPrediction: 20          # 预测所需最少数据点
  defaultAlgorithm: HOLT_WINTERS            # 默认预测算法
  backlogWarningThreshold: 10000             # 积压预警阈值
  confidenceLevel: 0.95                       # 置信度水平
```

## 部署架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Grafana (可视化)                          │
└─────────────────────────────────────────────────────────────────┘
                           │ HTTP
┌─────────────────────────────────────────────────────────────────┐
│                  Prometheus (时序数据库)                   │
└─────────────────────────────────────────────────────────────────┘
                           │ 抓取
┌─────────────────────────────────────────────────────────────────┐
│           MQ Monitor Application (Java应用)             │
│  ┌─────────┐  ┌────────┐  ┌──────────┐  ┌──────┐│
│  │ 指标采集器 │  │ 异常检测│  │ 时序预测  │  │ REST API ││
│  └─────────┘  └────────┘  └──────────┘  └──────┘│
│         │              │               │                  │       │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Prometheus Exporter (指标导出)            │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
       │                │                │
┌─────────┐    ┌──────────┐    ┌──────────┐
│ Kafka │    │ RabbitMQ │    │ RocketMQ │
└─────────┘    └──────────┘    └──────────┘
```

## 开发指南

### 扩展新的MQ类型

1. 在`mq-monitor-mq-clients`下创建新模块
2. 实现MQ客户端实现`xxxMonitorClient类
3. 在`MetricsCollectorService`中添加对应MQ类型支持
4. 在`MqMonitorApplication`中添加集群配置

### 添加新的告警规则

1. 在`AnomalyDetector`中添加新的检测方法
2. 在`AlertType`枚举中添加新的告警类型
3. 在`alerts.yml`中添加Prometheus告警规则

### 扩展预测算法

1. 在`TimeSeriesPredictor`中添加新的预测方法
2. 在`PredictionConfig`中配置默认算法
3. 在`predictBacklog`方法的switch中添加对应分支

## 许可证

MIT License
