# Kafka 消息积压自动处理工具

一个基于 Go 语言开发的 Kafka 消费组自动伸缩工具，通过监控消费组积压量，自动调整消费者副本数，实现消息积压的智能处理。

## 功能特性

- ✅ **消费组积压监控** - 实时监控 Kafka 消费组的滞后量
- ✅ **消费者动态伸缩** - 基于阈值自动增减消费者副本数
- ✅ **分区重分配** - 支持多种分区分配策略（Range、RoundRobin、Sticky、Uniform）
- ✅ **积压预测** - 基于历史数据的趋势预测（线性回归、指数平滑、移动平均）
- ✅ **K8s 集成** - 支持 Deployment 和 StatefulSet 的自动伸缩
- ✅ **Prometheus 指标** - 丰富的监控指标暴露
- ✅ **多种运行模式** - Off、Observation（观察模式）、Auto（自动模式）
- ✅ **冷却机制** - 防止频繁伸缩导致的系统不稳定

## 架构设计

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Kafka Cluster  │────▶│  Kafka Client   │────▶│  Lag Collector  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Kubernetes     │◀────│  Auto Scaler    │◀────│  Predictor      │
│  API Server     │     └─────────────────┘     └─────────────────┘
└─────────────────┘             │
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Prometheus     │
                        │  Metrics        │
                        └─────────────────┘
```

## 快速开始

### 前置要求

- Go 1.21+
- Kubernetes 集群（可选，本地开发可跳过）
- Kafka 集群
- Prometheus（可选，用于监控）

### 本地运行

1. **克隆项目**
```bash
git clone <repository-url>
cd kafka-autoscaler
```

2. **安装依赖**
```bash
make deps
```

3. **修改配置**

编辑 `config/config.yaml`，配置 Kafka 地址和自动伸缩规则。

4. **运行程序**
```bash
make run
```

### Docker 部署

1. **构建镜像**
```bash
make docker-build
```

2. **推送镜像**
```bash
make docker-push
```

### Kubernetes 部署

1. **创建命名空间**
```bash
kubectl create namespace kafka
```

2. **部署应用**
```bash
make deploy
```

3. **查看部署状态**
```bash
kubectl get pods -n kafka
kubectl get svc -n kafka
```

## 配置说明

### 主要配置项

```yaml
kafka:
  brokers:
    - "localhost:9092"
  timeout: 30s

kubernetes:
  inCluster: false
  kubeConfigPath: ""

autoscalers:
  - consumerGroupID: "my-consumer-group"
    k8sDeployment: "my-consumer-deployment"
    k8sNamespace: "default"
    k8sResourceType: "deployment"
    minReplicas: 1
    maxReplicas: 10
    scaleUpThreshold: 10000
    scaleDownThreshold: 1000
    scaleUpIncrement: 2
    scaleDownDecrement: 1
    cooldownPeriod: 5m
    predictionWindow: 5m
    usePrediction: true
    mode: "observation"
```

### 配置参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `consumerGroupID` | Kafka 消费组 ID | 必填 |
| `k8sDeployment` | Kubernetes Deployment 名称 | 必填 |
| `k8sNamespace` | Kubernetes 命名空间 | default |
| `k8sResourceType` | 资源类型 (deployment/statefulset) | deployment |
| `minReplicas` | 最小副本数 | 1 |
| `maxReplicas` | 最大副本数 | 10 |
| `scaleUpThreshold` | 扩容阈值（消息积压数） | 10000 |
| `scaleDownThreshold` | 缩容阈值（消息积压数） | 1000 |
| `scaleUpIncrement` | 每次扩容增加的副本数 | 1 |
| `scaleDownDecrement` | 每次缩容减少的副本数 | 1 |
| `cooldownPeriod` | 冷却期 | 5m |
| `predictionWindow` | 预测窗口 | 5m |
| `usePrediction` | 是否启用预测触发 | true |
| `mode` | 运行模式 (off/observation/auto) | observation |

### 运行模式

- **`off`**: 关闭自动伸缩功能
- **`observation`**: 观察模式，只输出伸缩建议，不实际执行
- **`auto`**: 自动模式，根据规则自动执行伸缩操作

## Prometheus 指标

### 消费组指标

| 指标名称 | 说明 |
|----------|------|
| `kafka_consumer_group_lag` | 每个分区的消费滞后量 |
| `kafka_consumer_group_total_lag` | 消费组总滞后量 |
| `kafka_consumer_group_members` | 消费组成员数 |
| `kafka_consumer_group_offset` | 当前消费偏移量 |
| `kafka_topic_end_offset` | Topic 最新偏移量 |

### 自动伸缩指标

| 指标名称 | 说明 |
|----------|------|
| `kafka_autoscaler_replicas` | 当前副本数 |
| `kafka_autoscaler_events_total` | 伸缩事件总数 |
| `kafka_autoscaler_actions_total` | 伸缩操作总数 |
| `kafka_autoscaler_lag_threshold` | 滞后阈值 |
| `kafka_autoscaler_predicted_lag` | 预测滞后量 |

## API 端点

| 端点 | 说明 |
|------|------|
| `:8080/health` | 健康检查 |
| `:8080/status` | 状态信息 |
| `:9090/metrics` | Prometheus 指标 |

## 分区重分配策略

### 支持的策略

1. **Range** - 按范围分配，连续的分区分配给同一消费者
2. **RoundRobin** - 轮询分配，均匀分配所有分区
3. **Sticky** - 粘性分配，尽量保持现有分配，减少分区移动
4. **Uniform** - 均匀分配，基于滞后量均衡分配

### 启用重分配

```yaml
rebalancer:
  enabled: true
  strategy: "sticky"
  rebalanceInterval: 15m
  dryRun: true
  enableUnevenDetection: true
  unevenThresholdRatio: 2.0
```

## 积压预测算法

### 线性回归 (Linear Regression)

基于历史数据拟合线性模型，预测未来的积压趋势。

### 指数平滑 (Exponential Smoothing)

对近期数据赋予更高权重，适合有趋势的数据。

### 移动平均 (Moving Average)

计算窗口内的平均值，平滑波动。

### 集成预测 (Ensemble)

综合多种算法的预测结果，提高预测准确性。

## 开发指南

### 项目结构

```
kafka-autoscaler/
├── cmd/
│   └── main.go              # 主程序入口
├── pkg/
│   ├── autoscaler/          # 自动伸缩控制器
│   ├── config/              # 配置管理
│   ├── kafka/               # Kafka 客户端
│   ├── kubernetes/          # K8s 客户端
│   ├── predictor/           # 预测算法
│   ├── prometheus/          # Prometheus 指标
│   └── rebalancer/          # 分区重分配
├── config/
│   └── config.yaml          # 配置文件
├── deploy/
│   └── kubernetes/          # K8s 部署文件
├── Dockerfile
├── Makefile
├── go.mod
└── README.md
```

### 本地开发

```bash
# 格式化代码
make fmt

# 运行测试
make test

# 代码检查
make lint

# 完整检查
make check
```

## 常见问题

### Q: 如何从观察模式切换到自动模式？

A: 修改配置文件中的 `mode` 为 `auto`，或通过 API 动态更新。

### Q: 如何防止频繁伸缩？

A: 通过调整 `cooldownPeriod` 参数设置冷却期，在冷却期内不会执行新的伸缩操作。

### Q: 预测功能如何工作？

A: 系统会收集历史积压数据，使用多种算法预测未来的积压趋势，如果预测值超过阈值，会提前触发扩容。

### Q: 支持 StatefulSet 吗？

A: 支持，将 `k8sResourceType` 设置为 `statefulset` 即可。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
