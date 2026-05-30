# Nginx 日志实时分析管道

基于 Flink + Kafka + Redis + ClickHouse + Grafana 构建的 Nginx 日志实时分析系统。

## 系统架构

```
Nginx Logs → Filebeat → Kafka → Flink → Redis → Grafana
                                 ↘
                                   ClickHouse
```

## 功能特性

### 核心指标计算
- **实时 QPS 计算**：按接口、状态码、IP、方法、主机多维度统计 QPS
- **错误率监控**：实时计算错误请求占比（4xx/5xx）
- **高精度响应时间分析**：基于 T-Digest 算法的 P50/P95/P99/P999 分位数延迟计算
- **完整统计信息**：Min、Max、Avg、StdDev、Variance 全量统计字段

### 智能异常检测（3-Sigma 动态阈值）
- **自适应阈值**：基于历史数据自动计算动态告警阈值（均值 ± 3×标准差）
- **多维度异常检测**：错误率异常、延迟异常、QPS 突增/突降
- **静态兜底机制**：历史数据不足时自动降级为固定阈值
- **智能告警分级**：根据偏差程度自动分级（INFO/WARNING/CRITICAL）

### 可控维度聚合
- **预定义维度组合**：避免维度爆炸，支持 9 种预定义维度
- **API 白名单过滤**：仅监控关注的接口，减少存储开销
- **灵活维度开关**：通过 Builder 模式灵活启用/禁用各类维度

### 数据持久化与可视化
- **Redis 实时缓存**：带 TTL 的实时指标存储，支持 P50/P95/P99/P999
- **ClickHouse 历史存储**：24 字段宽表，批量写入 + TTL 自动清理
- **动态阈值可视化**：Redis 存储当前阈值，支持 Grafana 展示
- **Grafana 实时仪表盘**：完整的监控面板

## 项目结构

```
├── src/main/java/com/loganalytics/
│   ├── NginxLogAnalysisJob.java          # Flink 主作业入口
│   ├── config/
│   │   └── FlinkConfig.java              # 配置类（支持T-Digest、3-sigma、维度配置）
│   ├── aggregate/
│   │   ├── MetricsAccumulator.java       # T-Digest累加器，增量聚合
│   │   └── MetricsAggregateFunction.java # Flink增量聚合函数
│   ├── model/
│   │   ├── NginxLogEvent.java            # 日志事件模型
│   │   ├── MetricsResult.java            # 指标结果（扩展24字段）
│   │   └── AlertEvent.java               # 告警事件
│   ├── parser/
│   │   └── NginxLogParser.java           # Nginx 日志解析器
│   ├── source/
│   │   └── KafkaSourceFactory.java       # Kafka 源工厂
│   ├── functions/
│   │   ├── DimensionExtractor.java       # 预定义维度提取器（Builder模式）
│   │   ├── MetricsResultWindowFunction.java # 窗口处理+历史统计
│   │   └── ThreeSigmaAnomalyDetector.java   # 3-sigma动态阈值检测器
│   └── sink/
│       ├── RedisSink.java                # Redis Sink（支持P50/P95/P99/P999）
│       ├── ClickHouseSink.java           # ClickHouse Sink（24字段宽表）
│       └── AlertSink.java                # 告警 Sink
├── src/test/java/com/loganalytics/
│   ├── aggregate/
│   │   └── MetricsAccumulatorTest.java   # T-Digest单元测试
│   ├── functions/
│   │   ├── ThreeSigmaAnomalyDetectorTest.java # 3-sigma单元测试
│   │   └── DimensionExtractorTest.java   # 预定义维度单元测试
│   └── parser/
│       └── NginxLogParserTest.java       # 日志解析测试
├── deploy/
│   ├── clickhouse/
│   │   └── init-db.sql                   # ClickHouse 初始化脚本（24字段）
│   ├── grafana/
│   │   ├── datasources/                  # Grafana 数据源
│   │   └── dashboards/                   # Grafana 仪表盘
│   └── filebeat/
│       └── filebeat.yml                  # Filebeat 配置
├── docker-compose.yml                     # Docker 部署配置
└── pom.xml                                # Maven 配置
```

## 快速开始

### 1. 环境要求

- Docker & Docker Compose
- Java 11+
- Maven 3.6+

### 2. 编译项目

```bash
mvn clean package -DskipTests
```

### 3. 启动基础设施

```bash
docker-compose up -d
```

启动的服务：
- Zookeeper: `localhost:2181`
- Kafka: `localhost:9092`
- Kafka UI: `http://localhost:8080`
- Redis: `localhost:6379`
- ClickHouse: `localhost:8123`
- Grafana: `http://localhost:3000` (admin/admin)
- Flink JobManager: `http://localhost:8081`

### 4. 提交 Flink 作业

```bash
# 方式1: 通过 Flink UI 提交
# 访问 http://localhost:8081，上传 target/nginx-log-analyzer-1.0.0.jar

# 方式2: 通过命令行提交
./bin/flink run target/nginx-log-analyzer-1.0.0.jar
```

### 5. 查看仪表盘

访问 Grafana: `http://localhost:3000` (用户名/密码: admin/admin)

内置仪表盘包含：
- 整体 QPS 趋势图
- 错误率趋势图
- 响应时间分位数（P50/P95/P99/P999）
- 动态阈值展示
- 请求量统计面板
- Top API 接口排行
- 状态码分布

## Nginx 日志格式配置

在 `nginx.conf` 中配置日志格式：

```nginx
log_format extended '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent" '
                    '$request_time $upstream_response_time '
                    '"$upstream_status" "$host"';

access_log /var/log/nginx/access.log extended;
```

## 配置项说明

### 核心配置（环境变量）

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `KAFKA_BROKERS` | `localhost:9092` | Kafka 地址 |
| `KAFKA_TOPIC` | `nginx-logs` | Kafka 主题 |
| `KAFKA_GROUP_ID` | `nginx-log-analyzer` | 消费者组 ID |
| `REDIS_HOST` | `localhost` | Redis 主机 |
| `REDIS_PORT` | `6379` | Redis 端口 |
| `CLICKHOUSE_URL` | `jdbc:clickhouse://localhost:8123/default` | ClickHouse URL |
| `WINDOW_SIZE_SECONDS` | `60` | 窗口大小（秒） |
| `SLIDE_SIZE_SECONDS` | `10` | 滑动间隔（秒） |

### T-Digest 分位数配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `TDIGEST_COMPRESSION` | `100.0` | T-Digest压缩因子，值越大精度越高但内存占用越大 |

### 3-Sigma 动态阈值配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SIGMA_MULTIPLIER` | `3.0` | 标准差倍数，默认3σ覆盖99.73%数据 |
| `HISTORY_WINDOW_SIZE` | `30` | 历史窗口大小，用于计算均值和标准差（窗口数） |

### 静态兜底阈值（历史数据不足时使用）

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `ERROR_RATE_THRESHOLD` | `5.0` | 错误率告警阈值（%） |
| `LATENCY_P99_THRESHOLD` | `1000.0` | P99 延迟告警阈值（ms） |
| `QPS_ALERT_THRESHOLD` | `10000` | QPS 告警阈值 |

### 维度聚合配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `ENABLED_DIMENSIONS` | `all,api,status,api_status,api_method,method,host` | 启用的维度（逗号分隔） |
| `ENABLE_API_WHITELIST` | `false` | 是否启用API白名单过滤 |
| `API_WHITELIST` | `` | API白名单（逗号分隔，如`/api/v1/users,/api/v1/products`） |

## 支持的聚合维度（预定义组合）

### 基础维度

| 维度 | 说明 | 示例 | 默认启用 |
|------|------|------|----------|
| `all` | 全局统计 | `all:total` | ✅ |
| `api` | 按接口路径 | `api:/api/v1/users` | ✅ |
| `status` | 按状态码 | `status:200` | ✅ |
| `method` | 按 HTTP 方法 | `method:GET` | ✅ |
| `host` | 按主机名 | `host:api.example.com` | ✅ |
| `ip` | 按客户端 IP | `ip:192.168.1.100` | ❌（默认禁用，高基数） |

### 组合维度（避免维度爆炸）

| 维度 | 说明 | 示例 | 默认启用 |
|------|------|------|----------|
| `api_status` | 按接口+状态码组合 | `api_status:/api/v1/users|200` | ✅ |
| `api_method` | 按接口+方法组合 | `api_method:/api/v1/users|GET` | ✅ |
| `status_method` | 按状态码+方法组合 | `status_method:200|GET` | ❌ |

> **维度控制**：通过 `ENABLED_DIMENSIONS` 环境变量灵活控制启用的维度，避免高基数维度（如 IP）导致的存储爆炸。
>
> **API 白名单**：启用 `ENABLE_API_WHITELIST=true` 后，仅监控 `API_WHITELIST` 中配置的接口，进一步降低存储开销。

## 告警规则（3-Sigma 动态阈值）

### 核心原理
基于统计学 3-Sigma 原则，覆盖 99.73% 的数据点，自动计算动态阈值：
- 上阈值 = 历史均值 + 3 × 历史标准差
- 下阈值 = 历史均值 - 3 × 历史标准差

### 告警类型

#### 1. 错误率异常（ERROR_RATE_ANOMALY）
- **触发条件**：当前错误率 > 均值 + 3×标准差
- **说明**：错误率异常升高

#### 2. 延迟异常（LATENCY_ANOMALY）
- **触发条件**：当前 P99 延迟 > 均值 + 3×标准差
- **说明**：接口响应时间异常升高

#### 3. QPS 突增（QPS_SPIKE）
- **触发条件**：当前 QPS > 均值 + 3×标准差
- **说明**：流量异常突增

#### 4. QPS 突降（QPS_DROP）
- **触发条件**：当前 QPS < 均值 - 3×标准差
- **说明**：流量异常下降

### 智能告警分级（根据偏差程度）

| 级别 | 触发条件 |
|------|----------|
| **INFO** | 偏差 ≥ 3σ（正常波动边界） |
| **WARNING** | 偏差 ≥ 4σ（显著异常） |
| **CRITICAL** | 偏差 ≥ 5σ（严重异常） |

### 静态兜底机制（历史数据不足时）

当历史窗口数据不足（默认需要至少 10 个窗口数据），自动降级为固定阈值告警：
- 错误率 > 5%
- P99 延迟 > 1000ms
- QPS > 10000 或 < 100（突增/突降）

### 告警示例

假设某接口历史数据：
- 历史错误率均值：2%，标准差：1%
→ 动态阈值：2% + 3×1% = 5%
- 当前错误率：10%
→ 偏差 = (10% - 2%) / 1% = 8σ
→ 触发 **CRITICAL** 级别告警

## 技术改进说明

### T-Digest 分位数算法
- **原方案**：使用 `List<Double>` 收集所有延迟值，排序后计算分位数
- **问题**：内存占用 O(n)，大数据量下性能差
- **新方案**：使用 T-Digest 算法，压缩因子 100
- **优势**：内存占用 O(1)，P99/P999 精度显著提升，支持高效合并

### 3-Sigma 动态阈值
- **原方案**：固定阈值（错误率>5%，P99>1000ms，QPS>10000）
- **问题**：无法适应不同接口的正常波动，误报率高
- **新方案**：基于历史数据自动计算动态阈值
- **优势**：自适应业务波动，降低误报率，支持 QPS 突降检测

### 预定义维度组合
- **原方案**：每个日志生成 6 个维度键，可能产生维度爆炸
- **问题**：高基数维度（如 IP、动态路径）导致存储激增
- **新方案**：预定义 9 种维度组合，支持 API 白名单过滤
- **优势**：存储量可控，可灵活开关，支持只监控核心接口

## 运行测试

```bash
mvn test
```

## 性能优化建议

1. **增加 Flink 并行度**：根据数据量调整 TaskManager 数量和 Slot 数
2. **调整窗口大小**：平衡实时性和计算开销
3. **开启 RocksDB 状态后端**：处理大状态场景
4. **配置检查点**：确保 Exactly-Once 语义
5. **调整 T-Digest 压缩因子**：在精度和内存之间取得平衡
6. **合理配置维度**：关闭不需要的维度，启用 API 白名单

## 常见问题

### 1. Flink 作业无法连接 Kafka
确保 Kafka 容器已正常启动，检查 `KAFKA_ADVERTISED_LISTENERS` 配置。

### 2. ClickHouse 写入失败
检查 ClickHouse 容器日志，确认表结构已正确创建（24 字段）。

### 3. Grafana 无数据
检查 ClickHouse 数据源配置是否正确，确认 Flink 作业正在运行。

### 4. 告警误报率高
- 调整 `SIGMA_MULTIPLIER`（如改为 4.0 提高阈值）
- 增加 `HISTORY_WINDOW_SIZE`（如改为 60 增加历史数据量）
- 检查维度配置是否合理

### 5. 内存占用过高
- 降低 `TDIGEST_COMPRESSION`（如改为 50）
- 关闭不需要的维度
- 启用 API 白名单过滤

### 6. 慢请求误报过多
- 提高 `SLOW_REQUEST_THRESHOLD_MS`（如改为 2000）
- 降低 `UPSTREAM_RATIO_THRESHOLD`（如改为 0.5，更严格判定上游慢）
- 增大 `SLOW_REQUEST_PROFILE_SIZE`（如改为 200，更平滑的动态阈值）

### 7. 流量预测不准确
- 增大 `FORECAST_HISTORY_SIZE`（如改为 120，更多历史数据）
- 检查数据是否稳定（波动过大的数据预测效果差）
- 流量有明显周期性时，线性回归效果有限，可考虑结合移动平均

### 8. 自定义指标表达式错误
- 检查变量名是否正确（支持 snake_case 和 camelCase）
- 确保表达式语法正确（括号匹配、运算符正确）
- 查看日志中的 "Failed to evaluate custom metric" 警告

## 许可证

MIT License
