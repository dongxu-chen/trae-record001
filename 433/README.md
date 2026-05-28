# Kubernetes Cost Allocation Tool

一个基于Go和React的Kubernetes成本分配工具，用于分析集群资源使用情况，按命名空间、标签、项目进行分账计算。

## 功能特性

### 核心功能
- **多维度成本分析**: 按命名空间、项目、标签维度分摊成本
- **资源类型覆盖**: 支持CPU、内存、存储、网络流量的成本计算
- **自定义分摊系数**: 支持为不同环境（生产/预发布/开发）设置不同的成本系数
- **闲置资源检测**: 自动识别未充分利用的资源，提供优化建议
- **成本预测**: 基于历史使用数据预测未来成本趋势
- **云厂商账单集成**: 支持AWS Cost Explorer API获取实际账单数据

### 技术栈
- **后端**: Go + Gin + K8s Client Go + Prometheus Client
- **前端**: React + TypeScript + Ant Design + Recharts
- **数据源**: Kubernetes API + Prometheus + Cloud Provider Billing API

## 项目结构

```
.
├── cmd/
│   └── server/
│       └── main.go              # 后端服务入口
├── internal/
│   ├── api/                     # REST API层
│   │   └── router.go
│   ├── config/                  # 配置管理
│   │   └── config.go
│   ├── k8sclient/               # K8s API客户端
│   │   └── client.go
│   ├── promclient/              # Prometheus客户端
│   │   └── client.go
│   ├── cost/                    # 成本计算引擎
│   │   └── calculator.go
│   └── cloud/                   # 云厂商API集成
│       └── aws.go
├── frontend/                    # React前端
│   ├── src/
│   │   ├── pages/               # 页面组件
│   │   ├── services/            # API服务
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── package.json
├── config.yaml                  # 配置文件
└── go.mod
```

## 快速开始

### 前置要求
- Go 1.21+
- Node.js 18+
- Kubernetes集群访问权限 (kubeconfig)
- Prometheus服务 (可选，用于获取实时metrics)
- AWS凭据 (可选，用于获取账单数据)

### 1. 配置

编辑 `config.yaml`:

```yaml
server:
  port: 8080

kubernetes:
  kubeconfig: "~/.kube/config"    # 留空则使用in-cluster配置
  inCluster: false

prometheus:
  address: "http://prometheus:9090"

cost:
  cpuPerCoreHour: 0.05            # CPU每核心小时成本
  memoryPerGBHour: 0.01           # 内存每GB小时成本
  storagePerGBHour: 0.001         # 存储每GB小时成本
  networkPerGB: 0.02              # 网络每GB成本
  idleThreshold: 0.3              # 闲置资源阈值 (30%)
  customFactors:
    production: 1.2               # 生产环境系数
    staging: 1.0                  # 预发布环境系数
    development: 0.5              # 开发环境系数

cloud:
  provider: "aws"
  region: "us-east-1"
  aws:
    accessKey: ""                 # 可选，使用环境变量更安全
    secretKey: ""
```

### 2. 启动后端服务

```bash
# 安装依赖
go mod download

# 运行服务
go run cmd/server/main.go
```

API服务将在 `http://localhost:8080` 启动

### 3. 启动前端服务

```bash
cd frontend

# 安装依赖
npm install

# 开发模式运行
npm run dev
```

前端将在 `http://localhost:3000` 启动

## API接口

### 健康检查
```
GET /api/v1/health
```

### 成本分析
```
POST /api/v1/cost/namespace       # 按命名空间分析成本
POST /api/v1/cost/project         # 按项目分析成本
POST /api/v1/cost/label           # 按标签分析成本
```

### 资源优化
```
GET  /api/v1/cost/idle            # 获取闲置资源
GET  /api/v1/optimizations        # 获取优化建议
POST /api/v1/cost/predict         # 成本预测
```

### 云账单
```
POST /api/v1/billing/current      # 当前账单
POST /api/v1/billing/forecast     # 账单预测
POST /api/v1/billing/services     # 按服务分类的账单
```

## 成本计算说明

### 公式
```
总成本 = CPU成本 + 内存成本 + 存储成本 + 网络成本
```

### 各资源成本计算
- **CPU成本**: `CPU使用量(核) * CPU单价 * 时长 * 环境系数`
- **内存成本**: `内存使用量(GB) * 内存单价 * 时长 * 环境系数`
- **存储成本**: `存储容量(GB) * 存储单价 * 时长 * 环境系数`
- **网络成本**: `网络流量(GB) * 网络单价 * 环境系数`

### 自定义系数
根据命名空间的 `environment` 标签自动应用系数:
- `environment=production` → 1.2x
- `environment=staging` → 1.0x
- `environment=development` → 0.5x

## 前端功能

1. **Dashboard**: 总览成本概览、命名空间数量、潜在节省
2. **Namespace Costs**: 各命名空间的详细成本分析，支持图表可视化
3. **Project Costs**: 按项目标签聚合成本
4. **Label Costs**: 按自定义标签聚合成本
5. **Idle Resources**: 闲置资源检测和浪费成本统计
6. **Optimizations**: 优化建议和预估节省金额
7. **Predictions**: 基于历史数据的成本趋势预测

## 安全说明

- 不要将敏感信息（如AWS密钥）直接提交到代码仓库
- 建议使用环境变量或K8s Secrets管理敏感配置
- API服务默认没有认证，生产环境请添加适当的安全措施

## License

MIT
