# 狼人杀游戏后端 (WolfKill Game Backend)

基于 Netty + Redis + Protobuf + MySQL 实现的实时狼人杀游戏后端系统。

## 技术栈

- **Netty 4.1.101**: 高性能网络通信框架
- **Redis**: 缓存和会话管理
- **Protobuf 3.25.1**: 高效的序列化协议
- **MySQL 8.0**: 数据持久化
- **Spring Boot 3.2.0**: 应用框架
- **JPA / Hibernate**: ORM框架
- **Redisson**: 分布式锁和高级Redis操作

## 功能特性

### 游戏房间管理
- 创建/加入/离开房间
- 房间密码保护
- 房间列表查询
- 房主权限管理

### 角色系统
- **村民 (Villager)**: 无特殊技能，白天投票
- **狼人 (Werewolf)**: 夜晚杀人
- **预言家 (Seer)**: 夜晚查验身份
- **女巫 (Witch)**: 拥有解药和毒药
- **猎人 (Hunter)**: 死亡时可以开枪
- **守卫 (Guard)**: 每晚守护一人
- **丘比特 (Cupid)**: 指定情侣

### 游戏流程
1. **等待阶段**: 玩家加入房间
2. **夜晚阶段**: 狼人杀人、预言家查验、女巫用药
3. **白天阶段**: 公布死亡信息
4. **发言阶段**: 玩家轮流发言
5. **投票阶段**: 投票处决玩家
6. 循环直至游戏结束

### 高级特性
- **心跳保活**: 定期检测玩家在线状态
- **断线重连**: 支持玩家掉线后重新连接
- **游戏录像**: 记录游戏全过程，支持回放
- **实时聊天**: 房间内聊天功能

## 项目结构

```
src/main/java/com/wolfkill/
├── WolfKillApplication.java          # 启动类
├── config/
│   ├── NettyConfig.java              # Netty配置
│   └── RedisConfig.java              # Redis配置
├── entity/
│   ├── Player.java                   # 玩家实体
│   ├── GameRoom.java                 # 游戏房间实体
│   ├── GameRecord.java               # 游戏记录实体
│   └── GameFrame.java                # 游戏帧实体
├── repository/
│   ├── PlayerRepository.java
│   ├── GameRoomRepository.java
│   ├── GameRecordRepository.java
│   └── GameFrameRepository.java
├── manager/
│   ├── PlayerManager.java            # 玩家会话管理
│   └── RoomManager.java              # 房间管理
├── model/
│   ├── PlayerSession.java            # 玩家会话
│   └── GameRoomSession.java          # 房间会话
├── netty/
│   ├── NettyServer.java              # Netty服务器
│   ├── ConnectionHandler.java        # 连接处理器
│   └── MessageHandler.java           # 消息处理器
├── service/
│   ├── GameService.java              # 游戏核心逻辑
│   ├── RoleService.java              # 角色分配服务
│   ├── MessageService.java           # 消息发送服务
│   ├── ReplayService.java            # 录像回放服务
│   ├── RedisService.java             # Redis操作服务
│   └── HeartbeatService.java         # 心跳检测服务
└── protocol/                         # Protobuf生成的代码
```

## 快速开始

### 1. 环境要求
- JDK 17+
- MySQL 8.0+
- Redis 6.0+
- Maven 3.6+

### 2. 数据库初始化
```bash
mysql -u root -p < src/main/resources/schema.sql
```

### 3. 配置修改
编辑 `src/main/resources/application.yml`:
```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/wolfkill
    username: root
    password: your_password
  data:
    redis:
      host: localhost
      port: 6379
```

### 4. 编译运行
```bash
# 编译（包含Protobuf代码生成）
mvn clean compile

# 运行
mvn spring-boot:run
```

### 5. 端口说明
- Netty TCP服务: 9000
- Spring Boot HTTP: 8080

## 消息协议

所有消息使用Protobuf序列化，消息格式：
```
MessageWrapper {
    MessageType type;
    bytes payload;
}
```

### 主要消息类型

| 类型 | 说明 |
|------|------|
| LOGIN_REQ/RES | 登录 |
| HEARTBEAT_REQ/RES | 心跳 |
| RECONNECT_REQ/RES | 重连 |
| CREATE_ROOM_REQ/RES | 创建房间 |
| JOIN_ROOM_REQ/RES | 加入房间 |
| START_GAME_REQ/RES | 开始游戏 |
| WOLF_KILL_REQ/RES | 狼人杀人 |
| SEER_CHECK_REQ/RES | 预言家查验 |
| WITCH_ACTION_REQ/RES | 女巫操作 |
| HUNTER_SHOT_REQ/RES | 猎人开枪 |
| VOTE_REQ/RES | 投票 |
| RECORD_LIST_REQ/RES | 录像列表 |
| RECORD_PLAYBACK_REQ/RES | 录像回放 |

## 游戏配置

在 `application.yml` 中可配置：
```yaml
game:
  room:
    max-players: 12      # 最大玩家数
    min-players: 6       # 最小玩家数
  heartbeat:
    interval: 5000       # 心跳检测间隔(ms)
    timeout: 30000       # 心跳超时时间(ms)
  replay:
    enabled: true        # 启用录像
    save-interval: 5000  # 录像保存间隔
```

## 游戏规则

### 胜负条件
- **狼人胜利**: 狼人数量 >= 好人数量
- **好人胜利**: 所有狼人被淘汰

### 夜晚行动顺序
1. 守卫守护
2. 狼人杀人
3. 预言家查验
4. 女巫用药

### 特殊说明
- 女巫解药可以救当晚被狼人杀死的玩家
- 女巫毒药可以毒杀任意一名玩家
- 猎人被投票或狼人杀死时可以开枪带走一人（被毒死除外）
- 守卫不能连续两晚守护同一人

## License

MIT License
