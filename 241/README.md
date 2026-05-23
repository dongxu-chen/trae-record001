# 分布式锁服务 (Distributed Lock Service)

基于 etcd + gRPC + Java 实现的高性能分布式锁服务，支持可重入锁、读写锁、自动租约续期等功能。

## 功能特性

### 核心功能
- ✅ **可重入锁** - 支持同一客户端多次获取同一把锁
- ✅ **读写锁** - 支持共享读锁和排他写锁
- ✅ **租约自动续期** - 防止因客户端崩溃导致的死锁
- ✅ **锁超时自动释放** - 租约过期自动清理

### 客户端特性
- ✅ **失败重试机制** - 基于 Resilience4j 的重试策略
- ✅ **熔断保护** - 服务故障时自动熔断
- ✅ **自动租约管理** - 客户端自动维护租约续期
- ✅ **简洁易用的API** - 支持 Lambda 表达式封装临界代码

### 监控特性
- ✅ **锁状态查询** - 查询锁持有者、等待队列等信息
- ✅ **全局统计** - 成功/失败次数、活跃锁数量等
- ✅ **批量查询** - 分页查询所有锁状态

### 高可用特性
- ✅ **etcd 集群** - 3节点以上etcd集群保证高可用
- ✅ **服务无状态** - 锁服务可水平扩展
- ✅ **负载均衡** - 支持gRPC负载均衡

## 项目结构

```
distributed-lock-parent/
├── distributed-lock-common/       # 公共模块 - gRPC proto定义
│   └── src/main/proto/
│       ├── lock_service.proto     # 锁服务接口定义
│       └── lock_monitor.proto     # 监控服务接口定义
│
├── distributed-lock-server/       # 服务端模块
│   ├── src/main/java/
│   │   └── com/distributed/lock/server/
│   │       ├── config/            # 配置类
│   │       ├── etcd/              # etcd客户端封装
│   │       ├── lock/              # 锁核心逻辑
│   │       │   ├── LockManager.java    # 锁管理器
│   │       │   └── LockInfo.java       # 锁信息数据结构
│   │       ├── grpc/              # gRPC服务实现
│   │       │   ├── LockServiceImpl.java
│   │       │   └── LockMonitorServiceImpl.java
│   │       └── LockServer.java    # 服务启动类
│   └── src/main/resources/
│       └── logback.xml
│
├── distributed-lock-client/       # 客户端SDK模块
│   └── src/main/java/
│       └── com/distributed/lock/client/
│           ├── config/            # 客户端配置
│           ├── DistributedLockClient.java   # 核心客户端
│           └── DistributedLock.java        # 锁工具类
│
└── distributed-lock-examples/     # 示例代码模块
    └── src/main/java/
        └── com/distributed/lock/examples/
            ├── ServerExample.java
            └── ClientExample.java
```

## 快速开始

### 环境要求
- JDK 11+
- Maven 3.6+
- etcd 3.5+

### 1. 启动 etcd

**开发环境单节点:**
```bash
docker run -d --name etcd -p 2379:2379 quay.io/coreos/etcd:v3.5.9 \
  etcd --name etcd1 \
  --listen-client-urls http://0.0.0.0:2379 \
  --advertise-client-urls http://localhost:2379
```

**生产环境集群:** 参考 [DEPLOYMENT.md](DEPLOYMENT.md)

### 2. 编译项目

```bash
# 编译生成gRPC代码
cd distributed-lock-common
mvn clean compile

# 编译整个项目
cd ..
mvn clean package -DskipTests
```

### 3. 启动服务端

```java
LockServerConfig config = LockServerConfig.builder()
    .etcdEndpoints(Arrays.asList("http://localhost:2379"))
    .grpcPort(50051)
    .defaultLeaseTtlSeconds(30)
    .build();

LockServer server = new LockServer(config);
server.start();
server.blockUntilShutdown();
```

### 4. 客户端使用

#### 基本使用

```java
// 创建客户端配置
LockClientConfig config = LockClientConfig.builder()
    .serverHost("localhost")
    .serverPort(50051)
    .clientId("client-001")
    .build();

try (DistributedLockClient client = new DistributedLockClient(config)) {
    // 创建锁
    DistributedLock lock = new DistributedLock(client, "my-resource");
    
    // 获取锁
    lock.lock();
    try {
        // 临界区代码
        System.out.println("Doing critical work...");
    } finally {
        lock.unlock();
    }
}
```

#### tryLock 模式

```java
DistributedLock lock = new DistributedLock(client, "my-resource");

if (lock.tryLock()) {
    try {
        // 获取锁成功
    } finally {
        lock.unlock();
    }
} else {
    // 获取锁失败
    System.out.println("Lock is held by another client");
}
```

#### Lambda 方式

```java
DistributedLock lock = new DistributedLock(client, "my-resource");

// 自动加锁解锁
String result = lock.executeWithLock(() -> {
    return "Critical operation result";
});
```

#### 可重入锁

```java
DistributedLock lock = new DistributedLock(client, "my-resource", LockType.EXCLUSIVE, true);

lock.lock();   // 第1次加锁
lock.lock();   // 第2次加锁 - 可重入

lock.unlock(); // 第1次解锁
lock.unlock(); // 第2次解锁 - 真正释放锁
```

#### 读写锁

```java
// 读锁 - 多个客户端可同时持有
DistributedLock readLock = new DistributedLock(client, "data", LockType.READ, true);

// 写锁 - 排他锁
DistributedLock writeLock = new DistributedLock(client, "data", LockType.WRITE, true);
```

#### 监控锁状态

```java
// 查询单个锁状态
LockStatusResponse status = client.getLockStatus("my-resource");
System.out.println("Locked: " + status.getIsLocked());
System.out.println("Holder: " + status.getHolderClientId());
System.out.println("Waiters: " + status.getWaitQueueLength());

// 查询统计信息
LockStatisticsResponse stats = client.getLockStatistics();
System.out.println("Active locks: " + stats.getActiveLocks());
System.out.println("Acquire success: " + stats.getLockAcquireSuccessCount());
```

## API 参考

### 锁类型

| 类型 | 说明 | 并发特性 |
|------|------|----------|
| EXCLUSIVE | 排他锁 | 同一时间只有一个持有者 |
| READ | 读锁 | 多客户端可同时持有 |
| WRITE | 写锁 | 排他，与读锁互斥 |

### 客户端配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| serverHost | localhost | 服务端地址 |
| serverPort | 50051 | 服务端端口 |
| clientId | UUID | 客户端唯一标识 |
| defaultTimeoutMs | 30000 | 锁获取超时(毫秒) |
| defaultLeaseTtlSeconds | 30 | 租约过期时间(秒) |
| autoRenewLease | true | 是否自动续期 |
| retryMaxAttempts | 3 | 最大重试次数 |
| retryWaitDurationMs | 500 | 重试间隔(毫秒) |
| circuitBreakerFailureRateThreshold | 50.0 | 熔断失败率阈值 |
| circuitBreakerWaitDurationInOpenStateMs | 10000 | 熔断恢复时间(毫秒) |

## 设计原理

### 租约机制
- 每个锁关联一个 etcd 租约
- 租约过期(默认30秒)后锁自动释放
- 服务端和客户端双重租约续期保证
- 防止客户端崩溃导致的死锁

### 可重入实现
- 每个锁持有者维护持有计数
- 同一客户端多次获取锁时计数递增
- 解锁时计数递减，计数为0时真正释放

### 读写锁机制
- 读锁共享：多个客户端可同时持有读锁
- 写锁排他：写锁与所有锁互斥
- 锁升级：持有写锁的客户端可获取读锁

### 容错机制
- **重试**：网络波动时自动重试请求
- **熔断**：服务端故障时快速失败
- **降级**：熔断后允许部分请求尝试恢复

## 部署

完整的高可用部署方案请参考 [DEPLOYMENT.md](DEPLOYMENT.md)，包含：
- etcd 集群部署 (Docker/Kubernetes)
- 锁服务集群部署
- gRPC 负载均衡配置
- Kubernetes 部署配置
- 监控和健康检查

## 性能优化

1. **etcd 调优**
   - 使用 SSD 存储
   - 合理设置压缩和快照参数
   - 网络低延迟优先

2. **服务端调优**
   - 调整线程池大小
   - gRPC 流控配置
   - JVM 内存参数

3. **客户端调优**
   - 复用客户端连接
   - 合理设置重试策略
   - 批量操作优化

## 注意事项

1. **锁粒度**：合理设计锁粒度，避免大范围锁竞争
2. **超时设置**：根据业务场景设置合理的超时时间
3. **异常处理**：始终在 finally 块中释放锁
4. **幂等性**：业务逻辑应保证幂等性
5. **监控告警**：监控锁等待时间和失败率

## License

MIT License