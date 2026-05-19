# Service Mesh Console Backend

基于 Istio + Go + K8s 的服务网格灰度发布控制台后端 API。

## 功能特性

### 1. 流量镜像 (Traffic Mirroring)
- 将生产流量复制到测试服务
- 支持配置镜像流量百分比
- 创建/更新/删除镜像配置

### 2. 金丝雀发布 (Canary Release)
- 基于权重的流量分配
- 基于 Header/Cookie 的流量路由
- 动态调整金丝雀流量比例
- 支持蓝绿部署

### 3. 熔断器 (Circuit Breaker)
- 连接池配置
- 异常实例检测
- 错误率阈值配置
- 熔断窗口配置

### 4. 分布式追踪 (Distributed Tracing)
- OpenTelemetry 集成
- 全链路追踪
- Trace ID 透传

## 项目结构

```
.
├── main.go                 # 程序入口
├── go.mod                  # 依赖管理
├── config/
│   └── config.go          # 配置管理
├── pkg/
│   ├── k8sclient/
│   │   └── client.go      # K8s/Istio 客户端
│   ├── tracing/
│   │   ├── tracing.go     # 追踪初始化
│   │   └── middleware.go  # 追踪中间件
│   ├── handler/
│   │   ├── types.go       # 请求响应类型
│   │   ├── mirror.go      # 流量镜像 API
│   │   ├── canary.go      # 金丝雀发布 API
│   │   └── circuitbreaker.go # 熔断器 API
│   └── server/
│       └── server.go      # HTTP 服务器
```

## API 接口

### 健康检查
```
GET /api/v1/health
```

### 流量镜像 API

#### 配置流量镜像
```
POST /api/v1/traffic-mirror
Content-Type: application/json

{
  "source_service": "my-service",
  "target_service": "my-service-v2",
  "namespace": "default",
  "percentage": 100,
  "enabled": true
}
```

#### 获取流量镜像配置
```
GET /api/v1/traffic-mirror?service=my-service&namespace=default
```

#### 删除流量镜像配置
```
DELETE /api/v1/traffic-mirror/{service}?namespace=default
```

### 金丝雀发布 API

#### 配置金丝雀发布
```
POST /api/v1/canary-release
Content-Type: application/json

{
  "service_name": "my-service",
  "namespace": "default",
  "stable_version": "v1",
  "canary_version": "v2",
  "traffic_percentage": 10,
  "match_headers": {
    "x-user-type": "beta"
  },
  "match_cookies": {
    "user_group": "test"
  },
  "enabled": true
}
```

#### 获取金丝雀发布配置
```
GET /api/v1/canary-release?service=my-service&namespace=default
```

#### 更新金丝雀流量比例
```
PATCH /api/v1/canary-release/{service}/traffic
Content-Type: application/json

{
  "traffic_percentage": 50
}
```

#### 删除金丝雀发布配置
```
DELETE /api/v1/canary-release/{service}?namespace=default
```

### 熔断器 API

#### 配置熔断器
```
POST /api/v1/circuit-breaker
Content-Type: application/json

{
  "service_name": "my-service",
  "namespace": "default",
  "max_connections": 100,
  "http1_max_pending_requests": 100,
  "http2_max_requests": 100,
  "max_requests_per_connection": 10,
  "max_retries": 3,
  "consecutive_errors": 5,
  "sleep_window_seconds": 30,
  "enabled": true
}
```

#### 获取熔断器配置
```
GET /api/v1/circuit-breaker?service=my-service&namespace=default
```

#### 验证熔断器配置（检查Envoy同步状态）
```
GET /api/v1/circuit-breaker/{service}/verify?namespace=default
```

#### 删除熔断器配置
```
DELETE /api/v1/circuit-breaker/{service}?namespace=default
```

### 请求采样 API

#### 配置请求采样
```
POST /api/v1/sampling
Content-Type: application/json

{
  "service_name": "my-service",
  "namespace": "default",
  "enabled": true,
  "sample_percentage": 10,
  "sampling_rules": [
    {
      "rule_name": "api-sampling",
      "match_headers": {
        "x-api-version": "v2"
      },
      "match_paths": ["/api/v2"],
      "sample_percentage": 100,
      "priority": 10
    }
  ]
}
```

#### 获取采样配置
```
GET /api/v1/sampling?service=my-service&namespace=default
```

#### 删除采样配置
```
DELETE /api/v1/sampling/{service}?namespace=default
```

### 智能路由 API

#### 配置智能路由
```
POST /api/v1/smart-route
Content-Type: application/json

{
  "service_name": "my-service",
  "namespace": "default",
  "enabled": true,
  "rules": [
    {
      "rule_name": "internal-users",
      "match_headers": {
        "x-user-role": "internal"
      },
      "match_source_ips": ["192.168.1.0/24", "10.0.0.1"],
      "match_paths": ["/internal"],
      "destination": {
        "host": "my-service-canary",
        "subset": "v2",
        "weight": 100
      },
      "priority": 100
    }
  ]
}
```

#### 获取智能路由配置
```
GET /api/v1/smart-route?service=my-service&namespace=default
```

#### 删除智能路由配置
```
DELETE /api/v1/smart-route/{service}?namespace=default
```

### 异常检测 API

#### 配置异常检测
```
POST /api/v1/anomaly-detection
Content-Type: application/json

{
  "service_name": "my-service",
  "namespace": "default",
  "enabled": true,
  "consecutive_errors": 5,
  "error_threshold_percent": 10,
  "interval_seconds": 60,
  "base_ejection_seconds": 30,
  "max_ejection_percent": 50,
  "min_health_percent": 70
}
```

#### 获取异常检测配置
```
GET /api/v1/anomaly-detection?service=my-service&namespace=default
```

#### 获取实例状态
```
GET /api/v1/anomaly-detection/instances?service=my-service&namespace=default
```

#### 手动剔除实例
```
POST /api/v1/anomaly-detection/eject
Content-Type: application/json

{
  "service_name": "my-service",
  "namespace": "default",
  "instance_ip": "10.0.0.123",
  "duration_sec": 300
}
```

#### 恢复实例
```
POST /api/v1/anomaly-detection/restore
Content-Type: application/json

{
  "service_name": "my-service",
  "namespace": "default",
  "instance_ip": "10.0.0.123"
}
```

#### 删除异常检测配置
```
DELETE /api/v1/anomaly-detection/{service}?namespace=default
```

### 流量拓扑 API

#### 获取流量拓扑图
```
GET /api/v1/topology?namespace=default&service=my-service&time_range=5m
```

#### 获取服务指标
```
GET /api/v1/topology/metrics/{service}?namespace=default
```

#### 清除流量数据
```
DELETE /api/v1/topology/data
```

## gRPC 追踪上下文传递

服务支持通过 gRPC 元数据进行追踪上下文传递：

```go
import "servicemesh-console/pkg/tracing"

// 从gRPC元数据中提取追踪上下文
ctx = tracing.ExtractFromGRPCMetadata(ctx)

// 将追踪上下文注入到gRPC元数据中
ctx = tracing.InjectToGRPCMetadata(ctx)
```

## 主要修复内容

### 1. 权重变更连接预热与逐步切换
- **自动预热模式**：配置`enable_warmup: true`时，系统会在指定时间内逐步切换流量
- **手动控制模式**：通过`gradual-start`和`gradual-stop`接口精确控制流量切换节奏
- **平滑切换**：避免连接中断，确保服务稳定性

### 2. 故障注入增强
- **延迟注入**：支持按百分比配置请求延迟
- **HTTP错误码注入**：支持配置5xx/4xx等错误码注入
- **灵活配置**：可同时配置延迟和中止故障，支持百分比控制

### 3. 熔断器配置修复与验证
- **正确的配置字段**：使用`Consecutive_5XxErrors`替代`ConsecutiveErrors`
- **时间格式标准化**：使用Istio标准的Duration格式
- **配置验证接口**：提供`verify`端点检查配置是否正确下发到Envoy
- **详细状态报告**：返回连接池、异常检测等配置的详细状态

### 4. gRPC元数据追踪上下文传递
- **W3C TraceContext标准**：支持标准的traceparent头
- **元数据提取/注入**：提供`ExtractFromGRPCMetadata`和`InjectToGRPCMetadata`函数
- **完整链路追踪**：确保跨服务调用的追踪链路完整

## 环境变量

```env
SERVER_PORT=8080
KUBE_CONFIG_PATH=~/.kube/config
NAMESPACE=default
LOG_LEVEL=info
GIN_MODE=release
```

## 运行方式

### 本地开发
```bash
# 安装依赖
go mod download

# 运行服务
go run main.go
```

### 容器化部署
```dockerfile
FROM golang:1.21-alpine
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o servicemesh-console .
EXPOSE 8080
CMD ["./servicemesh-console"]
```

## K8s RBAC 权限要求

服务需要以下权限：

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: servicemesh-console
rules:
- apiGroups: ["networking.istio.io"]
  resources: ["virtualservices", "destinationrules"]
  verbs: ["get", "list", "create", "update", "delete", "patch"]
```

## 技术栈

- **Web 框架**: Gin
- **日志**: Logrus
- **K8s 客户端**: client-go
- **Istio 客户端**: istio.io/client-go
- **追踪**: OpenTelemetry
