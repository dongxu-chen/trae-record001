# 消息队列死信处理平台 (Dead Letter Queue Processing Platform)

一个功能完整的消息队列死信处理平台，支持自动消费死信队列、智能分析死信原因、提供处理建议、死信重放、死信归档和告警规则。

## 技术架构

### 后端技术栈
- **Java 17** + **Spring Boot 3.2**
- **多MQ适配**：Kafka、RocketMQ、RabbitMQ
- **规则引擎**：Easy Rules 4.1
- **存储**：Elasticsearch 8.11
- **构建**：Maven 多模块

### 前端技术栈
- **React 18** + **TypeScript**
- **UI组件**：Ant Design 5
- **构建工具**：Vite 5
- **状态管理**：Zustand
- **图表**：ECharts

## 项目结构

```
dead-letter-platform/
├── dlq-common/                 # 公共模块
│   ├── enums/                  # 枚举类
│   ├── entity/                 # 实体类
│   ├── dto/                    # DTO类
│   └── utils/                  # 工具类
├── dlq-mq-adapter/             # MQ适配层
│   ├── consumer/               # 消费者实现
│   │   ├── kafka/
│   │   ├── rocketmq/
│   │   └── rabbitmq/
│   ├── producer/               # 生产者实现
│   ├── config/                 # 配置类
│   └── factory/                # 工厂类
├── dlq-analysis/               # 死信分析引擎
│   ├── analyzer/               # 分析器
│   ├── rules/                  # 规则定义
│   ├── config/                 # 规则引擎配置
│   ├── generator/              # 建议生成器
│   └── service/                # 分析服务
├── dlq-es/                     # Elasticsearch集成
│   ├── config/                 # ES配置
│   ├── constants/              # 索引常量
│   ├── repository/             # 数据访问层
│   └── service/                # 搜索/归档服务
├── dlq-service/                # 业务服务层
│   ├── service/                # 业务服务
│   └── scheduler/              # 定时任务
├── dlq-api/                    # REST API接口
│   ├── controller/             # Controller
│   ├── config/                 # 配置类
│   └── common/                 # 通用类
├── frontend/                   # 前端React应用
│   ├── src/
│   │   ├── pages/              # 页面组件
│   │   ├── components/         # 公共组件
│   │   ├── layouts/            # 布局组件
│   │   ├── api/                # API服务
│   │   ├── store/              # 状态管理
│   │   ├── types/              # 类型定义
│   │   └── utils/              # 工具函数
│   └── package.json
├── docker-compose.yml          # Docker编排
├── Dockerfile                  # 后端Dockerfile
├── Dockerfile.frontend         # 前端Dockerfile
└── pom.xml                     # 父POM
```

## 核心功能

### 1. 多MQ适配
- **Kafka**：支持手动提交offset、多topic订阅、死信转发
- **RocketMQ**：并发消费模式、三种发送模式（同步/异步/单向）
- **RabbitMQ**：手动ACK、死信队列自动创建、Confirm/Return回调

### 2. 死信分析引擎
- **规则引擎**：基于Easy Rules的可扩展规则系统
- **分析器**：
  - 格式错误分析（JSON格式、必填字段、数据类型）
  - 业务异常分析（NPE、数据库异常、业务异常）
  - 超时分析（Socket超时、Read超时、处理超时）
  - 拒绝策略分析（队列满、线程池饱和）
- **处理建议**：根据分析结果生成可操作的修复建议

### 3. 死信管理
- **死信重放**：单条/批量重放到原始队列
- **死信归档**：按条件归档到按月分区的索引
- **死信忽略**：标记忽略，不再处理
- **批量操作**：批量重放、批量归档、批量忽略

### 4. 告警规则
- **规则配置**：自定义触发条件（原因类型、重试次数、关键词等）
- **告警级别**：INFO、WARNING、CRITICAL
- **通知方式**：钉钉、企业微信、邮件、Webhook
- **告警静默**：防止重复告警

### 5. 统计分析
- **概览看板**：总死信数、待处理数、今日新增等
- **趋势分析**：最近7天死信趋势图
- **分布统计**：死信原因分布、MQ类型分布

## 快速开始

### 方式一：Docker Compose 一键启动

```bash
# 1. 克隆项目
git clone <repository-url>
cd dead-letter-platform

# 2. 编译后端
mvn clean package -DskipTests

# 3. 编译前端
cd frontend
npm install
npm run build
cd ..

# 4. 启动所有服务
docker-compose up -d

# 5. 访问应用
# 前端: http://localhost
# 后端API: http://localhost:8080
# Elasticsearch: http://localhost:9200
# RabbitMQ管理: http://localhost:15672 (admin/admin123)
# Kibana: http://localhost:5601 (可选，需加--profile optional)
```

### 方式二：本地开发

#### 后端启动

```bash
# 1. 启动依赖服务（ES, MQ）
docker-compose up -d elasticsearch kafka rocketmq-namesrv rocketmq-broker rabbitmq

# 2. 编译项目
mvn clean install -DskipTests

# 3. 启动应用
cd dlq-api
mvn spring-boot:run
```

#### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问 http://localhost:3000
```

## API 接口文档

### 死信管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dead-letters` | 分页查询死信列表 |
| GET | `/api/dead-letters/{id}` | 查询死信详情 |
| POST | `/api/dead-letters/{id}/replay` | 重放单条死信 |
| POST | `/api/dead-letters/batch-replay` | 批量重放 |
| POST | `/api/dead-letters/{id}/archive` | 归档单条 |
| POST | `/api/dead-letters/batch-archive` | 批量归档 |
| POST | `/api/dead-letters/{id}/ignore` | 忽略死信 |
| POST | `/api/dead-letters/batch-ignore` | 批量忽略 |
| GET | `/api/dead-letters/statistics` | 统计概览 |
| GET | `/api/dead-letters/aggregation` | 聚合统计 |

### 告警规则接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/alert-rules` | 规则列表 |
| GET | `/api/alert-rules/{id}` | 规则详情 |
| POST | `/api/alert-rules` | 创建规则 |
| PUT | `/api/alert-rules/{id}` | 更新规则 |
| DELETE | `/api/alert-rules/{id}` | 删除规则 |
| POST | `/api/alert-rules/{id}/enable` | 启用规则 |
| POST | `/api/alert-rules/{id}/disable` | 禁用规则 |

### 归档管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/archives` | 归档列表 |
| POST | `/api/archives/{id}/restore` | 恢复归档 |
| GET | `/api/archives/indexes` | 归档索引列表 |

### 分析接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/analysis/analyze` | 手动分析死信 |
| POST | `/api/analysis/batch-analyze` | 批量分析 |
| GET | `/api/analysis/suggestions/{id}` | 获取处理建议 |

## 配置说明

### MQ配置 (application.yml)

```yaml
mq:
  kafka:
    enabled: true
    bootstrap-servers: localhost:9092
    group-id: dlq-consumer-group
    auto-offset-reset: earliest
    topics:
      - order-topic
      - payment-topic
  
  rocketmq:
    enabled: true
    name-server: localhost:9876
    group: dlq-consumer-group
    topics:
      - order-topic
      - payment-topic
  
  rabbitmq:
    enabled: true
    host: localhost
    port: 5672
    username: admin
    password: admin123
    virtual-host: /
    queues:
      - order-queue
      - payment-queue
```

### Elasticsearch配置

```yaml
elasticsearch:
  enabled: true
  hosts:
    - localhost:9200
  username: elastic
  password: elastic
  index-prefix: dlq_
```

### 定时任务配置

```yaml
schedule:
  auto-analysis:
    enabled: true
    cron: "0 0 * * * ?"          # 每小时
  auto-replay:
    enabled: true
    cron: "0 */30 * * * ?"       # 每30分钟
  auto-archive:
    enabled: true
    cron: "0 0 2 * * ?"          # 每天凌晨2点
    keep-days: 30                # 保留30天
  statistics:
    enabled: true
    cron: "0 */5 * * * ?"        # 每5分钟
```

## 告警规则配置示例

```json
{
  "name": "数据库连接异常告警",
  "description": "当死信原因包含数据库连接异常时触发",
  "enabled": true,
  "triggerCondition": {
    "deadReasonType": "BIZ_EXCEPTION",
    "minRetryCount": 3,
    "timeRangeMinutes": 60,
    "keywords": ["SQLException", "连接超时", "Connection refused"]
  },
  "alertLevel": "CRITICAL",
  "notificationType": "DINGTALK",
  "notificationTarget": "https://oapi.dingtalk.com/robot/send?access_token=xxx"
}
```

## 扩展开发

### 添加新的MQ支持

1. 实现 `MessageConsumer` 和 `MessageProducer` 接口
2. 在 `MessageConsumerFactory` 和 `MessageProducerFactory` 中注册
3. 添加对应的配置类

### 添加新的分析规则

1. 在 `dlq-analysis` 模块中创建规则类，使用 `@Rule` 注解
2. 在对应分析器中注册规则
3. 规则会自动被规则引擎执行

### 添加新的通知方式

1. 实现 `AlertNotifier` 接口
2. 在 `AlertService` 中注册
3. 添加对应的配置

## 监控指标

通过 Spring Boot Actuator 暴露以下端点：

- `/actuator/health` - 健康检查
- `/actuator/info` - 应用信息
- `/actuator/metrics` - 指标信息
- `/actuator/prometheus` - Prometheus格式指标

## 许可证

MIT License
