# API重放攻击检测系统 (Replay Guard)

基于Java + Redis + LUA + 一致性哈希实现的API重放攻击检测系统。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         ReplayGuard                              │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ ReplayGuard  │→ │  RequestHasher│→ │  请求唯一性哈希计算   │  │
│  │  Manager     │  └──────────────┘  └──────────────────────┘  │
│  └──────┬───────┘                                                │
│         │                                                        │
│  ┌──────▼─────────────────────────────────────────────────────┐ │
│  │                    检测模块链                               │ │
│  │                                                              │ │
│  │  1. HoneypotDetector  (蜜罐检测/客户端封禁)                  │ │
│  │  2. NonceDetector     (Nonce防重/时间戳校验)                │ │
│  │  3. SlidingWindowDetector (滑动窗口限流)                    │ │
│  │  4. DistributedCounter (分布式计数器)                       │ │
│  └──────────────────────────────────────────────────────────────┘ │
│         │                                                        │
│  ┌──────▼─────────────────────────────────────────────────────┐ │
│  │              分布式存储层 (Redis + LUA)                    │ │
│  │                                                              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │ │
│  │  │ ZSet(窗口)│  │ String   │  │ String   │  │  String   │  │ │
│  │  │ 滑动窗口  │  │ Nonce值  │  │ 计数器   │  │ 蜜罐状态  │  │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └───────────┘  │ │
│  └──────────────────────────────────────────────────────────────┘ │
│         │                                                        │
│  ┌──────▼─────────────────────────────────────────────────────┐ │
│  │              一致性哈希路由 (ConsistentHashRouter)          │ │
│  │                                                              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │ │
│  │  │ Node-1   │  │ Node-2   │  │ Node-3   │  ...            │ │
│  │  └──────────┘  └──────────┘  └──────────┘                  │ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 核心特性

### 1. 请求唯一性哈希计算
- **RequestHasher**: 基于请求路径、参数、设备指纹等计算唯一性哈希
- SHA-256加密算法
- 参数顺序无关
- 路径规范化(大小写、结尾斜杠)
- JSON请求体标准化

### 2. 滑动窗口防重
- **SlidingWindowDetector**: 基于Redis有序集合(ZSet)实现滑动窗口
- LUA脚本保证原子性
- 自动清理过期数据
- 可配置时间窗口和最大请求数

### 3. Nonce防重检测
- **NonceDetector**: 防止同一Nonce被重复使用
- 时间戳有效性校验
- 分布式环境下的原子检查与设置

### 4. 分布式防重计数
- **DistributedCounter**: 基于Redis的分布式计数器
- LUA脚本保证原子性操作
- 支持阈值检测和自动过期

### 5. 慢查询蜜罐
- **HoneypotDetector**: 检测异常慢请求
- 累计慢请求次数
- 自动封禁恶意客户端
- 可配置阈值和封禁时长

### 6. 一致性哈希路由
- **ConsistentHashRouter**: 分布式节点路由
- 虚拟节点(150个/节点)保证均匀分布
- 支持动态增删节点
- 节点故障时键自动迁移

## 技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Java | 17+ | 运行环境 |
| Spring Boot | 3.2.4 | 应用框架 |
| Redis | 7.0+ | 数据存储 |
| Lettuce | 6.3.2 | Redis客户端 |
| LUA | - | 原子脚本执行 |

## 快速开始

### 1. 环境准备

```bash
# 启动Redis
docker run -d -p 6379:6379 redis:7-alpine
```

### 2. 配置修改

编辑 `src/main/resources/application.yml`:

```yaml
replay-guard:
  sliding-window:
    time-window-seconds: 60    # 滑动窗口时间(秒)
    max-requests-per-window: 10 # 窗口内最大请求数
  nonce-expire-seconds: 300     # Nonce过期时间
  honeypot:
    slow-threshold-ms: 2000     # 慢请求阈值(毫秒)
    max-slow-requests: 5         # 最大慢请求数
    block-duration-seconds: 600  # 封禁时长(秒)
  consistent-hash:
    virtual-node-count: 150     # 虚拟节点数
    nodes: node-1,node-2,node-3 # 节点列表
```

### 3. 构建运行

```bash
# 编译
mvn clean package -DskipTests

# 运行
java -jar target/replay-guard-1.0.0.jar
```

### 4. 请求头要求

客户端需要在请求头中携带以下信息:

| Header | 说明 | 必需 |
|--------|------|------|
| X-Timestamp | 请求时间戳(秒) | 推荐 |
| X-Nonce | 随机唯一标识 | 推荐 |
| X-Device-Fingerprint | 设备指纹 | 可选 |

## API接口

### 健康检查
```
GET /api/health
```

### 测试检测
```
POST /api/test/detect
Content-Type: application/json

{
  "requestPath": "/api/user",
  "method": "POST",
  "queryParams": {"id": "123"},
  "bodyHash": "abc123",
  "timestamp": "1716636000",
  "nonce": "unique-nonce",
  "deviceFingerprint": "device-123",
  "ipAddress": "192.168.1.1",
  "userAgent": "Mozilla/5.0"
}
```

### 哈希计算
```
GET /api/hash/compute?path=/api/test&fingerprint=xxx&timestamp=xxx&nonce=xxx
```

### 滑动窗口状态
```
GET /api/sliding-window/count?hash={unique_hash}
```

### 计数器操作
```
GET /api/counter/{key}
POST /api/counter/{key}/increment?maxCount=100&windowSeconds=60
DELETE /api/counter/{key}
```

### 蜜罐管理
```
GET /api/honeypot/status?clientId={client_id}
POST /api/honeypot/unblock?clientId={client_id}
```

### 一致性哈希
```
GET /api/consistent-hash/nodes
GET /api/consistent-hash/route?key={hash}&replicas=2
```

## LUA脚本说明

### 滑动窗口脚本
```lua
-- KEYS[1]: hash key
-- ARGV[1]: current timestamp
-- ARGV[2]: window size
-- ARGV[3]: max requests
-- ARGV[4]: request id
-- 返回: 1=允许, 0=拒绝
```

### Nonce检查脚本
```lua
-- KEYS[1]: nonce hash key
-- ARGV[1]: nonce value
-- ARGV[2]: expire seconds
-- 返回: 1=首次, 0=重复
```

### 蜜罐脚本
```lua
-- KEYS[1]: client key
-- ARGV[1]: slow threshold
-- ARGV[2]: max slow requests
-- ARGV[3]: block duration
-- ARGV[4]: request time
-- 返回: 1=正常, 2=封禁
```

### 分布式计数脚本
```lua
-- KEYS[1]: counter key
-- ARGV[1]: increment value
-- ARGV[2]: max count
-- ARGV[3]: window seconds
-- 返回: current count
```

## 测试

```bash
# 运行测试
mvn test

# 测试报告
mvn surefire-report:report
```

## 项目结构

```
replay-guard/
├── src/main/java/com/security/replayguard/
│   ├── ReplayGuardApplication.java
│   ├── config/
│   │   ├── RedisConfig.java
│   │   ├── ReplayGuardProperties.java
│   │   └── WebConfig.java
│   ├── controller/
│   │   └── ReplayGuardController.java
│   ├── core/
│   │   ├── RequestHasher.java
│   │   ├── SlidingWindowDetector.java
│   │   ├── NonceDetector.java
│   │   ├── DistributedCounter.java
│   │   ├── HoneypotDetector.java
│   │   ├── ConsistentHashRouter.java
│   │   └── ReplayGuardManager.java
│   ├── interceptor/
│   │   └── ReplayGuardInterceptor.java
│   └── model/
│       └── RequestFeature.java
└── src/test/java/com/security/replayguard/
    └── core/
        ├── RequestHasherTest.java
        ├── ConsistentHashRouterTest.java
        ├── ReplayGuardManagerTest.java
        └── LuaScriptsTest.java
```

## License

MIT
