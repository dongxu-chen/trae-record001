# 微服务调用链追踪染色工具

基于 Java + OpenTelemetry + 线程上下文传递 + 消息头注入 + Jaeger 实现的微服务调用链追踪染色工具。

## 功能特性

### 1. 核心追踪能力
- **请求入口染色标识注入**：在网关/服务入口自动注入 traceId、spanId、染色标识
- **跨服务传递**：通过 HTTP Header 自动向下游服务传递追踪上下文
- **端到端调用链追踪**：基于 OpenTelemetry 实现完整的调用链可视化
- **Jaeger 集成**：支持将追踪数据导出到 Jaeger 进行可视化分析

### 2. 异步调用支持
- **线程池上下文传递**：自定义 `TraceableThreadPoolTaskExecutor` 自动捕获和传递上下文
- **@Async 注解支持**：AOP 切面自动处理 `@Async` 方法的上下文传递
- **TransmittableThreadLocal**：支持线程池场景下的上下文透传

### 3. 消息队列支持
- **Kafka**：生产者/消费者拦截器自动注入和恢复追踪上下文
- **RabbitMQ**：消息后置处理器 + AOP 切面实现上下文传递
- **消息头注入**：自动将追踪信息注入消息头

### 4. 采样率控制
- **比例采样**：支持配置全局采样率（0.0 - 1.0）
- **染色采样**：支持配置染色请求的采样率
- **条件染色**：
  - 按用户 ID 染色（白名单机制）
  - 按业务类型染色
  - 按请求路径染色
  - 按 HTTP Header 染色标记染色

### 5. 多维度上下文绑定
- **ThreadLocal**：线程本地变量存储
- **MDC**：SLF4J MDC 日志上下文绑定
- **OpenTelemetry Context**：与 OpenTelemetry 原生上下文集成

### 6. 业务标签注入（新增）
- **主业务标签**：`X-Staining-Biz-Tag` 主业务标识，支持版本号 `X-Staining-Biz-Tag-Version`
- **标准业务标签**：自动识别 8 种标准业务 Header（OrderId、ProductId、MerchantId 等）
- **自定义业务标签**：支持 `X-Biz-*` 和 `X-Custom-*` 前缀的自定义标签
- **标签聚合分析**：按业务标签维度统计请求量、成功率、错误率、P95 延迟

### 7. 跨云调用链聚合（新增）
- **云环境标识**：自动注入云提供商、区域、可用区、账号、服务名等信息
- **跨云追踪ID**：生成全局唯一 `X-Cross-Cloud-Trace-Id`，多云环境统一追踪
- **原始追踪ID保留**：记录 `X-Origin-Trace-Id`，保留各云原生追踪ID
- **多云调用链可视化**：按跨云追踪ID聚合，展示跨云调用拓扑和耗时分析

### 8. 染色分析平台（新增）
- **数据采集**：自动采集所有染色请求的完整生命周期数据
- **多维度聚合分析**：支持按颜色、业务标签、业务类型、用户、云环境等维度聚合
- **Top N 慢请求**：自动识别慢请求，支持按响应时间排序
- **错误请求追踪**：集中展示所有错误请求及其错误信息
- **染色请求概览**：总请求数、跨云请求数、成功率、平均延迟等核心指标
- **Trace 详情查询**：根据 Trace ID 查询完整的调用链和分析数据
- **跨云调用链查询**：根据跨云追踪 ID 查询多云环境完整调用路径

## 项目结构

```
trace-staining/
├── src/main/java/com/tracing/staining/
│   ├── TraceStainingApplication.java          # 启动类
│   ├── aspect/
│   │   ├── RabbitTraceAspect.java             # RabbitMQ 消费者切面
│   │   └── TraceAsyncAspect.java              # @Async 异步方法切面
│   ├── config/
│   │   ├── AsyncConfig.java                   # 异步线程池配置
│   │   ├── KafkaConfig.java                   # Kafka 配置
│   │   ├── OpenTelemetryConfig.java           # OpenTelemetry + Jaeger 配置
│   │   ├── RabbitMqConfig.java                # RabbitMQ 配置
│   │   └── WebMvcConfig.java                  # Web MVC 拦截器配置
│   ├── constant/
│   │   └── TraceConstant.java                 # 追踪常量定义
│   ├── context/
│   │   ├── StainingContext.java               # 染色上下文对象
│   │   ├── TraceContextHolder.java            # 上下文管理器
│   │   └── TransmittableThreadLocal.java      # 可传递线程本地变量
│   ├── interceptor/
│   │   ├── TraceEntryInterceptor.java         # HTTP 入口拦截器
│   │   └── TraceRestTemplateInterceptor.java  # RestTemplate 出口拦截器
│   ├── mq/
│   │   ├── kafka/
│   │   │   ├── KafkaTraceConsumerInterceptor.java
│   │   │   └── KafkaTraceProducerInterceptor.java
│   │   └── rabbit/
│   │       └── RabbitTraceMessagePostProcessor.java
│   ├── sampler/
│   │   ├── DefaultTraceSampler.java           # 默认采样器实现
│   │   └── TraceSampler.java                  # 采样器接口
│   ├── service/
│   │   └── DemoService.java                   # 示例服务
│   └── controller/
│       └── TraceDemoController.java           # 演示控制器
├── src/main/resources/
│   └── application.yml                        # 应用配置
└── pom.xml                                    # Maven 配置
```

## 快速开始

### 1. 环境要求
- JDK 17+
- Maven 3.6+
- Jaeger (可选，用于链路可视化)
- Kafka (可选，用于消息队列演示)
- RabbitMQ (可选，用于消息队列演示)

### 2. 启动 Jaeger

```bash
docker run -d --name jaeger \
  -e COLLECTOR_ZIPKIN_HOST_PORT=:9411 \
  -p 16686:16686 \
  -p 4317:4317 \
  -p 4318:4318 \
  -p 14250:14250 \
  jaegertracing/all-in-one:latest
```

访问 Jaeger UI: http://localhost:16686

### 3. 编译项目

```bash
mvn clean package -DskipTests
```

### 4. 启动应用

```bash
java -jar target/trace-staining-1.0.0.jar
```

## 使用方式

### 1. HTTP Header 染色

通过在请求头中添加染色标识来标记特定请求：

```bash
curl -X GET http://localhost:8080/api/trace/context \
  -H "X-Staining-Flag: true" \
  -H "X-Staining-Color: RED" \
  -H "X-Staining-User-Id: user001" \
  -H "X-Staining-Biz-Type: ORDER"
```

### 2. API 接口说明

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/trace/context` | GET | 获取当前请求的追踪上下文 |
| `/api/trace/stained` | GET | 检查当前请求是否被染色 |
| `/api/trace/async` | GET | 异步调用演示 (@Async) |
| `/api/trace/threadpool` | GET | 线程池调用演示 |
| `/api/trace/downstream` | GET | 跨服务调用演示 |
| `/api/trace/kafka` | POST | Kafka 消息发送演示 |
| `/api/trace/rabbit` | POST | RabbitMQ 消息发送演示 |
| `/api/trace/nested` | GET | 嵌套调用演示 |
| `/api/trace/manual` | POST | 手动染色演示 |
| `/api/trace/full-demo` | GET | 完整功能演示 |

### 3. 核心 HTTP Header

| Header 名称 | 说明 | 示例 |
|------------|------|------|
| `traceId` | 全局追踪 ID | `550e8400e29b41d4a716446655440000` |
| `spanId` | 当前跨度 ID | `a716446655440000` |
| `X-Staining-Flag` | 染色标记 | `true` / `false` |
| `X-Staining-Color` | 染色颜色 | `RED`, `BLUE`, `GREEN` |
| `X-Staining-User-Id` | 用户 ID | `user001` |
| `X-Staining-Biz-Type` | 业务类型 | `ORDER`, `PAYMENT` |
| `X-Sampled` | 采样标记 | `true` / `false` |
| `X-Request-Id` | 请求 ID | UUID |

## 配置说明

### 核心配置项

```yaml
tracing:
  sample:
    rate: 1.0                    # 全局采样率 (0.0 - 1.0)
  staining:
    rate: 0.5                    # 自动染色比例
    user-ids: user001,user002    # 按用户ID染色白名单
    biz-types: ORDER,PAYMENT     # 按业务类型染色白名单
    paths: /api/trace/full-demo  # 按路径染色白名单
  jaeger:
    enabled: true                # 是否启用 Jaeger 导出
    endpoint: http://localhost:14250  # Jaeger gRPC 端点
```

### 日志格式配置

日志模式已配置为自动输出追踪信息：

```
%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level %logger{36} - traceId=%X{traceId} spanId=%X{spanId} userId=%X{X-Staining-User-Id} - %msg%n
```

## 高级特性

### 1. 上下文快照传递 (ContextSnapshot)

针对异步场景，实现了完整的上下文快照机制，确保异步执行时上下文完整恢复：

```java
// 1. 捕获当前线程完整上下文快照
ContextSnapshot snapshot = ContextSnapshot.capture();

// 2. 异步执行时恢复上下文
CompletableFuture.supplyAsync(() -> {
    Scope otelScope = null;
    try {
        otelScope = snapshot.setThreadContext();  // 恢复所有上下文
        // 执行业务逻辑 - 上下文已完整恢复
        return TraceContextHolder.getContext();
    } finally {
        snapshot.clearThreadContext(otelScope);   // 清理上下文
    }
}, executor);

// 3. 便捷包装方式
Runnable tracedTask = ContextSnapshot.wrapWithSnapshot(originalTask);
```

**快照内容**：
- `StainingContext` - 业务染色上下文
- `MDC` - 日志上下文
- `OpenTelemetry Context` - 追踪上下文
- `TransmittableThreadLocal` - 线程池传递变量

### 2. Header独立消息注入

所有消息队列的追踪信息**完全不侵入业务消息体**，仅在Header层传递：

**设计原则**：
- 所有追踪信息存储于消息 Header，业务消息体保持纯净
- 使用 `TraceHeaderAccessor` 统一操作 Header
- 支持二进制（Kafka）和字符串（RabbitMQ）两种Header格式
- 消费者仅提取 Trace Header，不修改消息体

```java
// Kafka 生产者 - 仅操作Header
Map<String, String> traceHeaders = TraceHeaderAccessor.toStringHeaders(childContext);
for (Map.Entry<String, String> entry : traceHeaders.entrySet()) {
    addHeaderIfAbsent(headers, entry.getKey(), entry.getValue());
}
log.debug("Kafka message headers injected (message body untouched)");

// RabbitMQ 消费者 - 仅提取Header
Map<String, Object> headers = message.getMessageProperties().getHeaders();
StainingContext context = TraceHeaderAccessor.extractFromHeaders(headers, 
    (h, key) -> (String) h.get(key));
```

**侵入对比**：
| 方式 | 业务消息体 | 追踪Header |
|------|-----------|------------|
| 旧方案 | ✅ 被修改，注入追踪字段 | ✅ 有 |
| 新方案 | ❌ 完全不触碰 | ✅ 仅Header层 |

### 3. 自适应采样

基于 QPS 和并发数动态调整采样率，在系统负载和追踪覆盖率之间取得平衡：

**核心算法**：
```
if (QPS > 高阈值 OR 并发 > 高阈值):
    采样率 = max(最小采样率, 当前采样率 * 0.8)  # 降采样保护系统
elif (QPS < 低阈值 AND 并发 < 低阈值):
    采样率 = min(最大采样率, 当前采样率 * 1.2)  # 升采样提升覆盖率
else:
    采样率 = 基准采样率                          # 正常负载
```

**关键特性**：
- 染色请求始终 100% 采样，不受自适应影响
- 调整间隔可配置（默认5秒），避免抖动
- 响应头自动返回当前采样状态：`X-Current-Qps`、`X-Current-Sample-Rate`
- 提供监控接口查看实时状态

**采样器状态监控**：
```bash
curl http://localhost:8080/api/trace/sampler-status
```

响应示例：
```json
{
  "currentSampleRate": "1.0000",
  "currentStainingRate": "0.5000",
  "currentQps": 45,
  "currentConcurrency": 12,
  "loadStatus": "NORMAL_LOAD - Sample rate at base",
  "qpsHighThreshold": 1000,
  "qpsLowThreshold": 100
}
```

### 4. 业务标签注入 (BizTag)

通过业务标签机制，将业务维度信息与追踪上下文深度绑定，支持多维度业务分析：

**核心能力**：
- **主业务标签**：`X-Staining-Biz-Tag` 承载核心业务标识（如活动ID、批次号）
- **标签版本**：`X-Staining-Biz-Tag-Version` 支持标签迭代，便于A/B测试和灰度分析
- **标准业务标签**：自动识别 8 种标准业务 Header
  - `X-Biz-Order-Id` - 订单ID
  - `X-Biz-Product-Id` - 商品ID
  - `X-Biz-Merchant-Id` - 商户ID
  - `X-Biz-Store-Id` - 门店ID
  - `X-Biz-Channel` - 渠道（APP/小程序/H5等）
  - `X-Biz-Source` - 流量来源
  - `X-Biz-Version` - 业务版本
  - `X-Biz-Env` - 环境标识
- **自定义业务标签**：支持 `X-Biz-*` 和 `X-Custom-*` 前缀的自定义标签

**代码示例**：
```java
// 1. 通过HTTP Header注入（推荐）
curl -X GET http://localhost:8080/api/trace/context \
  -H "X-Staining-Flag: true" \
  -H "X-Staining-Biz-Tag: PROMO_2024_SPRING" \
  -H "X-Staining-Biz-Tag-Version: v2.0" \
  -H "X-Biz-Order-Id: 123456789" \
  -H "X-Biz-Channel: APP" \
  -H "X-Custom-Campaign: NEW_YEAR_2024"

// 2. 代码中手动注入
StainingContext context = TraceContextHolder.getContext();
context.setBizTag("PROMO_2024_SPRING");
context.addBizTag("X-Biz-Order-Id", "123456789");
context.addBizTag("X-Custom-Campaign", "NEW_YEAR_2024");
```

**使用场景**：
- 📊 按业务活动维度统计调用链性能
- 🎯 A/B测试分组追踪和效果分析
- 🏪 多商户/多门店业务数据隔离分析
- 📱 按渠道分析用户行为和系统表现

### 5. 跨云调用链聚合 (Cross-Cloud Tracing)

实现多云环境下的统一追踪，打破云厂商边界，实现真正的端到端全局追踪：

**核心机制**：
- **全局跨云追踪ID**：生成 `X-Cross-Cloud-Trace-Id` 作为多云环境统一标识
- **原始追踪ID保留**：`X-Origin-Trace-Id` 保留各云环境原生 traceId
- **云环境元数据**：自动注入云厂商、区域、可用区、账号、服务名等信息
- **调用链重组**：按跨云追踪ID聚合，重组多云环境完整调用路径

**调用链传递流程**：
```
[阿里云 - 华东1] 服务A → [AWS - us-east-1] 服务B → [腾讯云 - 广州] 服务C
       ↓                          ↓                          ↓
traceId: aliyun-xxx        traceId: aws-xxx          traceId: tencent-xxx
originTraceId: aliyun-xxx  originTraceId: aliyun-xxx  originTraceId: aliyun-xxx
crossCloudTraceId: global-abc123 (全局统一)
```

**配置示例**：
```yaml
tracing:
  cloud:
    provider: aliyun                  # 当前云环境
    region: cn-hangzhou               # 区域
    availability-zone: cn-hangzhou-h  # 可用区
    account-id: 1234567890123456      # 账号ID
    service-name: order-service       # 服务名称
    cross-cloud:
      enabled: true                    # 启用跨云追踪
      trace-id-prefix: global          # 跨云ID前缀
```

**跨云调用链查询**：
```bash
# 查询跨云调用链
curl http://localhost:8080/api/trace/analysis/crosscloud/global-abc123def456

# 响应包含：
# - 总调用跳数
# - 经过的云厂商和区域
# - 每跳的服务名和耗时
# - 总端到端耗时
# - 完整的调用拓扑
```

### 6. 染色分析平台 (Staining Analysis Platform)

提供完整的染色请求聚合分析能力，支持从多个维度洞察系统行为：

**数据采集**：
- 自动采集所有染色请求的完整生命周期
- 记录请求时间、响应时间、HTTP状态、错误信息
- 携带完整的业务标签、云环境、染色信息

**分析能力**：

#### 6.1 概览分析
```bash
curl http://localhost:8080/api/trace/analysis/overview
```
返回：总染色请求数、跨云请求数、按颜色/标签/云区域统计、成功率、平均延迟

#### 6.2 多维度聚合分析
支持5种维度的聚合：
```bash
# 按染色颜色聚合
curl http://localhost:8080/api/trace/analysis/group/color

# 按业务标签聚合
curl http://localhost:8080/api/trace/analysis/group/biztag

# 按业务类型聚合
curl http://localhost:8080/api/trace/analysis/group/biztype

# 按用户聚合
curl http://localhost:8080/api/trace/analysis/group/user

# 按云环境聚合
curl http://localhost:8080/api/trace/analysis/group/cloud
```

每个维度返回：请求数、成功数、错误数、错误率、平均延迟、P95延迟

#### 6.3 业务标签分布
```bash
curl http://localhost:8080/api/trace/analysis/biztag-distribution
```
返回：标签分布统计、Top 10热门标签、各标签错误率对比

#### 6.4 慢请求分析
```bash
# 获取Top 20慢请求
curl http://localhost:8080/api/trace/analysis/slow-requests

# 获取Top 50慢请求
curl "http://localhost:8080/api/trace/analysis/slow-requests?limit=50"
```

#### 6.5 错误请求追踪
```bash
curl http://localhost:8080/api/trace/analysis/error-requests
```
集中展示所有错误请求及其错误信息

#### 6.6 Trace详情查询
```bash
# 根据Trace ID查询完整详情
curl http://localhost:8080/api/trace/analysis/trace/{traceId}
```

**典型使用场景**：
- 🔍 问题排查：根据染色标签快速定位特定业务场景的问题
- 📈 性能分析：按业务维度分析系统性能瓶颈
- ☁️ 多云对比：对比不同云环境的系统表现
- 🎯 效果评估：评估染色流量（如灰度、活动）的系统影响
- 📊 SLA监控：按业务维度监控服务级别协议

## 扩展开发

### 1. 自定义采样器

实现 `TraceSampler` 接口：

```java
@Component
public class CustomTraceSampler implements TraceSampler {
    @Override
    public boolean shouldSample(HttpServletRequest request, StainingContext context) {
        // 自定义采样逻辑
    }
    
    @Override
    public boolean shouldStain(HttpServletRequest request, StainingContext context) {
        // 自定义染色逻辑
    }
    
    @Override
    public String assignStainingColor(HttpServletRequest request, StainingContext context) {
        // 自定义染色颜色分配
    }
}
```

### 2. 手动操作上下文

```java
// 获取当前上下文
StainingContext context = TraceContextHolder.getContext();

// 创建新的染色上下文
StainingContext newContext = TraceContextHolder.createNewContext(
    true, "RED", "user001", "ORDER"
);

// 设置上下文
TraceContextHolder.setContext(newContext);

// 创建 OpenTelemetry Span
TraceContextHolder.createAndSetOtelSpan("operation-name");

try {
    // 执行业务逻辑
} finally {
    // 结束 Span 并清理上下文
    TraceContextHolder.endOtelSpan();
    TraceContextHolder.removeContext();
}
```

## 设计原理

### 1. 上下文传递机制
```
请求入口 → TraceEntryInterceptor → ThreadLocal/MDC/OTEL Context
          ↓
    业务逻辑执行
          ↓
RestTemplate/Kafka/RabbitMQ → 自动注入 Header → 下游服务
          ↓
    异步调用/线程池 → TransmittableThreadLocal 捕获和恢复
          ↓
响应返回 → 清理 ThreadLocal → 结束 Span
```

### 2. Span 生命周期
1. **创建**：在拦截器中创建 Span 并绑定到当前线程
2. **传播**：通过 HTTP Header / 消息头传递 W3C Trace Context
3. **结束**：在请求完成时自动结束 Span 并导出到 Jaeger

### 3. 采样策略
- **染色请求**：始终采样，确保染色请求的完整追踪
- **普通请求**：按配置的采样率随机采样
- **强制采样**：通过 `X-Sampled: true` Header 强制采样

## 核心代码参考

- [TraceContextHolder.java](file:///d:/Project/trae/project/record001/516/src/main/java/com/tracing/staining/context/TraceContextHolder.java) - 上下文管理器核心
- [TraceEntryInterceptor.java](file:///d:/Project/trae/project/record001/516/src/main/java/com/tracing/staining/interceptor/TraceEntryInterceptor.java) - HTTP 入口拦截器
- [OpenTelemetryConfig.java](file:///d:/Project/trae/project/record001/516/src/main/java/com/tracing/staining/config/OpenTelemetryConfig.java) - OpenTelemetry 配置
- [DefaultTraceSampler.java](file:///d:/Project/trae/project/record001/516/src/main/java/com/tracing/staining/sampler/DefaultTraceSampler.java) - 默认采样器实现

## License

MIT License
