# RabbitMQ 集群负载均衡工具

一个基于 Go 语言开发的 RabbitMQ 集群负载均衡工具，通过 RabbitMQ 管理 API 监控队列分布，自动迁移队列以实现负载均衡。

## 功能特性

### 1. 集群监控
- 实时监控 RabbitMQ 集群节点状态
- 收集队列分布、消息数量、内存使用等指标
- 计算节点负载评分（队列数量、消息数、内存使用率综合权重）

### 2. 自动负载均衡
- 基于负载阈值自动触发重平衡
- 智能选择需要迁移的队列
- 支持配置每个周期最大迁移数量

### 3. 节点宕机重平衡（实时触发）
- 实时检测节点健康状态
- **故障发现立即处理**：节点宕机自动触发队列迁移（无需等待下一个检查周期）
- 节点恢复自动感知并记录
- 支持紧急故障恢复优先级

### 4. 迁移影响最小化
- **消费者暂停/恢复**：迁移前暂停消费者，完成后恢复
- **低流量迁移**：仅在流量低于阈值时迁移
- **迁移时间窗口**：可配置只在特定时间段执行迁移
- **队列排除**：支持按模式排除特定队列/vhost
- **大小限制**：跳过过大或过小的队列
- **冷却时间**：避免频繁迁移同一队列

### 5. 流量预测与突发模式识别
- 基于线性回归的时间序列预测
- 预测未来消息数量和流量趋势
- **突发流量检测**：自动识别突发模式
- **突发期禁止迁移**：突发流量期间跳过迁移，避免影响业务
- 支持移动平均、指数平滑、季节性分析

### 6. 队列租户隔离与重要队列专属节点
- **租户隔离**：按 vhost 和队列模式划分租户，限制队列只能分配到指定节点
- **专属节点**：重要队列绑定专属节点，确保资源独占和高可用
- **负载上限**：每个租户可配置最大负载评分，超过上限禁止迁入
- **违规检测**：自动检测租户隔离违规，输出详细违规信息
- **迁移验证**：每次迁移前验证目标节点是否符合租户策略

### 7. 自动扩缩节点
- **负载驱动扩容**：集群平均负载超过阈值时自动增加节点
- **负载驱动缩容**：负载持续低于阈值且存在多余空闲节点时自动缩容
- **冷却机制**：扩缩操作后冷却期内不再触发，防止抖动
- **节点范围限制**：可配置最小/最大节点数
- **可扩展 Provider**：支持自定义节点供给接口（默认 Mock 实现）

### 8. 迁移演练
- **模拟迁移**：在不实际执行的情况下模拟迁移计划
- **影响评估**：计算迁移前后每个节点的负载变化
- **风险评分**：综合评估迁移风险（0-100分）
- **风险拦截**：高风险迁移自动拦截，防止误操作
- **租户合规检查**：演练时同步检查租户隔离违规
- **自动演练**：可配置定时自动演练，持续评估集群风险
- **详细报告**：生成包含风险等级、违规详情、建议的完整报告

### 9. Prometheus 监控
- 暴露丰富的监控指标
- 节点负载、队列状态、迁移统计
- 预测指标和故障统计
- 突发模式和消费者暂停状态
- 租户隔离和专属队列指标
- 自动扩缩事件指标
- 迁移演练风险指标

## 项目结构

```
rabbitmq-lb/
├── cmd/
│   └── main.go                 # 主程序入口
├── pkg/
│   ├── rabbitmq/
│   │   └── client.go           # RabbitMQ 管理 API 客户端
│   ├── config/
│   │   └── config.go           # 配置管理
│   ├── monitor/
│   │   └── monitor.go          # 集群监控模块
│   ├── balancer/
│   │   ├── migrator.go         # 队列迁移和负载均衡逻辑
│   │   └── failure_detector.go # 节点故障检测
│   ├── predictor/
│   │   └── predictor.go        # 流量预测和突发检测模块
│   ├── tenant/
│   │   └── tenant.go           # 租户隔离和专属节点管理
│   ├── autoscaler/
│   │   └── autoscaler.go       # 自动扩缩节点模块
│   ├── drill/
│   │   └── drill.go            # 迁移演练模块
│   └── metrics/
│       └── prometheus.go       # Prometheus 指标暴露
├── config.yaml                  # 配置文件
├── go.mod
└── README.md
```

## 快速开始

### 1. 编译

```bash
go mod tidy
go build -o rabbitmq-lb cmd/main.go
```

### 2. 配置

编辑 `config.yaml`:

```yaml
rabbitmq:
  url: "http://localhost:15672"
  username: "guest"
  password: "guest"
  timeout: "10s"
  vhost: "/"

balancer:
  check_interval: "30s"
  rebalance_threshold: 0.2
  max_migrations_per_cycle: 5
  min_messages_per_queue: 100
  max_queue_size: 1000000
  node_failure_timeout: "60s"
  dry_run: false
  migration_cooldown: "5m"
  low_traffic_threshold: 1.0
  exclude_queues:
    - "amq.*"

prediction:
  enabled: true
  burst_detection_window: 10
  burst_threshold: 3.0

tenant:
  enabled: true
  tenants:
    - name: "payment"
      vhost: "payment"
      queues: ["*"]
      exclusive_nodes: ["rabbit@node-payment-1", "rabbit@node-payment-2"]
      priority: 10
      max_load_score: 3.0
  dedicated_queues:
    - queue_name: "order-critical"
      vhost: "payment"
      nodes: ["rabbit@node-payment-1"]
      priority: 10
      min_nodes: 1

autoscaler:
  enabled: true
  min_nodes: 2
  max_nodes: 10
  scale_up_threshold: 2.0
  scale_down_threshold: 0.3
  scale_up_cooldown: "5m"
  scale_down_cooldown: "10m"
  evaluation_interval: "1m"
  provider: "mock"

drill:
  enabled: true
  interval: "5m"
  auto_run: true
  max_risk_level: "high"
  block_on_risk: true

prometheus:
  enabled: true
  address: ":9090"
  path: "/metrics"
```

### 3. 运行

```bash
./rabbitmq-lb [config.yaml]
```

## 工作原理

### 负载均衡算法

1. **负载计算**：每个节点的负载评分由三部分组成：
   - 队列数量占比 (40%)
   - 消息总数占比 (40%)
   - 内存使用率 (20%)

2. **重平衡触发**：当任意节点负载与平均负载的偏差超过阈值时触发

3. **队列选择**：
   - 从过载节点按消息数降序排列
   - 排除不符合条件的队列（大小、排除模式、冷却中、突发流量）
   - 预测流量增长的队列优先迁移

4. **目标节点**：选择负载最低的可用节点（考虑租户隔离约束）

### 租户隔离机制

```
迁移计划生成
    ↓
租户策略验证
    ├─ 专属队列 → 检查目标节点是否在允许列表
    ├─ 租户隔离 → 检查目标节点是否在租户专属节点列表
    ├─ 负载上限 → 检查目标节点是否超过租户最大负载
    └─ 节点独占 → 检查目标节点是否被其他专属队列占用
    ↓
验证通过 → 执行迁移
验证失败 → 阻止迁移并记录违规
```

### 自动扩缩机制

```
定时评估（evaluation_interval）
    ↓
计算集群平均负载
    ↓
判断是否需要扩缩
    ├─ 低于最小节点数 → 立即扩容
    ├─ 平均负载 > scale_up_threshold → 扩容
    ├─ 平均负载 < scale_down_threshold 且有多个空闲节点 → 缩容
    └─ 冷却期内 → 不操作
    ↓
执行扩缩并触发重平衡
```

### 迁移演练流程

```
生成迁移计划
    ↓
模拟执行（不实际迁移）
    ├─ 计算每个节点迁移前后负载变化
    ├─ 评估每条迁移的风险等级
    ├─ 检查租户隔离违规
    └─ 检查大队列、活跃流量等风险因素
    ↓
计算综合风险评分（0-100）
    ↓
风险等级判定
    ├─ low (< 30) → 可安全执行
    ├─ medium (30-49) → 需注意
    ├─ high (50-69) → 建议调整
    └─ critical (>= 70) → 阻止执行
    ↓
生成详细报告和建议
```

### 安全迁移流程

```
检测到需要迁移
    ↓
租户策略验证
    ↓
队列有消费者/流量？
    ├─ 是 → 暂停消费者（设置低优先级Policy）
    │         ↓
    │       等待1秒确保生效
    └─ 否 → ──┐
              ↓
设置新的 master 节点位置（ha-mode: nodes）
    ↓
等待队列迁移完成（超时保护）
    ↓
迁移成功？
    ├─ 是 → 恢复消费者 → 清理迁移Policy
    └─ 否 → 恢复消费者（失败回滚）→ 返回错误
```

## Prometheus 指标

### 节点指标
- `rabbitmq_lb_node_load_score` - 节点负载评分
- `rabbitmq_lb_node_queue_count` - 节点队列数
- `rabbitmq_lb_node_total_messages` - 节点消息总数
- `rabbitmq_lb_node_total_memory_bytes` - 节点内存使用
- `rabbitmq_lb_node_status` - 节点状态 (1=running, 0=stopped, -1=failed)

### 队列指标
- `rabbitmq_lb_queue_messages` - 队列消息数
- `rabbitmq_lb_queue_consumers` - 队列消费者数
- `rabbitmq_lb_queue_publish_rate` - 发布速率
- `rabbitmq_lb_queue_deliver_rate` - 投递速率
- `rabbitmq_lb_queue_consumer_paused` - 消费者暂停状态

### 迁移指标
- `rabbitmq_lb_migrations_total` - 总迁移数
- `rabbitmq_lb_migrations_success_total` - 成功迁移数
- `rabbitmq_lb_migrations_failed_total` - 失败迁移数
- `rabbitmq_lb_migration_duration_seconds` - 迁移耗时分布
- `rabbitmq_lb_consumers_paused_total` - 暂停消费者的队列总数

### 预测指标
- `rabbitmq_lb_prediction_queue_trend` - 队列趋势
- `rabbitmq_lb_prediction_confidence` - 预测置信度
- `rabbitmq_lb_predicted_messages` - 预测消息数

### 突发流量指标
- `rabbitmq_lb_queue_burst_status` - 突发状态
- `rabbitmq_lb_queue_burst_magnitude` - 突发强度
- `rabbitmq_lb_queue_burst_duration_seconds` - 突发持续时间
- `rabbitmq_lb_burst_queues_total` - 突发队列总数

### 故障指标
- `rabbitmq_lb_failed_nodes_total` - 故障节点数
- `rabbitmq_lb_node_failures_total` - 节点故障次数
- `rabbitmq_lb_node_recoveries_total` - 节点恢复次数

### 租户隔离指标
- `rabbitmq_lb_tenant_violations_total` - 租户隔离违规数
- `rabbitmq_lb_dedicated_queues_total` - 专属队列数
- `rabbitmq_lb_tenant_node_assignment` - 租户节点分配

### 自动扩缩指标
- `rabbitmq_lb_autoscaler_events_total` - 扩缩事件数
- `rabbitmq_lb_autoscaler_managed_nodes_total` - 托管节点数
- `rabbitmq_lb_autoscaler_decision_status` - 当前扩缩决策状态

### 迁移演练指标
- `rabbitmq_lb_drill_runs_total` - 演练执行次数
- `rabbitmq_lb_drill_risk_score` - 最新演练风险评分
- `rabbitmq_lb_drill_violation_count` - 最新演练违规数
- `rabbitmq_lb_drill_blocked_migrations` - 被拦截的迁移数

## 配置说明

### 租户隔离配置

```yaml
tenant:
  enabled: true
  tenants:
    - name: "payment"                # 租户名称
      vhost: "payment"               # 所属 vhost（"*" 表示全部）
      queues: ["*"]                  # 匹配的队列模式列表
      exclusive_nodes:               # 租户专属节点
        - "rabbit@node-payment-1"
        - "rabbit@node-payment-2"
      priority: 10                   # 优先级（越大越重要）
      max_load_score: 3.0            # 租户节点最大负载评分
  dedicated_queues:
    - queue_name: "order-critical"   # 专属队列名称
      vhost: "payment"               # 所属 vhost
      nodes:                         # 允许的节点列表
        - "rabbit@node-payment-1"
      priority: 10                   # 优先级
      min_nodes: 1                   # 最少节点数
```

### 自动扩缩配置

```yaml
autoscaler:
  enabled: true
  min_nodes: 2                       # 最小节点数
  max_nodes: 10                      # 最大节点数
  scale_up_threshold: 2.0            # 扩容负载阈值
  scale_down_threshold: 0.3          # 缩容负载阈值
  scale_up_step: 1                   # 每次扩容节点数
  scale_up_cooldown: "5m"            # 扩容冷却时间
  scale_down_cooldown: "10m"         # 缩容冷却时间
  evaluation_interval: "1m"          # 评估间隔
  provider: "mock"                   # 节点供给器（mock/aws/gcp/自定义）
```

### 迁移演练配置

```yaml
drill:
  enabled: true                      # 是否启用演练
  interval: "5m"                     # 自动演练间隔
  auto_run: true                     # 是否自动运行
  max_risk_level: "high"             # 允许执行的最高风险等级
  block_on_risk: true                # 超过风险等级时是否阻止迁移
```

### 突发检测配置

```yaml
prediction:
  burst_detection_window: 10         # 基线计算数据点数量
  burst_threshold: 3.0               # 突发判定阈值（倍数）
```

## 注意事项

1. **RabbitMQ 版本**：需要支持 HA 队列功能的 RabbitMQ 版本 (3.x+)
2. **权限**：管理用户需要 `administrator` 权限
3. **队列同步**：大队列同步期间可能影响性能，建议在低峰期执行
4. **Dry Run**：首次使用建议开启 dry_run 模式验证迁移计划
5. **突发检测**：突发期间队列不会被迁移，确保高流量期间业务稳定
6. **故障恢复**：节点故障会立即触发迁移，无需等待检查周期
7. **租户隔离**：启用租户隔离后，迁移计划必须通过策略验证才能执行
8. **自动扩缩**：默认使用 Mock Provider，生产环境需实现自定义 NodeProvider 接口
9. **迁移演练**：建议开启 block_on_risk 防止高风险迁移

## License

MIT
