# Thanos Multi-Cluster Alert Testing Platform

基于 Thanos Receiver 的多集群告警规则测试平台，支持 PromQL 实时调试、分布式告警测试和故障注入。

## 🚀 平台特性

### 1. Thanos Receiver 统一接收
- 支持多集群 Prometheus Remote Write 指标接收
- 统一的时序数据存储和查询接口
- 内置 TSDB 存储引擎
- 集群标签自动注入

### 2. PromQL 实时调试
- 即时查询 (Instant Query)
- 范围查询 (Range Query)
- PromQL 语法解析和验证
- 查询历史记录
- 指标元数据查询

### 3. 分布式告警规则测试
- 告警规则语法检查
- 告警状态历史追踪
- `for` 等待窗口模拟
- `resolve_delay` 恢复延迟模拟
- 告警静默管理
- 测试报告生成

### 4. 故障注入系统
- **指标尖峰注入** (Metric Spike) - 突然的指标值激增
- **服务中断模拟** (Outage) - 模拟服务完全不可用
- **性能降级模拟** (Degradation) - 逐渐的性能下降
- 自定义故障持续时间和参数
- 按集群/指标/实例精准控制

### 5. Web UI 交互界面
- RESTful API 接口
- WebSocket 实时推送
- CORS 跨域支持
- 集群健康状态监控

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Web UI / Clients                       │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                  API Backend (Go + Gin)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐   │
│  │  Query   │  │  Alert   │  │  Fault   │  │  Cluster  │   │
│  │ Service  │  │ Service  │  │ Service  │  │  Manager  │   │
│  └──────────┘  └──────────┘  └──────────┘  └───────────┘   │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    Thanos Query / Receiver                    │
└──────────────────────────────┬──────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼───────┐      ┌───────▼───────┐      ┌───────▼───────┐
│  US East 1    │      │   EU West 1   │      │ AP Southeast 1│
│  Prometheus   │      │  Prometheus   │      │  Prometheus   │
│  + Simulator  │      │  + Simulator  │      │  + Simulator  │
└───────────────┘      └───────────────┘      └───────────────┘
```

## 📦 快速开始

### 前置条件
- Docker & Docker Compose
- Go 1.19+ (仅开发时需要)
- 至少 4GB RAM

### 方式一：Docker Compose 一键启动

```bash
# 克隆项目
git clone <repository-url>
cd prometheus-alert-tester

# 创建配置目录
mkdir -p config/grafana/{datasources,dashboards}

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 方式二：本地开发模式

```bash
# 下载依赖
go mod tidy

# 构建后端
go build -o alert-tester ./cmd/platform

# 启动后端（需要本地运行 Thanos）
./alert-tester -port 8080 -thanos http://localhost:9090 -dev
```

## 📡 API 接口文档

### 查询服务

#### 即时查询
```http
GET /api/v1/query?query=up&time=1600000000
```

#### 范围查询
```http
GET /api/v1/query?query=rate(http_requests_total[5m])&start=1600000000&end=1600003600&step=1m
```

#### 解析 PromQL
```http
POST /api/v1/query/parse
Content-Type: application/json

{
  "query": "up == 0"
}
```

#### 获取标签列表
```http
GET /api/v1/labels
```

### 告警服务

#### 测试告警规则
```http
POST /api/v1/alerts/test
Content-Type: application/json

{
  "expr": "up == 0",
  "for": "5m",
  "time_range": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-01T01:00:00Z",
    "step": "1m"
  }
}
```

**响应示例：**
```json
{
  "valid": true,
  "states": [...],
  "total_points": 60,
  "true_points": 10,
  "would_fire": true,
  "fire_duration": "5m"
}
```

#### 上传告警规则
```http
POST /api/v1/rules
Content-Type: application/json

{
  "yaml": "groups:\n  - name: example\n    rules:\n      - alert: InstanceDown\n        expr: up == 0\n        for: 5m"
}
```

#### 获取当前告警
```http
GET /api/v1/alerts
```

#### 获取告警历史
```http
GET /api/v1/alerts/history
```

### 故障注入服务

#### 创建指标尖峰
```http
POST /api/v1/faults/spike
Content-Type: application/json

{
  "cluster": "us-east-1",
  "metric": "node_cpu_seconds_total",
  "labels": {
    "instance": "server-01",
    "mode": "idle"
  },
  "amplitude": 10.0,
  "duration": "5m",
  "shape": "sudden"
}
```

#### 创建服务中断
```http
POST /api/v1/faults/outage
Content-Type: application/json

{
  "cluster": "us-east-1",
  "metric": "up",
  "instances": ["server-01", "server-02"],
  "duration": "10m"
}
```

#### 创建性能降级
```http
POST /api/v1/faults/degradation
Content-Type: application/json

{
  "cluster": "eu-west-1",
  "metric": "http_request_duration_seconds",
  "start_value": 0.1,
  "end_value": 2.0,
  "duration": "30m",
  "curve_type": "linear"
}
```

#### 停止故障
```http
POST /api/v1/faults/stop
Content-Type: application/json

{
  "id": "fault-1234567890"
}
```

#### 获取活跃故障
```http
GET /api/v1/faults
```

### 集群管理

#### 获取所有集群
```http
GET /api/v1/clusters
```

#### 添加集群
```http
POST /api/v1/clusters
Content-Type: application/json

{
  "id": "cn-north-1",
  "name": "China North (Beijing)",
  "description": "China production cluster",
  "endpoint": "http://prometheus-cn-north-1:9090",
  "labels": {
    "region": "cn-north-1",
    "env": "production",
    "cloud": "aliyun"
  },
  "enabled": true
}
```

#### 启动/停止集群
```http
POST /api/v1/clusters/{id}/start
POST /api/v1/clusters/{id}/stop
```

#### 获取集群健康状态
```http
GET /api/v1/clusters/{id}/health
```

## 🧪 使用场景示例

### 场景一：测试新的告警规则

1. 编写告警规则 YAML
2. 通过 API 上传规则
3. 注入目标故障（如 CPU 尖峰）
4. 观察告警触发状态
5. 验证 for 窗口和 resolve 行为
6. 生成测试报告

```bash
# 1. 注入 CPU 尖峰
curl -X POST http://localhost:8080/api/v1/faults/spike \
  -H "Content-Type: application/json" \
  -d '{
    "cluster": "us-east-1",
    "metric": "node_cpu_seconds_total",
    "amplitude": 15,
    "duration": "10m"
  }'

# 2. 测试告警规则
curl -X POST http://localhost:8080/api/v1/alerts/test \
  -H "Content-Type: application/json" \
  -d '{
    "expr": "100 - (avg by(instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100) > 80",
    "for": "5m"
  }'

# 3. 查看告警
curl http://localhost:8080/api/v1/alerts
```

### 场景二：对比多集群告警

1. 在所有集群同时注入相同故障
2. 观察各集群告警触发时间
3. 对比告警阈值的合理性
4. 优化跨集群告警策略

### 场景三：告警静默规则测试

1. 设置告警静默规则
2. 注入故障触发告警
3. 验证告警是否被正确静默
4. 测试静默过期后告警是否恢复

## 📊 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| API Backend | 8080 | 告警测试平台主 API |
| Thanos Query | 9090 | Thanos 查询接口 (UI) |
| Thanos Receiver GRPC | 10901 | Thanos Store API |
| Thanos Receiver HTTP | 10902 | Thanos HTTP 接口 |
| Thanos Remote Write | 19291 | Remote Write 接收端口 |
| Grafana | 3000 | 可视化仪表板 |
| Prometheus US | 9091 | US East Prometheus |
| Prometheus EU | 9092 | EU West Prometheus |
| Prometheus AP | 9093 | AP Southeast Prometheus |

## 🔧 配置说明

### Thanos 对象存储配置
`config/objstore.yml`:
```yaml
type: FILESYSTEM
config:
  directory: "/thanos/data"
```

### Prometheus 配置示例
每个集群的 Prometheus 配置包含 Remote Write 配置：
```yaml
global:
  external_labels:
    cluster: us-east-1
    region: us-east-1

remote_write:
  - url: "http://thanos-receiver:19291/api/v1/receive"
```

## 📝 开发指南

### 目录结构
```
prometheus-alert-tester/
├── cmd/
│   └── platform/
│       └── main.go              # 平台主入口
├── internal/
│   └── platform/
│       ├── alert/               # 告警服务
│       ├── cluster/             # 集群管理
│       ├── fault/               # 故障注入
│       └── query/               # 查询服务
├── config/                       # 配置文件
├── docker-compose.yml            # Docker 编排
├── Dockerfile.backend           # 后端 Dockerfile
└── PLATFORM_README.md            # 本文档
```

### 本地开发
```bash
# 仅启动依赖服务（Thanos + Prometheus）
docker-compose up thanos-receiver thanos-query prometheus-us-east-1 -d

# 本地运行后端
go run ./cmd/platform -dev -thanos http://localhost:9090
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
