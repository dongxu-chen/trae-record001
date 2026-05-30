# 分布式链路追踪采样工具

基于 Java + OpenTelemetry + 自适应采样 + Redis + Grafana 实现的智能分布式链路追踪采样工具。

## 功能特性

### 核心功能
- **智能采样决策**：根据服务重要性和请求特征进行智能采样
- **高延迟请求全采**：超过阈值的高延迟请求100%采样
- **错误请求全采**：错误请求自动全部采样用于问题排查
- **常规请求低概率采样**：正常请求按配置的基础概率采样

### 动态调整
- **自适应采样率**：根据实际流量自动调整采样率
- **服务重要性加权**：重要服务采样率更高
- **端点级别配置**：支持针对特定端点配置采样倍率
- **Redis 集中配置**：采样配置存储在Redis，支持动态更新

### 可视化
- **Grafana 仪表盘**：采样决策分布、请求速率、延迟趋势
- **Prometheus 指标**：标准的Spring Boot Actuator指标
- **采样决策记录**：每个采样决策都附带原因说明

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     业务服务 (Spring Boot)                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  IntelligentAdaptiveSampler (OpenTelemetry Sampler) │   │
│  └───────────────────┬─────────────────────────────────┘   │
│                      │                                       │
│  ┌───────────────────▼─────────────────────────────────┐   │
│  │  AdaptiveRateAdjuster (动态采样率调整)                │   │
│  └───────────────────┬─────────────────────────────────┘   │
└──────────────────────┼──────────────────────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │         Redis              │
        │  - 采样配置存储             │
        │  - 延迟统计数据             │
        │  - 采样决策历史             │
        └──────────────┬──────────────┘
                       │
┌──────────────────────┼──────────────────────────────────────┐
│                      │                                       │
│  ┌───────────────────▼─────────────────────────────────┐   │
│  │            OTel Collector                          │   │
│  └───────────────────┬─────────────────────────────────┘   │
│                      │                                       │
│  ┌───────────────────▼─────────────────────────────────┐   │
│  │            Prometheus (指标存储)                     │   │
│  └───────────────────┬─────────────────────────────────┘   │
│                      │                                       │
│  ┌───────────────────▼─────────────────────────────────┐   │
│  │            Grafana (可视化仪表盘)                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 环境要求
- JDK 11+
- Maven 3.6+
- Docker & Docker Compose

### 步骤1: 启动基础设施

```bash
docker-compose up -d
```

启动的服务:
- Redis: localhost:6379
- OTel Collector: localhost:4317 (gRPC)
- Prometheus: localhost:9090
- Grafana: localhost:3000 (admin/admin)

### 步骤2: 编译和运行应用

```bash
mvn clean package -DskipTests
java -jar target/distributed-sampling-tool-1.0.0.jar
```

### 步骤3: 访问 Grafana

打开浏览器访问: http://localhost:3000

默认登录信息:
- 用户名: `admin`
- 密码: `admin`

## API 接口说明

### 采样管理接口 (`/api/sampling`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/sampling/stats` | 获取采样统计数据 |
| GET | `/api/sampling/rate` | 获取当前采样率 |
| POST | `/api/sampling/rate?rate=0.5` | 手动设置采样率 |
| POST | `/api/sampling/rate/adjust` | 触发采样率自适应调整 |
| GET | `/api/sampling/endpoint/{key}` | 获取端点采样配置 |
| POST | `/api/sampling/endpoint/{key}/multiplier?multiplier=2.0` | 设置端点采样倍率 |
| POST | `/api/sampling/stats/reset` | 重置统计数据 |
| POST | `/api/sampling/cache/clear` | 清除缓存 |

### 演示接口 (`/api/demo`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/demo/hello` | 基础测试接口 |
| GET | `/api/demo/fast` | 快速响应接口 (低延迟) |
| GET | `/api/demo/slow` | 慢响应接口 (高延迟，会全采) |
| GET | `/api/demo/variable?minMs=100&maxMs=1000` | 可变延迟接口 |
| GET | `/api/demo/error` | 错误接口 (错误请求全采) |
| GET | `/api/demo/nested` | 嵌套Span演示 |
| POST | `/api/demo/work` | 自定义工作负载 |

## 配置说明

### 应用配置 (`application.yml`)

```yaml
tracing:
  service:
    name: sampling-service
    importance: HIGH  # LOW/MEDIUM/HIGH/CRITICAL
  
  sampling:
    enabled: true
    default-sample-rate: 0.1           # 默认采样率 10%
    high-latency-threshold-ms: 500     # 高延迟阈值(ms)
    error-sample-rate: 1.0             # 错误请求采样率
    adaptive:
      enabled: true
      target-spans-per-second: 100     # 目标每秒采样数
      adjustment-interval-ms: 30000    # 调整间隔
      min-sample-rate: 0.01            # 最小采样率
      max-sample-rate: 1.0             # 最大采样率

redis:
  host: localhost
  port: 6379
```

### 服务重要性级别

| 级别 | 采样倍率 | 适用场景 |
|------|---------|---------|
| LOW | 0.5x | 后台任务、非核心服务 |
| MEDIUM | 1.0x | 普通业务服务 |
| HIGH | 2.0x | 核心业务服务 |
| CRITICAL | 3.0x | 支付、订单等关键服务 |

### 采样决策逻辑

```
请求到达
   │
   ├─► 父Span已采样? ──是──► 采样 (PARENT_SAMPLED)
   │
   ├─► 是错误请求? ──是──► 采样 (ERROR_REQUEST)
   │
   ├─► 预测延迟 >= 阈值? ──是──► 采样 (HIGH_LATENCY)
   │
   └─► 概率采样
         └─► 基础采样率 × 服务重要性倍率 × 端点倍率
              └─► 命中? ──是──► 采样 (PROBABILISTIC)
                    └─► 否 ──► 不采样 (NOT_SAMPLED)
```

## 核心组件说明

### 1. IntelligentAdaptiveSampler
- 实现 OpenTelemetry `Sampler` 接口
- 核心采样决策逻辑
- 统计各类采样原因的数量

### 2. AdaptiveRateAdjuster
- 定时任务：定期计算实际采样率
- 根据目标SPS自动调整基础采样率
- 移动平均算法平滑波动

### 3. RedisSamplingConfigStore
- 端点延迟统计（用于延迟预测）
- 端点采样倍率配置
- 采样决策历史记录

### 4. LatencyStatsInterceptor
- 记录每个请求的实际延迟
- 更新 Redis 中的延迟统计数据

## 采样属性说明

每个采样的 Span 会附带以下属性：

| 属性名 | 说明 |
|--------|------|
| `sampling.reason` | 采样原因 |
| `sampling.rate` | 实际采样率 |
| `service.importance` | 服务重要性级别 |
| `sampling.latency_prediction_ms` | 预测延迟(ms) |

采样原因类型:
- `PARENT_SAMPLED`: 父链路已采样
- `ERROR_REQUEST`: 错误请求
- `HIGH_LATENCY`: 高延迟请求
- `PROBABILISTIC`: 概率采样命中
- `NOT_SAMPLED`: 未采样

## 测试示例

### 1. 测试高延迟请求全采
```bash
# 多次调用慢接口
for i in {1..10}; do
  curl -s http://localhost:8080/api/demo/slow | jq '.sampled'
done
# 预期: 所有 sampled = true
```

### 2. 测试错误请求全采
```bash
curl -s http://localhost:8080/api/demo/error | jq '.sampled'
# 预期: sampled = true
```

### 3. 测试概率采样
```bash
for i in {1..100}; do
  curl -s http://localhost:8080/api/demo/fast | jq '.sampled'
done | grep true | wc -l
# 预期: 约10个true (基础采样率10%)
```

### 4. 手动调整采样率
```bash
# 设置采样率为50%
curl -X POST "http://localhost:8080/api/sampling/rate?rate=0.5"

# 设置特定端点采样倍率为2
curl -X POST "http://localhost:8080/api/sampling/endpoint/GET:/api/demo/fast/multiplier?multiplier=2.0"
```

## 监控指标

通过 `/actuator/prometheus` 暴露的关键指标:

- `http_server_requests_seconds_count`: 请求总数
- `http_server_requests_seconds_sum`: 请求总耗时
- `tomcat_sessions_active_max`: 活跃会话数
- `jvm_memory_used_bytes`: JVM内存使用

## 常见问题

### Q: Redis连接失败怎么办?
A: 检查Redis是否正常启动，配置文件中的host和port是否正确。

### Q: 为什么高延迟请求没有全采?
A: 延迟预测基于历史数据，首次调用可能预测不准，多调用几次后会准确。

### Q: 如何修改服务重要性?
A: 修改 `application.yml` 中的 `tracing.service.importance` 配置。

## 许可证

MIT License
