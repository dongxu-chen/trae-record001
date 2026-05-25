# 用户行为埋点分析系统

基于 Java + Kafka + Flink + ClickHouse + Redis 构建的企业级用户行为埋点分析系统。

## 核心功能

### 基础功能
- **数据接入**：支持Web/小程序/后端多端埋点数据上报
- **实时ETL**：数据清洗、用户识别（匿名ID→登录ID）、会话切割
- **用户识别**：设备绑定关系管理，跨设备登录时触发人工合并确认
- **动态会话阈值**：基于用户历史会话间隔分布自动计算会话超时时间
- **漏斗分析**：支持滑动窗口（小时/日/周）的漏斗转化分析
- **点击流分析**：用户行为轨迹查询、实时活跃用户统计

### 新增功能（v2.0）
- **实时异常检测**：基于Z-score统计方法识别埋点数据突增/突降，分级别告警
- **用户路径分析**：会话内用户行为流转分析，桑基图数据格式输出
- **留存分析**：支持自定义初始事件和回访事件，按平台/渠道分组留存计算

## 系统架构

```
                    ┌─────────────────┐
                    │  前端/后端埋点  │
                    │  (Web/小程序/SDK)│
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Collector服务  │
                    │  (HTTP API)     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     Kafka       │
                    │  (Raw Events)   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     Flink       │
                    │  数据清洗        │
                    │  用户识别        │
                    │  会话切割        │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
    ┌────────────┐   ┌──────────────┐   ┌───────────┐
    │   Redis    │   │  ClickHouse  │   │   Kafka   │
    │ (用户映射)  │   │ (事件/会话表) │   │(清洗后数据)│
    └────────────┘   └──────┬───────┘   └───────────┘
                            │
                            ▼
                    ┌─────────────────┐
                    │   Query服务     │
                    │  点击流/漏斗分析│
                    └─────────────────┘
```

## 技术栈

| 组件 | 技术选型 | 版本 | 作用 |
|------|----------|------|------|
| 开发语言 | Java | 11 | 后端开发 |
| 消息队列 | Kafka | 2.8.x | 高吞吐数据缓冲 |
| 实时计算 | Flink | 1.17.x | 数据ETL处理 |
| 数据存储 | ClickHouse | 23.x | OLAP分析数据库 |
| 缓存 | Redis | 7.x | 用户映射、会话缓存 |
| Web框架 | Spring Boot | 2.7.x | API服务开发 |
| 序列化 | FastJSON2 | 2.0.x | JSON处理 |
| 连接池 | HikariCP | 5.x | 数据库连接池 |

## 项目结构

```
user-behavior-tracking/
├── tracking-common/          # 公共模块
│   ├── model/                # 数据模型
│   ├── constant/             # 常量定义
│   └── util/                 # 工具类
├── tracking-collector/       # 数据采集服务
│   ├── controller/           # REST API
│   ├── service/              # 业务逻辑
│   └── config/               # 配置类
├── tracking-flink/           # Flink实时计算
│   ├── function/             # Flink算子
│   └── TrackingFlinkJob.java # Flink主作业
├── tracking-storage/         # 数据存储层
│   ├── dao/                  # 数据访问
│   ├── service/              # 存储服务
│   └── config/               # 存储配置
├── tracking-query/           # 查询服务
│   ├── controller/           # 查询API
│   └── service/              # 查询逻辑
├── tracking-sdk/             # 前端SDK
│   ├── tracking-web.js       # Web端SDK
│   ├── tracking-miniapp.js   # 小程序SDK
│   └── JavaTrackingSDK.java  # Java后端SDK
└── deploy/                   # 部署配置
    ├── docker-compose.yml    # 容器编排
    └── sql/                  # 数据库脚本
```

## 核心功能

### 1. 数据采集层 (Collector)

- **HTTP API 接口**：支持单条和批量埋点数据上报
- **前端埋点**：支持 Web/小程序/APP 前端上报
- **后端埋点**：支持服务端事件上报
- **数据验证**：事件格式、字段长度、时间范围校验
- **自动补全**：IP解析、UserAgent解析、地理位置
- **批量发送**：异步批量写入 Kafka，提升性能

### 2. 实时计算层 (Flink)

#### 数据清洗
- 过滤无效数据（爬虫、机器人）
- 字段标准化（统一大小写、去空格）
- IP脱敏（掩码最后一段）
- 异常数据丢弃

#### 用户识别（ID Mapping）
- 匿名ID → 用户ID 映射
- 设备ID → 匿名ID → 用户ID 关联
- 基于 Redis 存储映射关系
- 登录后自动关联历史行为

#### 会话切割
- 基于 30 分钟超时的会话划分
- 会话状态管理（Flink State + Redis）
- 会话聚合统计（时长、事件数、页面路径）
- 会话开始/结束事件生成

### 3. 数据存储层

#### ClickHouse 表设计
- **tracking_events**：事件明细表（MergeTree）
- **tracking_sessions**：会话聚合表（MergeTree）
- **tracking_user_mapping**：用户映射表（ReplacingMergeTree）
- **tracking_event_summary**：事件汇总表（SummingMergeTree + 物化视图）

#### Redis 存储
- 用户ID映射：`tracking:user:mapping:{anonymousId}`
- 设备映射：`tracking:device:anonymous:{deviceId}`
- 会话缓存：`tracking:session:{sessionId}`

### 4. 查询服务层

#### 点击流分析 API
- `POST /api/v1/clickstream/query` - 多条件查询点击流
- `GET /api/v1/clickstream/user/{userId}` - 查询用户行为轨迹
- `GET /api/v1/clickstream/session/{sessionId}` - 查询会话详情
- `GET /api/v1/clickstream/active-users` - 统计活跃用户数

#### 漏斗分析 API
- `POST /api/v1/funnel/analysis` - 自定义漏斗分析
- `GET /api/v1/funnel/purchase` - 购买转化漏斗
- `GET /api/v1/funnel/registration` - 注册转化漏斗

## 快速开始

### 1. 环境要求

- JDK 11+
- Maven 3.6+
- Docker 20+ & Docker Compose

### 2. 启动基础组件

```bash
cd deploy
docker-compose up -d zookeeper kafka redis clickhouse
```

### 3. 初始化数据库

```bash
# 创建 ClickHouse 表结构
clickhouse-client --host localhost --port 8123 < deploy/init-clickhouse.sql

# 创建 Kafka Topic
bash deploy/init-kafka.sh
```

### 4. 编译项目

```bash
mvn clean package -DskipTests
```

### 5. 启动服务

#### 启动 Collector 服务

```bash
cd tracking-collector
java -jar target/tracking-collector-1.0.0.jar
```

#### 提交 Flink 作业

```bash
cd deploy
bash run-flink-job.sh
```

#### 启动 Query 服务

```bash
cd tracking-query
java -jar target/tracking-query-1.0.0.jar
```

### 6. 验证服务

```bash
# 测试 Collector
curl -X POST http://localhost:8080/tracking/v1/track \
  -H "Content-Type: application/json" \
  -d '{
    "event": "page_view",
    "timestamp": '$(date +%s000)',
    "anonymousId": "anon_test_001",
    "platform": "web",
    "appId": "test_app",
    "url": "https://example.com/page1",
    "properties": {
      "page_title": "首页"
    }
  }'

# 测试 Query API
curl http://localhost:8081/api/v1/clickstream/active-users
```

## API 文档

### 埋点上报接口

#### 单条上报
```
POST /tracking/v1/track
Content-Type: application/json

{
  "event": "page_view",           // 事件名称
  "timestamp": 1699999999000,     // 事件时间戳
  "anonymousId": "anon_xxx",      // 匿名ID
  "userId": "user123",            // 登录用户ID（可选）
  "sessionId": "sess_xxx",        // 会话ID（可选）
  "deviceId": "dev_xxx",          // 设备ID（可选）
  "platform": "web",              // 平台
  "appId": "my_app",              // 应用ID
  "appVersion": "1.0.0",          // 应用版本
  "channel": "organic",           // 渠道
  "os": "Windows",                // 操作系统
  "osVersion": "10",              // 系统版本
  "ip": "192.168.1.1",             // IP地址
  "userAgent": "Mozilla/5.0...", // UserAgent
  "url": "https://example.com",   // 页面URL
  "title": "页面标题",             // 页面标题
  "properties": {                 // 自定义属性
    "key": "value"
  }
}
```

#### 批量上报
```
POST /tracking/v1/track/batch
Content-Type: application/json

[
  {...},  // 事件1
  {...}   // 事件2
]
```

#### 后端埋点
```
POST /tracking/v1/backend/track
```

### 查询接口

#### 点击流查询
```
POST /api/v1/clickstream/query
Content-Type: application/json

{
  "userId": "user123",
  "startTime": 1699999999000,
  "endTime": 1700086399000,
  "event": "page_view",
  "platform": "web",
  "page": 1,
  "pageSize": 20
}
```

#### 漏斗分析（单窗口）
```
POST /api/v1/funnel/analysis
Content-Type: application/json

{
  "funnelName": "购买漏斗",
  "events": ["page_view", "add_to_cart", "purchase"],
  "startTime": 1699999999000,
  "endTime": 1700086399000,
  "windowMinutes": 1440,
  "platform": "web"
}
```

#### 漏斗分析（滑动窗口 - 按日）
```
POST /api/v1/funnel/analysis
Content-Type: application/json

{
  "funnelName": "7日日均购买漏斗",
  "events": ["page_view", "add_to_cart", "purchase"],
  "startTime": 1699999999000,
  "endTime": 1700604799000,
  "windowMinutes": 1440,
  "platform": "web",
  "slidingWindow": true,
  "slidingWindowUnit": "daily",
  "slidingWindowSize": 1,
  "slidingWindowStep": 1
}
```

#### 漏斗分析（滑动窗口 - 按周）
```
POST /api/v1/funnel/analysis
Content-Type: application/json

{
  "funnelName": "4周周均购买漏斗",
  "events": ["page_view", "add_to_cart", "purchase"],
  "startTime": 1699999999000,
  "endTime": 1702419199000,
  "windowMinutes": 10080,
  "platform": "web",
  "slidingWindow": true,
  "slidingWindowUnit": "weekly",
  "slidingWindowSize": 1,
  "slidingWindowStep": 1
}
```

#### 漏斗分析（滑动窗口 - 按小时）
```
POST /api/v1/funnel/analysis
Content-Type: application/json

{
  "funnelName": "24小时分时转化漏斗",
  "events": ["page_view", "add_to_cart", "purchase"],
  "startTime": 1699999999000,
  "endTime": 1700086399000,
  "windowMinutes": 60,
  "platform": "web",
  "slidingWindow": true,
  "slidingWindowUnit": "hourly",
  "slidingWindowSize": 1,
  "slidingWindowStep": 1
}
```

### 实时异常检测

#### 获取异常告警列表
```
GET /api/v1/anomaly/alerts
Content-Type: application/json

参数:
- severity: 告警级别(low/medium/high/critical)，可选
- page: 页码，默认1
- pageSize: 每页条数，默认20

响应:
{
  "code": 200,
  "data": [
    {
      "alertId": "alert_abc123",
      "anomalyType": "spike",
      "severity": "high",
      "metricName": "event:page_view",
      "currentValue": 5000,
      "baselineValue": 1000,
      "deviationPercent": 400,
      "zScore": 5.2,
      "description": "Spike detected for event:page_view...",
      "status": "open",
      "detectionTime": 1699999999000
    }
  ]
}
```

#### 查询异常告警
```
POST /api/v1/anomaly/alerts/query
Content-Type: application/json

{
  "startTime": 1699999999000,
  "endTime": 1700086399000,
  "severity": "high",
  "anomalyType": "spike",
  "status": "open",
  "page": 1,
  "pageSize": 20
}
```

#### 获取告警统计
```
GET /api/v1/anomaly/stats
Content-Type: application/json

参数:
- startTime: 开始时间，可选
- endTime: 结束时间，可选
```

#### 确认告警
```
POST /api/v1/anomaly/alert/{alertId}/acknowledge
Content-Type: application/x-www-form-urlencoded

acknowledgedBy=admin&comment=已知问题，正在处理
```

### 用户路径分析（桑基图）

#### 获取桑基图数据
```
POST /api/v1/path/sankey
Content-Type: application/json

{
  "startTime": 1699999999000,
  "endTime": 1700086399000,
  "platform": "web",
  "appId": "test_app",
  "startEvent": "page_view",
  "maxPathLength": 10,
  "topN": 50,
  "ignoreRepeats": true
}

响应:
{
  "code": 200,
  "data": {
    "nodes": [
      {"id": "node_0", "name": "page_view", "category": "page_view", "value": 10000},
      {"id": "node_1", "name": "add_to_cart", "category": "click", "value": 3000},
      {"id": "node_2", "name": "purchase", "category": "conversion", "value": 800}
    ],
    "links": [
      {"source": "node_0", "target": "node_1", "value": 3000, "sourceName": "page_view", "targetName": "add_to_cart"},
      {"source": "node_1", "target": "node_2", "value": 800, "sourceName": "add_to_cart", "targetName": "purchase"}
    ]
  }
}
```

#### 获取Top路径列表
```
POST /api/v1/path/top
Content-Type: application/json

{
  "startTime": 1699999999000,
  "endTime": 1700086399000,
  "platform": "web",
  "maxPathLength": 5,
  "topN": 20
}
```

### 留存分析

#### 自定义留存分析
```
POST /api/v1/retention/analysis
Content-Type: application/json

{
  "retentionType": "custom",
  "initialEvent": "register",
  "returnEvent": "purchase",
  "startTime": 1699999999000,
  "endTime": 1700604799000,
  "retentionDays": [1, 3, 7, 14, 30],
  "platform": "web",
  "channel": "organic",
  "groupBy": "platform",
  "useCache": true
}

响应:
{
  "code": 200,
  "data": {
    "initialEvent": "register",
    "returnEvent": "purchase",
    "initialUsers": 10000,
    "retentionItems": [
      {"day": 1, "label": "1天留存", "returnUsers": 3500, "retentionRate": 35.0},
      {"day": 3, "label": "3天留存", "returnUsers": 1500, "retentionRate": 15.0},
      {"day": 7, "label": "7天留存", "returnUsers": 800, "retentionRate": 8.0}
    ]
  }
}
```

#### 经典留存（安装->打开）
```
POST /api/v1/retention/classic
Content-Type: application/x-www-form-urlencoded

startTime=1699999999000&endTime=1700604799000&retentionDays=1&retentionDays=3&retentionDays=7&platform=android
```

#### 注册后7天下单留存
```
POST /api/v1/retention/custom
Content-Type: application/x-www-form-urlencoded

initialEvent=register&returnEvent=purchase&startTime=1699999999000&endTime=1700604799000&retentionDays=7&retentionDays=14&retentionDays=30
```

#### 审核合并请求
```
POST /api/v1/devices/merge/merge_1699999999_abc123/review
Content-Type: application/x-www-form-urlencoded

status=approved&reviewedBy=admin&comment=确认是同一用户多设备
```

#### 分析会话间隔计算动态阈值
```
POST /api/v1/session-stats/analyze
Content-Type: application/json

[1699990000000, 1699995000000, 1700000000000, 1700006000000, 1700012000000,
 1700020000000, 1700030000000, 1700040000000, 1700050000000, 1700060000000,
 1700070000000, 1700080000000, 1700090000000, 1700100000000, 1700110000000]
```

## SDK 使用

### Web SDK

```html
<script src="tracking-web.js"></script>
<script>
  // 初始化
  var tracker = new Tracking({
    serverUrl: 'http://localhost:8080/tracking',
    appId: 'my_app',
    debug: true
  });

  // 发送自定义事件
  tracker.track('button_click', {
    button_name: '立即购买',
    button_id: 'btn_buy'
  });

  // 用户登录
  tracker.login('user123');

  // 用户退出
  tracker.logout();
</script>
```

### 小程序 SDK

```javascript
const Tracking = require('./tracking-miniapp.js');

const tracker = new Tracking({
  serverUrl: 'http://localhost:8080/tracking',
  appId: 'my_miniapp'
});

// 在App.onLaunch中初始化
App({
  onLaunch: function() {
    tracker.track('app_launch');
  }
});

// 在页面onShow中上报页面浏览
Page({
  onShow: function() {
    tracker.trackPageView();
  }
});
```

### Java SDK

```java
JavaTrackingSDK tracker = JavaTrackingSDK.builder()
    .serverUrl("http://localhost:8080/tracking")
    .appId("my_app")
    .debug(true)
    .build();

// 上报事件
tracker.track("order_create", Map.of(
    "order_id", "ORD123456",
    "amount", 99.99
), "user123", null);

// 上报购买事件
tracker.trackPurchase("user123", "ORD123456", 99.99, null);

// 关闭SDK
tracker.shutdown();
```

## 监控与运维

### 健康检查

```bash
# Collector
curl http://localhost:8080/tracking/v1/health

# Query
curl http://localhost:8081/api/v1/clickstream/active-users
```

### Flink Web UI
- 地址：http://localhost:8081
- 查看作业状态、Checkpoint、反压情况

### Kafka Manager
- 地址：http://localhost:9000
- 查看Topic消费情况、消息堆积

### ClickHouse 查询示例

```sql
-- 统计每日PV/UV
SELECT
    event_date,
    sum(pv) AS pv,
    sum(uv) AS uv
FROM tracking_event_summary
WHERE event = 'page_view'
GROUP BY event_date
ORDER BY event_date DESC;

-- 统计平均会话时长
SELECT
    avg(duration) / 1000 AS avg_duration_seconds,
    avg(event_count) AS avg_events
FROM tracking_sessions
WHERE start_time >= toUnixTimestamp(now() - INTERVAL 1 DAY) * 1000;

-- 查询用户完整行为轨迹
SELECT
    event,
    timestamp,
    url,
    properties
FROM tracking_events
WHERE user_id = 'user123'
ORDER BY timestamp ASC;
```

## 性能优化建议

### Kafka
- 分区数建议设置为 Flink 并行度的整数倍
- 开启压缩（snappy/lz4）
- 合理设置消息保留时间

### Flink
- 开启 Checkpoint（建议 1 分钟）
- 使用 RocksDB State Backend
- 设置合理的并行度
- 开启 Operator Chain

### ClickHouse
- 按日期分区，按月合并
- 合理设置索引粒度
- 定期执行 OPTIMIZE
- 使用 Materialized View 预聚合

### Redis
- 使用集群模式提高可用性
- 设置合理的过期时间
- 监控内存使用

## 常见问题

### 1. 数据丢失怎么办？
- 确保 Kafka acks=all
- Flink 开启 Exactly-Once 语义
- ClickHouse 使用 ReplacingMergeTree 去重

### 2. 如何处理数据重复？
- 每个事件生成唯一 ID
- ClickHouse 使用 ReplacingMergeTree
- 基于事件 ID 去重

### 3. 如何保证数据顺序？
- Kafka 按用户 ID 分区发送
- Flink 按 key 处理保证顺序

## 许可证

MIT License
