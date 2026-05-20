# Prometheus 告警规则管理工具

一个功能完整的 Prometheus 告警规则管理系统，提供 Web 界面进行规则的增删改查、分组管理、版本控制、PromQL 语法校验、模拟测试等功能。

## 功能特性

### 核心功能
- **告警规则管理**：完整的 CRUD 操作，支持规则的创建、查看、编辑、删除
- **分组管理**：将规则按业务或系统进行分组管理
- **版本控制**：每次规则修改自动保存版本，支持历史版本查看和回滚
- **PromQL 语法校验**：实时校验 PromQL 表达式语法正确性
- **模拟测试**：输入模拟指标数据，验证告警规则是否会触发
- **批量导入导出**：支持 Prometheus 原生 YAML 格式和 JSON 格式的批量导入导出
- **Prometheus API 集成**：直接查询 Prometheus 数据、查看当前规则和告警状态

### 技术栈
- **后端**：Go + Gin + GORM + SQLite
- **前端**：React 18 + Ant Design + Monaco Editor
- **PromQL 解析**：官方 Prometheus promql 解析器

## 项目结构

```
.
├── backend/                    # Go 后端
│   ├── main.go                # 主程序入口
│   ├── go.mod                 # Go 模块依赖
│   ├── models/                # 数据模型
│   │   └── models.go          # 数据库表定义
│   ├── handlers/              # API 处理器
│   │   ├── group.go           # 分组管理
│   │   ├── rule.go            # 规则管理+版本+导入导出
│   │   ├── promql.go          # PromQL 校验和模拟
│   │   ├── prometheus.go      # Prometheus API 接入
│   │   └── analysis.go        # 性能分析、依赖分析、模板市场
│   ├── routes/                # 路由配置
│   │   └── routes.go          # API 路由定义
│   └── services/              # 核心服务
│       ├── promql.go          # PromQL 解析和模拟引擎
│       └── analysis.go        # 性能分析、依赖检测、模板数据
└── frontend/                   # React 前端
    ├── package.json           # 前端依赖
    ├── vite.config.js         # Vite 配置
    ├── index.html             # HTML 入口
    └── src/
        ├── main.jsx           # 入口文件
        ├── App.jsx            # 主应用组件
        ├── index.css          # 全局样式
        ├── api/
        │   └── client.js      # API 客户端
        └── pages/             # 页面组件
            ├── RulesPage.jsx       # 规则管理
            ├── GroupsPage.jsx      # 分组管理
            ├── SimulatePage.jsx    # 模拟测试
            ├── PrometheusPage.jsx  # Prometheus 集成
            └── ImportExportPage.jsx # 导入导出
```

## 快速开始

### 环境要求
- Go 1.21+
- Node.js 18+
- Prometheus (可选，用于集成功能)

### 1. 启动后端

```bash
cd backend

# 安装依赖
go mod tidy

# 编译运行
go run main.go
# 或编译后运行
go build -o server.exe .
./server.exe
```

后端服务将在 `http://localhost:8080` 启动

### 2. 启动前端

```bash
cd frontend

# 安装依赖
npm install
# 或使用 yarn
yarn install

# 启动开发服务器
npm run dev
```

前端服务将在 `http://localhost:3000` 启动

### 3. 配置 Prometheus 集成 (可选)

设置环境变量指向你的 Prometheus 实例：

```bash
# Windows
set PROMETHEUS_URL=http://your-prometheus:9090

# Linux/Mac
export PROMETHEUS_URL=http://your-prometheus:9090
```

## API 接口

### 分组管理
- `GET /api/groups` - 获取所有分组
- `POST /api/groups` - 创建分组
- `GET /api/groups/:id` - 获取分组详情
- `PUT /api/groups/:id` - 更新分组
- `DELETE /api/groups/:id` - 删除分组

### 规则管理
- `GET /api/rules` - 获取所有规则（可选 group_id 过滤）
- `POST /api/rules` - 创建规则
- `GET /api/rules/:id` - 获取规则详情
- `PUT /api/rules/:id` - 更新规则
- `DELETE /api/rules/:id` - 删除规则
- `GET /api/rules/:id/versions` - 获取规则版本历史
- `POST /api/rules/:id/versions/:versionId/restore` - 恢复到指定版本

### PromQL 服务
- `POST /api/promql/validate` - 校验 PromQL 语法
- `POST /api/promql/simulate` - 模拟测试告警规则

### 导入导出
- `POST /api/io/import` - 批量导入规则
- `GET /api/io/export` - 批量导出规则

### Prometheus 集成
- `GET /api/prometheus/rules` - 获取 Prometheus 当前规则
- `GET /api/prometheus/alerts` - 获取当前触发的告警
- `POST /api/prometheus/query` - 执行 PromQL 查询

## 核心功能说明

### PromQL 语法校验
使用官方 Prometheus promql 解析器进行语法校验，支持：
- 实时校验表达式语法
- 显示表达式类型（vector、scalar、matrix 等）
- 详细的错误信息定位

### 模拟测试引擎
支持输入自定义指标数据来测试告警规则：
- 自定义指标名称、标签和数值
- 支持标签匹配（=, !=, =~, !~）
- 支持聚合函数（sum, avg, min, max, count 等）
- 支持 rate、irate 等函数解析
- 实时显示匹配的指标和触发结果

### 版本管理
- 每次修改自动保存新版本
- 记录修改时间和变更说明
- 支持一键回滚到历史版本
- 版本对比查看

### 导入导出格式
支持 Prometheus 原生 YAML 格式：

```yaml
groups:
  - name: example
    rules:
      - alert: HighCPUUsage
        expr: cpu_usage > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High CPU usage detected
          description: CPU usage is above 80% for 5 minutes
```

## 增强功能使用指南

### PromQL 语法校验增强

使用官方 PromQL 解析器，提供详细的语法分析：

**请求：**
```json
POST /api/promql/validate
{
  "expr": "sum by (instance) (rate(cpu_usage_total[5m])) > 80"
}
```

**响应：**
```json
{
  "valid": true,
  "expr_type": "vector",
  "ast_info": {
    "type": "vector",
    "expr_string": "sum by (instance) (rate(cpu_usage_total[5m])) > 80",
    "metrics": ["cpu_usage_total"],
    "functions": ["rate"],
    "aggregations": ["sum"],
    "binary_operators": ["gt"]
  },
  "message": "PromQL syntax is valid"
}
```

### 时间序列模拟测试

模拟持续时间条件验证：

**请求：**
```json
POST /api/promql/simulate
{
  "expr": "cpu_usage > 80",
  "for": "5m",
  "time_series": [
    {
      "name": "cpu_usage",
      "labels": {"instance": "server-01"},
      "points": [
        {"timestamp": "2026-05-20T10:00:00Z", "value": 75},
        {"timestamp": "2026-05-20T10:01:00Z", "value": 85},
        {"timestamp": "2026-05-20T10:02:00Z", "value": 88},
        {"timestamp": "2026-05-20T10:03:00Z", "value": 90},
        {"timestamp": "2026-05-20T10:04:00Z", "value": 92},
        {"timestamp": "2026-05-20T10:05:00Z", "value": 95},
        {"timestamp": "2026-05-20T10:06:00Z", "value": 93}
      ]
    }
  ]
}
```

**响应：**
```json
{
  "firing": true,
  "firing_for": "5m0s",
  "duration_verified": true,
  "required_duration": "5m",
  "actual_duration": "5m0s",
  "matched_time_series": [...],
  "timeline": [
    {"timestamp": "2026-05-20T10:01:00Z", "event_type": "start_firing", "message": "cpu_usage started firing at 85.00"},
    {"timestamp": "2026-05-20T10:06:00Z", "event_type": "duration_met", "message": "cpu_usage met 5m0s duration requirement"}
  ],
  "message": "Alert firing for 5m0s! Duration condition met (5m required)"
}
```

### 生成测试数据

一键生成模拟数据：

**请求：**
```json
POST /api/promql/generate-test-data
{
  "name": "cpu_usage",
  "labels": {"instance": "server-01", "job": "node"},
  "duration": "10m",
  "interval": "30s",
  "pattern": "spike",
  "start_value": 40,
  "end_value": 95
}
```

**响应：**
```json
{
  "time_series": {
    "name": "cpu_usage",
    "labels": {"instance": "server-01", "job": "node"},
    "points": [
      {"timestamp": "2026-05-20T10:00:00Z", "value": 40},
      {"timestamp": "2026-05-20T10:00:30Z", "value": 40},
      ...
      {"timestamp": "2026-05-20T10:05:00Z", "value": 95},
      ...
    ]
  },
  "point_count": 20,
  "duration": "10m",
  "interval": "30s"
}
```

### 版本对比

对比历史版本与当前版本：

**请求：**
```
GET /api/rules/123/versions/456/compare
```

**响应：**
```json
{
  "current_version": 5,
  "target_version": 3,
  "change_count": 2,
  "differences": [
    {
      "field": "expr",
      "old_value": "cpu_usage > 80",
      "new_value": "cpu_usage > 90",
      "changed": true
    },
    {
      "field": "for",
      "old_value": "5m",
      "new_value": "10m",
      "changed": true
    },
    {
      "field": "name",
      "old_value": "HighCPUUsage",
      "new_value": "HighCPUUsage",
      "changed": false
    }
  ],
  "preview_rule": {...}
}
```

### 带确认的版本回滚

安全地恢复到历史版本：

**请求：**
```json
POST /api/rules/123/versions/456/restore-confirm
{
  "confirm": true,
  "change_log": "回滚到v3版本，修复v4版本的错误表达式"
}
```

**响应：**
```json
{
  "message": "Successfully restored to version 3",
  "rule": {...},
  "version": 6,
  "changes": [...]
}
```

## 数据库

使用 SQLite 作为嵌入式数据库，数据文件为 `alert_rules.db`，位于后端程序运行目录。

数据表：
- `alert_groups` - 告警分组
- `alert_rules` - 告警规则
- `alert_rule_versions` - 规则版本历史

## 开发说明

### 后端添加新功能
1. 在 `models/` 添加数据模型
2. 在 `services/` 添加业务逻辑
3. 在 `handlers/` 添加 API 处理器
4. 在 `routes/routes.go` 注册路由

### 前端添加新页面
1. 在 `src/pages/` 创建页面组件
2. 在 `src/App.jsx` 配置路由
3. 在侧边栏菜单添加导航项

## 常见问题

### Q: 启动后端时提示缺少依赖？
A: 确保在 backend 目录下运行 `go mod tidy` 安装所有依赖。

### Q: 前端无法连接后端？
A: 检查 `frontend/vite.config.js` 中的代理配置，确保后端端口正确。

### Q: Prometheus 集成不工作？
A: 确保 `PROMETHEUS_URL` 环境变量设置正确，且 Prometheus 实例可访问。

### Q: 如何修改后端端口？
A: 修改 `backend/main.go` 中的端口号，同时更新前端代理配置。

## 许可证

MIT License
