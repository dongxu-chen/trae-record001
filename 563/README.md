# ETCD 集群备份恢复管理系统

一个完整的 ETCD 集群备份恢复工具，支持多集群管理、增量备份、加密存储、定时任务、恢复演练等功能。

## 功能特性

### 备份功能
- ✅ **完整备份**: 对整个 ETCD 集群进行全量快照备份
- ✅ **增量备份**: 基于前一次备份的差异备份，节省存储空间
- ✅ **备份加密**: AES-256-GCM 加密存储，保障数据安全
- ✅ **备份校验**: 定期校验备份文件完整性和一致性
- ✅ **多存储支持**: 支持本地文件系统和 S3 兼容对象存储

### 恢复功能
- ✅ **点-in-time 恢复**: 支持选择历史时间点进行恢复
- ✅ **恢复演练**: 不实际写入集群的恢复模拟
- ✅ **跨集群恢复**: 支持将备份恢复到不同的目标集群

### 管理功能
- ✅ **多集群管理**: 同时管理多个 ETCD 集群
- ✅ **定时任务**: 基于 Cron 表达式的定时备份
- ✅ **集群状态监控**: 实时监控集群健康状态
- ✅ **Web UI**: 现代化的 React 管理界面

## 技术栈

### 后端
- **Go 1.21+**: 主编程语言
- **ETCD Client v3**: ETCD API 客户端
- **Gin**: Web 框架
- **Cron**: 定时任务调度
- **MinIO SDK**: S3 兼容对象存储
- **AES-256-GCM**: 数据加密

### 前端
- **React 18**: UI 框架
- **Material UI**: 组件库
- **React Router**: 路由管理
- **Axios**: HTTP 客户端
- **Chart.js**: 数据可视化

## 项目结构

```
├── backend/                    # Go 后端
│   ├── cmd/
│   │   └── server/
│   │       └── main.go        # 主入口
│   ├── internal/
│   │   ├── api/                # REST API 接口
│   │   ├── backup/             # 备份恢复核心逻辑
│   │   ├── cluster/            # 集群管理
│   │   ├── encryption/         # 加密模块
│   │   ├── scheduler/          # 定时任务
│   │   └── storage/            # 存储抽象层
│   ├── pkg/
│   │   └── models/             # 数据模型
│   └── go.mod
└── frontend/                   # React 前端
    ├── src/
    │   ├── api/                # API 客户端
    │   ├── pages/              # 页面组件
    │   └── components/         # 通用组件
    ├── package.json
    └── vite.config.js
```

## 快速开始

### 环境要求
- Go 1.21+
- Node.js 18+
- ETCD 3.4+

### 后端启动

```bash
cd backend

# 安装依赖
go mod download

# 运行服务
go run cmd/server/main.go
```

服务将在 `http://localhost:8080` 启动

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

前端将在 `http://localhost:3000` 启动

## 配置说明

### 环境变量

#### 存储配置
```bash
# 存储类型: local 或 s3
STORAGE_TYPE=local

# 本地存储路径
STORAGE_LOCAL_PATH=./data/backups

# S3 配置
S3_ENDPOINT=s3.amazonaws.com
S3_BUCKET=etcd-backups
S3_REGION=us-east-1
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
```

#### 加密配置
```bash
# 启用加密
ENCRYPTION_ENABLED=true

# 加密密钥 (base64 编码)
ENCRYPTION_KEY=your-encryption-key
```

#### ETCD 集群配置
```bash
ETCD_CLUSTER_NAME=default
ETCD_USERNAME=root
ETCD_PASSWORD=your-password
```

## API 接口

### 集群管理
- `GET /api/v1/clusters` - 获取集群列表
- `POST /api/v1/clusters` - 添加集群
- `GET /api/v1/clusters/:id` - 获取集群详情
- `PUT /api/v1/clusters/:id` - 更新集群
- `DELETE /api/v1/clusters/:id` - 删除集群
- `GET /api/v1/clusters/:id/status` - 获取集群状态

### 备份管理
- `GET /api/v1/backups` - 获取备份列表
- `POST /api/v1/backups/full` - 创建完整备份
- `POST /api/v1/backups/incremental` - 创建增量备份
- `POST /api/v1/backups/:id/verify` - 校验备份
- `POST /api/v1/backups/:id/dryrun` - 恢复演练

### 恢复任务
- `GET /api/v1/restores` - 获取恢复任务列表
- `POST /api/v1/restores` - 创建恢复任务

### 定时任务
- `GET /api/v1/schedules` - 获取定时任务列表
- `POST /api/v1/schedules` - 创建定时任务
- `PUT /api/v1/schedules/:id` - 更新定时任务
- `DELETE /api/v1/schedules/:id` - 删除定时任务

## 使用示例

### 1. 添加 ETCD 集群

```bash
curl -X POST http://localhost:8080/api/v1/clusters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "production",
    "endpoints": ["http://etcd-1:2379", "http://etcd-2:2379"],
    "username": "root",
    "password": "your-password"
  }'
```

### 2. 创建完整备份

```bash
curl -X POST http://localhost:8080/api/v1/backups/full \
  -H "Content-Type: application/json" \
  -d '{"clusterId": "cluster-uuid"}'
```

### 3. 恢复备份

```bash
curl -X POST http://localhost:8080/api/v1/restores \
  -H "Content-Type: application/json" \
  -d '{
    "backupId": "backup-uuid",
    "targetClusterId": "target-cluster-uuid"
  }'
```

### 4. 创建定时备份任务

```bash
curl -X POST http://localhost:8080/api/v1/schedules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily-full-backup",
    "clusterId": "cluster-uuid",
    "cronExpr": "0 0 2 * * *",
    "backupType": "full",
    "retentionDays": 30,
    "enabled": true
  }'
```

## 安全建议

1. **启用备份加密**: 生产环境必须启用备份加密
2. **使用 TLS**: 配置 ETCD 集群使用 TLS 连接
3. **访问控制**: 保护 API 端点，使用认证和授权
4. **定期演练**: 定期进行恢复演练，确保备份可用
5. **异地备份**: 将备份存储在不同地理位置

## 故障排查

### 备份失败
- 检查 ETCD 集群连接状态
- 验证存储权限和空间
- 查看服务日志获取详细错误信息

### 恢复失败
- 确保目标集群可访问
- 验证备份文件完整性
- 检查目标集群版本兼容性

## License

MIT
