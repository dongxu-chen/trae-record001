# 服务拓扑自动发现工具

基于Kubernetes的服务间调用拓扑自动发现工具，支持多语言、异步调用和消息队列场景。

## 技术栈

- **后端**: Java 17 + Spring Boot 3.2
- **服务发现**: Kubernetes API (Fabric8 Client)
- **调用链分析**: OpenTelemetry 规范
- **图数据库**: Neo4j 5.x
- **前端**: React 18 + TypeScript + Vite + Ant Design
- **可视化**: vis-network

## 功能特性

- ✅ Kubernetes 服务自动发现（定时扫描）
- ✅ 多语言支持：Java、Python、Go、Node.js、Rust、C#、Ruby、PHP
- ✅ 同步/异步调用识别
- ✅ 消息队列调用检测：Kafka、RabbitMQ、ActiveMQ、Redis
- ✅ HTTP、gRPC、数据库调用支持
- ✅ 服务拓扑图可视化展示
- ✅ 调用统计与延迟监控
- ✅ REST API 接口

## 快速开始

### 方式一：Docker Compose 启动

```bash
cd docker
docker-compose up -d
```

访问: http://localhost:3000

### 方式二：本地开发

#### 启动 Neo4j

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/neo4j123456 \
  neo4j:5.15-community
```

#### 启动后端

```bash
cd backend
mvn spring-boot:run
```

#### 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问: http://localhost:3000

## API 接口

### 拓扑查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/topology` | 获取完整拓扑图 |
| GET | `/api/topology/namespace/{namespace}` | 获取指定命名空间拓扑 |
| GET | `/api/topology/stats` | 获取拓扑统计信息 |
| GET | `/api/topology/services` | 获取所有服务列表 |
| GET | `/api/topology/services/{id}` | 获取服务详情 |

### 服务发现

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/topology/discovery/trigger` | 手动触发服务发现 |

### 调用链分析

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/topology/trace` | 提交Trace数据进行分析 |
| POST | `/api/topology/call` | 手动记录服务调用 |

### 管理

| 方法 | 路径 | 说明 |
|------|------|------|
| DELETE | `/api/topology/clear` | 清除所有数据 |
| GET | `/api/topology/health` | 健康检查 |

## 提交 Trace 数据示例

```bash
curl -X POST http://localhost:8080/api/topology/trace \
  -H "Content-Type: application/json" \
  -d '{
    "traceId": "trace-123",
    "spans": [
      {
        "spanId": "span-1",
        "serviceName": "order-service",
        "serviceNamespace": "default",
        "targetService": "payment-service",
        "httpMethod": "POST",
        "path": "/api/payments",
        "startTime": 1700000000000000,
        "endTime": 1700000000050000
      }
    ]
  }'
```

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                        前端 UI                           │
│  React + Ant Design + vis-network 拓扑可视化              │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    Spring Boot 后端                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  K8s 发现模块 │  │ 调用链分析器 │  │  图数据库操作 │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌──────────────────┐         ┌──────────────────┐
│  Kubernetes API  │         │     Neo4j        │
│  服务发现         │         │  图存储/查询      │
└──────────────────┘         └──────────────────┘
```

## 服务节点属性

- `id`: 服务唯一标识
- `name`: 服务名称
- `namespace`: 命名空间
- `type`: 发现类型（KUBERNETES_SERVICE / DISCOVERED_VIA_TRACING）
- `language`: 编程语言
- `version`: 版本
- `status`: 状态
- `serviceType`: Kubernetes Service类型
- `clusterIp`: Cluster IP
- `ports`: 端口列表
- `labels`: 标签
- `annotations`: 注解

## 调用关系属性

- `callType`: 调用类型（SYNC_HTTP / ASYNC_HTTP / MESSAGE_QUEUE / DATABASE / GRPC）
- `protocol`: 协议
- `isAsync`: 是否异步
- `messageQueue`: 消息队列类型
- `httpMethod`: HTTP方法
- `path`: 请求路径
- `callCount`: 调用次数
- `errorCount`: 错误次数
- `avgLatencyMs`: 平均延迟（毫秒）

## 项目结构

```
.
├── backend/                 # Java 后端
│   ├── src/main/java/com/servicetopology/
│   │   ├── k8s/            # Kubernetes 服务发现
│   │   ├── tracing/        # 调用链分析
│   │   ├── neo4j/          # Neo4j 操作
│   │   ├── api/            # REST API
│   │   ├── model/          # 数据模型
│   │   └── config/         # 配置
│   └── pom.xml
├── frontend/               # React 前端
│   ├── src/
│   │   ├── components/     # 组件
│   │   ├── services/       # API 服务
│   │   └── types/          # 类型定义
│   └── package.json
├── docker/                 # Docker 配置
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
└── docs/                   # 文档
```

## 配置说明

### 后端配置 (application.yml)

```yaml
kubernetes:
  discovery:
    enabled: true
    namespaces:
      - default
    scan-interval: 30000  # 扫描间隔（毫秒）

tracing:
  enabled: true
  message-queue-detection:
    enabled: true
    queue-prefixes:
      - kafka
      - rabbitmq
      - activemq
      - redis

discovery:
  async-call-detection:
    enabled: true
    async-headers:
      - X-Async-Call
      - X-Correlation-ID
      - traceparent
```

## 许可证

MIT License
