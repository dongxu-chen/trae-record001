# API 聚合网关项目

基于 Spring Cloud Gateway 构建的响应式 API 网关，支持 REST、GraphQL、gRPC 等多种协议的路由和聚合。

## 项目架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway Core                        │
│  (Port: 8080)                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐  │
│  │   REST     │  │  GraphQL   │  │   gRPC     │  │ Aggregate │  │
│  │   Route    │  │   Route    │  │   Bridge   │  │   Route   │  │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬─────┘  │
│        │                │                │                │        │
│  ┌─────▼────────────────▼────────────────▼────────────────▼─────┐  │
│  │                    Resilience4j 熔断器/限流/隔离舱             │  │
│  └───────────────────────────────┬──────────────────────────────┘  │
│                                  │                                 │
│  ┌───────────────────────────────▼──────────────────────────────┐  │
│  │                      Redis 缓存层 (Redisson)                   │  │
│  └───────────────────────────────┬──────────────────────────────┘  │
│                                  │                                 │
└──────────────────────────────────┼─────────────────────────────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │    Mock Backend     │
                        │  (Port: 8081/9090)  │
                        │  - REST API         │
                        │  - GraphQL Server   │
                        │  - gRPC Server      │
                        └─────────────────────┘
```

## 模块说明

| 模块 | 说明 | 端口 |
|------|------|------|
| api-gateway-core | API 网关核心，基于 Spring Cloud Gateway | 8080 |
| grpc-bridge | gRPC 桥接模块，实现 HTTP 到 gRPC 的转换 | - |
| mock-backend | 模拟后端服务，提供 REST/GraphQL/gRPC 接口 | 8081 (HTTP), 9090 (gRPC) |

## 技术栈

- **Java 17**
- **Spring Boot 3.2.0**
- **Spring Cloud 2023.0.0**
- **Spring Cloud Gateway** - 响应式网关
- **Resilience4j 2.1.0** - 熔断器、限流、隔离舱、超时控制
- **Redisson 3.25.0** - Redis 客户端和分布式锁
- **gRPC 1.60.0** - 高性能 RPC 框架
- **GraphQL Java 2.3.0** - GraphQL 实现
- **Project Lombok** - 简化 Java 代码

## 快速开始

### 环境要求

- JDK 17+
- Maven 3.8+
- Redis 6.0+ (localhost:6379)

### 启动 Redis

```bash
# Windows
redis-server

# 或使用 Docker
docker run -d -p 6379:6379 redis:latest
```

### 编译项目

```bash
mvn clean install
```

### 启动服务

1. 启动 Mock Backend:

```bash
cd mock-backend
mvn spring-boot:run
```

2. 启动 API Gateway:

```bash
cd api-gateway-core
mvn spring-boot:run
```

### 验证服务

- API 网关: http://localhost:8080
- Mock 后端 REST: http://localhost:8081
- GraphQL Playground: http://localhost:8081/graphiql
- gRPC 服务: localhost:9090

## API 示例

### 1. REST API

#### 获取用户列表

```bash
curl http://localhost:8080/api/rest/users?page=0&size=10
```

#### 创建用户

```bash
curl -X POST http://localhost:8080/api/rest/users \
  -H "Content-Type: application/json" \
  -d '{"name":"张三","email":"zhangsan@example.com","age":25}'
```

#### 获取用户信息

```bash
curl http://localhost:8080/api/rest/users/1
```

### 2. GraphQL API

#### 查询用户

```graphql
query {
  getUser(id: 1) {
    id
    name
    email
    age
  }
}
```

通过网关访问:

```bash
curl -X POST http://localhost:8080/api/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"query { getUser(id: 1) { id name email age } }"}'
```

#### 查询订单列表

```graphql
query {
  listOrders(page: 0, size: 10) {
    orders {
      id
      userId
      product
      amount
      status
    }
    total
  }
}
```

### 3. gRPC Bridge API

#### 调用 UserService.GetUser

```bash
curl -X POST http://localhost:8080/api/grpc/user/getUser \
  -H "Content-Type: application/json" \
  -d '{"id": 1}'
```

#### 调用 UserService.ListUsers

```bash
curl -X POST http://localhost:8080/api/grpc/user/listUsers \
  -H "Content-Type: application/json" \
  -d '{"page": 0, "size": 10}'
```

#### 调用 OrderService.CreateOrder

```bash
curl -X POST http://localhost:8080/api/grpc/order/createOrder \
  -H "Content-Type: application/json" \
  -d '{"userId": 1, "product": "iPhone 15", "amount": 5999.00}'
```

#### 快速获取用户（GET 方式）

```bash
curl "http://localhost:8080/api/grpc/user/get?id=1"
```

#### gRPC 健康检查

```bash
curl http://localhost:8080/api/grpc/health?service=UserService
```

### 4. 聚合 API

#### 获取用户详情及订单

```bash
curl http://localhost:8080/api/aggregate/user/1/detail
```

## 配置说明

### API Gateway 配置 (`api-gateway-core/src/main/resources/application.yml`)

#### 服务器配置

```yaml
server:
  port: 8080
```

#### Resilience4j 熔断器配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| sliding-window-size | 滑动窗口大小 | 10 |
| failure-rate-threshold | 失败率阈值(%) | 50 |
| wait-duration-in-open-state | 熔断状态等待时间 | 10s |
| slow-call-duration-threshold | 慢调用判定阈值 | 2s |

**断路器实例:**
- `restApiCircuitBreaker` - REST API 断路器
- `graphqlCircuitBreaker` - GraphQL 断路器
- `grpcCircuitBreaker` - gRPC 断路器
- `aggregationCircuitBreaker` - 聚合 API 断路器

#### Resilience4j 限流配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| limit-for-period | 每个周期允许的请求数 | 10 |
| limit-refresh-period | 限流刷新周期 | 1s |
| permit-wait-duration | 许可等待时间 | 0s |

**限流器实例:**
- `defaultRateLimiter` - 默认限流器 (10 QPS)
- `grpcRateLimiter` - gRPC 限流器 (50 QPS)
- `apiRateLimiter` - API 限流器 (100 QPS)

#### Resilience4j 超时配置

| 实例 | 超时时间 |
|------|----------|
| restApiTimeLimiter | 3s |
| graphqlTimeLimiter | 5s |
| grpcTimeLimiter | 10s |
| aggregationTimeLimiter | 15s |

#### Resilience4j 隔离舱配置

| 实例 | 最大并发数 |
|------|-----------|
| defaultBulkhead | 10 |
| graphqlBulkhead | 20 |
| grpcBulkhead | 30 |

#### Redis 配置

```yaml
spring:
  data:
    redis:
      host: localhost
      port: 6379
      database: 0
```

#### 缓存配置

```yaml
gateway:
  cache:
    enabled: true
    default-expire-time: 5m
    key-prefix: "gateway:cache"
```

缓存规则支持按路径配置不同的过期时间、包含/排除查询参数等。

#### gRPC 客户端配置

```yaml
grpc:
  client:
    default-host: localhost
    default-port: 9090
    default-deadline: 30s
```

支持多服务配置，每个服务可独立配置主机、端口、截止时间等。

### Mock Backend 配置 (`mock-backend/src/main/resources/application.yml`)

#### 服务器配置

```yaml
server:
  port: 8081
```

#### gRPC 服务端配置

```yaml
grpc:
  server:
    port: 9090
    host: 0.0.0.0
```

#### 模拟延迟配置

```yaml
mock:
  delay:
    enabled: true
    min-delay-ms: 100
    max-delay-ms: 500
    use-random: true
```

支持按路径配置不同的延迟策略:
- `/api/users/**`: 200-1000ms 随机延迟
- `/api/orders/**`: 500-2000ms 随机延迟
- `/api/products/**`: 固定 150ms 延迟

#### 模拟错误配置

```yaml
mock:
  error:
    enabled: true
    error-rate: 0.1  # 10% 错误率
```

支持按路径配置不同的错误率:
- `/api/users/**`: 5% 错误率
- `/api/orders/**`: 15% 错误率
- `/api/products/**`: 0% 错误率

#### 模拟超时配置

```yaml
mock:
  timeout:
    enabled: true
    timeout-rate: 0.05  # 5% 超时率
    timeout-ms: 10000
```

## 核心功能

### 1. 多协议路由
- REST API 路由 (`/api/rest/**`)
- GraphQL 路由 (`/api/graphql/**`)
- gRPC 桥接路由 (`/api/grpc/**`)
- 聚合 API 路由 (`/api/aggregate/**`)

### 2. 弹性设计
- **Circuit Breaker**: 自动熔断故障服务
- **Rate Limiter**: 限制请求速率，防止过载
- **Time Limiter**: 控制请求超时时间
- **Bulkhead**: 隔离并发请求，防止雪崩
- **Retry**: 自动重试失败请求

### 3. 缓存机制
- 基于 Redis 的分布式缓存
- 支持按路径配置缓存规则
- 支持查询参数和请求头参与缓存 Key 生成
- 缓存统计功能

### 4. 过滤器
- `AuthenticationFilter` - 认证过滤
- `RequestLoggingFilter` - 请求日志
- `ResponseHeaderFilter` - 响应头处理
- `RequestCacheFilter` - 缓存过滤

### 5. gRPC 桥接
- HTTP JSON 到 gRPC Protobuf 的自动转换
- 连接池管理
- 健康检查
- 连接统计

## 监控指标

熔断器状态可通过 Actuator 端点查看（需启用 Actuator）:

```bash
# 查看断路器状态
curl http://localhost:8080/actuator/circuitbreakers

# 查看限流状态
curl http://localhost:8080/actuator/ratelimiters
```

## 开发调试

### 调整模拟延迟和错误率

编辑 `mock-backend/src/main/resources/application.yml`:

```yaml
mock:
  delay:
    enabled: false  # 关闭延迟
  error:
    enabled: false  # 关闭错误
  timeout:
    enabled: false  # 关闭超时
```

### 查看日志

日志文件位置:
- API Gateway: `api-gateway-core/logs/api-gateway.log`
- Mock Backend: `mock-backend/logs/mock-backend.log`

### 调整日志级别

```yaml
logging:
  level:
    com.apigateway: DEBUG  # 调整为 DEBUG 查看详细日志
```

## 常见问题

### 1. Redis 连接失败

确保 Redis 服务已启动并监听 `localhost:6379`，检查配置:

```yaml
spring:
  data:
    redis:
      host: localhost
      port: 6379
```

### 2. gRPC 连接失败

确保 Mock Backend 已启动，gRPC 服务监听 9090 端口:

```bash
# Windows 查看端口占用
netstat -ano | findstr 9090
```

### 3. 熔断器一直打开

检查 Mock Backend 的错误率配置，可能错误率设置过高，可临时关闭:

```yaml
mock:
  error:
    enabled: false
```

## License

MIT License
