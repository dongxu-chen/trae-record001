# Redis 键空间通知处理工具

一个完整的 Redis 键空间通知处理系统，支持订阅 Redis 的键过期、删除、新增事件，并触发业务回调。

## 功能特性

- ✅ **多数据库支持**: 同时监听多个 Redis 数据库
- ✅ **事件过滤**: 支持按键前缀、事件类型过滤事件
- ✅ **重试机制**: 指数退避重试队列，处理失败自动重试
- ✅ **业务回调**: 支持缓存清除、数据同步等 Webhook 回调
- ✅ **实时监控**: React 前端面板，实时查看事件统计和详情
- ✅ **REST API**: 完整的 HTTP API 接口

## 技术栈

### 后端
- Go 1.21+
- Redis Pub/Sub
- Gin (HTTP 框架)
- Zap (日志)

### 前端
- React 18
- Axios
- Recharts (图表)

## 项目结构

```
.
├── backend/                 # Go 后端
│   ├── main.go             # 程序入口
│   ├── config/             # 配置
│   ├── models/             # 数据模型
│   ├── redis/              # Redis 客户端和订阅
│   ├── processor/          # 事件处理器
│   ├── retry/              # 重试队列
│   ├── api/                # HTTP API
│   └── logger/             # 日志
├── frontend/               # React 前端
│   ├── src/
│   │   ├── components/     # React 组件
│   │   ├── App.js          # 主应用
│   │   └── index.js        # 入口
│   └── package.json
└── README.md
```

## 快速开始

### 前置要求

- Redis 5.0+ (需启用键空间通知)
- Go 1.21+
- Node.js 16+

### 1. 配置 Redis

确保 Redis 已启用键空间通知：

```bash
redis-cli config set notify-keyspace-events Exg
```

或者在 `redis.conf` 中添加：
```
notify-keyspace-events Exg
```

### 2. 启动后端

```bash
cd backend
go mod download
go run main.go
```

后端服务默认运行在 `http://localhost:8081`

### 3. 启动前端

```bash
cd frontend
npm install
npm start
```

前端服务默认运行在 `http://localhost:3000`

## 配置说明

### Redis 配置

在 `backend/config/config.go` 中修改：

```go
Redis: RedisConfig{
    Address:   "localhost:6379",    // Redis 地址
    Password:  "",                  // 密码（可选）
    Databases: []int{0, 1, 2},      // 监听的数据库
}
```

### 事件过滤

```go
Filter: EventFilter{
    Enabled:       true,
    IncludePrefix: []string{"user:", "order:"},  // 只处理这些前缀
    ExcludePrefix: []string{"temp:"},            // 排除这些前缀
    EventTypes:    []string{"expired", "del", "set"},  // 监听的事件类型
}
```

### 重试配置

```go
Retry: RetryConfig{
    Enabled:       true,
    MaxAttempts:   3,                // 最大重试次数
    InitialDelay:  time.Second,      // 初始延迟
    MaxDelay:      time.Second * 30, // 最大延迟
    BackoffFactor: 2.0,              // 退避因子
}
```

### 回调配置

```go
Callback: CallbackConfig{
    CacheClearURL: "http://your-service/api/cache/clear",  // 过期/删除时调用
    DataSyncURL:   "http://your-service/api/data/sync",    // 新增/更新时调用
    Timeout:       time.Second * 10,
}
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/stats` | 获取统计数据 |
| GET | `/api/events` | 获取事件列表 |
| DELETE | `/api/events` | 清空事件记录 |
| GET | `/api/config` | 获取配置 |
| PUT | `/api/config` | 更新配置 |
| GET | `/api/redis/status` | Redis 连接状态 |

## 事件类型

| 事件类型 | 触发时机 | 回调动作 |
|----------|----------|----------|
| `expired` | 键过期 | 清除缓存 |
| `del` | 键被删除 | 清除缓存 |
| `set` | 键被设置/更新 | 数据同步 |

## 回调请求格式

Webhook 回调将发送 POST 请求，请求体格式：

```json
{
  "event_type": "expired",
  "key": "user:123",
  "db": 0,
  "timestamp": 1717234567
}
```

## 前端功能

- **实时统计**: 总事件数、成功/失败数、重试队列大小
- **事件分布**: 饼图展示过期/删除/新增事件比例
- **事件列表**: 最近事件详情，包括键名、数据库、处理状态
- **Redis 状态**: 实时显示各数据库连接状态
- **自动刷新**: 每 3 秒自动更新数据

## 代码参考

### 核心文件

- [main.go](file:///d:/Trae/project/record001/648/backend/main.go) - 程序入口
- [subscriber.go](file:///d:/Trae/project/record001/648/backend/redis/subscriber.go) - Redis PubSub 订阅
- [processor.go](file:///d:/Trae/project/record001/648/backend/processor/processor.go) - 事件处理器
- [queue.go](file:///d:/Trae/project/record001/648/backend/retry/queue.go) - 重试队列
- [callback.go](file:///d:/Trae/project/record001/648/backend/processor/callback.go) - 业务回调
- [App.js](file:///d:/Trae/project/record001/648/frontend/src/App.js) - React 主应用

## License

MIT
