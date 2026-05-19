# 统一日志查询平台

基于 Java + Elasticsearch + ANTLR 实现的统一日志查询平台，支持多数据源接入、全文检索、语法高亮、分页和导出功能。

## 核心特性

- **多数据源接入**：支持文件、Kafka、Elasticsearch 三种日志源
- **全文检索引擎**：基于 ANTLR 迭代器模式实现的查询语法解析，支持模糊匹配、AND/OR/NOT 逻辑组合
- **中文分词支持**：集成 IK 分词器，支持智能分词和同义词扩展
- **查询语法高亮**：搜索结果自动高亮匹配关键词
- **日志模板挖掘**：自动聚类相似日志，识别高频模式（如 timeout 类日志）
- **实时日志流**：WebSocket 实时推送最新日志，支持关键词过滤
- **调用链分析**：基于 TraceID 自动关联跨服务日志，展示完整调用链
- **高性能**：基于 Caffeine 缓存、异步批量写入、Elasticsearch 优化，查询响应低于 500ms
- **异步分块导出**：支持 CSV 和 JSON 格式异步导出，分块写入，提供下载链接
- **分页查询**：支持灵活的分页配置

## 技术栈

- **Java 17** + **Spring Boot 3.2.0**
- **Elasticsearch 8.11.0** - 存储和查询引擎
- **ANTLR 4.13.1** - 查询语法解析
- **Kafka 3.6.0** - 日志消息队列
- **Caffeine** - 高性能缓存
- **Lombok** - 简化代码

## 项目结构

```
src/main/java/com/logplatform/
├── UnifiedLogQueryApplication.java    # 启动类
├── config/                            # 配置类
│   ├── ElasticsearchConfig.java       # ES 配置
│   ├── LogCollectorProperties.java   # 采集器配置
│   ├── QueryProperties.java          # 查询配置
│   ├── CacheConfig.java              # 缓存配置
│   ├── AsyncConfig.java              # 异步配置
│   └── WebConfig.java                # Web 配置
├── controller/                        # REST API
│   └── LogQueryController.java       # 查询控制器
├── service/                           # 服务层
│   ├── ElasticsearchQueryService.java # ES 查询服务
│   ├── LogQueryService.java          # 查询服务（含缓存）
│   ├── LogIngestionService.java      # 日志写入服务
│   └── IndexManagementService.java   # 索引管理
├── collector/                         # 日志采集器
│   ├── LogCollector.java             # 采集器接口
│   ├── FileLogCollector.java         # 文件采集
│   ├── KafkaLogCollector.java        # Kafka 采集
│   └── ElasticsearchLogCollector.java # ES 采集
├── parser/                            # 查询语法解析
│   ├── LogQuery.g4                   # ANTLR 语法定义
│   ├── QueryParserService.java       # 解析服务
│   ├── ElasticsearchQueryVisitor.java # ES 查询构建器
│   └── LogQueryErrorListener.java    # 错误监听器
├── model/                             # 数据模型
│   ├── LogEntry.java                 # 日志条目
│   ├── LogQueryRequest.java          # 查询请求
│   └── LogQueryResult.java           # 查询结果
└── exception/                         # 异常处理
    └── GlobalExceptionHandler.java    # 全局异常处理
```

## 查询语法

### 基础查询

```
# 简单关键词
error

# 短语匹配（精确匹配）
"connection failed"

# 通配符
user*
log?
```

### 字段查询

```
level:ERROR
appName:order-service
message:"timeout exception"
status:[400 TO 500]
```

### 逻辑运算

```
# AND 运算
error AND timeout

# OR 运算
error OR warn

# NOT 运算
error NOT debug

# 括号分组
(error OR warn) AND appName:service1
```

### 示例

```
# 查询 service1 的错误日志，包含 timeout 关键词
level:ERROR AND appName:service1 AND timeout

# 查询最近一小时的错误或警告
(level:ERROR OR level:WARN) AND @timestamp:[now-1h TO now]

# 排除调试日志的所有异常
exception NOT level:DEBUG
```

## API 接口

### 搜索日志
```http
POST /api/logs/search
Content-Type: application/json

{
  "query": "error AND timeout",
  "appName": "order-service",
  "level": "ERROR",
  "startTime": "2024-01-01T00:00:00Z",
  "endTime": "2024-01-01T23:59:59Z",
  "page": 0,
  "size": 20,
  "highlight": true
}
```

### 统计数量
```http
POST /api/logs/count
Content-Type: application/json

{
  "query": "error",
  "level": "ERROR"
}
```

### 导出 CSV
```http
POST /api/logs/export/csv
Content-Type: application/json

{
  "query": "error",
  "size": 1000
}
```

### 导出 JSON
```http
POST /api/logs/export/json
Content-Type: application/json

{
  "query": "error",
  "size": 1000
}
```

### 日志写入
```http
POST /api/logs/ingest
Content-Type: application/json

{
  "appName": "order-service",
  "level": "ERROR",
  "message": "Database connection timeout",
  "logger": "com.example.OrderService",
  "thread": "http-nio-8080-exec-1",
  "host": "server-01",
  "traceId": "abc123xyz"
}
```

## 性能优化

### Elasticsearch 优化
- 索引模板预定义，自动按天分片
- 3 分片 1 副本，均衡读写性能
- refresh_interval 设为 5s，提升写入性能
- 使用 best_compression 压缩，节省存储空间
- keyword 类型用于精确匹配字段，减少内存占用

### 查询优化
- Caffeine 本地缓存，缓存 5 分钟，最大 1000 条
- 查询结果高亮使用 ES 原生高亮 API
- 分页查询避免深度分页（使用 search_after 优化）
- 限制单次查询最大返回 100 条

### 写入优化
- 异步批量写入，每 500 条或 1 秒刷盘
- 使用 bulk API 批量写入
- 连接池配置：最大 100 连接，每路由 50 连接

## 快速开始

### 1. 环境要求
- JDK 17+
- Maven 3.8+
- Elasticsearch 8.x

### 2. 配置 Elasticsearch
修改 `application.yml`:
```yaml
elasticsearch:
  uris: http://localhost:9200
  username: elastic
  password: changeme
```

### 3. 编译构建
```bash
# 生成 ANTLR 代码并编译
mvn clean compile

# 打包
mvn package -DskipTests
```

### 4. 启动应用
```bash
java -jar target/unified-log-query-1.0.0.jar
```

### 5. 测试
```bash
# 写入测试日志
curl -X POST http://localhost:8080/api/logs/ingest \
  -H "Content-Type: application/json" \
  -d '{"appName":"test","level":"INFO","message":"Hello World"}'

# 查询日志
curl -X POST http://localhost:8080/api/logs/search \
  -H "Content-Type: application/json" \
  -d '{"query":"Hello","size":10}'
```

## 配置说明

### 文件采集配置
```yaml
log:
  collector:
    file:
      enabled: true
      scan-interval: 5000
      sources:
        - name: app1
          path: /var/log/app1/*.log
          encoding: UTF-8
          multiline-pattern: '^\d{4}-\d{2}-\d{2}'
```

### Kafka 采集配置
```yaml
log:
  collector:
    kafka:
      enabled: true
      bootstrap-servers: localhost:9092
      topics:
        - name: app-logs
          group-id: log-collector-group
          concurrency: 3
```

### IK 分词器配置
```yaml
elasticsearch:
  analysis:
    use-smart: true
    enable-synonym: true
    synonym-path: elasticsearch/analysis/synonyms.txt
    stopword-path: elasticsearch/analysis/stopwords.txt
```

### 异步导出配置
```yaml
export:
  max-export-size: 100000
  temp-dir: /tmp/log-exports
  chunk-size: 1000
  base-url: /api/logs/export/download
  cleanup-interval-minutes: 60
  max-age-minutes: 360
```

### 日志挖掘配置
```yaml
mining:
  similarity-threshold: 0.75
  analysis-window-hours: 1
  max-clusters: 100
  max-templates: 50
  interval-minutes: 5
```

### Trace 分析配置
```yaml
trace:
  max-logs: 1000
  default-time-range-hours: 24
```

## License

MIT License
