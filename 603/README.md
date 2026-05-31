# Pulsar 消息积压处理工具

一个功能完整的Pulsar消息积压监控和自动处理工具，支持：

- ✅ Topic积压量实时监控
- ✅ 消费者自动伸缩
- ✅ 动态分区调整
- ✅ 生产者限流
- ✅ 积压预测（基于线性回归）
- ✅ 可配置的处理策略
- ✅ 操作执行审计

## 项目结构

```
.
├── backend/                    # Go 后端
│   ├── cmd/
│   │   └── main.go            # 主入口
│   ├── pkg/
│   │   ├── api/               # REST API 服务器
│   │   ├── audit/             # 审计日志模块
│   │   ├── autoscaler/        # 自动伸缩模块
│   │   ├── config/            # 配置管理
│   │   ├── monitor/           # 监控模块
│   │   ├── partition/         # 分区管理模块
│   │   ├── prediction/        # 积压预测模块
│   │   ├── pulsar/            # Pulsar 客户端封装
│   │   ├── ratelimiter/       # 限流模块
│   │   └── strategy/          # 策略配置模块
│   └── go.mod
└── frontend/                   # React 前端
    ├── public/
    ├── src/
    │   ├── pages/             # 页面组件
    │   │   ├── Dashboard.js   # 监控面板
    │   │   ├── Predictions.js # 积压预测
    │   │   ├── Strategies.js  # 策略配置
    │   │   └── AuditLog.js    # 审计日志
    │   ├── services/          # API 服务
    │   ├── App.js
    │   └── index.js
    └── package.json
```

## 功能特性

### 1. 监控模块 (monitor)
- 定时采集Topic积压量
- 支持自定义监控间隔
- 积压历史数据存储
- 实时状态更新

### 2. 自动伸缩模块 (autoscaler)
- 基于积压阈值自动调整消费者数量
- 支持最小/最大消费者数配置
- 扩容/缩容阈值可配置
- 防抖机制防止频繁调整

### 3. 分区管理模块 (partition)
- 自动调整Topic分区数量
- 基于单分区平均积压判断
- 支持指数级扩容/缩容

### 4. 限流模块 (ratelimiter)
- 基于令牌桶算法的生产者限流
- 积压过高时自动降速
- 积压恢复后自动恢复速率

### 5. 预测模块 (prediction)
- 线性回归预测未来积压
- 置信度计算
- 预测告警

### 6. 策略配置模块 (strategy)
- 按Topic配置独立策略
- 默认策略兜底
- 支持灵活的阈值配置

### 7. 审计模块 (audit)
- 所有操作日志记录
- 支持按Topic/操作类型过滤
- 搜索功能

## 快速开始

### 后端启动

```bash
cd backend
go mod tidy
go run cmd/main.go
```

环境变量配置：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| PULSAR_URL | pulsar://localhost:6650 | Pulsar broker地址 |
| PULSAR_ADMIN_URL | http://localhost:8080 | Pulsar admin地址 |
| SERVER_PORT | 8081 | API服务端口 |
| MONITOR_INTERVAL | 30 | 监控间隔(秒) |
| AUTOSCALER_ENABLED | true | 是否启用自动伸缩 |
| MIN_CONSUMERS | 1 | 最小消费者数 |
| MAX_CONSUMERS | 20 | 最大消费者数 |
| SCALE_UP_THRESHOLD | 10000 | 扩容阈值 |
| SCALE_DOWN_THRESHOLD | 1000 | 缩容阈值 |

### 前端启动

```bash
cd frontend
npm install
npm start
```

访问 http://localhost:3000 即可查看管理界面。

## API 接口

### Topic管理
- `GET /api/v1/topics` - 获取监控Topic列表
- `POST /api/v1/topics` - 添加监控Topic
- `DELETE /api/v1/topics/:topic` - 移除监控Topic
- `GET /api/v1/topics/:topic/backlog` - 获取积压数据
- `GET /api/v1/topics/:topic/history` - 获取历史数据

### 消费者管理
- `GET /api/v1/autoscale/:topic/:subscription` - 获取消费者数量
- `POST /api/v1/autoscale/:topic/:subscription` - 设置消费者数量

### 分区管理
- `GET /api/v1/partitions/:topic` - 获取分区数
- `POST /api/v1/partitions/:topic` - 设置分区数

### 限流管理
- `GET /api/v1/ratelimit/:topic` - 获取限流速率
- `POST /api/v1/ratelimit/:topic` - 设置限流速率

### 预测
- `GET /api/v1/predictions/:topic` - 获取预测结果

### 策略配置
- `GET /api/v1/strategies` - 获取所有策略
- `GET /api/v1/strategies/:topic` - 获取指定策略
- `POST /api/v1/strategies` - 更新策略
- `DELETE /api/v1/strategies/:topic` - 删除策略

### 审计日志
- `GET /api/v1/audit` - 获取审计日志
- `GET /api/v1/audit/topic/:topic` - 获取指定Topic审计日志

## 技术栈

### 后端
- **Go 1.21** - 高性能编程语言
- **Gin** - Web框架
- **Apache Pulsar Client** - Pulsar客户端
- **golang.org/x/time/rate** - 限流器

### 前端
- **React 18** - UI框架
- **Material-UI** - 组件库
- **Recharts** - 图表库
- **Axios** - HTTP客户端

## 架构设计

### 数据流

```
Pulsar Cluster
    ↓
[Monitor Module] → 采集积压数据
    ↓
[Handler Chain]
    ├→ [AutoScaler] → 调整消费者数量
    ├→ [Partition Manager] → 调整分区
    ├→ [Rate Limiter] → 调整发送速率
    └→ [Predictor] → 预测未来积压
    ↓
[Strategy Manager] → 策略匹配
    ↓
[Audit Logger] → 记录操作日志
    ↓
[REST API] → 前端交互
```

### 处理策略

每个Topic可以配置独立的处理策略，策略包括：

1. **自动伸缩策略**
   - 是否启用
   - 最小/最大消费者数
   - 扩容/缩容阈值

2. **分区管理策略**
   - 是否启用
   - 最小/最大分区数
   - 扩容/缩容阈值

3. **限流策略**
   - 是否启用
   - 基础发送速率
   - 触发限流/恢复阈值

4. **预测策略**
   - 是否启用
   - 告警阈值

## 使用场景

1. **流量突增应对** - 自动扩容消费者处理突发流量
2. **资源优化** - 低峰期自动缩容节省资源
3. **故障预防** - 通过预测提前发现潜在积压
4. **流量管控** - 积压过高时限制生产者发送速率
5. **合规审计** - 所有操作可追溯可审计

## 注意事项

1. 本工具需要与实际的Pulsar集群配合使用
2. 分区调整功能需要Pulsar admin API权限
3. 限流功能建议与实际生产者应用集成使用
4. 预测功能需要足够的历史数据才能准确

## License

MIT
