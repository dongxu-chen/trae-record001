# 智能定时任务调度器

基于 Go + etcd + Redis + PostgreSQL 实现的高可用分布式定时任务调度系统。

## 功能特性

- **高可用调度**: 多节点互备，基于 etcd 实现 Leader 选举
- **负载均衡**: 自动在各节点间均衡任务分配
- **任务分片**: 支持大数据量任务的分片执行
- **错过任务补偿**: 自动检测并重新调度错过的任务
- **故障恢复**: 节点宕机时自动将任务重新分配给其他节点
- **优先级调度**: 支持任务优先级配置
- **重试机制**: 失败任务自动指数退避重试

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                     HTTP API Layer                      │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  Scheduler Core                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ Leader   │  │ Task     │  │ Load     │  │ Missed │ │
│  │ Election │  │ Scanner  │  │ Balance  │  │ Tasks  │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│    etcd      │    │    Redis     │    │  PostgreSQL  │
│  - 服务发现  │    │  - 任务队列  │    │  - 任务存储  │
│  - 分布式锁  │    │  - 分片队列  │    │  - 执行记录  │
│  - Leader选  │    │  - 缓存      │    │  - 节点状态  │
│    举        │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
```

## 快速开始

### 1. 启动依赖服务

```bash
docker-compose up -d
```

### 2. 编译运行

```bash
go mod download
go run main.go
```

### 3. 启动多节点

```bash
# 节点1
go run main.go -node-id node-1

# 节点2
go run main.go -node-id node-2

# 节点3
go run main.go -node-id node-3
```

## API 接口

### 创建任务

```bash
POST /api/v1/tasks
Content-Type: application/json

{
  "name": "daily_report",
  "cron_expr": "0 0 1 * * ?",
  "task_type": "data_processing",
  "payload": {"source": "database", "target": "s3"},
  "shard_key": "user_data",
  "shard_total": 5,
  "priority": 5,
  "max_retries": 3
}
```

### 查询任务

```bash
GET /api/v1/tasks/:id
```

### 暂停任务

```bash
POST /api/v1/tasks/:id/pause
```

### 恢复任务

```bash
POST /api/v1/tasks/:id/resume
```

### 删除任务

```bash
DELETE /api/v1/tasks/:id
```

### 获取统计信息

```bash
GET /api/v1/stats
```

### 提交分片任务

```bash
POST /api/v1/shards
Content-Type: application/json

{
  "shard_key": "batch_process_20240101",
  "payload": {"batch_date": "2024-01-01"}
}
```

## 配置说明

### config.yaml

```yaml
server:
  host: "0.0.0.0"
  port: 8080
  node_id: "node-1"

etcd:
  endpoints:
    - "localhost:2379"
  dial_timeout: 5000      # 连接超时(ms)
  lease_ttl: 30           # 租约TTL(秒)
  root_prefix: "/scheduler"

redis:
  addr: "localhost:6379"
  password: ""
  db: 0
  pool_size: 100

postgres:
  host: "localhost"
  port: 5432
  user: "scheduler"
  password: "scheduler123"
  dbname: "scheduler"
  max_connections: 100

scheduler:
  scan_interval: 1000              # 任务扫描间隔(ms)
  balance_interval: 30000          # 负载均衡间隔(ms)
  retry_interval: 5000             # 重试间隔(ms)
  max_retries: 3                   # 默认最大重试次数
  shard_size: 1000                 # 默认分片大小
  miss_compensation_threshold: 300 # 错过任务阈值(秒)
  hash_slot_count: 16384           # 哈希槽总数(默认16384)
  heartbeat_check_interval: 3000   # 心跳检测间隔(ms), 每3秒检测一次
  heartbeat_timeout: 10000         # 心跳超时时间(ms), 10秒无响应标记离线
```

## 核心组件说明

### 1. 任务调度 (Scheduler)

- **Leader 选举**: 基于 etcd 分布式锁实现，只有 Leader 节点负责全局任务调度
- **任务扫描**: 定期扫描数据库中到期的任务，加入 Redis 队列
- **延迟队列**: 使用 Redis ZSet 实现延迟任务，到期后移至就绪队列
- **Worker 池**: 多协程并发执行任务

### 2. 负载均衡 (Load Balancer)

- 定期统计各节点任务数
- 计算平均负载和阈值
- 将过载节点的低优先级任务迁移到轻载节点
- 基于分片的任务可以独立调度

### 3. 任务分片 (Task Sharding)

- 创建任务时指定 `shard_total` 自动创建多个分片任务
- 每个分片独立调度和执行
- 支持基于 `shard_key` 的分组执行

### 4. 故障恢复 (Fault Tolerance)

- 节点心跳检测 (基于 etcd 租约)
- 宕机节点任务自动重新分配
- 错过执行时间的任务自动补偿调度
- 执行失败任务指数退避重试

## 扩展任务类型

```go
scheduler.RegisterHandler("my_custom_task", func(ctx context.Context, task *models.Task) error {
    // 处理自定义任务逻辑
    var payload MyPayload
    json.Unmarshal(task.Payload, &payload)
    
    // 分片信息
    shardIndex := task.ShardIndex
    shardTotal := task.ShardTotal
    
    return nil
})
```

## 生产环境建议

1. **etcd 集群**: 至少 3 节点 etcd 集群保证高可用
2. **Redis 集群**: 使用 Redis Cluster 或 Sentinel 保证 Redis 高可用
3. **PostgreSQL**: 主从复制 + 读写分离
4. **监控告警**: 接入 Prometheus + Grafana 监控关键指标
5. **日志收集**: 统一日志收集便于问题排查

## 关键指标监控

- `scheduler_tasks_pending`: 等待执行的任务数
- `scheduler_tasks_running`: 正在执行的任务数
- `scheduler_nodes_count`: 在线节点数
- `scheduler_queue_ready`: Redis 就绪队列长度
- `scheduler_queue_delay`: Redis 延迟队列长度
- `scheduler_node_tasks_{node_id}`: 各节点任务分配数
