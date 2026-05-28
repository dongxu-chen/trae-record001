# 限流降级中心 (Rate Limit Center)

基于 Sentinel + Redis + Apollo + Grafana 实现的集中式限流降级中心，提供完整的流量控制、降级熔断、集群限流、流量预热等功能。

## 功能特性

### 🎯 核心功能
- **QPS限流**: 基于QPS的流量控制，支持快速失败、预热、排队等待等策略
- **热点参数限流**: 针对热点参数的精细化限流控制
- **集群限流**: 分布式环境下的集群流量控制，支持Token Server模式
- **降级熔断**: 基于慢调用比例、异常比例、异常数的熔断策略
- **流量预热**: 冷启动流量预热，保护系统平稳启动
- **动态配置**: 基于Apollo配置中心的规则动态生效
- **系统自适应**: 基于系统负载、CPU使用率等的自适应限流

### 📊 监控与分析
- **Prometheus指标**: 完整的监控指标暴露
- **Grafana大盘**: 可视化监控仪表盘
- **拦截日志**: 详细的限流拦截日志记录与分析
- **实时统计**: 实时QPS、响应时间、线程数等指标

## 技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Java | 11 | 开发语言 |
| Spring Boot | 2.7.15 | 应用框架 |
| Sentinel | 1.8.6 | 流量控制框架 |
| Redis | 7.0+ | 规则存储与集群通信 |
| Apollo | 2.1.0 | 配置中心(可选) |
| MyBatis Plus | 3.5.3.2 | ORM框架 |
| MySQL | 8.0+ | 规则持久化存储 |
| Prometheus | 2.47.0 | 监控指标采集 |
| Grafana | 10.1.0 | 可视化监控 |

## 快速开始

### 1. 数据库初始化

```bash
mysql -uroot -p < sql/schema.sql
```

### 2. 本地运行

```bash
# 编译项目
mvn clean package -DskipTests

# 运行应用
java -jar target/rate-limit-center-1.0.0.jar
```

### 3. Docker部署

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 停止服务
docker-compose down
```

## API接口

### 限流规则管理

```
# 流控规则
GET    /api/flow-rules              # 查询流控规则列表
GET    /api/flow-rules/{id}         # 查询单个流控规则
POST   /api/flow-rules              # 创建流控规则
PUT    /api/flow-rules              # 更新流控规则
DELETE /api/flow-rules/{id}         # 删除流控规则
PATCH  /api/flow-rules/{id}/status  # 更新规则状态
POST   /api/flow-rules/sync         # 同步规则到Redis

# 降级规则
GET    /api/degrade-rules           # 查询降级规则列表
POST   /api/degrade-rules           # 创建降级规则
PUT    /api/degrade-rules           # 更新降级规则
DELETE /api/degrade-rules/{id}      # 删除降级规则

# 热点参数规则
GET    /api/param-flow-rules        # 查询热点参数规则列表
POST   /api/param-flow-rules        # 创建热点参数规则
PUT    /api/param-flow-rules        # 更新热点参数规则
DELETE /api/param-flow-rules/{id}   # 删除热点参数规则

# 系统规则
GET    /api/system-rules            # 查询系统规则列表
POST   /api/system-rules            # 创建系统规则
PUT    /api/system-rules            # 更新系统规则
DELETE /api/system-rules/{id}       # 删除系统规则
```

### 集群限流

```
GET    /api/cluster/state           # 获取集群状态
GET    /api/cluster/clients         # 获取集群客户端列表
GET    /api/cluster/server          # 获取集群Token Server
POST   /api/cluster/mode/client     # 切换到客户端模式
POST   /api/cluster/mode/server     # 切换到服务端模式
GET    /api/cluster/token-stats     # 获取Token请求统计
```

### 流量预热

```
POST   /api/warm-up/start           # 启动流量预热
POST   /api/warm-up/stop            # 停止流量预热
GET    /api/warm-up/status          # 获取预热状态
GET    /api/warm-up/current-limit   # 获取当前预热阈值
GET    /api/warm-up/completed       # 检查预热是否完成
```

### 日志与监控

```
GET    /api/logs                    # 查询限流日志
GET    /api/logs/stats              # 获取日志统计
GET    /api/metrics/resource        # 获取资源监控指标
GET    /api/metrics/all             # 获取所有资源监控指标
GET    /actuator/prometheus         # Prometheus指标端点
```

## 配置说明

### application.yml 核心配置

```yaml
# Redis配置
spring:
  data:
    redis:
      host: 127.0.0.1
      port: 6379

# Sentinel配置
sentinel:
  transport:
    port: 8719
    dashboard: 127.0.0.1:8858

# 限流中心配置
rate-limit:
  cluster:
    enabled: true
    server-port: 18730
  warm-up:
    enabled: true
    default-warm-up-period-seconds: 10
  log:
    enabled: true
    retain-days: 30
  apollo:
    enabled: false
```

### Apollo配置（可选）

启用Apollo配置中心后，支持以下配置项的动态更新：

- `sentinel.flow.*` - 流控规则
- `sentinel.degrade.*` - 降级规则
- `sentinel.param.*` - 热点参数规则
- `sentinel.system.*` - 系统规则

## 监控大盘

### 访问地址
- **应用地址**: http://localhost:8090/rate-limit
- **Sentinel控制台**: http://localhost:8858
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin123)

### 监控指标

| 指标名称 | 类型 | 说明 |
|----------|------|------|
| sentinel_pass_total | Counter | 通过的请求总数 |
| sentinel_block_total | Counter | 拦截的请求总数 |
| sentinel_exception_total | Counter | 异常请求总数 |
| sentinel_rt_seconds | Timer | 请求响应时间 |
| sentinel_pass_qps | Gauge | 当前通过QPS |
| sentinel_block_qps | Gauge | 当前拦截QPS |
| sentinel_rt_avg | Gauge | 平均响应时间 |
| sentinel_thread_count | Gauge | 当前线程数 |

## 项目结构

```
rate-limit-center/
├── src/main/java/com/ratelimit/center/
│   ├── RateLimitCenterApplication.java    # 启动类
│   ├── common/                             # 通用类
│   │   ├── Result.java
│   │   ├── PageResult.java
│   │   └── RateLimitConstants.java
│   ├── config/                             # 配置类
│   │   ├── SentinelConfig.java
│   │   ├── RedisConfig.java
│   │   ├── MybatisPlusConfig.java
│   │   ├── WebConfig.java
│   │   └── ApolloConfig.java
│   ├── controller/                         # 控制器
│   │   ├── FlowRuleController.java
│   │   ├── DegradeRuleController.java
│   │   ├── ParamFlowRuleController.java
│   │   ├── SystemRuleController.java
│   │   ├── ClusterController.java
│   │   ├── WarmUpController.java
│   │   ├── LogController.java
│   │   └── MetricController.java
│   ├── service/                            # 服务层
│   │   ├── FlowRuleService.java
│   │   ├── DegradeRuleService.java
│   │   ├── ParamFlowRuleService.java
│   │   ├── SystemRuleService.java
│   │   ├── ClusterFlowService.java
│   │   ├── WarmUpService.java
│   │   ├── RateLimitLogService.java
│   │   └── MetricService.java
│   ├── entity/                             # 实体类
│   ├── mapper/                             # Mapper接口
│   ├── handler/                            # 处理器
│   │   └── GlobalExceptionHandler.java
│   └── interceptor/                        # 拦截器
│       └── RateLimitInterceptor.java
├── src/main/resources/
│   ├── application.yml
│   └── application-docker.yml
├── sql/
│   └── schema.sql
├── grafana/
│   ├── dashboard.json
│   └── prometheus.yml
├── Dockerfile
├── docker-compose.yml
└── pom.xml
```

## 最佳实践

### 1. 规则配置建议
- QPS限流阈值建议设置为系统压测值的70%-80%
- 降级规则建议设置合理的时间窗口和最小请求数
- 集群限流建议采用全局阈值模式，避免流量不均

### 2. 监控告警建议
- 拦截率超过5%时告警
- 平均响应时间超过阈值时告警
- 异常率突增时告警

### 3. 性能优化建议
- 合理设置日志保留天数，避免日志过多
- Redis建议使用集群模式提高可用性
- 生产环境建议配置适当的JVM参数

## License

MIT License
