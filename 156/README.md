# Leaf 分布式ID生成器 - 号段模式

基于美团Leaf架构实现的高性能分布式ID生成服务，采用双buffer号段模式，支持Prometheus监控和Grafana可视化。

## ✨ 功能特性

### 1. Leaf号段模式
- **双Buffer机制**: 当前号段+预加载号段，无缝切换
- **异步预加载**: 剩余10%时自动触发下一号段加载
- **自旋等待**: 号段耗尽时自旋等待加载完成
- **ZooKeeper存储**: 号段max_id持久化和原子更新

### 2. 业务Tag隔离
- 支持按业务（order, user, product等）独立号段
- 每个业务可配置不同的号段大小
- 支持自定义前缀和ID格式化
- 动态注册新业务Tag

### 3. 高性能优化
- 内存中原子递增，纯内存操作
- 号段批量加载，减少ZooKeeper交互
- 理论QPS: 10万+/秒（取决于号段大小）
- 延迟 < 1ms

### 4. Prometheus监控
- ID生成QPS统计（按业务Tag）
- ID生成延迟分布（p50, p95, p99）
- 号段加载与切换频率
- ZooKeeper连接状态
- 号段剩余ID数监控
- HTTP请求指标

### 5. Grafana可视化
- 预配置完整的监控仪表盘
- 实时QPS和延迟趋势图
- 号段剩余ID预警
- 系统健康状态总览

## 📁 项目结构

```
.
├── config/
│   └── index.js              # 配置文件
├── src/
│   ├── app.js                # 主应用入口
│   ├── leafSegmentManager.js # Leaf号段管理器核心
│   ├── metricsCollector.js   # Prometheus指标收集器
│   ├── idFormatter.js        # ID格式化工具
│   ├── zookeeperManager.js   # ZooKeeper管理器
│   └── routes/
│       └── leafRoutes.js     # API路由
├── grafana/
│   └── dashboard.json        # Grafana仪表盘配置
├── package.json
└── README.md
```

## 🚀 快速开始

### 前置要求
- Node.js 14+
- ZooKeeper 3.5+
- Prometheus + Grafana (可选，用于监控)

### 1. 安装依赖
```bash
npm install
```

### 2. 启动ZooKeeper
```bash
# 本地启动ZooKeeper
./bin/zkServer.sh start
```

### 3. 启动服务
```bash
npm start
```

服务启动后，控制台会显示完整的API端点列表。

## 📡 API 文档

### 基础接口

#### 健康检查
```
GET /health
```
响应示例：
```json
{
  "status": "ok",
  "version": "2.0.0",
  "mode": "leaf-segment",
  "zkConnected": true,
  "timestamp": 1700000000000
}
```

### ID生成接口

#### 生成单个ID
```
GET /api/v1/id/next?bizTag=order&format=1
```

参数：
- `bizTag`: 业务标签，默认default
- `format`: 是否返回格式化ID，0/1，默认0

响应示例：
```json
{
  "success": true,
  "id": "1001",
  "bizTag": "order",
  "idType": "segment",
  "prefix": "ORD",
  "formattedId": "ORD_1234567890_1001",
  "shortId": "ORD_rs",
  "humanReadable": "ORD_20231201_0000_1001"
}
```

#### 批量生成ID
```
GET /api/v1/id/batch/100?bizTag=user&format=1
```

参数：
- count: 生成数量，最大10000
- bizTag: 业务标签
- format: 是否格式化

### 号段管理接口

#### 查看号段状态
```
GET /api/v1/id/segment/status?bizTag=order
```

响应示例：
```json
{
  "success": true,
  "data": {
    "bizTag": "order",
    "prefix": "ORD",
    "step": 1000,
    "current": {
      "minId": 1001,
      "maxId": 2000,
      "currentId": 1500,
      "remaining": 500,
      "idlePercentage": 0.5
    },
    "next": {
      "minId": 2001,
      "maxId": 3000,
      "remaining": 1000
    },
    "isLoadingNext": false
  }
}
```

#### 查看所有业务Tag
```
GET /api/v1/id/biz/tags
```

#### 注册新业务Tag
```
POST /api/v1/id/biz/register
Content-Type: application/json

{
  "bizTag": "payment",
  "step": 2000,
  "prefix": "PAY"
}
```

### 监控指标接口

#### Prometheus格式指标
```
GET /api/v1/id/metrics
```

此端点返回Prometheus标准格式的指标，用于Prometheus采集。

#### JSON格式指标
```
GET /api/v1/id/metrics/json
```

返回结构化的指标数据，包括：
- ID生成QPS统计
- 号段加载次数
- 号段切换次数
- 系统健康指标

### 性能压测接口

```
GET /api/v1/id/benchmark/10000?bizTag=default
```

参数：
- count: 压测数量，最大1000000
- bizTag: 业务标签

响应示例：
```json
{
  "success": true,
  "benchmark": {
    "type": "leaf-segment",
    "bizTag": "default",
    "count": 10000,
    "elapsedMs": 45.23,
    "throughputPerSecond": 221088,
    "avgNsPerId": 452
  }
}
```

## 📊 监控与可视化

### 1. 配置Prometheus采集

在 `prometheus.yml` 中添加：

```yaml
scrape_configs:
  - job_name: 'leaf-id-generator'
    scrape_interval: 5s
    static_configs:
      - targets: ['localhost:3000']
    metrics_path: '/api/v1/id/metrics'
```

### 2. 导入Grafana仪表盘

1. 打开Grafana界面
2. 进入 "Create" → "Import"
3. 上传 `grafana/dashboard.json` 文件
4. 选择Prometheus数据源
5. 完成导入

### 3. 仪表盘包含的监控项

| 面板 | 说明 |
|------|------|
| ID生成QPS | 每个业务Tag的每秒ID生成量 |
| ID生成延迟 | p50/p95/p99延迟分布 |
| ZooKeeper连接状态 | 实时连接状态监控 |
| 号段剩余ID数 | 各业务Tag的号段剩余量 |
| 号段加载频率 | 号段加载和切换次数统计 |
| 号段加载错误 | 失败的号段加载次数 |
| HTTP请求QPS | API接口调用统计 |

## 🔧 核心原理

### 双Buffer号段机制

```
           ┌─────────────────────────────────────┐
           │          当前号段 (Active)           │
           │  1001 - 2000   当前: 1500   剩:500 │
           └─────────────────────────────────────┘
                              │
                              │ 剩余 < 10% 触发预加载
                              ▼
           ┌─────────────────────────────────────┐
           │        下一号段 (预加载)            │
           │  2001 - 3000   已加载完成，待切换   │
           └─────────────────────────────────────┘

当当前号段耗尽时，原子切换到下一号段
```

### 号段加载流程

```
1. 服务启动
   ↓
2. 初始化各业务Tag的初始号段
   ↓
3. ID请求到达，内存递增
   ↓
4. 剩余ID < 10%？
   ├─ 否 → 继续服务
   └─ 是 → 异步加载下一号段
         ↓
5. 当前号段耗尽
   ↓
6. 检查下一号段是否就绪
   ├─ 是 → 原子切换
   └─ 否 → 同步等待加载
         ↓
7. 继续服务
```

## 📈 性能指标

| 指标 | 值 | 说明 |
|------|-----|------|
| 单节点QPS | 100,000+/秒 | 取决于号段步长 |
| 平均延迟 | < 1ms | 纯内存操作 |
| P99延迟 | < 2ms | 号段切换时略高 |
| 号段加载时间 | 10-50ms | ZooKeeper写入 |

## 🛡️ 容错机制

### 1. ZooKeeper连接断开
- 现有号段可继续服务直到耗尽
- 触发告警，等待连接恢复
- 连接恢复后自动加载下一号段

### 2. 号段加载失败
- 重试机制，最多3次
- 降级为同步加载
- 触发监控告警

### 3. 并发请求
- 自旋锁保护号段切换
- 异步加载不阻塞正常请求
- 极端情况毫秒级等待

## 🔄 与Snowflake模式对比

| 特性 | Leaf号段模式 | Snowflake模式 |
|------|-------------|--------------|
| ID类型 | 连续递增整数 | 趋势递增长整数 |
| ID长度 | 可变，通常8-12位 | 固定64位 (18-19位) |
| 顺序性 | 严格连续递增 | 趋势递增，非严格连续 |
| 时钟依赖 | 无依赖 | 强依赖时钟 |
| 外部依赖 | ZooKeeper | ZooKeeper (workerID) |
| 单节点QPS | 10万+/秒 | 1万+/秒 |
| 延迟 | < 1ms | < 2ms |
| 适用场景 | 订单号、流水号等 | 分布式唯一ID、TraceID |

## 📝 默认业务Tag

| Tag | 前缀 | 说明 |
|-----|------|------|
| order | ORD | 订单ID |
| user | USR | 用户ID |
| product | PRD | 商品ID |
| payment | PAY | 支付ID |
| default | ID | 默认通用ID |

## 🤝 客户端SDK

已提供Go和Java客户端SDK，位于 `sdks/` 目录：

- **Go SDK**: 简单易用的HTTP客户端，支持所有API
- **Java SDK**: 兼容Java 11+，Jackson序列化

使用示例详见 `sdks/README.md`

## 📄 License

MIT
