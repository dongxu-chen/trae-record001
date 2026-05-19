# Thanos Multi-Cluster Alert Testing Platform - 架构设计

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Web UI (React + TypeScript)                    │
│  ┌────────────┐  ┌────────────┐  ┌───────────┐  ┌───────────────┐   │
│  │ Dashboard  │  │ PromQL Play│  │ Alert Test│  │ Fault Injection │
│  └────────────┘  └────────────┘  └───────────┘  └───────────────┘   │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │ REST API / WebSocket
┌───────────────────────────────────▼─────────────────────────────────┐
│                   Backend API Server (Go + Gin)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────────┐  │
│  │ Query Service│  │ Alert Service │  │ Fault Injection Service    │  │
│  └──────────────┘  └──────────────┘  └────────────────────────────┘  │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │ gRPC / HTTP
┌───────────────────────────────────▼─────────────────────────────────┐
│                         Thanos Receiver                               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    TSDB (Time Series Database)                  │  │
│  └───────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │ Remote Write API
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
┌───────▼───────┐           ┌───────▼───────┐           ┌───────▼───────┐
│  Cluster A    │           │  Cluster B    │           │  Cluster C    │
│  (Simulated)  │           │  (Simulated)  │           │  (Simulated)  │
│  Prometheus   │           │  Prometheus   │           │  Prometheus   │
└───────────────┘           └───────────────┘           └───────────────┘
```

---

## 核心组件说明

### 1. Web UI (Frontend)
- **技术栈**: React + TypeScript + TailwindCSS + Recharts
- **核心模块**:
  - 仪表板 Dashboard: 集群状态、告警统计
  - PromQL Playground: 实时查询 + 图表可视化
  - Alert Tester: 告警规则测试、for 窗口模拟
  - Fault Injection: 故障注入控制面板

### 2. Backend API (Go)
- **技术栈**: Go + Gin Web Framework + Prometheus Client
- **核心服务**:
  - **QueryService**: PromQL 查询代理、查询历史、查询解析
  - **AlertService**: 告警规则管理、状态追踪、静默管理
  - **FaultInjectionService**: 指标故障注入、时序模拟
  - **ClusterService**: 多集群配置、健康检查

### 3. Thanos Receiver
- 统一接收多集群 Prometheus Remote Write 指标
- 提供统一的 PromQL 查询端点
- 支持外部标签标识集群来源
- 内置 TSDB 存储

### 4. 多集群模拟层
- 可编程的指标生成器
- 支持故障模式注入
- 真实 Prometheus Remote Write 协议
- 集群标签自动注入

---

## 数据流

### 指标接收流
```
Cluster Simulator (Go)
    │ remote_write
    ▼
Thanos Receiver
    │ TSDB Storage
    ▼
PromQL Query API
    │
    ▼
Web UI / Alert Engine
```

### 告警测试流
```
Alert Rule YAML
    │
    ▼
Alert Validator ────┐
    │               │
    ▼               │
PromQL Engine    For Window Simulation
    │               │
    ▼               ▼
State Machine → Alert Results
    │
    ▼
WebSocket → Real-time UI Updates
```

---

## API 设计

### REST API 端点

#### 查询服务
```
GET    /api/v1/query          - PromQL 即时查询
GET    /api/v1/query_range    - PromQL 范围查询
POST   /api/v1/query/parse    - PromQL 语法解析
GET    /api/v1/series         - 时序元数据
GET    /api/v1/labels         - 标签列表
```

#### 告警服务
```
GET    /api/v1/alerts             - 当前告警列表
POST   /api/v1/alerts/test        - 测试告警规则
GET    /api/v1/alerts/history     - 告警历史
POST   /api/v1/rules              - 上传告警规则
GET    /api/v1/rules              - 规则列表
DELETE /api/v1/rules/:id          - 删除规则
```

#### 故障注入服务
```
POST   /api/v1/faults/start            - 启动故障注入
POST   /api/v1/faults/stop             - 停止故障注入
GET    /api/v1/faults                  - 活跃故障列表
POST   /api/v1/faults/spike            - 指标尖峰注入
POST   /api/v1/faults/outage           - 服务中断模拟
POST   /api/v1/faults/degradation      - 性能降级模拟
```

#### 集群管理
```
GET    /api/v1/clusters           - 集群列表
POST   /api/v1/clusters           - 添加集群
GET    /api/v1/clusters/:id/health - 集群健康检查
POST   /api/v1/clusters/:id/start  - 启动集群模拟
POST   /api/v1/clusters/:id/stop   - 停止集群模拟
```

#### WebSocket 端点
```
WS     /ws/alerts          - 告警实时推送
WS     /ws/metrics         - 指标实时推送
WS     /ws/faults          - 故障状态推送
```

---

## 数据模型

### 集群配置
```yaml
cluster:
  id: us-east-1
  name: US East Production
  labels:
    region: us-east-1
    env: production
    provider: aws
  enabled: true
  scrape_interval: 15s
  remote_write:
    url: http://thanos-receiver:19291/api/v1/receive
```

### 告警规则
```yaml
groups:
  - name: example
    interval: 1m
    rules:
      - alert: HighCPU
        expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High CPU usage on {{ $labels.instance }}
```

### 故障注入配置
```yaml
fault:
  id: cpu-spike-01
  type: metric_spike
  target:
    cluster: us-east-1
    metric: node_cpu_seconds_total
    labels:
      instance: server-01
      mode: idle
  pattern:
    type: sudden_spike
    duration: 5m
    amplitude: 10x
    start_time: 2024-01-15T10:00:00Z
```

---

## 部署架构

### Docker Compose Services
```
┌─────────────────────────────────────────────────────────┐
│                   docker-compose.yml                      │
├─────────────────────────────────────────────────────────┤
│  thanos-receiver:  0.0.0.0:10902 (Store API)            │
│                     0.0.0.0:19291 (Receive API)          │
│  backend:          0.0.0.0:8080                          │
│  frontend:         0.0.0.0:3000                          │
│  simulator-us-east-1:                                    │
│  simulator-eu-west-1:                                    │
│  simulator-ap-southeast-1:                               │
└─────────────────────────────────────────────────────────┘
```

---

## 核心特性矩阵

| 特性 | 状态 | 说明 |
|------|------|------|
| Thanos Receiver 集成 | ✅ 设计完成 | 统一指标接收 |
| 多集群模拟 | ✅ 设计完成 | 可编程集群模拟器 |
| PromQL 实时查询 | ✅ 设计完成 | 完整 PromQL 支持 |
| 指标可视化 | ✅ 设计完成 | 交互式图表 |
| For 窗口模拟 | ✅ 设计完成 | 精确时间控制 |
| Resolve Delay 模拟 | ✅ 设计完成 | 恢复延迟模拟 |
| 故障注入 | ✅ 设计完成 | 多种故障模式 |
| 静默管理 | ✅ 设计完成 | Alertmanager 兼容 |
| Web UI 界面 | ✅ 设计完成 | React 单页应用 |
| WebSocket 实时推送 | ✅ 设计完成 | 状态实时更新 |
| 测试报告生成 | ✅ 设计完成 | 详细结果导出 |

---

## 设计原则

1. **真实环境模拟**: 使用真实的 Thanos 和 Prometheus 协议，不做简化
2. **精确时间控制**: 支持纳秒级别的时间模拟，可加速/减速
3. **可观测性**: 平台自身也是可观测的，内置指标
4. **可扩展性**: 插件化架构，易于添加新的故障模式和告警规则
5. **开发者友好**: 完整的 API 文档、示例、调试工具

---

*架构版本: 1.0.0
最后更新: 2024-01-15*
