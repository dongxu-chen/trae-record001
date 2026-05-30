# Kafka Consumer Lag Analyzer

Kafka消费者延迟分析工具，用于监控和分析Kafka消费者组的消费延迟，识别延迟热点分区，并提供延迟归因和优化建议。

## 功能特性

- **实时Lag监控**: 按消费组、主题、分区多维度统计消费延迟
- **热点分区识别**: 基于统计学方法（均值+标准差）自动识别高延迟分区
- **延迟归因分析**: 智能识别5种延迟原因：
  - 慢处理（Slow Processing）
  - 网络延迟（Network Latency）
  - 分区不均衡（Partition Imbalance）
  - 再平衡（Rebalancing）
  - 高吞吐量压力（High Throughput）
- **优化建议**: 根据延迟原因提供针对性的优化建议
- **Prometheus指标**: 暴露14+种Prometheus指标用于监控
- **Grafana仪表盘**: 预置完整的可视化仪表盘
- **HTTP API**: 提供RESTful API查询分析结果

## 项目结构

```
kafka-lag-analyzer/
├── cmd/
│   └── analyzer/          # 主程序入口
│       └── main.go
├── internal/
│   ├── config/            # 配置管理
│   ├── kafka/             # Kafka Admin API客户端
│   ├── analyzer/          # 延迟分析引擎
│   │   ├── types.go       # 数据类型定义
│   │   ├── analyzer.go    # 核心分析逻辑
│   │   ├── attribution.go # 延迟归因
│   │   └── recommendations.go # 优化建议
│   └── metrics/           # Prometheus指标暴露
├── deployments/
│   ├── docker/            # Docker部署配置
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile
│   │   ├── prometheus.yml
│   │   └── grafana/       # Grafana自动配置
│   └── grafana/
│       └── dashboard.json # Grafana仪表盘
├── config.yaml            # 配置文件示例
├── Makefile               # 构建脚本
└── go.mod
```

## 核心指标

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `kafka_consumer_lag_partition_lag` | Gauge | 分区级延迟 |
| `kafka_consumer_lag_partition_current_offset` | Gauge | 分区当前提交偏移量 |
| `kafka_consumer_lag_partition_end_offset` | Gauge | 分区最新偏移量 |
| `kafka_consumer_lag_partition_lag_change_rate` | Gauge | 分区延迟变化率 |
| `kafka_consumer_lag_topic_total_lag` | Gauge | 主题总延迟 |
| `kafka_consumer_lag_topic_avg_lag` | Gauge | 主题平均延迟 |
| `kafka_consumer_lag_topic_max_lag` | Gauge | 主题最大延迟 |
| `kafka_consumer_lag_group_total_lag` | Gauge | 消费组总延迟 |
| `kafka_consumer_lag_group_member_count` | Gauge | 消费组成员数 |
| `kafka_consumer_lag_group_status` | Gauge | 消费组状态(0=正常,1=警告,2=严重) |
| `kafka_consumer_lag_delay_cause` | Gauge | 延迟原因及置信度 |
| `kafka_consumer_lag_hot_partition_count` | Gauge | 热点分区数量 |

## 快速开始

### 方式一：Docker Compose 一键部署

```bash
# 克隆项目后进入目录
cd kafka-lag-analyzer

# 启动完整栈（Kafka + Zookeeper + Analyzer + Prometheus + Grafana）
make docker-up

# 查看日志
make docker-logs

# 创建测试主题
make kafka-topic

# 生产测试消息
make kafka-produce

# 启动测试消费者
make kafka-consume

# 检查端点
make check-endpoints
```

访问地址：
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- 分析器API: http://localhost:8080
- Metrics端点: http://localhost:8080/metrics

### 方式二：本地运行

```bash
# 安装依赖
make deps

# 构建
make build

# 修改config.yaml配置Kafka地址
vim config.yaml

# 运行
make run
```

## HTTP API

### 健康检查
```
GET /health
```

### 获取所有消费组列表
```
GET /api/groups
```

### 获取所有消费组分析结果
```
GET /api/analysis
```

### 获取指定消费组分析结果
```
GET /api/analysis/{group}
```

### 获取分区历史数据
```
GET /api/history/{group}/{topic}/{partition}
```

### Metrics端点
```
GET /metrics
```

## 配置说明

```yaml
kafka:
  brokers:
    - "localhost:9092"
  consumer_groups: []  # 空数组表示监控所有组
  topics: []           # 空数组表示监控所有主题
  username: ""
  password: ""
  tls_enabled: false
  timeout: 30s
  scrape_interval: 15s

analyzer:
  lag_threshold: 1000              # 延迟告警阈值
  hotspot_threshold: 0.5            # 热点分区判定（标准差倍数）
  slow_processing_threshold: 100.0  # 慢处理阈值（msgs/sec）
  network_latency_threshold: 500.0  # 网络延迟阈值
  imbalance_threshold: 0.3          # 不均衡阈值（变异系数）
  history_retention: 100            # 历史数据保留点数

metrics:
  enable_prometheus: true
  path: "/metrics"

server:
  host: "0.0.0.0"
  port: 8080
```

## 延迟归因算法

### 1. 慢处理检测
- 分析历史数据，检测lag持续增长但offset增长缓慢的分区
- 计算平均消费速率，低于阈值判定为慢处理
- 置信度 = 慢处理分区数 / 总分区数

### 2. 网络延迟检测
- 计算lag时间序列的变异系数（标准差/均值）
- 高变异系数表明lag波动剧烈，可能存在网络问题
- 置信度 = 波动分区数 / 总分区数

### 3. 分区不均衡检测
- 计算各分区lag的变异系数
- 超过阈值表明分区负载不均衡
- 可能原因：消息键分布不均、消费者分配策略不合理

### 4. 再平衡检测
- 监控消费组状态，PreparingRebalance/CompletingRebalance状态触发告警
- 再平衡期间消费者会暂停消费，导致lag增加

### 5. 高吞吐量检测
- 每个分区的平均lag超过阈值
- 表明消息流入速度超过消费能力，需要扩容

## 优化建议分类

| 类别 | 说明 |
|------|------|
| **Performance** | 性能优化：处理逻辑优化、批量处理、异步处理 |
| **Scaling** | 扩容建议：增加消费者实例、增加分区数 |
| **Configuration** | 配置调优：超时参数、批量参数、分配策略 |
| **Partitioning** | 分区优化：消息键策略、分区器选择 |
| **Network** | 网络优化：连接质量、就近部署 |
| **Rebalance** | 再平衡优化：会话超时、静态成员 |
| **Architecture** | 架构优化：限流、削峰填谷 |
| **Monitoring** | 监控告警：指标监控、阈值告警 |

## Grafana仪表盘

仪表盘包含6个面板组：

1. **Overview**: 总lag统计、分布饼图、消费组状态
2. **Lag Trends**: 主题级和分区级lag趋势图
3. **Delay Analysis**: 延迟原因表、分区lag详情表
4. **Hot Partitions**: Top 10热点分区柱状图
5. **Consumer Group Info**: 成员数趋势、热点分区数趋势

## 构建与测试

```bash
# 构建
make build

# 测试
make test

# 清理
make clean

# Docker构建
make docker-build
```

## 依赖

- Go 1.22+
- Kafka 2.8+
- [IBM/sarama](https://github.com/IBM/sarama) - Kafka客户端库
- [prometheus/client_golang](https://github.com/prometheus/client_golang) - Prometheus客户端
- [spf13/viper](https://github.com/spf13/viper) - 配置管理

## 常见问题

**Q: 为什么有的分区lag显示为0？**
A: 可能是该分区没有消息，或者消费组还没有消费该分区。

**Q: 如何监控指定的消费组？**
A: 在config.yaml的`kafka.consumer_groups`中配置要监控的组名列表。

**Q: 可以监控多个Kafka集群吗？**
A: 当前版本只支持单个Kafka集群。可以启动多个analyzer实例分别监控不同集群。

**Q: 如何设置告警？**
A: 可以使用Prometheus Alertmanager配置告警规则，例如：
```yaml
groups:
- name: kafka-lag.rules
  rules:
  - alert: KafkaLagHigh
    expr: kafka_consumer_lag_group_total_lag > 10000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High consumer lag for group {{ $labels.group }}"
```

## License

MIT
