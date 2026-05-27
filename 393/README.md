# Kafka集群巡检工具

一个功能完整的Kafka集群巡检工具，支持多维度健康检查、性能瓶颈分析、优化建议和可视化报告。

## 功能特性

### 核心检查功能
- ✅ **Broker健康状态检查** - 检测Broker在线状态、Controller选举
- ✅ **ISR副本状态检查** - 检测副本不足的分区
- ✅ **消费者积压检查** - 监控消费组滞后情况
- ✅ **Topic分区分布检查** - 分析分区在Broker间的分布均衡性
- ✅ **磁盘使用率检查** - 监控Broker磁盘空间使用情况

### 指标收集
- 📊 **Kafka Admin API** - 集群元数据、消费组、分区信息
- 🔧 **JMX指标** - CPU、内存、请求延迟、消息吞吐率
- 📈 **Prometheus** - 集成Prometheus指标收集

### 分析功能
- 🔍 **性能瓶颈分析** - 自动识别CPU、内存、磁盘、网络等瓶颈
- 💡 **优化建议** - 智能生成分区分配、扩容、配置优化建议
- 🎯 **分区数推荐** - 根据消息速率计算最佳分区数

### 报告输出
- 📄 **HTML报告** - 美观的可视化报告
- 📋 **Markdown报告** - 适合文档归档
- 📝 **JSON报告** - 便于程序解析和二次开发

### 可视化
- 📊 **Grafana仪表板** - 实时监控Kafka集群状态
- 🐳 **Docker一键部署** - 快速搭建监控环境

## 快速开始

### 环境要求
- Python 3.8+
- Kafka 2.0+
- JMX Exporter (可选，用于JMX指标收集)
- Prometheus (可选，用于指标存储)
- Grafana (可选，用于可视化)

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置文件

编辑 `config.yaml` 配置文件：

```yaml
kafka:
  bootstrap_servers: "localhost:9092,localhost:9093,localhost:9094"
  security_protocol: "PLAINTEXT"

jmx:
  enabled: true
  jmx_hosts:
    - "localhost:9999"
    - "localhost:9998"
    - "localhost:9997"

prometheus:
  enabled: true
  url: "http://localhost:9090"

checks:
  broker:
    offline_threshold: 1
  isr:
    under_replicated_threshold: 0
  lag:
    lag_warning_threshold: 1000
    lag_critical_threshold: 10000
  disk:
    disk_warning_threshold: 70
    disk_critical_threshold: 85

output:
  report_dir: "./reports"
  format: ["html", "json", "markdown"]
```

### 使用方法

#### 1. 执行完整巡检
```bash
python main.py
```

#### 2. 指定配置文件
```bash
python main.py --config /path/to/config.yaml
```

#### 3. 仅输出特定格式报告
```bash
python main.py --format html
python main.py --format json
python main.py --format markdown
```

#### 4. 跳过部分检查
```bash
# 跳过JMX收集
python main.py --skip-jmx

# 跳过Prometheus收集
python main.py --skip-prometheus

# 跳过性能分析
python main.py --skip-analysis
```

#### 5. 配置验证（Dry Run）
```bash
python main.py --dry-run
```

#### 6. 分区数推荐
```bash
# 根据预期消息速率推荐分区数
python main.py --suggest-partition 10000
```

#### 7. 查看帮助
```bash
python main.py --help
```

## Docker部署监控栈

使用docker-compose快速搭建Kafka监控环境：

```bash
# 启动完整监控栈（Kafka集群 + Prometheus + Grafana）
docker-compose up -d

# 访问Grafana
# 浏览器打开: http://localhost:3000
# 用户名: admin
# 密码: admin
```

### Docker服务说明

| 服务 | 端口 | 说明 |
|------|------|------|
| ZooKeeper | 2181 | Kafka依赖的协调服务 |
| Kafka Broker 1 | 9092 / 9997 | Kafka Broker节点1 |
| Kafka Broker 2 | 9093 / 9998 | Kafka Broker节点2 |
| Kafka Broker 3 | 9094 / 9999 | Kafka Broker节点3 |
| Prometheus | 9090 | 时序数据库 |
| Grafana | 3000 | 可视化仪表板 |

## 项目结构

```
.
├── main.py                          # 主入口程序
├── config.yaml                      # 配置文件
├── requirements.txt                 # Python依赖
├── docker-compose.yml               # Docker部署配置
├── README.md                        # 项目说明
├── kafka_inspector/                 # 核心模块
│   ├── __init__.py
│   ├── kafka_admin_check.py         # Kafka Admin API检查
│   ├── jmx_collector.py             # JMX指标收集
│   ├── prometheus_collector.py      # Prometheus指标收集
│   ├── bottleneck_analyzer.py       # 性能瓶颈分析
│   ├── partition_advisor.py         # 分区分配建议
│   └── report_generator.py          # 报告生成
├── prometheus/                      # Prometheus配置
│   └── prometheus.yml
├── grafana/                         # Grafana配置
│   ├── dashboards/
│   │   └── kafka-overview.json      # Kafka概览仪表板
│   └── provisioning/
│       ├── datasources/
│       │   └── prometheus.yml
│       └── dashboards/
│           └── kafka.yml
├── reports/                         # 报告输出目录
└── logs/                            # 日志目录
```

## 报告内容说明

### HTML报告
包含以下章节：
1. **集群概览** - 整体健康状态评分
2. **Broker健康状态** - Broker列表、在线状态
3. **ISR副本状态** - 副本不足分区详情
4. **消费者积压** - Top 10积压消费组
5. **性能瓶颈分析** - 检测到的瓶颈及影响
6. **优化建议** - 具体的优化措施

### 性能瓶颈检测维度
- CPU使用率过高
- 内存使用率过高
- 磁盘空间不足
- 请求处理线程不足
- 生产/消费请求延迟过高
- 副本不足分区
- 消费组积压
- 分区分布不均
- Broker离线

### 优化建议类型
- 分区重分配方案
- Broker扩容建议
- Topic配置优化
- 消费组优化
- 资源配置调整

## 核心模块说明

### KafkaAdminChecker
使用kafka-python库的Admin API进行集群元数据检查：
- `check_broker_health()` - 检查Broker健康状态
- `check_isr_status()` - 检查ISR副本状态
- `check_consumer_lag()` - 检查消费者积压
- `check_topic_partitions()` - 检查分区分布

### JMXCollector
通过JMX收集Broker运行时指标：
- CPU、内存使用率
- 消息流入/流出速率
- 请求处理延迟（P99）
- 副本不足分区数
- 请求处理线程空闲率

### PrometheusCollector
通过Prometheus HTTP API查询指标：
- Broker级别指标聚合
- 消费组积压查询
- Topic级别的消息速率
- 磁盘使用情况估算

### BottleneckAnalyzer
多维度性能瓶颈分析：
- 基于阈值的异常检测
- 瓶颈影响评估
- 严重程度分级（WARNING/CRITICAL）

### PartitionAdvisor
智能分区分配建议：
- 分区分布均衡性分析
- 分区数计算推荐
- 重分配方案生成
- 扩容建议

## 阈值配置参考

| 指标 | 警告阈值 | 严重阈值 | 说明 |
|------|----------|----------|------|
| CPU使用率 | 70% | 85% | 高于此值可能影响性能 |
| 内存使用率 | 70% | 85% | JVM堆内存使用率 |
| 磁盘使用率 | 70% | 85% | 磁盘空间使用百分比 |
| 消费积压 | 1000 | 10000 | 消费组消息滞后数 |
| 生产延迟P99 | 100ms | 500ms | 生产请求响应时间 |
| 消费延迟P99 | 200ms | 1000ms | 消费请求响应时间 |
| 副本不足分区 | 1 | 10 | ISR收缩的分区数 |

## 常见问题

### Q: 如何启用SASL认证？
A: 在config.yaml中配置：
```yaml
kafka:
  security_protocol: "SASL_PLAINTEXT"
  sasl_mechanism: "PLAIN"
  sasl_username: "your_username"
  sasl_password: "your_password"
```

### Q: JMX连接失败怎么办？
A: 确保：
1. Kafka Broker已启用JMX
2. 防火墙已开放JMX端口
3. 可以使用`--skip-jmx`参数跳过JMX检查

### Q: 如何定期执行巡检？
A: 使用cron定时任务：
```bash
# 每天凌晨2点执行巡检
0 2 * * * /usr/bin/python3 /path/to/main.py >> /var/log/kafka_inspector.log 2>&1
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
