# 快速开始指南

## 5分钟快速运行演示应用

### 1. 安装依赖

```bash
flutter pub get
```

### 2. 运行演示应用

```bash
cd lib/example
flutter run
```

演示应用将连接到公共 MQTT Broker (broker.hivemq.com)，你可以：
- 在本地创建/删除笔记
- 断开网络后继续操作（离线模式）
- 恢复网络后自动同步
- 在多个设备上测试实时同步

---

## 生产环境部署

### 步骤1: 部署 Appwrite 服务器

1. 安装 Docker
2. 运行 Appwrite:

```bash
docker run -it --rm \
  --volume /var/run/docker.sock:/var/run/docker.sock \
  --volume "$(pwd)"/appwrite:/usr/src/code/appwrite:rw \
  --entrypoint="install" \
  appwrite/appwrite:1.4.13
```

3. 访问控制台: http://localhost
4. 创建新项目，记录 `projectId`
5. 创建数据库，记录 `databaseId`
6. 创建集合，配置权限: `users.[userID]`

### 步骤2: 部署 MQTT Broker

**选项A: 使用 EMQX**
```bash
docker run -d --name emqx -p 1883:1883 -p 8083:8083 -p 8883:8883 emqx/emqx:latest
```

**选项B: 使用 HiveMQ CE**
```bash
docker run -d --name hivemq -p 1883:1883 hivemq/hivemq-ce:latest
```

### 步骤3: 配置应用

编辑 `lib/example/main.dart`:

```dart
// MQTT 配置（替换为你的Broker）
final mqtt = MQTTSyncClient(
  broker: 'mqtt.yourdomain.com',
  port: 1883,        // 8883 for TLS
  clientId: 'device_${_deviceId}',
  userId: 'actual_user_id',
  encryptionKey: _encryptionKey,
);

// Appwrite 配置
final appwrite = AppwriteSyncClient(
  endpoint: 'https://appwrite.yourdomain.com/v1',
  projectId: 'your_project_id',
  databaseId: 'your_database_id',
  deviceId: _deviceId,
  encryptionKey: _encryptionKey,
  localDb: _db,
);
```

### 步骤4: 启用 TLS（生产环境必须）

```dart
// MQTT TLS 配置
final mqtt = MQTTSyncClient(
  broker: 'mqtt.yourdomain.com',
  port: 8883,
  // ...
);

// Appwrite HTTPS
final appwrite = AppwriteSyncClient(
  endpoint: 'https://appwrite.yourdomain.com/v1',
  // ...
);
```

---

## 核心 API 使用示例

### 1. 初始化同步引擎

```dart
final crypto = CryptoService();
final encryptionKey = crypto.deriveKey('user_password', 'salt_value');

final db = SQLiteDatabase('device_123');
db.setEncryptionKey(encryptionKey);

final mqtt = MQTTSyncClient(
  broker: 'broker.hivemq.com',
  port: 1883,
  clientId: 'device_123',
  userId: 'user_456',
  encryptionKey: encryptionKey,
);

final engine = SyncEngine(
  db: db,
  mqtt: mqtt,
  deviceId: 'device_123',
  conflictStrategy: ConflictStrategy.lastWriteWins,
);

await engine.initialize();
```

### 2. 文档操作

```dart
// 创建文档
await engine.createDocument('notes', 'note_001', {
  'title': '我的笔记',
  'content': '这是一条测试笔记',
  'createdAt': DateTime.now().toIso8601String(),
});

// 获取文档
final doc = await engine.getDocument('notes', 'note_001');

// 获取集合所有文档
final allNotes = await engine.getCollection('notes');

// 更新文档
await engine.updateDocument('notes', 'note_001', {
  'title': '更新后的标题',
  'content': '新的内容',
});

// 删除文档（软删除）
await engine.deleteDocument('notes', 'note_001');
```

### 3. 监听同步状态

```dart
engine.statusStream.listen((status) {
  switch (status) {
    case SyncStatus.offline:
      print('已离线');
      break;
    case SyncStatus.connecting:
      print('连接中...');
      break;
    case SyncStatus.online:
      print('已连接');
      break;
    case SyncStatus.syncing:
      print('同步中...');
      break;
    case SyncStatus.error:
      print('同步错误');
      break;
  }
});

engine.progressStream.listen((progress) {
  print('同步进度: ${(progress * 100).toStringAsFixed(0)}%');
});
```

### 4. Appwrite 认证

```dart
// 注册
final user = await appwrite.register(
  'user@example.com',
  'password123',
  '用户名',
);

// 登录
final user = await appwrite.login('user@example.com', 'password123');

// 获取当前用户
final currentUser = await appwrite.getCurrentUser();

// 登出
await appwrite.logout();
```

### 5. 手动触发同步

```dart
// MQTT 强制同步（立即推送本地未同步操作）
await engine.forceSync();

// Appwrite 完整同步（双向同步）
await appwrite.fullSync();

// 仅本地到远程
await appwrite.syncLocalToRemote();

// 仅远程到本地
await appwrite.syncRemoteToLocal();
```

---

## 离线场景测试指南

### 测试场景1: 离线编辑

1. 打开应用，确认已连接
2. 创建几条笔记
3. 断开网络（飞行模式 / 拔网线）
4. 继续创建 / 修改笔记
5. 恢复网络
6. ✅ 验证: 所有离线操作自动同步，数据不丢失

### 测试场景2: 多设备并发

1. 设备A和设备B同时打开应用
2. 两台设备都断开网络
3. 设备A修改笔记X
4. 设备B修改同一笔记X
5. 设备A先联网，设备B后联网
6. ✅ 验证: 根据 LWW 策略，时间较新的版本生效

### 测试场景3: 全新设备初始化

1. 在设备A创建数据并同步
2. 在设备B登录同一账号
3. ✅ 验证: 设备B从 Appwrite 拉取所有加密数据并解密

---

## 常见问题

### Q: MQTT 连接失败怎么办？
A: 检查:
1. Broker 地址和端口是否正确
2. 网络连接是否正常
3. 防火墙是否阻止了 MQTT 端口（1883/8883）
4. Broker 是否启用了认证（需要用户名密码）

### Q: 数据解密失败怎么办？
A: 确认:
1. 使用相同的密码派生密钥
2. Salt 值在所有设备上一致
3. 数据在传输过程中没有损坏（HMAC验证失败说明被篡改）

### Q: 如何处理大规模数据？
A: 建议:
1. 大文件使用 Appwrite Storage，不通过 MQTT 同步
2. 使用增量同步而非全量同步
3. 本地分页加载数据，避免内存占用过高

### Q: 向量时钟越来越大怎么办？
A: 定期执行检查点清理，合并并重置向量时钟：
```dart
// 每1000次操作后执行一次压缩
await engine.requestCheckpoint('notes');
```

---

## 下一步

- 阅读 [架构文档](./ARCHITECTURE.md) 了解完整设计
- 查看各个组件的源代码理解实现细节
- 根据你的业务需求调整冲突解决策略
- 实现用户界面和业务逻辑
