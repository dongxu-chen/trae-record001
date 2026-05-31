# Kafka 跨集群数据镜像工具

一个高性能的 Kafka 跨集群数据镜像工具，支持全量+增量同步模式，集成数据过滤、双向同步防环、Prometheus 监控。

## 功能特性

- ✅ **全量+增量同步：支持历史数据全量同步和实时增量同步
- ✅ **数据过滤：支持按 Key/Value/Topic 正则过滤
- ✅ **双向同步防环：通过消息头标记防止循环同步
- ✅ **Prometheus 监控：同步延迟、消息计数、消费Lag等指标
- ✅ **高可用：基于 Kafka Consumer Group 实现
- ✅ **SASL/SCRAM 认证支持

## 项目结构

```
kafka-mirror/
├── cmd/
│   └── main.go              # 主程序入口
├── config/
│   ├── config.go            # 配置管理
│   └── config.yaml        # 配置文件示例
├── interceptor/
│   └── interceptor.go     # 消息拦截器（过滤+防环）
├── metrics/
│   └── metrics.go         # Prometheus 监控指标
├── mirror/
│   └── mirror.go          # 核心镜像逻辑
├── mirrormaker2/
│   ├── mm2.properties       # MirrorMaker2 配置
│   └── interceptor/       # Java 自定义拦截器
├── deploy/
│   ├── docker/
│   │   └── Dockerfile   # Docker 构建文件
│   └── prometheus/
│       ├── prometheus.yml # Prometheus 配置
│       └── kafka-mirror-rules.yml # 告警规则
└── go.mod
└── README.md
```

## 快速开始

### 1. 编译

```bash
go mod download
go build -o kafka-mirror ./cmd/main.go
```

### 2. 配置

编辑 `config/config.yaml`：

```yaml
source_cluster:
  brokers: "source-kafka-1:9092"
  username: "user"
  password: "pass"
  security_protocol: "SASL_SSL"
  sasl_mechanism: "SCRAM-SHA-512"

target_cluster:
  brokers: "target-kafka-1:9092"

topics:
  - "orders"
  - "payments"

sync_mode: "full+incremental"

filter:
  key_regex: ""
  value_regex: "^\\{.*\\}$"

enable_loop_prevention: true
```

### 3. 运行

```bash
./kafka-mirror -config config/config.yaml
```

## 配置说明

### 同步模式

- `full`: 仅执行全量同步，同步完成后退出
- `incremental`: 仅执行增量实时同步
- `full+incremental`: 先全量同步历史数据，再进行增量同步

### 数据过滤

支持三种正则过滤：

- `key_regex`: 按消息 Key 过滤
- `value_regex`: 按消息 Value 过滤
- `topic_regex`: 按 Topic 名称过滤

### 双向同步防环

通过在消息头添加标记头（默认为 `x-mirror-source: mirrored`，消费者拦截器检测到该标记时跳过消息。

## 监控指标

访问 `http://localhost:9090/metrics` 查看指标：

| 指标名称 | 类型 | 说明 |
|-----------|------|------|
| `kafka_mirror_messages_consumed_total` | Counter | 消费消息总数 |
| `kafka_mirror_messages_produced_total` | Counter | 生产消息总数 |
| `kafka_mirror_messages_filtered_total` | Counter | 过滤消息数 |
| `kafka_mirror_messages_dropped_total` | Counter | 防环丢弃消息数 |
| `kafka_mirror_sync_latency_seconds` | Histogram | 同步延迟（秒） |
| `kafka_mirror_consumer_lag` | Gauge | 消费者Lag |
| `kafka_mirror_active_connections` | Gauge | 活跃连接数 |
| `kafka_mirror_last_sync_timestamp_seconds` | Gauge | 最后同步时间戳 |

## MirrorMaker2 集成

本项目同时提供了基于 Kafka MirrorMaker2 的配置和自定义拦截器。

### 使用 MirrorMaker2

1. 编译 Java 拦截器：

```bash
cd mirrormaker2/interceptor
javac -cp $KAFKA_HOME/libs/*:. *.java
jar cf kafka-mirror-interceptor.jar *.class
```

2. 启动 MirrorMaker2：

```bash
export CLASSPATH="./kafka-mirror-interceptor.jar:$CLASSPATH
$KAFKA_HOME/bin/connect-mirror-maker.sh mm2.properties
```

## Docker 部署

### 构建镜像：

```bash
docker build -f deploy/docker/Dockerfile -t kafka-mirror:latest .
```

### 运行容器：

```bash
docker run -d \
  --name kafka-mirror \
  -v $(pwd)/config.yaml:/app/config/config.yaml \
  -p 9090:9090 \
  kafka-mirror:latest
```

## 告警规则

Prometheus 告警规则配置在 `deploy/prometheus/kafka-mirror-rules.yml`：

- **KafkaMirrorHighLatency: 同步延迟过高（P99 > 5秒）
- **KafkaMirrorConsumerLagHigh: 消费者Lag过高（> 10000）
- **KafkaMirrorNoMessagesProduced: 10分钟无消息生产
- **KafkaMirrorHighDropRate: 消息丢弃率过高（> 10%）
- **KafkaMirrorNoActiveConnection: 无活跃连接

## 性能调优

### 批量大小

增加 `batch_size` 参数可提高吞吐量，但会增加延迟。

### 刷新间隔

`flush_interval_ms` 控制生产者刷新频率。

## 许可证

MIT License
