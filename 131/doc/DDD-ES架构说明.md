# 支付清算对账系统 - DDD + Event Sourcing 架构说明

## 1. 架构概述

本系统采用 **领域驱动设计 (DDD)** 结合 **事件溯源 (Event Sourcing)** 架构模式，同时实现 **CQRS** 读写分离，使用 Elasticsearch 作为查询模型存储。

### 核心设计原则

1. **账户流水作为事件源**：所有状态变更均以事件形式持久化
2. **对账结果从事件流中重建**：不直接保存对账结果，而是通过事件重放构建
3. **CQRS模式**：命令模型和查询模型完全分离
4. **支持无损发布**：通过事件重放实现无停机数据迁移和版本升级

---

## 2. 架构分层

```
┌─────────────────────────────────────────────────────────┐
│                      API Interface Layer                 │
├─────────────────────────────────────────────────────────┤
│                  Application Service Layer                │
│  ┌─────────────────┐          ┌──────────────────┐    │
│  │  Command Handlers│          │   Query Services  │    │
│  └─────────────────┘          └──────────────────┘    │
├─────────────────────────────────────────────────────────┤
│                      Domain Layer                        │
│  ┌─────────────────┐          ┌──────────────────┐    │
│  │  Aggregates     │          │   Domain Events   │    │
│  └─────────────────┘          └──────────────────┘    │
├─────────────────────────────────────────────────────────┤
│                Infrastructure Layer                      │
│  ┌─────────────────┐          ┌──────────────────┐    │
│  │  Event Store    │          │   Elasticsearch   │    │
│  └─────────────────┘          └──────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 核心领域模型

### 3.1 聚合根 (Aggregate Root)

#### AccountTransaction - 账户交易聚合

```java
public class AccountTransaction extends AggregateRoot<String> {
    private String transactionNo;      // 交易流水号
    private String orderNo;             // 订单号
    private String channelCode;         // 渠道编码
    private String merchantNo;          // 商户号
    private BigDecimal amount;          // 交易金额
    private BigDecimal fee;             // 手续费
    private LocalDateTime transTime;    // 交易时间
    private Integer status;             // 状态
}
```

#### ReconciliationAggregate - 对账聚合

```java
public class ReconciliationAggregate extends AggregateRoot<String> {
    private String reconciliationNo;       // 对账编号
    private String channelCode;            // 渠道编码
    private LocalDate reconciliationDate;  // 对账日期
    private List<ChannelTransaction> channelTransactions; // 渠道交易列表
    private List<Discrepancy> discrepancies;             // 差异列表
    private ReconciliationResult result;                 // 对账结果
}
```

### 3.2 领域事件 (Domain Events)

| 事件类型 | 说明 |
|---------|------|
| TransactionCreatedEvent | 交易创建事件 |
| ReconciliationStartedEvent | 对账开始事件 |
| ChannelTransactionCreatedEvent | 渠道交易创建事件 |
| DiscrepancyDetectedEvent | 差异发现事件 |
| ReconciliationCompletedEvent | 对账完成事件 |

---

## 4. Event Store 实现

### 4.1 事件存储表结构

```sql
CREATE TABLE event_store (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    event_id VARCHAR(64) NOT NULL,           -- 事件唯一ID
    aggregate_id VARCHAR(64) NOT NULL,       -- 聚合根ID
    aggregate_type VARCHAR(64) NOT NULL,     -- 聚合根类型
    version BIGINT NOT NULL,                  -- 事件版本号（乐观锁）
    event_type VARCHAR(128) NOT NULL,        -- 事件类型
    event_data TEXT NOT NULL,                 -- 事件JSON数据
    occurred_on DATETIME NOT NULL,            -- 事件发生时间
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 事件重放机制

```java
// 重放所有事件重建读模型
eventReplayService.replayAllEvents();

// 重放指定聚合类型的事件
eventReplayService.replayEventsByAggregateType("ReconciliationAggregate");
```

**重放流程**：
1. 清空 Elasticsearch 索引
2. 从 event_store 按时间顺序加载所有事件
3. 逐个事件应用，重建查询模型
4. 完成后索引与事件源完全一致

---

## 5. CQRS 模式

### 5.1 命令模型 (Command Model)

#### 命令示例：CreateReconciliationCommand

```java
public class CreateReconciliationCommand extends Command {
    private String reconciliationNo;
    private String channelCode;
    private LocalDate reconciliationDate;
    private String fileName;
    private String filePath;
}
```

#### 命令处理器

```java
@Service
public class CreateReconciliationHandler implements CommandHandler<CreateReconciliationCommand, String> {
    @Override
    @Transactional
    public String handle(CreateReconciliationCommand command) {
        // 1. 创建聚合根
        ReconciliationAggregate reconciliation = ReconciliationAggregate.create(...);
        
        // 2. 保存事件到 Event Store
        reconciliationRepository.save(reconciliation);
        
        return command.getReconciliationNo();
    }
}
```

### 5.2 查询模型 (Query Model)

#### Elasticsearch 文档结构

```java
@Document(indexName = "reconciliation")
public class ReconciliationDoc {
    @Field(type = FieldType.Keyword)
    private String reconciliationNo;
    
    @Field(type = FieldType.Keyword)
    private String channelCode;
    
    @Field(type = FieldType.Date)
    private String reconciliationDate;
    
    // 统计字段
    private Integer sysTotalCount;
    private BigDecimal sysTotalAmount;
    private Integer channelTotalCount;
    private BigDecimal channelTotalAmount;
    private Integer matchedCount;
    private Integer longCount;
    private Integer shortCount;
    private Integer status;
}
```

#### 查询服务

```java
@Service
public class ReconciliationQueryService {
    // 根据对账号查询
    public ReconciliationDoc getByReconciliationNo(String reconciliationNo);
    
    // 按渠道和日期范围搜索
    public List<ReconciliationDoc> search(String channelCode, String startDate, String endDate);
    
    // 获取汇总统计
    public ReconciliationSummary getSummary(String channelCode, String date);
}
```

---

## 6. 事件同步机制

### 6.1 事件监听器

```java
@Component
public class ReconciliationEventListener {
    @Autowired
    private ElasticsearchRestTemplate elasticsearchTemplate;

    @EventListener
    public void handleReconciliationStarted(ReconciliationStartedEvent event) {
        // 同步到 Elasticsearch
        ReconciliationDoc doc = convertToDoc(event);
        elasticsearchTemplate.save(doc);
    }

    @EventListener
    public void handleReconciliationCompleted(ReconciliationCompletedEvent event) {
        // 更新 Elasticsearch 中的对账结果
        ReconciliationDoc doc = elasticsearchTemplate.get(event.getReconciliationNo(), ReconciliationDoc.class);
        updateDocFromEvent(doc, event);
        elasticsearchTemplate.save(doc);
    }
}
```

### 6.2 最终一致性保证

```
写操作流程:
1. Command 到达 Application Service
2. 加载/创建聚合根
3. 聚合根产生领域事件
4. 事件持久化到 Event Store
5. 事务提交
6. 事件发布到 Spring Event Bus
7. 监听器异步更新 Elasticsearch

一致性保证:
- Event Store 是唯一真相源
- Elasticsearch 数据可随时通过重放事件重建
- 即使同步失败，也可以通过重放恢复
```

---

## 7. 无损发布与对账重放

### 7.1 无损发布流程

**发布新版本时**：

```
1. 部署新版本应用（新旧版本同时运行）
2. 新版本启动后自动执行事件重放
   eventReplayService.replayAllEvents();
3. 验证新版本 Elasticsearch 数据正确性
4. 切换流量到新版本
5. 下线旧版本
```

### 7.2 对账重放能力

**场景1：对账规则变更**

```java
// 1. 修改对账规则逻辑
// 2. 重新执行所有对账
for (String reconciliationNo : allReconciliations) {
    ReconciliationAggregate agg = repository.load(reconciliationNo);
    // 重新应用对账规则
    agg.reExecuteReconciliation();
    repository.save(agg);
}
// 3. 重放事件更新读模型
eventReplayService.replayAllEvents();
```

**场景2：修复历史数据Bug**

```java
// 1. 发布修复版本
// 2. 触发事件重放
eventReplayService.replayAllEvents();
// 3. 所有读模型数据自动修复完成
```

---

## 8. 核心优势

### 8.1 审计追踪

- 所有状态变更都有完整的事件历史
- 任何时间点的状态都可以精确回溯
- 满足金融监管的审计要求

### 8.2 时间旅行

```java
// 重建2024-01-15时的对账状态
LocalDateTime pointInTime = LocalDateTime.of(2024, 1, 15, 23, 59, 59);
ReconciliationAggregate agg = repository.loadAt("R001", pointInTime);
```

### 8.3 可测试性

- 领域模型完全独立于基础设施
- 不依赖数据库也能测试业务逻辑
- 事件溯源天然支持事件驱动测试

### 8.4 扩展性

- 新增读模型：只需监听事件，无需修改写逻辑
- 集成第三方系统：订阅事件即可
- 业务规则变更：只需重放事件，无需数据迁移

---

## 9. 项目结构

```
src/main/java/com/payment/reconciliation/ddd/
├── core/                           # 核心抽象
│   ├── AggregateRoot.java         # 聚合根基类
│   ├── Command.java               # 命令基类
│   ├── CommandHandler.java        # 命令处理器接口
│   ├── DomainEvent.java           # 领域事件基类
│   └── EventStore.java            # 事件存储接口
├── domain/
│   ├── aggregate/                 # 聚合根
│   │   ├── AccountTransaction.java
│   │   └── ReconciliationAggregate.java
│   ├── event/                     # 领域事件
│   │   ├── TransactionCreatedEvent.java
│   │   ├── ReconciliationStartedEvent.java
│   │   ├── ReconciliationCompletedEvent.java
│   │   ├── ChannelTransactionCreatedEvent.java
│   │   └── DiscrepancyDetectedEvent.java
│   └── repository/                # 仓储接口
│       └── ReconciliationRepository.java
├── application/
│   ├── command/                   # 命令定义
│   │   └── CreateReconciliationCommand.java
│   ├── handler/                   # 命令处理器
│   │   └── CreateReconciliationHandler.java
│   ├── query/                     # 查询模型
│   │   ├── ReconciliationDoc.java
│   │   └── ReconciliationQueryService.java
│   ├── listener/                  # 事件监听器
│   │   └── ReconciliationEventListener.java
│   └── service/                   # 应用服务
│       └── EventReplayService.java
└── infrastructure/
    └── eventstore/                # 事件存储实现
        ├── EventStoreEntity.java
        ├── EventStoreMapper.java
        └── EventStoreImpl.java
```

---

## 10. 快速开始

### 10.1 初始化数据库

```bash
mysql -u root -p < src/main/resources/sql/event_store_init.sql
```

### 10.2 启动 Elasticsearch

```bash
docker run -d -p 9200:9200 -p 9300:9300 elasticsearch:7.17.0
```

### 10.3 创建对账（命令示例）

```java
CreateReconciliationCommand command = new CreateReconciliationCommand();
command.setReconciliationNo("R20240115001");
command.setChannelCode("ALIPAY");
command.setReconciliationDate(LocalDate.of(2024, 1, 15));
command.setFileName("20240115_alipay.csv");
command.setFilePath("/data/reconciliation/20240115_alipay.csv");

String reconciliationNo = createReconciliationHandler.handle(command);
```

### 10.4 查询对账结果

```java
ReconciliationDoc doc = reconciliationQueryService.getByReconciliationNo("R20240115001");
```

---

## 11. 运维监控

### 11.1 关键指标监控

| 指标 | 说明 | 阈值 |
|------|------|------|
| event_store 记录数 | 事件总数量 | 趋势监控 |
| 事件重放耗时 | 重放所有事件时间 | < 5分钟 |
| 事件同步延迟 | 事件产生到ES可查询时间 | < 1秒 |
| 聚合版本连续性 | 版本号是否有断层 | 必须连续 |

### 11.2 数据一致性检查

```sql
-- 定期检查事件数量一致性
SELECT COUNT(*) FROM event_store;

-- 检查每个聚合的版本连续性
SELECT aggregate_id, MIN(version), MAX(version), COUNT(*)
FROM event_store
GROUP BY aggregate_id
HAVING MAX(version) - MIN(version) + 1 <> COUNT(*);
```

---

**架构版本**: 1.0.0
**最后更新**: 2024-01-15
