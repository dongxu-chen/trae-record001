# 服务网格流量治理平台 (Service Mesh Gateway)

基于 **Go + Istio + Kiali + Redis + React** 的服务网格流量治理平台，提供完整的流量管理、拓扑可视化和分析报表功能。

## 功能特性

### 核心流量治理
- **权重路由** - 按百分比将流量分配到不同服务版本，支持灰度发布/金丝雀发布
- **基于Header的路由** - 根据HTTP Header内容（精确/前缀/正则匹配）进行路由决策
- **流量镜像** - 将生产流量实时复制到测试服务，零风险验证
- **故障注入** - 注入延迟或HTTP错误，验证系统韧性

### 可视化与分析
- **流量拓扑可视化** - Canvas绘制的服务调用拓扑图，支持缩放/拖拽/点击查看详情
- **路由规则热更新** - 规则变更即时推送到Istio VirtualService，无需重启
- **流量分析报表** - 多维度流量报表（日报/周报/月报），含延迟/错误率/吞吐量

### 技术架构
- **Go后端** - Gin框架提供RESTful API，通过K8s Dynamic Client管理Istio资源
- **Istio集成** - 原生操作VirtualService/DestinationRule，无缝对接服务网格
- **Kiali集成** - 对接Kiali获取服务拓扑和流量指标
- **Redis缓存** - 流量指标存储、拓扑缓存、路由规则持久化
- **React前端** - Ant Design组件库 + Canvas拓扑图 + ECharts图表

## 项目结构

```
.
├── backend/                    # Go后端服务
│   ├── cmd/server/             # 主程序入口
│   │   └── main.go
│   ├── pkg/
│   │   ├── api/                # API处理器与路由
│   │   │   ├── handlers.go     # RESTful API处理器
│   │   │   └── router.go       # 路由配置
│   │   ├── istio/              # Istio客户端
│   │   │   └── client.go       # VirtualService/DestinationRule管理
│   │   ├── models/             # 数据模型
│   │   │   ├── routing.go      # 路由规则模型
│   │   │   └── traffic.go      # 流量指标模型
│   │   └── redis/              # Redis客户端
│   │       ├── client.go       # Redis连接与操作封装
│   │       └── traffic_store.go # 流量数据存储
│   ├── config/                 # 配置文件
│   │   └── config.yaml
│   ├── Dockerfile
│   └── go.mod
├── frontend/                   # React前端
│   ├── src/
│   │   ├── pages/              # 页面组件
│   │   │   ├── Dashboard.tsx   # 仪表盘
│   │   │   ├── Topology.tsx    # 流量拓扑可视化
│   │   │   ├── RoutingRules.tsx # 路由规则管理
│   │   │   ├── TrafficAnalysis.tsx # 流量分析报表
│   │   │   └── IstioResources.tsx  # Istio资源管理
│   │   ├── services/
│   │   │   └── api.ts          # API服务封装
│   │   ├── types/
│   │   │   └── index.ts        # TypeScript类型定义
│   │   ├── App.tsx             # 主布局
│   │   └── index.tsx           # 入口
│   ├── Dockerfile
│   └── package.json
├── k8s/                        # Kubernetes部署配置
│   ├── deployment.yaml         # 应用部署
│   ├── redis.yaml              # Redis部署
│   ├── rbac.yaml               # RBAC权限
│   ├── istio-gateway.yaml      # Istio网关配置
│   └── kiali-config.yaml       # Kiali集成配置
└── docker-compose.yaml         # 本地开发环境
```

## API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/routing/weight` | 创建权重路由 |
| POST | `/api/v1/routing/header` | 创建Header路由 |
| POST | `/api/v1/routing/mirror` | 创建流量镜像 |
| POST | `/api/v1/routing/fault` | 创建故障注入 |
| GET  | `/api/v1/routing/rules` | 获取路由规则列表 |
| DELETE | `/api/v1/routing/rules/:namespace/:id` | 删除路由规则 |
| GET  | `/api/v1/topology` | 获取流量拓扑 |
| GET  | `/api/v1/metrics` | 获取流量指标 |
| POST | `/api/v1/reports` | 生成流量报表 |
| GET  | `/api/v1/reports/:id` | 获取报表详情 |
| GET  | `/api/v1/istio/virtualservices` | 获取VirtualService列表 |
| GET  | `/api/v1/istio/destinationrules` | 获取DestinationRule列表 |

## 快速开始

### 本地开发 (Docker Compose)

```bash
docker-compose up --build
```

前端: http://localhost:3000
后端API: http://localhost:8080

### Kubernetes部署

```bash
# 创建命名空间
kubectl apply -f k8s/deployment.yaml

# 部署Redis
kubectl apply -f k8s/redis.yaml

# 配置RBAC权限
kubectl apply -f k8s/rbac.yaml

# 配置Istio网关
kubectl apply -f k8s/istio-gateway.yaml

# 配置Kiali集成
kubectl apply -f k8s/kiali-config.yaml
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SMG_SERVER_PORT` | 8080 | 服务端口 |
| `SMG_REDIS_ADDR` | localhost:6379 | Redis地址 |
| `SMG_REDIS_PASSWORD` | | Redis密码 |
| `SMG_REDIS_DB` | 0 | Redis数据库 |
| `KUBECONFIG` | | K8s配置文件路径(空则使用InCluster) |

## 技术栈

- **后端**: Go 1.21, Gin, K8s client-go, Istio client-go, go-redis
- **前端**: React 18, TypeScript, Ant Design 5, ECharts, vis-network
- **基础设施**: Istio, Kiali, Redis, Kubernetes, Docker
