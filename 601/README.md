# 实时数据同步校验工具 (Data Sync Checker)

一个用于实时检测和校验源端与目标端数据差异的工具，支持多种数据源，提供差异自动修复功能。

## 功能特性

### 核心功能
- ✅ **多数据源支持**: MySQL、Redis、Elasticsearch
- ✅ **实时数据比对**: 增量/全量数据对比
- ✅ **同步延迟检测**: 实时监控数据同步延迟
- ✅ **数据丢失检测**: 识别源端/目标端缺失数据
- ✅ **差异自动修复**: 自动或手动修复数据差异
- ✅ **消息队列集成**: 支持 Kafka、RocketMQ
- ✅ **实时推送**: WebSocket 实时推送差异和进度
- ✅ **可视化看板**: 数据趋势图表和统计

### 差异类型
| 类型 | 说明 | 修复策略 |
|------|------|----------|
| MISSING_IN_TARGET | 目标端缺失数据 | 从源端同步到目标端 |
| MISSING_IN_SOURCE | 源端缺失数据 | 删除目标端冗余数据 |
| VALUE_MISMATCH | 字段值不匹配 | 用源端值覆盖目标端 |
| LATENCY_EXCEEDED | 同步延迟过高 | 等待并重试验证 |

## 技术栈

### 后端
- **框架**: Spring Boot 3.2
- **语言**: Java 17
- **数据库连接**: HikariCP 连接池
- **消息队列**: Kafka / RocketMQ
- **WebSocket**: STOMP + SockJS
- **缓存**: Caffeine
- **JSON**: Fastjson2

### 前端
- **框架**: React 18 + Vite
- **UI组件**: Ant Design 5
- **图表**: ECharts
- **状态管理**: React Hooks
- **实时通信**: STOMP over WebSocket

## 项目结构

```
├── src/
│   └── main/
│       ├── java/com/datacheck/
│       │   ├── DataSyncCheckerApplication.java    # 启动类
│       │   ├── config/                           # 配置类
│       │   │   ├── DataSourceConfig.java
│       │   │   ├── RedisConfig.java
│       │   │   ├── ElasticsearchConfig.java
│       │   │   ├── WebSocketConfig.java
│       │   │   └── ThreadPoolConfig.java
│       │   ├── datasource/                       # 数据源适配器
│       │   │   ├── DataSourceAdapter.java
│       │   │   ├── DataSourceAdapterFactory.java
│       │   │   ├── MysqlDataSourceAdapter.java
│       │   │   ├── RedisDataSourceAdapter.java
│       │   │   └── ElasticsearchDataSourceAdapter.java
│       │   ├── check/                            # 比对引擎
│       │   │   ├── CheckEngine.java
│       │   │   └── DataComparator.java
│       │   ├── messagequeue/                     # 消息队列
│       │   │   ├── MessageQueueService.java
│       │   │   ├── KafkaProducerService.java
│       │   │   └── RocketMQProducerService.java
│       │   ├── repair/                           # 自动修复
│       │   │   └── AutoRepairService.java
│       │   ├── service/                          # 服务层
│       │   │   └── WebSocketService.java
│       │   ├── controller/                       # 控制器
│       │   │   └── CheckController.java
│       │   ├── scheduler/                        # 调度器
│       │   │   └── CheckScheduler.java
│       │   ├── exception/                        # 异常处理
│       │   │   └── GlobalExceptionHandler.java
│       │   └── model/                            # 数据模型
│       │       ├── enums/
│       │       ├── DataRecord.java
│       │       ├── DiffResult.java
│       │       ├── CheckResult.java
│       │       ├── CheckTask.java
│       │       └── WebSocketMessage.java
│       └── resources/
│           └── application.yml                    # 配置文件
├── frontend/                                      # React 前端
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── index.css
│   │   ├── services/
│   │   │   ├── api.js
│   │   │   └── websocket.js
│   │   └── pages/
│   │       ├── Dashboard.jsx       # 数据看板
│   │       ├── TaskList.jsx        # 任务列表
│   │       ├── DiffList.jsx        # 差异列表
│   │       └── CreateTask.jsx      # 创建任务
│   ├── package.json
│   └── vite.config.js
├── pom.xml
├── start-backend.bat
├── start-frontend.bat
└── start-all.bat
```

## 快速开始

### 环境要求
- JDK 17+
- Maven 3.6+
- Node.js 16+
- MySQL 5.7+ / Redis 5.0+ / Elasticsearch 7.0+ (根据需要)
- Kafka 2.8+ / RocketMQ 4.9+ (根据需要)

### 配置

编辑 `src/main/resources/application.yml`:

```yaml
# MySQL 配置
datasource:
  mysql:
    source:
      url: jdbc:mysql://localhost:3306/source_db
      username: root
      password: root
    target:
      url: jdbc:mysql://localhost:3306/target_db
      username: root
      password: root

# Redis 配置
data:
  redis:
    source:
      host: localhost
      port: 6379
    target:
      host: localhost
      port: 6380

# Elasticsearch 配置
elasticsearch:
  source:
    hosts: http://localhost:9200
  target:
    hosts: http://localhost:9201

# 消息队列配置
message-queue:
  type: kafka  # kafka 或 rocketmq
  kafka:
    bootstrap-servers: localhost:9092
    topic: data-sync-topic
```

### 启动

#### Windows

**一键启动所有服务:**
```bat
start-all.bat
```

**仅启动后端:**
```bat
start-backend.bat
```

**仅启动前端:**
```bat
start-frontend.bat
```

#### 手动启动

**后端:**
```bash
mvn clean compile
mvn spring-boot:run
```

**前端:**
```bash
cd frontend
npm install
npm run dev
```

### 访问

- **后端 API**: http://localhost:8080/api
- **前端 UI**: http://localhost:3000
- **WebSocket**: ws://localhost:8080/api/ws

## API 接口

### 任务管理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/check/task` | 创建校验任务 |
| POST | `/api/check/task/{id}/start` | 启动任务 |
| POST | `/api/check/task/execute` | 创建并立即执行 |
| POST | `/api/check/task/{id}/cancel` | 取消任务 |
| GET | `/api/check/task/{id}` | 获取任务详情 |
| GET | `/api/check/tasks` | 获取任务列表 |
| GET | `/api/check/task/{id}/result` | 获取校验结果 |

### 差异管理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/check/repair/{diffId}?taskId={taskId}` | 触发修复 |
| GET | `/api/check/diffs` | 获取差异列表 |

### 统计信息
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/check/statistics` | 获取统计数据 |
| GET | `/api/check/datasources` | 获取可用数据源 |
| GET | `/api/check/datasource/{type}/tables` | 获取表列表 |
| GET | `/api/check/datasource/{type}/table/{tableName}/columns` | 获取列信息 |

### WebSocket 消息

订阅主题:
- `/topic/diffs` - 实时差异推送
- `/topic/tasks/{taskId}` - 任务进度
- `/topic/results` - 任务完成通知
- `/topic/repairs` - 修复状态更新

消息格式:
```json
{
  "type": "DIFF",
  "payload": {
    "id": "uuid",
    "key": "record-key",
    "diffType": "VALUE_MISMATCH",
    "sourceType": "MYSQL",
    "tableName": "users",
    "diffFields": {
      "name": {
        "source": "Alice",
        "target": "Bob"
      }
    },
    "detectedAt": "2024-01-01T12:00:00"
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

## 使用示例

### 1. 创建 MySQL 校验任务

```bash
curl -X POST http://localhost:8080/api/check/task/execute \
  -H "Content-Type: application/json" \
  -d '{
    "sourceType": "MYSQL",
    "tableName": "users",
    "primaryKey": "id",
    "compareFields": ["name", "email", "status"],
    "excludeFields": ["password", "created_at"],
    "whereCondition": "status = 1",
    "batchSize": 1000,
    "latencyThresholdMs": 5000,
    "autoRepair": true
  }'
```

### 2. 创建 Redis 校验任务

```bash
curl -X POST http://localhost:8080/api/check/task/execute \
  -H "Content-Type: application/json" \
  -d '{
    "sourceType": "REDIS",
    "tableName": "user:",
    "autoRepair": true
  }'
```

### 3. 创建 Elasticsearch 校验任务

```bash
curl -X POST http://localhost:8080/api/check/task/execute \
  -H "Content-Type: application/json" \
  -d '{
    "sourceType": "ELASTICSEARCH",
    "tableName": "users-index",
    "autoRepair": true
  }'
```

## 核心设计

### 数据比对引擎

1. **批量读取**: 使用分页/游标批量读取数据，避免内存溢出
2. **双端迭代**: 同时迭代源端和目标端，进行有序比对
3. **智能缓存**: 缓存目标端数据，减少重复查询
4. **并行处理**: 使用线程池并行处理比对任务

### 自动修复策略

```
检测到差异
    ↓
判断修复开关
    ├─ 关闭 → 标记为待修复，等待手动触发
    └─ 开启 → 进入修复流程
        ↓
根据差异类型选择修复方式
    ├─ MISSING_IN_TARGET → INSERT
    ├─ MISSING_IN_SOURCE → DELETE
    ├─ VALUE_MISMATCH → UPDATE
    └─ LATENCY_EXCEEDED → 等待重查
        ↓
执行修复（最多重试N次）
    ↓
更新修复状态
    ├─ 成功 → SUCCESS
    └─ 失败 → FAILED（记录错误信息）
```

### 消息队列集成

差异结果会同时发送到:
1. WebSocket - 实时推送到前端
2. Kafka/RocketMQ - 供其他系统消费处理

## 性能优化

- **批量读取**: 每次读取 1000 条记录（可配置）
- **并行处理**: 多线程并行比对
- **智能缓存**: Caffeine 缓存列信息和中间结果
- **连接池**: HikariCP 数据库连接池
- **异步处理**: 比对和修复都是异步执行

## 监控指标

系统收集以下指标:
- 总任务数、完成数、失败数
- 总差异数、已修复数、修复率
- 同步延迟（平均、最大）
- 数据处理速度
- 各数据源可用性

## License

MIT
