# A/B 测试平台后端

基于 Java + Spring Boot + Redis + ClickHouse 构建的企业级 A/B 测试平台。

## 功能特性

### 1. 实验配置管理
- 支持实验的创建、启动、暂停、恢复、结束、删除
- 灵活的流量分配配置（1%-100%）
- 多实验组配置，支持自定义流量权重
- 指标定义：转化率指标、连续型指标（均值、求和等）

### 2. 用户分桶
- 基于 MurmurHash 的一致性哈希分桶
- 同一用户始终分配到同一实验组
- 支持按用户ID、设备ID等多种分流键
- Redis 缓存分桶结果，提升查询性能

### 3. 实时指标计算
- 基于 ClickHouse 的高性能实时分析
- 支持转化率计算（曝光→转化漏斗）
- 支持连续型指标计算（均值、方差、求和）
- 多维度趋势分析

### 4. 统计显著性检验
- **卡方检验 (Chi-Square Test)**: 用于转化率类指标
- **T检验 (Welch's T-Test)**: 用于连续型指标（如均值比较）
- 置信区间计算（95%置信度）
- 自动判断统计显著性

### 5. 实验报告
- 综合实验报告生成
- 各实验组指标对比
- 统计显著性结果汇总
- 趋势数据查询

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (REST)                     │
├─────────────────────────────────────────────────────────┤
│  ExperimentController │ BucketingController │ Report     │
├─────────────────────────────────────────────────────────┤
│                    Service Layer                        │
├──────────────┬──────────────┬─────────────┬────────────┤
│  Experiment  │  Bucketing   │  Metrics    │ Statistics │
│   Service    │   Service    │   Service   │  Service   │
├──────────────┴──────────────┴─────────────┴────────────┤
│        H2 (MySQL)       │      Redis      │  ClickHouse │
│    实验元数据存储       │   分桶结果缓存  │  事件日志   │
└─────────────────────────┴─────────────────┴─────────────┘
```

## API 接口

### 实验管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/experiments` | 创建实验 |
| GET | `/api/experiments` | 获取实验列表 |
| GET | `/api/experiments/{id}` | 获取实验详情 |
| POST | `/api/experiments/{id}/start` | 启动实验 |
| POST | `/api/experiments/{id}/pause` | 暂停实验 |
| POST | `/api/experiments/{id}/resume` | 恢复实验 |
| POST | `/api/experiments/{id}/complete` | 结束实验 |
| DELETE | `/api/experiments/{id}` | 删除实验 |
| POST | `/api/experiments/traffic` | 调整流量 |

### 用户分桶

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/experiments/{experimentId}/assign/{userId}` | 用户分配实验组 |

### 事件上报

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/experiments/events` | 上报单个事件 |
| POST | `/api/experiments/events/batch` | 批量上报事件 |

### 报告查询

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/experiments/{id}/report` | 获取完整实验报告 |
| GET | `/api/experiments/{id}/report/metrics/{metricName}` | 获取单个指标统计结果 |
| GET | `/api/experiments/{id}/trend?days=7` | 获取趋势数据 |

## 使用示例

### 1. 创建实验

```bash
curl -X POST http://localhost:8080/api/experiments \
-H "Content-Type: application/json" \
-d '{
  "name": "按钮颜色测试",
  "description": "测试红色和蓝色按钮的点击率差异",
  "owner": "product_team",
  "trafficPercentage": 50,
  "trafficKey": "user_id",
  "variants": [
    {
      "name": "control",
      "trafficWeight": 50,
      "isControl": true,
      "configuration": "{\"color\": \"blue\"}"
    },
    {
      "name": "test_red",
      "trafficWeight": 50,
      "isControl": false,
      "configuration": "{\"color\": \"red\"}"
    }
  ],
  "metrics": [
    {
      "name": "click_rate",
      "description": "按钮点击率",
      "type": "CONVERSION",
      "eventName": "button_click"
    },
    {
      "name": "stay_time",
      "description": "页面停留时间",
      "type": "CONTINUOUS",
      "eventName": "page_leave",
      "propertyName": "seconds",
      "aggregationType": "AVG"
    }
  ]
}'
```

### 2. 用户分桶

```bash
curl http://localhost:8080/api/experiments/1/assign/user_123
```

响应：
```json
{
  "userId": "user_123",
  "experimentId": 1,
  "experimentName": "按钮颜色测试",
  "variantName": "test_red",
  "variantConfiguration": "{\"color\": \"red\"}",
  "isControl": false,
  "bucket": 3456
}
```

### 3. 上报曝光事件

```bash
curl -X POST http://localhost:8080/api/experiments/events \
-H "Content-Type: application/json" \
-d '{
  "userId": "user_123",
  "eventName": "exposure",
  "experimentId": 1,
  "variantName": "test_red"
}'
```

### 4. 上报点击事件

```bash
curl -X POST http://localhost:8080/api/experiments/events \
-H "Content-Type: application/json" \
-d '{
  "userId": "user_123",
  "eventName": "button_click",
  "experimentId": 1,
  "variantName": "test_red"
}'
```

### 5. 查看实验报告

```bash
curl http://localhost:8080/api/experiments/1/report
```

## 快速开始

### 环境要求
- JDK 17+
- Maven 3.6+
- Redis 6.0+
- ClickHouse 22.0+

### 启动服务

1. 启动 Redis
2. 启动 ClickHouse
3. 编译运行：

```bash
mvn clean package
java -jar target/abtest-platform-1.0.0.jar
```

服务启动后访问：http://localhost:8080

H2 数据库控制台：http://localhost:8080/h2-console
- JDBC URL: `jdbc:h2:mem:abtestdb`
- 用户名: `sa`
- 密码: (空)

## 核心数据结构

### 实验表 (experiments)
- id, name, description, owner, status, traffic_percentage, traffic_key
- start_time, end_time, created_at, updated_at

### 实验组表 (variants)
- id, experiment_id, name, traffic_weight, is_control, configuration

### 指标表 (metrics)
- id, experiment_id, name, description, type (CONVERSION/CONTINUOUS)
- event_name, property_name, aggregation_type

### ClickHouse 事件表 (events)
```sql
CREATE TABLE events (
    timestamp DateTime,
    user_id String,
    experiment_id Int64,
    variant_name String,
    event_name String,
    properties String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (experiment_id, variant_name, timestamp, user_id)
```

## 统计检验说明

### 转化率指标 (卡方检验)
- 零假设：实验组和对照组转化率相同
- 显著性水平：α = 0.05
- p < 0.05 拒绝零假设，认为差异显著

### 连续型指标 (T检验)
- 使用 Welch's T-Test（不假设方差齐性）
- 显著性水平：α = 0.05
- 计算 95% 置信区间

## License

MIT License
