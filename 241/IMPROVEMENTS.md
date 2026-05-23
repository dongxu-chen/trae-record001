# 分布式锁服务 - 功能改进说明

## 本次改进内容

### 1. 客户端心跳检测与强制释放锁 ✅

#### 功能描述
- 服务端为每个锁持有者维护最后心跳时间戳
- 后台线程定期检测心跳是否超时（默认：租约TTL的1/2）
- 心跳超时后强制释放锁并触发告警
- 客户端自动发送心跳，也支持手动发送

#### 实现细节

**服务端 (LockManager.java):**
```java
// 每个持有者维护最后心跳时间
private final AtomicLong lastHeartbeatTime;

// 心跳检测线程定期检查
heartbeatChecker.scheduleAtFixedRate(() -> {
    // 检测心跳超时
    if (holder.isHeartbeatExpired(heartbeatTimeoutMs)) {
        // 强制释放锁
        // 触发告警事件
        notifyHeartbeatLost(event);
    }
}, heartbeatTimeoutMs / 2, ...);
```

**客户端 (DistributedLockClient.java):**
```java
// 自动心跳发送
HeartbeatSender 定时发送心跳

// 注册心跳丢失监听器
client.addHeartbeatLostListener(event -> {
    // 处理告警逻辑
    alertService.notify("Heartbeat lost for lock: " + event.getLockName());
});
```

#### API 变化
- 新增 `HeartbeatRequest` / `HeartbeatResponse` proto消息
- 新增 `LockService.Heartbeat` gRPC方法
- 新增 `DistributedLockClient.sendHeartbeat()` 方法
- 新增 `DistributedLockClient.addHeartbeatLostListener()` 方法

---

### 2. 分段线程池 - 按锁分片处理租约续期 ✅

#### 功能描述
- 将锁按名称哈希分片到多个线程池
- 每个分片独立处理租约续期，避免单线程瓶颈
- 分片数量 = CPU核心数，充分利用多核性能

#### 实现细节
```java
// 分片数量 = CPU核心数
this.shardCount = Runtime.getRuntime().availableProcessors();
this.leaseRenewExecutors = new ScheduledExecutorService[shardCount];

// 按锁名哈希分配分片
private int getShardIndex(String lockName) {
    return Math.abs(lockName.hashCode() % shardCount);
}

// 每个分片独立处理
for (int shard = 0; shard < shardCount; shard++) {
    leaseRenewExecutors[shard].scheduleAtFixedRate(() -> {
        for (Map.Entry<String, LockInfo> entry : lockRegistry.entrySet()) {
            if (getShardIndex(lockName) != currentShard) {
                continue;  // 只处理本分片的锁
            }
            // 处理租约续期
        }
    }, renewInterval, renewInterval, TimeUnit.SECONDS);
}
```

#### 性能优势
- 避免单线程处理所有锁的续期瓶颈
- 多核CPU并行处理，提高续期效率
- 锁数量大时性能提升明显

---

### 3. 读写锁互斥改进 - 写锁优先级 ✅

#### 问题背景
**原问题：** 当有大量读锁时，写锁可能一直等待导致写饥饿（Write Starvation）

**解决方案：** 当有写锁在等待时，阻塞新的读锁请求

#### 实现细节

**LockInfo.java - 新增写锁等待计数:**
```java
private final AtomicInteger waitingWriteLockCount;

public void addWaiter(Waiter waiter) {
    waitQueue.add(waiter);
    if (isWriteLock(waiter.getLockType())) {
        waitingWriteLockCount.incrementAndGet();
    }
}

public boolean hasWaitingWriteLock() {
    return waitingWriteLockCount.get() > 0;
}
```

**LockManager.java - 读锁获取逻辑:**
```java
private boolean canAcquireLock(LockInfo lockInfo, String clientId, LockType lockType, boolean reentrant) {
    // ... 其他检查
    
    if (lockType == LockType.READ) {
        // 关键：有写锁等待时，新读锁被阻塞
        if (lockInfo.hasWaitingWriteLock()) {
            return false;
        }
        return lockInfo.isReadLocked();
    }
    
    return false;
}
```

#### 行为对比

**改进前（可能写饥饿）:**
```
时间线:
T1: Reader1 获取读锁 ✓
T2: Writer 请求写锁 (等待)
T3: Reader2 获取读锁 ✓  ← 问题：Writer继续等待
T4: Reader3 获取读锁 ✓  ← 问题：Writer继续等待
T5: Reader1 释放读锁
T6: Reader2 释放读锁
T7: Reader3 释放读锁
T8: Writer 获取写锁 ✓  ← 等待了很久！
```

**改进后（写锁优先）:**
```
时间线:
T1: Reader1 获取读锁 ✓
T2: Writer 请求写锁 (等待，标记有写锁等待)
T3: Reader2 尝试获取读锁 ✗  ← 被阻塞！
T4: Reader3 尝试获取读锁 ✗  ← 被阻塞！
T5: Reader1 释放读锁
T6: Writer 获取写锁 ✓  ← Writer及时获取锁！
T7: Writer 释放写锁
T8: Reader2, Reader3 可重新竞争读锁
```

#### 公平性说明
- 写锁等待时，新读锁被加入等待队列
- 遵循 FIFO 顺序，防止读写互相饥饿
- 适合读多写少但写操作时效性要求高的场景

---

## 架构图

### 改进后的服务端架构
```
                            ┌─────────────────────────────────────┐
                            │         LockManager                   │
                            │                                      │
┌─────────┐   Heartbeat    │  ┌───────────────────────────────┐  │
│ Client  │ ─────────────▶ │  │    Heartbeat Checker          │  │
└─────────┘                │  │  (检测心跳超时，强制释放锁)    │  │
                            │  └───────────────────────────────┘  │
                            │                                      │
                            │  ┌───────────────────────────────┐  │
                            │  │   Lease Renew Executors       │  │
                            │  │   ┌─────┐ ┌─────┐ ┌─────┐    │  │
                            │  │   │Shard│ │Shard│ │Shard│    │  │
                            │  │   │  0  │ │  1  │ │ ... │    │  │
                            │  │   └─────┘ └─────┘ └─────┘    │  │
                            │  │   (按锁分片处理租约续期)       │  │
                            │  └───────────────────────────────┘  │
                            │                                      │
                            │  ┌───────────────────────────────┐  │
                            │  │   Lock Acquisition Logic      │  │
                            │  │   - 可重入检查                 │  │
                            │  │   - 读写锁兼容检查             │  │
                            │  │   - 写锁等待优先 (防饥饿)      │  │
                            │  └───────────────────────────────┘  │
                            └─────────────────────────────────────┘
```

---

## 使用示例

### 1. 心跳告警监听
```java
DistributedLockClient client = new DistributedLockClient(config);

// 注册心跳丢失告警
client.addHeartbeatLostListener(event -> {
    // 发送告警邮件/短信/钉钉通知
    alertService.sendAlert(
        "Heartbeat Lost Alert",
        String.format("Lock %s held by %s lost heartbeat at %d", 
            event.getLockName(), 
            event.getClientId(),
            event.getEventTime())
    );
    
    // 业务补偿逻辑
    businessService.handleLockForceReleased(event.getLockName());
});
```

### 2. 手动心跳发送
```java
// 获取锁后手动发送心跳
DistributedLock lock = new DistributedLock(client, "my-lock");
lock.lock();
try {
    // 长耗时操作过程中手动心跳
    for (int i = 0; i < 10; i++) {
        doSomeWork();
        client.sendHeartbeat();  // 手动心跳
    }
} finally {
    lock.unlock();
}
```

### 3. 写锁优先场景
```java
// 读操作 - 当没有写锁等待时可共享
DistributedLock readLock = new DistributedLock(client, "data", LockType.READ, true);
readLock.lock();
try {
    // 读数据
} finally {
    readLock.unlock();
}

// 写操作 - 优先级高，防止饥饿
DistributedLock writeLock = new DistributedLock(client, "data", LockType.WRITE, true);
writeLock.lock();  // 等待时会阻塞新的读锁
try {
    // 写数据
} finally {
    writeLock.unlock();
}
```

---

## 配置参数

### 服务端配置
```java
LockServerConfig config = LockServerConfig.builder()
    .defaultLeaseTtlSeconds(30)           // 租约TTL (秒)
    .leaseAutoRenewEnabled(true)           // 启用自动续期
    .leaseRenewIntervalSeconds(10)         // 续期间隔 (秒)
    // 心跳超时 = leaseTtl * 1000 / 2 (自动计算)
    .build();
```

### 客户端配置
```java
LockClientConfig config = LockClientConfig.builder()
    .defaultLeaseTtlSeconds(30)           // 租约TTL (秒)
    .autoRenewLease(true)                  // 客户端自动续期
    // 心跳间隔 = leaseTtl * 1000 / 3 (自动计算)
    .build();
```

---

## 监控指标

新增监控指标：
- `heartbeat_lost_count` - 心跳丢失总次数
- `write_lock_waiting_count` - 每个锁的等待写锁数量

可通过监控系统告警：
- 心跳丢失率 > 0 触发告警
- 写锁平均等待时间 > 阈值 触发告警