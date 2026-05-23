# 分布式任务调度系统

一个基于 Go + Redis + MySQL 实现的分布式任务调度系统核心模块。

## 功能特性

- **任务注册**: 通过 HTTP API 注册任务
- **任务触发**: 支持 Cron 表达式和固定间隔触发
- **任务依赖**: DAG 有向无环图 + 拓扑排序，支持深层任务依赖
- **失败重试**: 指数退避重试机制（基数为2，最大间隔1小时）
- **超时控制**: 每个任务可配置超时时间，超时自动标记失败
- **节点健康检查**: 自动检测故障节点，任务重新分配
- **调度审计日志**: 完整记录调度决策、重试次数、执行耗时
- **至少执行一次**: 保证任务至少执行一次
- **执行历史**: 按月分表存储，自动路由查询
- **分布式**: 基于 Redis 分布式锁，支持多实例部署

## 技术栈

- **Go 1.21+**: 主编程语言
- **Redis**: 分布式锁、任务队列
- **MySQL**: 任务元数据、执行历史存储
- **Gin**: HTTP 框架
- **GORM**: ORM 框架
- **robfig/cron**: Cron 表达式解析

## 项目结构

```
.
├── cmd/
│   └── scheduler/          # 主程序入口
├── config/                 # 配置文件和数据库schema
├── examples/               # 示例脚本
├── internal/
│   ├── models/             # 数据模型
│   ├── store/              # 数据存储层
│   ├── scheduler/          # 调度器核心
│   ├── executor/           # 任务执行器
│   └── http/
│       ├── handlers/       # HTTP处理器
│       └── server.go       # HTTP服务器
└── pkg/
    ├── lock/               # 分布式锁
    └── retry/              # 重试机制
```

## 快速开始

### 1. 环境要求

- Go 1.21+
- MySQL 5.7+
- Redis 5.0+

### 2. 数据库初始化

```bash
mysql -u root -p < config/schema.sql
```

### 3. 配置环境变量

```bash
export MYSQL_DSN="root:password@tcp(127.0.0.1:3306)/scheduler?charset=utf8mb4&parseTime=True&loc=Local"
export REDIS_ADDR="127.0.0.1:6379"
export REDIS_PASSWORD=""
export HTTP_PORT=":8080"
export SCHEDULER_ID="scheduler-1"
```

### 4. 编译运行

```bash
go mod tidy
go build -o scheduler.exe ./cmd/scheduler
./scheduler.exe
```

## API 接口

### 任务管理

#### 创建任务
```http
POST /api/v1/tasks
Content-Type: application/json

{
    "name": "定时日志任务",
    "description": "每分钟执行一次",
    "task_type": "log",
    "payload": "{\"message\": \"任务执行了\", \"level\": \"INFO\"}",
    "trigger_type": "cron",
    "cron_expr": "0 * * * * *",
    "max_retries": 3,
    "retry_delay": 5,
    "timeout_sec": 300
}
```

**Trigger Type 说明:**
- `cron`: Cron 表达式触发
- `interval`: 固定间隔触发（秒）
- `manual`: 手动触发

**Cron 表达式格式:**
```
┌───────────── 秒 (0 - 59)
│ ┌───────────── 分 (0 - 59)
│ │ ┌───────────── 时 (0 - 23)
│ │ │ ┌───────────── 日 (1 - 31)
│ │ │ │ ┌───────────── 月 (1 - 12)
│ │ │ │ │ ┌───────────── 周几 (0 - 6) (周日=0)
│ │ │ │ │ │
│ │ │ │ │ │
* * * * * *
```

#### 获取任务列表
```http
GET /api/v1/tasks?offset=0&limit=20
```

#### 获取单个任务
```http
GET /api/v1/tasks/{id}
```

#### 更新任务
```http
PUT /api/v1/tasks/{id}
Content-Type: application/json
```

#### 暂停任务
```http
DELETE /api/v1/tasks/{id}
```

#### 手动触发任务
```http
POST /api/v1/tasks/{id}/trigger
```

### 执行历史

#### 获取任务执行历史
```http
GET /api/v1/tasks/{id}/executions?offset=0&limit=20
```

#### 获取所有执行记录
```http
GET /api/v1/executions?offset=0&limit=20
```

#### 获取单个执行记录
```http
GET /api/v1/executions/{id}
```

### 健康检查
```http
GET /health
```

## 使用示例

### 1. 创建间隔任务

```bash
curl -X POST http://localhost:8080/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "每30秒任务",
    "task_type": "log",
    "payload": "{\"message\": \"间隔任务\", \"level\": \"INFO\"}",
    "trigger_type": "interval",
    "interval_sec": 30
  }'
```

### 2. 创建任务依赖链

```bash
# 创建任务 A
TASK_A=$(curl -s -X POST http://localhost:8080/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "任务A",
    "task_type": "log",
    "payload": "{\"message\": \"任务A完成\", \"level\": \"INFO\"}",
    "trigger_type": "manual"
  }' | grep -o '"id":"[^"]*"' | cut -d'"' -f4)

# 创建任务 B，依赖任务 A
curl -X POST http://localhost:8080/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "任务B",
    "task_type": "log",
    "payload": "{\"message\": \"任务B执行\", \"level\": \"INFO\"}",
    "trigger_type": "manual",
    "dependencies": "'"$TASK_A"'"
  }'

# 触发任务 A，完成后自动触发任务 B
curl -X POST http://localhost:8080/api/v1/tasks/$TASK_A/trigger
```

## 核心设计

### 1. 分布式调度

- 使用 Redis 分布式锁实现 Leader 选举
- 只有 Leader 节点负责调度任务
- 任务分发到 Redis 队列
- 所有 Worker 节点从队列消费任务

### 2. 至少执行一次保证

- 任务执行前获取分布式锁
- 执行超时后自动恢复
- 失败任务根据重试策略重新调度

### 3. 指数退避重试

重试间隔计算公式:
```
delay = base_delay * (2 ^ attempt)
```

- **基数**: 固定为 2
- **最大延迟**: 3600 秒（1小时）
- **默认最大重试次数**: 5次

重试序列示例（基础延迟1秒）:
| 重试次数 | 延迟时间 |
|---------|---------|
| 第1次 | 1秒 |
| 第2次 | 2秒 |
| 第3次 | 4秒 |
| 第4次 | 8秒 |
| 第5次 | 16秒 |
| ... | ... |
| 最大 | 3600秒 |

### 4. DAG 任务依赖调度

- 使用有向无环图 (DAG) 管理任务依赖关系
- 拓扑排序预先计算执行顺序
- 支持超过10层的深层依赖链
- 自动检测循环依赖
- 依赖检查从 O(n) 优化到 O(1)

**架构优势**:
- 避免遍历所有任务检查依赖
- 预先计算执行顺序，调度延迟稳定
- 支持批量任务的并行执行优化

### 5. 按月分表存储

执行历史按月自动分表，表名格式: `task_executions_YYYYMM`

**自动分表特性**:
- 启动时自动创建未来3个月分表
- 运行时动态创建分表
- 查询时自动路由到对应分表
- 支持跨6个月范围的联合查询

**分表管理 API**:
```go
store.CreateNextMonthPartition()    // 创建下月分表
store.IsPartitioningEnabled()       // 检查是否启用分表
```

## 扩展任务类型

```go
// 注册自定义任务处理器
executor.RegisterHandler("custom", func(ctx context.Context, payload string) (string, error) {
    // 自定义业务逻辑
    return "success", nil
})
```

## 多实例部署

启动多个实例，使用不同的 `SCHEDULER_ID`:

```bash
# 实例 1
SCHEDULER_ID=scheduler-1 ./scheduler

# 实例 2
SCHEDULER_ID=scheduler-2 ./scheduler
```

系统自动进行 Leader 选举，只有一个实例负责调度，所有实例都可以执行任务。

## License

MIT
