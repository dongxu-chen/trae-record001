# 配置密钥管理服务 (Key Management Service)

一个企业级密钥管理解决方案，支持密钥加密存储、自动轮转、访问审计，并提供Kubernetes CSI驱动实现应用透明接入。

## 架构概览

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React UI      │────▶│   Go API        │────▶│   HashiCorp     │
│  (Frontend)     │     │  (Backend)      │     │     Vault       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │                       │
                              ▼                       ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │    Database     │     │   AWS KMS       │
                        │   (SQLite/PG)   │     │  (Optional)     │
                        └─────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌─────────────────┐
                        │ Kubernetes CSI  │
                        │    Driver       │
                        └─────────────────┘
```

## 核心功能

### 1. 密钥管理 (Secret Management)
- 支持多种密钥类型：数据库密码、API密钥、证书、通用密码
- 版本控制：每次更新自动创建新版本
- 标签分类：支持自定义标签进行密钥分类
- 过期管理：支持设置密钥过期时间

### 2. 加密存储 (Encryption)
- **Vault Transit Engine**：AES-256-GCM加密
- **AWS KMS集成**：可选的云KMS加密
- **信封加密**：使用数据密钥加密，根密钥由KMS保护

### 3. 密钥轮转 (Key Rotation)
- 手动轮转：通过API/UI触发密钥更新
- 自动轮转：支持配置自动轮转策略
- 版本历史：保留历史版本可回溯

### 4. 访问审计 (Audit Logging)
- 完整审计日志：记录所有密钥操作
- 操作类型：CREATE/READ/UPDATE/DELETE/ROTATE
- 用户追踪：记录操作用户、IP地址、User Agent
- 统计分析：按操作类型统计访问情况

### 5. Kubernetes CSI驱动
- 透明接入：应用无需修改代码
- 自动挂载：密钥自动挂载为容器内文件
- 动态更新：支持密钥热更新
- 临时卷：支持Ephemeral Volume模式

## 快速开始

### 本地开发 (Docker Compose)

```bash
# 启动所有服务
make docker-up

# 查看服务状态
docker-compose ps

# 访问前端
open http://localhost:3000

# 访问API
curl http://localhost:8080/api/v1/health
```

### 手动运行

```bash
# 安装依赖
make deps

# 启动后端
make run

# 启动前端 (新终端)
make run-frontend
```

## API文档

### 密钥管理 API

#### 创建密钥
```bash
POST /api/v1/secrets
Content-Type: application/json
X-User: admin

{
  "name": "db-password",
  "description": "Production database password",
  "type": "database",
  "value": "my-secret-password",
  "labels": {
    "env": "production",
    "team": "backend"
  }
}
```

#### 获取密钥列表
```bash
GET /api/v1/secrets?limit=20&offset=0&type=database
```

#### 获取密钥详情
```bash
GET /api/v1/secrets/{id-or-name}
```

#### 更新密钥
```bash
PUT /api/v1/secrets/{id-or-name}
{
  "description": "Updated description",
  "value": "new-password"
}
```

#### 轮转密钥
```bash
POST /api/v1/secrets/{id-or-name}/rotate
{
  "new_value": "new-rotated-password"
}
```

#### 删除密钥
```bash
DELETE /api/v1/secrets/{id-or-name}
```

### 审计日志 API

```bash
GET /api/v1/audit/logs?limit=50&offset=0&user=admin&secret_id=xxx
GET /api/v1/audit/stats
```

## Kubernetes部署

### 1. 部署服务

```bash
# 创建命名空间和部署
make k8s-deploy

# 或者手动应用
kubectl apply -f k8s/keymgmt-service.yaml
kubectl apply -f k8s/csi-driver.yaml
```

### 2. 配置Vault Token Secret

```bash
kubectl create secret generic vault-token \
  --namespace keymgmt-system \
  --from-literal=token=your-vault-token
```

### 3. 在应用中使用CSI驱动

创建Pod并挂载密钥卷：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  containers:
  - name: my-app
    image: nginx
    volumeMounts:
    - name: db-secrets
      mountPath: "/secrets/db"
      readOnly: true
  volumes:
  - name: db-secrets
    csi:
      driver: secrets.keymgmt.io
      volumeAttributes:
        secretName: "db-password"
        secretNamespace: "default"
```

应用启动后，密钥将自动挂载到 `/secrets/db/` 目录下的文件中。

## 项目结构

```
.
├── backend/                    # Go 后端服务
│   ├── cmd/server/            # 服务入口
│   ├── internal/
│   │   ├── api/               # API 处理器和路由
│   │   ├── vault/             # Vault 集成
│   │   ├── kms/               # AWS KMS 集成
│   │   ├── audit/             # 审计服务
│   │   └── models/            # 数据模型
│   └── pkg/utils/             # 工具函数
├── csi-driver/                # Kubernetes CSI 驱动
│   ├── cmd/                   # 驱动入口
│   └── internal/
│       ├── driver/            # CSI 驱动实现
│       └── server/            # gRPC 服务
├── frontend/                  # React 前端
│   ├── src/
│   │   ├── components/        # UI 组件
│   │   ├── pages/             # 页面组件
│   │   ├── services/          # API 服务
│   │   └── types/             # TypeScript 类型
│   └── package.json
├── deploy/                    # 部署配置
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── Dockerfile.csi
│   └── nginx.conf
├── k8s/                       # Kubernetes 配置
│   ├── keymgmt-service.yaml
│   ├── csi-driver.yaml
│   └── example-pod.yaml
├── docker-compose.yml         # 本地开发环境
├── Makefile                   # 构建脚本
└── config.yaml                # 服务配置
```

## 配置说明

### config.yaml

```yaml
server:
  port: "8080"

database:
  path: "./data/secrets.db"

vault:
  address: "http://localhost:8200"
  token: "root"
  mount_path: "secret"

kms:
  region: "us-east-1"
  key_id: ""

audit:
  retention_days: 90
```

## 安全最佳实践

1. **Vault Token管理**：在生产环境中使用Vault Agent注入Token
2. **TLS加密**：为API服务配置SSL/TLS证书
3. **网络隔离**：将Vault和密钥服务部署在私有网络
4. **访问控制**：实现细粒度的RBAC权限控制
5. **定期轮转**：配置根密钥和服务账号密钥定期轮转
6. **审计监控**：将审计日志发送到集中日志系统

## 生产部署建议

1. 使用PostgreSQL替代SQLite
2. 部署高可用Vault集群
3. 启用AWS KMS作为根密钥保护
4. 配置Prometheus监控指标
5. 配置Grafana可视化仪表盘
6. 设置告警通知（密钥过期、异常访问等）

## 许可证

MIT License
