# DB Guardian - 数据库连接风暴防护系统

一个功能完整的数据库连接风暴防护工具，提供实时监控、智能限流和连接分析功能。

## 功能特性

### 核心功能
- **数据库代理** - 透明拦截所有数据库连接
- **连接风暴检测** - 实时监控连接速率，自动检测异常
- **智能限流** - 连接池限流 + 客户端IP限流
- **空闲连接释放** - 自动清理超时空闲连接

### 分析功能
- **慢建连检测** - 识别建立时间过长的连接
- **连接泄漏分析** - 检测潜在的连接泄漏
- **连接趋势分析** - 实时展示连接数变化趋势

### 管理功能
- **React 监控仪表盘** - 可视化实时数据
- **WebSocket 实时推送** - 秒级数据更新
- **控制面板** - 动态调整限流配置
- **告警中心** - 统一管理异常事件

## 项目结构

```
.
├── cmd/
│   └── main.go              # 程序入口
├── internal/
│   ├── api/
│   │   └── server.go        # HTTP API & WebSocket 服务
│   ├── config/
│   │   └── config.go        # 配置管理
│   ├── limiter/
│   │   └── limiter.go       # 限流器模块
│   └── proxy/
│       ├── proxy.go         # 数据库代理核心
│       └── analyzer.go      # 连接分析器
├── pkg/
│   └── logger/
│       └── logger.go        # 日志工具
├── web/                     # React 前端
│   ├── src/
│   │   ├── components/      # UI 组件
│   │   ├── hooks/           # React Hooks
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
├── go.mod
└── .env.example
```

## 快速开始

### 前置要求
- Go 1.21+
- Node.js 18+
- MySQL 数据库 (可选，用于实际代理)

### 1. 启动后端服务

```bash
# 复制配置文件
cp .env.example .env

# 修改 .env 配置，指向你的数据库

# 安装依赖
go mod download

# 运行服务
go run cmd/main.go
```

后端服务将在以下端口启动：
- 代理端口: 3307 (应用连接此端口)
- API 端口: 8080 (管理后台 API)

### 2. 启动前端服务

```bash
cd web

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:3000 查看监控仪表盘。

## 配置说明

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| LOG_LEVEL | 日志级别 (debug/info/warn/error) | info |
| PROXY_HOST | 代理监听地址 | 0.0.0.0 |
| PROXY_PORT | 代理监听端口 | 3307 |
| DB_HOST | 目标数据库地址 | localhost |
| DB_PORT | 目标数据库端口 | 3306 |
| MAX_TOTAL_CONN | 最大总连接数 | 500 |
| MAX_PER_CLIENT | 单IP最大连接数 | 50 |
| RATE_LIMIT | 连接速率限制 (个/分钟) | 100 |
| SLOW_CONN_THRESHOLD | 慢建连阈值 | 5s |
| LEAK_THRESHOLD | 泄漏检测阈值 | 30m |
| IDLE_TIMEOUT | 空闲连接超时 | 10m |
| STORM_THRESHOLD | 风暴检测阈值 | 50 |

## API 接口

### 统计数据
- `GET /api/stats` - 获取系统统计
- `GET /api/connections` - 获取活跃连接列表
- `GET /api/slow-connections` - 慢建连记录
- `GET /api/leak-candidates` - 连接泄漏候选
- `GET /api/alerts` - 告警列表
- `GET /api/trend` - 连接趋势数据
- `GET /api/limiter` - 限流器状态
- `GET /api/clients` - 客户端统计

### 控制操作
- `POST /api/connections/release` - 释放空闲连接
- `POST /api/limiter/config` - 更新限流配置

### WebSocket
- `GET /ws` - 实时统计推送

## 使用方式

### 1. 配置应用连接
将应用的数据库连接地址改为代理地址：

```
# 原连接
mysql://user:pass@localhost:3306/dbname

# 代理连接
mysql://user:pass@localhost:3307/dbname
```

### 2. 监控仪表盘
打开前端页面，查看：
- 实时连接数和速率
- 慢建连和泄漏告警
- 连接趋势图表
- 客户端连接分布

### 3. 应急处理
在控制面板中可以：
- 调整最大连接数限制
- 手动释放空闲连接
- 查看系统状态详情

## 工作原理

### 连接风暴防护流程

```
应用请求 → 代理接收 → 客户端限流检查 → 连接池限流检查
                ↓
          连接分析记录 → 风暴检测 → [触发保护]
                ↓
          转发到真实数据库 ← 允许连接
```

### 风暴检测机制

系统监控最近 N 个连接的时间间隔：
- 如果 N 个连接在 10 秒内完成 → 判定为风暴
- 触发保护：自动将最大连接数减半
- 5 分钟后恢复正常阈值

## 技术栈

**后端:**
- Go 1.21
- Gin (HTTP 框架)
- Gorilla WebSocket
- 原生 TCP 代理

**前端:**
- React 18
- Vite
- Tailwind CSS
- Recharts (图表)
- Lucide React (图标)

## 注意事项

1. **生产部署**: 建议在代理前增加负载均衡
2. **性能影响**: 代理会增加约 1-3ms 的连接延迟
3. **SSL/TLS**: 当前版本不支持 SSL 连接代理
4. **MySQL 协议**: 代理工作在 TCP 层，兼容 MySQL 协议

## 许可证

MIT License
