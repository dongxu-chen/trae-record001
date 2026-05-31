# 云资源标签合规性检查工具

一个用于检查云资源（ECS、RDS、OSS）标签合规性的全栈工具，支持多账号管理、自定义合规规则和标签自动补全建议。

## 功能特性

- 🌐 **多账号支持** - 同时管理多个云厂商账号
- 📋 **资源扫描** - 扫描 ECS、RDS、OSS 等云资源
- 🎯 **规则引擎** - 自定义标签合规规则（必填标签、禁止标签、正则匹配等）
- ✅ **合规检查** - 自动检测标签违规项并分类显示
- 💡 **智能建议** - 根据规则提供标签自动补全建议
- 📊 **数据可视化** - 仪表盘展示合规统计和趋势

## 技术栈

### 后端
- **Go 1.21+** - 高性能服务端语言
- **Gin** - Web 框架
- **YAML** - 配置文件格式

### 前端
- **React 18** - 用户界面框架
- **React Router** - 路由管理
- **原生 CSS** - 样式方案

## 项目结构

```
├── backend/                    # Go 后端
│   ├── cmd/
│   │   └── main.go            # 程序入口
│   ├── internal/
│   │   ├── api/               # API 路由层
│   │   │   └── router.go
│   │   ├── cloud/             # 云厂商集成层
│   │   │   ├── manager.go
│   │   │   └── mock_provider.go
│   │   ├── config/            # 配置管理
│   │   │   └── config.go
│   │   └── rules/             # 规则引擎
│   │       └── engine.go
│   ├── config/
│   │   ├── config.yaml        # 服务配置
│   │   └── rules.yaml         # 合规规则
│   └── go.mod
├── frontend/                   # React 前端
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── pages/             # 页面组件
│   │   │   ├── Dashboard.js
│   │   │   ├── Resources.js
│   │   │   ├── ResourceDetail.js
│   │   │   ├── Rules.js
│   │   │   └── Compliance.js
│   │   ├── services/          # API 服务
│   │   │   └── api.js
│   │   ├── App.js
│   │   └── index.js
│   └── package.json
└── README.md
```

## 快速开始

### 后端启动

1. 进入后端目录：
```bash
cd backend
```

2. 安装依赖：
```bash
go mod download
```

3. 启动服务：
```bash
go run cmd/main.go
```

服务将在 `http://localhost:8080` 启动

### 前端启动

1. 进入前端目录：
```bash
cd frontend
```

2. 安装依赖：
```bash
npm install
```

3. 启动开发服务器：
```bash
npm start
```

前端将在 `http://localhost:3000` 启动

## API 接口

### 健康检查
```
GET /api/v1/health
```

### 账号管理
```
GET /api/v1/accounts
```

### 资源管理
```
GET /api/v1/resources
GET /api/v1/resources?accountId=xxx&type=ECS
GET /api/v1/resources/:id/suggestions
```

### 规则管理
```
GET    /api/v1/rules
POST   /api/v1/rules
PUT    /api/v1/rules/:id
DELETE /api/v1/rules/:id
```

### 合规检查
```
GET /api/v1/compliance
GET /api/v1/compliance/summary
```

## 规则类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `required_tag` | 必填标签 | Environment 标签必须存在 |
| `forbidden_tag` | 禁止标签 | Owner 标签已废弃 |
| `tag_value_in_list` | 值列表匹配 | Environment 必须是 Production/Development/Testing 之一 |
| `tag_value_regex` | 正则匹配 | CostCenter 必须匹配 ^CC\d{3}$ |
| `case_sensitive` | 大小写敏感 | Environment 首字母必须大写 |

## 配置说明

### 账号配置 (config/config.yaml)

```yaml
accounts:
  - id: account-prod-001
    name: Production Account
    cloud: aliyun
    accessKey: your-access-key
    accessSecret: your-access-secret
    region: cn-hangzhou
```

### 规则配置 (config/rules.yaml)

```yaml
rules:
  - id: required-environment
    name: Required Environment Tag
    type: required_tag
    description: All resources must have an Environment tag
    key: Environment
    severity: high
    enabled: true
    values:
      - Production
      - Development
      - Testing
```

## 使用说明

1. **仪表盘** - 查看整体合规情况、资源统计和违规分布
2. **资源列表** - 浏览所有云资源，按账号、类型、状态筛选
3. **资源详情** - 查看单个资源的详细信息、违规项和标签建议
4. **规则管理** - 创建、编辑、启用/禁用合规规则
5. **合规检查** - 执行全面检查，查看所有违规项详情

## 扩展开发

### 添加新的云厂商 Provider

1. 在 `internal/cloud/` 下创建新的 provider 文件
2. 实现 `Provider` 接口：
```go
type Provider interface {
    GetResources(resourceType ResourceType) ([]Resource, error)
    GetAccountID() string
    GetAccountName() string
}
```

### 添加新的规则类型

1. 在 `internal/rules/engine.go` 中添加新的 RuleType
2. 在 `applyRule` 方法中实现对应的检查逻辑

## License

MIT
