# Appwrite MQTT Sync Architecture

## 概述

这是一个完整的离线优先（Offline-First）同步架构，使用 Appwrite 作为自托管后端，SQLite 作为本地数据库，MQTT 协议实现实时同步，并采用端到端加密（E2EE）确保数据安全。

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                客户端（Flutter）                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐   │
│  │     UI层     │    │   状态管理层   │    │     业务逻辑层       │   │
│  │  (Widgets)   │    │  (Provider)   │    │   (Sync Engine)     │   │
│  └──────────────┘    └──────────────┘    └──────────────────────┘   │
│                                    │                                      │
│  ┌─────────────────────────────────▼──────────────────────────────────┐│
│  │                    核心同步层（Core Sync Layer）                      ││
│  ├──────────────────────────────────────────────────────────────────────┤│
│  │                                                                      ││
│  │  ┌─────────────────┐     ┌─────────────────┐     ┌───────────────┐  ││
│  │  │  SQLite 数据库  │     │   E2EE 加密层    │     │   MQTT 客户端  │  ││
│  │  │  (本地存储)     │     │  (CryptoService) │     │  (实时同步)    │  ││
│  │  └─────────────────┘     └─────────────────┘     └───────────────┘  ││
│  │                                                                      ││
│  └──────────────────────────────────────────────────────────────────────┘│
│                                    │                                      │
│                                    │  MQTT 协议                           │
└────────────────────────────────────┼──────────────────────────────────────┘
                                     │
                ┌────────────────────▼────────────────────┐
                │                                           │
                │        MQTT Broker (HiveMQ/EMQX)        │
                │          (实时消息转发)                   │
                │                                           │
                └────────────────────┬─────────────────────┘
                                     │
                ┌────────────────────▼────────────────────┐
                │                                           │
                │         Appwrite 自托管服务器             │
                │  ┌─────────┐  ┌──────────┐  ┌─────────┐ │
                │  │ Accounts│  │Database  │  │ Storage │ │
                │  └─────────┘  └──────────┘  └─────────┘ │
                │                                           │
                └───────────────────────────────────────────┘
```

---

## 核心组件

### 1. 架构核心定义 (`lib/core/architecture.dart`)

定义了整个系统的基础类型和枚举：

#### `SyncStatus` - 同步状态
```dart
enum SyncStatus {
  offline,     // 离线
  connecting,  // 连接中
  online,      // 在线
  syncing,     // 同步中
  error,       // 错误
}
```

#### `ConflictStrategy` - 冲突解决策略
```dart
enum ConflictStrategy {
  lastWriteWins,  // 最后写入获胜（默认）
  firstWriteWins, // 最先写入获胜
  merge,          // 合并策略
  manual,         // 手动解决
  clientWins,     // 客户端优先
}
```

#### `SyncMessage` - 同步消息
```dart
class SyncMessage {
  final String id;                    // 消息唯一ID
  final String collectionId;          // 集合ID
  final String documentId;            // 文档ID
  final SyncOperation operation;       // 操作类型
  final Map<String, dynamic> encryptedData;  // 加密数据
  final int version;                  // 版本号
  final String vectorClock;           // 向量时钟（JSON编码）
  final String deviceId;              // 设备ID
  final DateTime timestamp;           // 时间戳
  final String signature;             // HMAC签名
  final String nonce;                 // 防重放随机数
}
```

#### `VectorClock` - 向量时钟
用于检测并发修改和因果关系：
```dart
class VectorClock {
  bool happensBefore(VectorClock other);    // 检测因果关系
  bool isConcurrent(VectorClock other);      // 检测并发
  VectorClock merge(VectorClock other);      // 合并时钟
  void increment(String deviceId);           // 递增设备时钟
}
```

---

### 2. 端到端加密层 (`lib/core/encryption/crypto_service.dart`)

#### 核心功能
- **AES-256-GCM**: 对称加密算法，提供机密性和完整性
- **PBKDF2**: 密钥派生，100,000次迭代
- **HMAC-SHA256**: 消息认证码，防篡改
- **ECDH (secp256r1)**: 椭圆曲线密钥交换（用于多设备同步）

#### 工作流程
```
加密:
  明文数据 → JSON序列化 → AES-256-GCM加密 → Base64编码 → 发送

解密:
  接收 → Base64解码 → AES-256-GCM解密 → JSON反序列化 → 明文数据

签名验证:
  消息元数据 → HMAC-SHA256 → 签名比对 → 防篡改验证
```

#### 安全特性
1. **服务器零知识**: 服务器只存储加密数据，无法读取明文
2. **前向保密**: 使用随机 Nonce，相同明文每次加密结果不同
3. **重放攻击防护**: 每条消息携带唯一 Nonce，服务器验证唯一性
4. **完整性保护**: GCM模式提供内置完整性校验

---

### 3. SQLite 本地数据库 (`lib/core/database/sqlite_database.dart`)

#### 数据库表结构
```sql
-- 文档主表
CREATE TABLE documents (
  id TEXT PRIMARY KEY,
  collection_id TEXT NOT NULL,
  encrypted_data TEXT NOT NULL,     -- AES-256-GCM加密的JSON
  version INTEGER NOT NULL DEFAULT 1,
  vector_clock TEXT NOT NULL,       -- 向量时钟JSON
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  deleted INTEGER NOT NULL DEFAULT 0, -- 软删除标记
  synced INTEGER NOT NULL DEFAULT 0   -- 是否已同步标记
);

-- 操作日志（用于增量同步）
CREATE TABLE operation_logs (
  id TEXT PRIMARY KEY,
  collection_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  operation TEXT NOT NULL,           -- create/update/delete/merge
  encrypted_data TEXT NOT NULL,
  version INTEGER NOT NULL,
  vector_clock TEXT NOT NULL,
  device_id TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  signature TEXT NOT NULL,           -- HMAC签名
  nonce TEXT NOT NULL,               -- 防重放
  synced INTEGER NOT NULL DEFAULT 0
);

-- 同步状态表
CREATE TABLE sync_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

#### 核心方法
```dart
// CRUD操作
insertDocument(collectionId, documentId, data)
updateDocument(collectionId, documentId, data)
deleteDocument(collectionId, documentId)
getDocument(collectionId, documentId)
getCollection(collectionId)

// 同步相关
getUnsyncedOperations()
markOperationSynced(id)
markDocumentSynced(collectionId, documentId)
applyRemoteOperation(syncMessage)

// 状态管理
saveSyncState(key, value)
getSyncState(key)
```

---

### 4. MQTT 实时同步客户端 (`lib/core/sync/mqtt_sync_client.dart`)

#### MQTT 协议特性
- **QoS 2**: 精确一次送达，确保消息不重复不丢失
- **保留消息**: 新订阅者立即获取最新状态
- **遗嘱消息**: 异常离线时通知其他设备
- **心跳保活**: 30秒间隔，检测连接状态

#### Topic 设计
```
users/{userId}/sync/{collectionId}     # 文档同步消息
users/{userId}/broadcast/checkpoint    # 检查点请求
users/{userId}/sync/progress           # 同步进度广播
users/{userId}/offline                 # 设备离线通知（遗嘱）
```

#### 消息流
```
设备A: 修改文档 → 写入本地DB → 追加操作日志 → MQTT发布
      ↓
MQTT Broker: 路由到所有订阅该topic的设备
      ↓
设备B: 接收消息 → 验证签名/Nonce → 向量时钟检查
      ↓
      ├─ 过时消息 → 丢弃
      ├─ 并发修改 → 触发冲突解决
      └─ 新消息 → 应用到本地DB
```

#### 防重放机制
- 每个设备维护最近1000个 Nonce 缓存
- 新消息 Nonce 必须不在缓存中
- 时间戳必须在±5分钟内有效

---

### 5. 同步引擎 (`lib/core/sync/sync_engine.dart`)

#### 核心职责
1. 协调 SQLite 和 MQTT 之间的数据流动
2. 实现向量时钟冲突检测
3. 管理离线操作队列
4. 网络恢复后自动同步

#### 冲突解决流程
```
收到远程操作
    │
    ▼
获取本地文档版本
    │
    ▼
比较向量时钟
    │
    ├─ 远程 < 本地: 丢弃（已过时）
    ├─ 远程 > 本地: 应用更新
    └─ 并发修改:
        │
        ├─ LWW策略: 取时间戳最新的
        ├─ 合并策略: 字段级合并
        └─ 手动策略: 通知用户选择
```

#### 自动同步触发条件
- 网络连接恢复时（离线→在线）
- 本地有未同步操作时
- 收到其他设备的同步消息时
- 用户手动触发

---

### 6. Appwrite 客户端 (`lib/core/appwrite/appwrite_client.dart`)

#### 职责
- 用户认证（登录/注册）
- Appwrite 数据库双向同步
- 加密文件存储
- 作为 MQTT 实时同步的备份

#### 同步策略
- **Appwrite → 本地**: 增量拉取，基于 `updated_at` 时间戳
- **本地 → Appwrite**: 批量上传未同步操作
- **冲突处理**: 向量时钟检测，远程版本优先（可配置）

#### 文档存储格式
```json
{
  "$id": "document-uuid",
  "encrypted_data": "base64(AES-GCM(JSON(data)))",
  "device_id": "device-uuid",
  "vector_clock": "{\"deviceA\": 5, \"deviceB\": 3}",
  "version": 6,
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

## 完整同步流程

### 场景1: 单设备离线操作
```
1. 用户离线时创建/修改文档
   ↓
2. 写入本地 SQLite（标记 synced=0）
   ↓
3. 追加操作日志
   ↓
4. 网络恢复后
   ├─ MQTT 实时同步到其他设备
   └─ Appwrite 持久化备份
```

### 场景2: 多设备并发修改
```
设备A离线修改文档 (version=1 → 2, clock={A:2,B:1})
设备B离线修改同一文档 (version=1 → 2, clock={A:1,B:2})
    │
    └─ 设备A先上线 → 同步到Broker
       设备B后上线
          │
          ├─ 接收设备A的更新
          ├─ 向量时钟检测并发
          ├─ 应用冲突策略（LWW/合并）
          └─ 合并后的版本同步到所有设备
```

### 场景3: 新设备初始化
```
新设备登录
    │
    ▼
从Appwrite拉取所有加密文档
    │
    ▼
解密后写入本地SQLite
    │
    ▼
连接MQTT订阅同步Topic
    │
    ▼
开始接收实时更新
```

---

## 安全架构

### 数据加密矩阵
| 位置 | 加密方式 | 密钥持有者 |
|-----|---------|-----------|
| 本地SQLite | AES-256-GCM | 用户设备 |
| MQTT传输 | TLS 1.3 + AES-256-GCM | 用户设备 |
| Appwrite存储 | AES-256-GCM | 用户设备（服务器无法解密） |
| 消息签名 | HMAC-SHA256 | 用户设备 |

### 威胁防护
| 威胁 | 防护措施 |
|-----|---------|
| 中间人攻击 | TLS 1.3 + HMAC签名验证 |
| 重放攻击 | Nonce缓存 + 时间戳窗口 |
| 数据篡改 | 向量时钟版本号 + HMAC |
| 服务器泄露 | 端到端加密，服务器无密钥 |
| 设备丢失 | 密钥由用户密码派生，需密码解密 |

---

## 部署配置

### 前置要求
1. **Appwrite 服务器** (v1.4+)
   - 自托管或云托管
   - 启用 Database 和 Storage
   - 配置文档权限: `users.[userID]`

2. **MQTT Broker**
   - HiveMQ Community / EMQX / Mosquitto
   - 启用 TLS 1.3
   - 启用用户名密码认证
   - Topic ACL: 用户只能读写自己的 namespace

3. **Flutter 客户端**
   - Android: API 21+
   - iOS: 12.0+
   - Web: 支持现代浏览器

### 客户端配置
```dart
// MQTT 配置
final mqtt = MQTTSyncClient(
  broker: 'mqtt.yourdomain.com',
  port: 8883,  // TLS端口
  clientId: 'device_{unique_id}',
  userId: 'user_{user_id}',
  encryptionKey: derivedKey,
);

// Appwrite 配置
final appwrite = AppwriteSyncClient(
  endpoint: 'https://appwrite.yourdomain.com/v1',
  projectId: 'your_project_id',
  databaseId: 'your_database_id',
  deviceId: deviceId,
  encryptionKey: derivedKey,
  localDb: sqliteDb,
);
```

---

## 性能特性

### 本地操作
- **延迟**: < 10ms（SQLite 本地读写）
- **可用性**: 100%（离线可用）
- **并发**: 单设备串行化，保证一致性

### 同步性能
- **MQTT 延迟**: < 100ms（局域网）/ < 500ms（广域网）
- **批量同步**: 100条/秒
- **消息开销**: 每条消息约 200-500 字节

### 可扩展性
- **设备数量**: 无理论上限（MQTT Broker决定）
- **文档数量**: SQLite 支持百万级
- **单文档大小**: 推荐 < 1MB（MQTT 消息限制）

---

## 与 Firebase 对比

| 特性 | 本架构 | Firebase |
|-----|--------|---------|
| **数据主权** | ✅ 完全自托管，数据可控 | ❌ 第三方托管 |
| **端到端加密** | ✅ 原生支持，服务器不可见 | ⚠️ 需要自行实现 |
| **实时同步** | ✅ MQTT QoS 2，可靠 | ✅ Firestore 实时监听 |
| **离线支持** | ✅ 完整本地CRUD | ✅ 有限离线支持 |
| **成本** | ✅ 自托管几乎零成本 | ❌ 按量计费，规模化昂贵 |
| **冲突解决** | ✅ 向量时钟，可配置策略 | ⚠️ 基础LWW |
| **多设备同步** | ✅ 完整支持 | ✅ 支持 |
| **部署复杂度** | ⚠️ 需要维护MQTT和Appwrite | ✅ 托管服务 |

---

## 最佳实践

1. **加密密钥管理**
   - 密钥由用户密码通过 PBKDF2 派生
   - 考虑使用生物特征保护密钥
   - 实现密钥轮换机制

2. **同步策略**
   - 频繁小改动使用 MQTT 实时同步
   - 大数据批量使用 Appwrite 后台同步
   - 网络切换时触发全量一致性检查

3. **冲突预防**
   - 设计数据模型减少并发修改
   - 粒度小的文档（每个笔记一个文档）
   - 使用操作日志而非直接覆盖

4. **监控与调试**
   - 记录同步状态和错误日志
   - 监控 MQTT 连接质量
   - 实现远程日志收集（脱敏后）

---

## 文件结构

```
lib/core/
├── architecture.dart              # 核心类型定义
├── encryption/
│   └── crypto_service.dart        # E2EE 加密服务
├── database/
│   └── sqlite_database.dart       # SQLite 本地数据库
├── sync/
│   ├── mqtt_sync_client.dart      # MQTT 同步客户端
│   └── sync_engine.dart           # 同步引擎核心
└── appwrite/
    └── appwrite_client.dart        # Appwrite 集成

lib/example/
└── main.dart                       # 完整演示应用
```
