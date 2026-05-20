# 短链系统 v4.0 架构设计文档

## 一、整体架构概览

```
                    ┌────────────────────────────────────────────────────────────┐
                    │                       用户请求层                              │
                    │                                                            │
                    │   短链跳转    埋点上报    热力图查询    统计分析               │
                    │                                                            │
                    └──────────────────────────┬─────────────────────────────────┘
                                               │
                    ┌──────────────────────────▼─────────────────────────────────┐
                    │                    API 网关层 (Express)                      │
                    │                                                            │
                    │   Snowflake ID 生成    鉴权    路由    参数校验               │
                    └──────────────────────────┬─────────────────────────────────┘
                                               │
              ┌────────────────────────────────┼────────────────────────────────┐
              │                                │                                │
    ┌─────────▼─────────┐           ┌──────────▼──────────┐        ┌──────────▼──────────┐
    │   短链存储层      │           │    Kafka 消息队列   │        │   实时聚合结果层    │
    │                   │           │                      │        │                      │
    │   Redis (主存)   │◄──────────┤  Topic: heatmap-    │        │   Redis (聚合结果)  │
    │   - 短码映射     │           │    clicks           │        │   - 热力图网格数据  │
    │   - TTL 过期管理│           │  Topic: access-      │        │   - UV/MV 统计      │
    │                   │           │    logs             │        │   - 点击目标Top榜   │
    └───────────────────┘           └──────────┬──────────┘        └──────────┬──────────┘
                                                │                              │
                        ┌───────────────────────┴───────────────┐              │
                        │                                       │              │
              ┌─────────▼─────────┐                 ┌──────────▼──────────┐   │
              │  Flink 实时计算   │                 │  ClickHouse 消费者  │   │
              │                   │                 │                      │   │
              │ - 滚动窗口聚合   │                 │ - 批量写入优化      │   │
              │ - 热力图网格计算 │                 │ - 去重与清洗        │   │
              │ - UV/MV 去重统计│                 │ - 并发控制          │   │
              │ - 延迟监控        │                 │                      │   │
              └─────────┬─────────┘                 └──────────┬──────────┘   │
                        │                                       │              │
              ┌─────────▼─────────┐                 ┌──────────▼──────────┐   │
              │   Redis 结果缓存  │                 │   ClickHouse 存储    │◄──┘
              │                   │                 │                      │
              │ - 实时热力图数据 │                 │ - 原始点击日志      │
              │ - 实时UV/MV统计  │                 │ - 访客会话记录      │
              │ - 热门点击目标   │                 │ - 物化视图预聚合    │
              └───────────────────┘                 │ - 数据TTL管理       │
                                                    └─────────────────────┘
```

## 二、核心组件详解

### 2.1 分布式唯一ID生成器 (Snowflake)

**位置**: `utils/DistributedSnowflake.js`

**设计原理**:
```
64位ID结构:
┌───────────────────────────────────────────────────────────────────────────┐
│  时间戳 (41位)   │ 数据中心ID(5位) │  工作节点ID(5位) │   序列号(12位)   │
└───────────────────────────────────────────────────────────────────────────┘
```

**关键特性**:
- **分布式协调**: 使用Redis分布式锁自动分配Worker ID
- **心跳续租**: 定期更新锁，防止节点失效
- **时钟回拨保护**: 检测并拒绝服务
- **短码转换**: 62进制编码，生成8位可读短码

**短码示例**:
```
ID: 17623849123456789
↓ Base62编码
短码: 3xKpQ8Zb
```

### 2.2 Kafka 消息队列层

**位置**: `config/kafka.js`

**Topic 设计**:
| Topic 名称 | 用途 | 分区数 | 保留时间 |
|-----------|------|-------|---------|
| heatmap-clicks | 热力图点击事件 | 8 | 7天 |
| access-logs | 短链跳转访问日志 | 4 | 30天 |

**生产者特性**:
- 异步发送，低延迟
- 失败重试机制
- 批量发送优化
- 消息压缩

**消费者组**:
| Consumer Group | 消费目标 | 处理逻辑 |
|---------------|---------|---------|
| clickhouse-sink | 所有Topic | 批量写入ClickHouse |
| flink-aggregator | heatmap-clicks | 实时聚合计算 |

### 2.3 Flink 风格实时计算引擎

**位置**: `services/flinkRealTimeAggregator.js`

**窗口设计**:
```
滚动窗口 (Tumbling Window)
┌─────────┬─────────┬─────────┬─────────┐
│  10s   │  10s   │  10s   │  10s   │
└─────────┴─────────┴─────────┴─────────┘
          ↑
      窗口边界对齐到整点
```

**聚合算子**:
1. **热力图网格聚合**:
   - 网格大小: 20x20像素
   - 累加每个网格点击次数

2. **UV/MV 去重统计**:
   - 基于Canvas指纹去重
   - 会话级别去重

3. **热门点击目标 TopN**:
   - 按元素标签/ID/类名分组
   - 滚动计算Top 20

**输出Key结构**:
```
realtime:heatmap:{path}       → Hash {x,y -> count}
realtime:uvm:{path}           → Hash {uv, mv, clicks}
realtime:targets:{path}       → Hash {targetKey -> count}
realtime:latency:last         → String {avgLatencyMs}
```

### 2.4 ClickHouse 存储层

**表设计**:

**1. heatmap_clicks (点击明细表)**:
```sql
CREATE TABLE heatmap_clicks (
    fingerprint String,
    session_id String,
    url String,
    path String,
    x Int32,
    y Int32,
    absolute_x Int32,
    absolute_y Int32,
    scroll_x Int32,
    scroll_y Int32,
    viewport_width Int32,
    viewport_height Int32,
    target String,
    target_id String,
    target_class String,
    timestamp DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (path, fingerprint, timestamp)
TTL timestamp + INTERVAL 1 YEAR
```

**2. visitor_sessions (访客会话表)**:
```sql
CREATE TABLE visitor_sessions (
    fingerprint String,
    session_id String,
    ip String,
    user_agent String,
    first_seen DateTime DEFAULT now(),
    last_seen DateTime DEFAULT now(),
    visit_count Int32 DEFAULT 1,
    page_views Int32 DEFAULT 0,
    total_clicks Int32 DEFAULT 0,
    country String DEFAULT '',
    browser String DEFAULT '',
    os String DEFAULT '',
    device String DEFAULT ''
) ENGINE = ReplacingMergeTree(last_seen)
PARTITION BY toYYYYMM(first_seen)
ORDER BY (fingerprint, session_id)
TTL first_seen + INTERVAL 1 YEAR
```

**3. uvm_hourly (小时级物化视图)**:
```sql
CREATE MATERIALIZED VIEW uvm_hourly
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (path, hour)
AS SELECT
    path,
    toStartOfHour(timestamp) AS hour,
    uniq(fingerprint) AS uv,
    count() AS mv,
    uniq(session_id) AS sessions
FROM heatmap_clicks
GROUP BY path, hour
```

### 2.5 双读架构查询层

**查询路由策略**:
```
请求
  ↓
┌─────────────────────────────────┐
│ 优先读取 Redis 实时聚合结果     │
└────────────┬────────────────────┘
             │
    ┌────────┴────────┐
    │ 有数据？        │
    └───┬──────────┬──┘
        │ Yes      │ No
        ▼          ▼
   ┌─────────┐  ┌──────────────────────────────┐
   │ 返回    │  │  回查 ClickHouse 历史数据     │
   │ 实时   │  │  预聚合物化视图加速查询        │
   │ 数据   │  └───────────────┬───────────────┘
   └─────────┘                  │
        │                       │
        └───────────┬───────────┘
                    │
                   ▼
            结果合并返回
```

**性能对比**:
| 数据源 | 延迟 | 数据新鲜度 | 适用场景 |
|-------|------|-----------|---------|
| Redis | < 1ms | 近实时 (< 10s) | 热力图展示、实时看板 |
| ClickHouse | 50-500ms | T+5s | 历史趋势分析、报表导出 |
| 双读合并 | 50-500ms | 全量数据 | 精确统计分析 |

## 三、数据流与延迟分析

### 3.1 埋点数据端到端流程

```
  用户点击
     ↓  (0ms)
  前端SDK采集
  (Canvas指纹 + 坐标)
     ↓  (< 10ms)
  HTTP POST /api/heatmap/track
     ↓  (< 1ms)
  Kafka Producer 发送
     ↓  (< 100ms)
     Kafka
     ↓  (< 10ms)
  Flink 实时聚合消费
     ↓  (< 1ms)
  Redis 写入聚合结果
     ↓
  用户查询热力图
     ↓  (< 1ms)
  Redis 聚合结果直接返回

  目标端到端延迟: < 3 秒
```

### 3.2 延迟监控点

| 阶段 | 监控指标 | 阈值 |
|-----|---------|-----|
| Kafka 发送延迟 | producer_latency | < 100ms |
| Flink 处理延迟 | flink_processing_latency | < 500ms |
| 端到端延迟 | end_to_end_latency | < 3000ms |
| ClickHouse 写入延迟 | ch_insert_latency | < 1000ms |

## 四、水平扩展方案

### 4.1 无状态服务扩展
- API 服务: 无状态，直接横向扩展
- Kafka Producer: 多节点共享连接池

### 4.2 有状态服务扩展
- **Snowflake 工作节点**:
  - 最大支持 32 (datacenter) × 32 (worker) = 1024 节点
  - Redis 自动分配 Worker ID

- **Flink 聚合节点**:
  - 按路径分片 (Path Sharding)
  - 消费者组自动负载均衡

### 4.3 存储层扩展
- **Redis**: 集群模式，按Key分片
- **Kafka**: 增加分区数，扩展并行度
- **ClickHouse**: 分布式表 + 本地表，线性扩展

## 五、关键优化点

### 5.1 写入优化
1. **Kafka 批量发送**: 批量大小=16KB，延迟=100ms
2. **ClickHouse 批量插入**: 每批次1000行，间隔3秒
3. **Redis Pipeline**: 批量写入聚合结果

### 5.2 查询优化
1. **双读架构**: 实时 + 历史分离
2. **物化视图**: 预聚合减少计算量
3. **Redis Hash结构**: 高效存储网格数据

### 5.3 成本优化
1. **数据TTL**: 1年自动过期
2. **冷热分离**: 实时数据(7天) vs 归档数据
3. **采样查询**: 超大数据集自动采样

## 六、故障恢复机制

### 6.1 Kafka 不可用时
- 降级: 内存队列缓冲
- 持久化: 本地磁盘缓冲文件
- 恢复: Kafka恢复后自动重放

### 6.2 Redis 不可用时
- 降级: 直查 ClickHouse
- 缓存: 本地内存Cache热点数据

### 6.3 ClickHouse 不可用时
- 降级: 仅返回实时数据
- 告警: 触发监控告警

## 七、部署架构

```
                        ┌─────────────────────────┐
                        │      负载均衡器         │
                        │      (Nginx)           │
                        └──────────┬──────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
    ┌───────▼───────┐     ┌───────▼───────┐     ┌───────▼───────┐
    │   API 节点 1  │     │   API 节点 2  │     │   API 节点 N  │
    │   (Express)   │     │   (Express)   │     │   (Express)   │
    └───────┬───────┘     └───────┬───────┘     └───────┬───────┘
            │                      │                      │
            └──────────────────────┼──────────────────────┘
                                   │
                        ┌──────────▼──────────┐
                        │   Kafka 集群 (8节点)│
                        └──────────┬──────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              │                                         │
    ┌─────────▼─────────┐                     ┌─────────▼─────────┐
    │ Flink 聚合节点组  │                     │ ClickHouse 集群   │
    │ (4节点消费组)     │                     │ (3副本 + 2分片)   │
    └─────────┬─────────┘                     └─────────┬─────────┘
              │                                         │
    ┌─────────▼─────────┐                     ┌─────────▼─────────┐
    │   Redis 集群      │                     │  离线归档存储    │
    │   (6节点集群)    │                     │  (S3/OSS)        │
    └───────────────────┘                     └───────────────────┘
```

## 八、版本演进路线

| 版本 | 核心特性 | 架构里程碑 |
|-----|---------|-----------|
| v1.0 | 基础短链 + ClickHouse | 单体架构 |
| v2.0 | Snowflake + 异步埋点 | 异步架构 |
| v3.0 | 热力图 + UVM分析 | 双读架构 |
| v4.0 | Kafka + Flink 实时流 | Lambda架构 ✓ |
| v5.0 | 真正Flink集群 + 流批一体 | 下一代Kappa架构 |
