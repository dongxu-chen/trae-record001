# 服务网格安全策略管理平台

基于 **Go + Istio API + OPA + React + Kiali** 构建的企业级服务网格安全策略管理平台。

## 功能特性

### 核心策略管理
- **mTLS 策略管理** - 管理双向 TLS 认证策略，支持 STRICT/PERMISSIVE/DISABLE 三种模式
- **授权策略管理** - 管理服务间访问控制，支持 ALLOW/DENY/AUDIT 动作
- **请求认证规则** - 管理 JWT 等请求级身份验证规则

### 高级分析功能
- **策略冲突检测** - 自动检测策略间的规则冲突，提供修复建议
- **影响范围分析** - 分析策略变更对服务和工作负载的影响，评估风险等级
- **策略推荐引擎** - 基于服务指标智能推荐安全策略优化建议

### 灰度发布系统
- **多发布策略** - 支持线性、金丝雀、蓝绿三种发布模式
- **实时监控** - 发布过程中实时监控成功率、延迟、错误率
- **自动回滚** - 健康检查失败时自动回滚策略

### 可视化与集成
- **服务拓扑可视化** - 基于 Kiali 的服务拓扑图展示
- **OPA 策略引擎** - 集成 Open Policy Agent 进行策略评估
- **仪表盘** - 统一的安全态势展示和统计分析

## 技术栈

### 后端
- **语言**: Go 1.21+
- **Web 框架**: Gin
- **Istio 集成**: istio.io/client-go
- **Kubernetes 集成**: k8s.io/client-go
- **OPA 集成**: open-policy-agent/opa
- **配置管理**: Viper
- **日志**: Zap

### 前端
- **框架**: React 18 + TypeScript
- **UI 组件**: Material-UI 5
- **路由**: React Router 6
- **图表**: Recharts
- **可视化**: ReactFlow
- **HTTP 客户端**: Axios

## 项目结构

```
.
├── backend/                    # Go 后端
│   ├── cmd/
│   │   └── server/
│   │       └── main.go        # 服务入口
│   ├── internal/
│   │   ├── api/               # API 处理器
│   │   ├── config/            # 配置管理
│   │   ├── models/            # 数据模型
│   │   ├── istio/             # Istio API 集成
│   │   ├── opa/               # OPA 策略引擎
│   │   ├── analysis/          # 策略分析模块
│   │   ├── recommendation/    # 策略推荐引擎
│   │   ├── canary/            # 灰度发布管理
│   │   └── kiali/             # Kiali 集成
│   ├── go.mod
│   └── config.yaml
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── pages/             # 页面组件
│   │   ├── components/        # 通用组件
│   │   ├── services/          # API 服务
│   │   ├── types/             # TypeScript 类型
│   │   ├── App.tsx
│   │   └── index.tsx
│   ├── package.json
│   └── public/
└── README.md
```

## 快速开始

### 后端启动

```bash
cd backend

# 安装依赖
go mod download

# 启动服务
go run cmd/server/main.go
```

后端服务将在 `http://localhost:8080` 启动

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm start
```

前端应用将在 `http://localhost:3000` 启动

## API 接口

### 策略管理
- `GET /api/v1/policies` - 获取策略列表
- `POST /api/v1/policies` - 创建策略
- `GET /api/v1/policies/:id` - 获取策略详情
- `PUT /api/v1/policies/:id` - 更新策略
- `DELETE /api/v1/policies/:id` - 删除策略

### 策略分析
- `POST /api/v1/analysis/conflict` - 冲突检测
- `POST /api/v1/analysis/impact` - 影响分析

### 策略推荐
- `GET /api/v1/recommendations` - 获取推荐列表
- `POST /api/v1/recommendations/:id/apply` - 应用推荐

### 灰度发布
- `GET /api/v1/canary` - 获取发布列表
- `POST /api/v1/canary` - 创建发布
- `POST /api/v1/canary/:id/pause` - 暂停发布
- `POST /api/v1/canary/:id/resume` - 继续发布
- `POST /api/v1/canary/:id/promote` - 立即发布
- `POST /api/v1/canary/:id/rollback` - 回滚

### 服务拓扑
- `GET /api/v1/topology` - 获取服务拓扑
- `GET /api/v1/topology/namespaces` - 获取命名空间列表

### OPA 管理
- `POST /api/v1/opa/evaluate` - 评估策略
- `GET /api/v1/opa/policies` - 获取策略列表

## 配置说明

### 后端配置 (config.yaml)

```yaml
server:
  port: 8080
  mode: debug

kubernetes:
  kubeconfig: ~/.kube/config
  inCluster: false

istio:
  namespace: istio-system

opa:
  url: http://localhost:8181

kiali:
  url: http://localhost:20001

database:
  type: sqlite
  path: ./mesh-policy.db

log:
  level: info
  format: json
```

## 核心模块说明

### Istio 客户端

封装了 Istio CRD 的 CRUD 操作：
- `PeerAuthentication` - mTLS 策略
- `AuthorizationPolicy` - 授权策略
- `RequestAuthentication` - 请求认证

### OPA 集成

支持策略的动态管理和实时评估，可将 Istio 策略转换为 Rego 语言规则。

### 策略冲突检测

检测以下类型的冲突：
- mTLS 模式冲突（同一工作负载被多条策略设置不同模式）
- 授权动作冲突（同一请求同时被 ALLOW 和 DENY）
- JWT 颁发者重复（同一 issuer 配置多套规则）

### 策略影响分析

计算策略变更的风险等级：
- Critical - 影响关键服务或大量工作负载
- High - 可能导致服务中断
- Medium - 影响部分非关键功能
- Low - 无明显业务影响

### 灰度发布管理器

支持三种发布策略：
- **线性发布** - 按时间均匀增加流量
- **金丝雀发布** - 按比例阶梯式增加流量
- **蓝绿发布** - 新版本 100% 切换

## 许可证

MIT License
