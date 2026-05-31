# 分布式锁监控平台

一个功能完整的分布式锁监控平台，支持Redis和ZooKeeper两种分布式锁实现，提供锁事件埋点、Prometheus指标监控、Grafana可视化仪表盘、Elasticsearch日志存储以及锁竞争、死锁、热点锁分析功能。

## 技术栈

- **Java 11** - 开发语言
- **Spring Boot 2.7.x** - 应用框架
- **Redisson 3.24.x** - Redis分布式锁实现
- **Apache Curator 5.4.x** - ZooKeeper分布式锁实现
- **Prometheus** - 指标采集
- **Grafana** - 可视化监控
- **Elasticsearch 7.x** - 事件日志存储
- **Docker & Docker Compose** - 容器化部署

## 项目结构

```
distributed-lock-monitor/
├── lock-core/              # 核心接口和公共类
│   ├── DistributedLock.java          # 分布式锁接口
│   ├── AbstractDistributedLock.java  # 抽象基类（包含埋点逻辑）
│   ├── LockEvent.java                # 锁事件模型
│   └── LockEventListener.java        # 事件监听器接口
├── lock-redis/             # Redis分布式锁实现
│   ├── RedisDistributedLock.java
│   └── RedisLockFactory.java
├── lock-zookeeper/         # ZooKeeper分布式锁实现
│   ├── ZkDistributedLock.java
│   └── ZkLockFactory.java
├── lock-monitor/           # 监控模块
│   ├── LockMetricsCollector.java     # Prometheus指标收集器
│   ├── LockMonitorManager.java       # 监控管理器
│   ├── LockEventEsStorage.java       # Elasticsearch存储
│   └── LockEventEsRepository.java
├── lock-analysis/          # 分析模块
│   ├── LockAnalysisService.java      # 锁分析服务
│   ├── LockAnalysisController.java   # 分析API
│   └── AnalysisEventListener.java
├── lock-boot/              # Spring Boot启动模块
│   ├── LockMonitorApplication.java
│   ├── LockConfig.java
│   └── LockDemoController.java
└── deploy/                 # 部署配置
    ├── docker-compose.yml
    ├── Dockerfile
    ├── prometheus/
    └── grafana/
```

## 核心功能

### 1. 锁埋点与事件采集
- 自动采集锁的申请、持有、释放事件
- 事件包含：锁Key、锁类型、线程信息、主机信息、等待时间、持有时间等

### 2. Prometheus监控指标
- `lock_acquire_total` - 锁申请总数（按结果分类：success/fail）
- `lock_wait_time_ms` - 锁等待时间（含p50/p75/p95/p99分位数）
- `lock_hold_time_ms` - 锁持有时间（含p50/p75/p95/p99分位数）
- `lock_held_current` - 当前持有锁数量
- `lock_contention_total` - 锁竞争总数

### 3. 锁分析功能
- **热点锁识别** - 识别频繁被获取的锁
- **锁竞争分析** - 分析高竞争锁及其竞争率
- **死锁风险检测** - 检测潜在死锁风险
- **锁统计概览** - 整体锁使用情况统计

### 4. REST API接口

#### 演示接口
```
GET /api/lock-demo/redis/{lockKey}     # 测试Redis锁
GET /api/lock-demo/zookeeper/{lockKey} # 测试ZooKeeper锁
GET /api/lock-demo/concurrent/{lockKey} # 并发锁测试
```

#### 分析接口
```
GET /api/lock-analysis/overview            # 整体统计概览
GET /api/lock-analysis/hot-locks           # 热点锁列表
GET /api/lock-analysis/high-contention-locks  # 高竞争锁列表
GET /api/lock-analysis/statistics/{lockKey}   # 单个锁统计
GET /api/lock-analysis/deadlocks           # 潜在死锁检测
```

#### 监控端点
```
GET /actuator/prometheus    # Prometheus指标
GET /actuator/health        # 健康检查
```

## 快速开始

### 方式一：Docker Compose一键部署

```bash
cd deploy
docker-compose up -d
```

访问地址：
- 应用服务: http://localhost:8080
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Elasticsearch: http://localhost:9200

### 方式二：本地开发运行

1. 启动依赖服务（Redis、ZooKeeper、Elasticsearch）
2. 修改 `lock-boot/src/main/resources/application.yml` 配置
3. 编译运行：

```bash
mvn clean package -DskipTests
java -jar lock-boot/target/lock-boot-1.0.0.jar
```

## 使用示例

```java
@Autowired
private RedisLockFactory redisLockFactory;

@Autowired
private MonitorLockEventListener monitorListener;

public void doSomething() {
    RedisDistributedLock lock = redisLockFactory.getLock("order:123");
    
    // 添加监控监听器（自动埋点）
    lock.addEventListener(monitorListener);
    
    try {
        if (lock.tryLock(5, 30, TimeUnit.SECONDS)) {
            try {
                // 执行业务逻辑
            } finally {
                lock.unlock();
            }
        }
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
    }
}
```

## Grafana仪表盘

项目已内置Grafana仪表盘，包含以下监控面板：
- 总锁申请数
- 总锁竞争数
- 当前持有锁数
- 锁申请速率趋势图
- 锁等待时间（p95）趋势图
- 按锁Key分组的申请统计

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    Business Application                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               Distributed Lock Layer                        │
│  ┌───────────────┐      ┌─────────────────────┐           │
│  │  Redis Lock   │      │  ZooKeeper Lock     │           │
│  └───────┬───────┘      └──────────┬──────────┘           │
└──────────┼───────────────────────────┼──────────────────────┘
           │                           │
           └─────────────┬─────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Lock Event Instrumentation                     │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  │
│  │  Prometheus   │  │  Elasticsearch│  │  Analysis     │  │
│  │    Metrics    │  │    Storage    │  │    Engine     │  │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘  │
└──────────┼──────────────────┼──────────────────┼───────────┘
           │                  │                  │
           ▼                  ▼                  ▼
┌──────────────┐   ┌──────────────────┐  ┌───────────────┐
│  Prometheus  │   │  Elasticsearch   │  │  REST API     │
└──────┬───────┘   └──────────────────┘  └───────┬───────┘
       │                                         │
       ▼                                         ▼
┌──────────────┐                        ┌───────────────┐
│   Grafana    │                        │   Analysis    │
│  Dashboard   │                        │   Results     │
└──────────────┘                        └───────────────┘
```

## 注意事项

1. **Elasticsearch配置**：如不需要ES存储，可在配置中禁用，Prometheus指标不受影响
2. **锁事件监听器**：确保在使用锁时正确注册监听器，否则无法采集监控数据
3. **性能影响**：监控埋点对性能影响极小，但高并发场景下建议异步处理ES写入
4. **生产环境**：建议配置Elasticsearch集群、Prometheus持久化存储和适当的告警规则