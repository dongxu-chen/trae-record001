# 数据库死锁自动解除工具

一个功能完整的数据库死锁自动检测和解除工具，支持 MySQL 和 PostgreSQL 数据库。

## 功能特性

- ✅ **死锁检测** - 自动检测数据库死锁，构建等待图识别死锁循环
- ✅ **规则引擎** - 可配置的死锁处理规则，支持条件匹配和动作执行
- ✅ **自动解除** - 自动 KILL 阻塞事务解除死锁（可配置策略）
- ✅ **手动解除** - 支持人工查看和手动解除死锁
- ✅ **影响评估** - 对 KILL 事务进行影响评估，提供业务建议
- ✅ **历史分析** - 死锁历史记录和统计分析
- ✅ **策略配置** - 灵活的检测策略和解除策略配置
- ✅ **Web UI** - 美观的 React 前端界面

## 技术栈

**后端 (Go):**
- Gin Web 框架
- 原生 database/sql 驱动
- 支持 MySQL 和 PostgreSQL

**前端 (React):**
- React 18
- React Router
- Recharts 图表库
- Lucide 图标库
- Vite 构建工具

## 项目结构

```
.
├── backend/                    # Go 后端
│   ├── config/                 # 配置模块
│   │   └── config.go
│   ├── database/               # 数据库连接和检测
│   │   └── connector.go
│   ├── models/                 # 数据模型
│   │   └── deadlock.go
│   ├── engine/                 # 核心引擎
│   │   ├── detector.go         # 死锁检测器
│   │   └── rule_engine.go      # 规则引擎
│   ├── api/                    # API 处理器
│   │   └── handlers.go
│   ├── main.go                 # 主程序入口
│   └── go.mod
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── pages/              # 页面组件
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Deadlocks.jsx
│   │   │   ├── History.jsx
│   │   │   ├── Rules.jsx
│   │   │   ├── Statistics.jsx
│   │   │   └── Config.jsx
│   │   ├── api/                # API 客户端
│   │   │   └── client.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── README.md
```

## 快速开始

### 1. 启动后端服务

```bash
cd backend
go mod tidy
go run main.go
```

后端服务将在 `http://localhost:8080` 启动。

### 2. 启动前端服务

```bash
cd frontend
npm install
npm run dev
```

前端服务将在 `http://localhost:3000` 启动。

### 3. 配置数据库连接

打开浏览器访问 `http://localhost:3000/config`，配置数据库连接信息：

- 数据库类型：MySQL 或 PostgreSQL
- 主机地址
- 端口
- 用户名和密码
- 数据库名

### 4. 开始检测

在仪表板页面点击"开始检测"按钮启动死锁检测。

## 核心功能说明

### 死锁检测原理

工具通过以下方式检测死锁：

1. 定期查询数据库的锁等待信息
2. 构建事务等待关系图
3. 使用 DFS 算法检测循环依赖
4. 识别死锁事务组

### 解除策略

支持以下 KILL 策略：

- **最年轻事务** - KILL 执行时间最短的事务（回滚成本最低）
- **最老事务** - KILL 执行时间最长的事务（可能是问题根源）
- **最小工作量** - KILL 工作量最小的事务

### 规则引擎

默认内置规则：

1. **长事务杀手** - 自动 KILL 运行超过 5 分钟的事务
2. **高影响保护** - 保护影响超过 10000 行的事务不被自动 KILL
3. **系统用户排除** - 不 KILL 系统用户的事务

可以在"规则引擎"页面添加自定义规则。

### 影响评估

每次 KILL 操作前会进行影响评估：

- 影响行数
- 预计回滚时间
- 业务影响等级（低/中/高）
- 操作建议

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 健康检查 |
| GET | /api/deadlocks/current | 获取当前死锁 |
| GET | /api/deadlocks/history | 获取历史死锁 |
| POST | /api/deadlocks/:id/resolve | 解除死锁 |
| GET | /api/rules | 获取规则列表 |
| POST | /api/rules | 创建规则 |
| PUT | /api/rules/:id | 更新规则 |
| DELETE | /api/rules/:id | 删除规则 |
| GET | /api/config | 获取配置 |
| PUT | /api/config | 更新配置 |
| GET | /api/statistics | 获取统计数据 |
| POST | /api/detector/start | 启动检测器 |
| POST | /api/detector/stop | 停止检测器 |

## 注意事项

1. **权限要求**：数据库用户需要有 `PROCESS` 和 `SUPER` 权限才能查看和 KILL 其他事务
2. **谨慎启用自动 KILL**：建议先在测试环境验证，确认规则正确后再启用自动模式
3. **监控告警**：建议配合监控系统使用，死锁发生时及时通知相关人员
4. **性能影响**：检测间隔建议设置在 5 秒以上，避免对数据库造成额外压力

## License

MIT
