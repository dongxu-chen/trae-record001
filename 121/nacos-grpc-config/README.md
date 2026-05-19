# Nacos gRPC 配置中心

基于 Nacos + gRPC 长连接的配置推送架构，支持配置秒级推送、增量变更、客户端主动拉取备选等高级特性。

## 核心特性

### ✅ 配置秒级推送
- **gRPC长连接订阅**：服务端与客户端维持长连接
- **秒级配置推送**：配置变更后秒级推送到所有订阅客户端
- **心跳保活**：自动检测连接状态，支持断线重连

### ✅ 增量配置推送
- **变更检测**：服务端对比配置差异，仅推送变更的KV
- **版本控制**：基于版本号避免重复推送
- **变更类型**：支持新增、修改、删除三种变更类型

### ✅ 双模式配置获取
- **长连接推送**：优先使用长连接实时推送
- **主动拉取备选**：长连接异常时支持主动拉取
- **全量/增量拉取**：支持全量配置或增量变更拉取

### ✅ Spring Boot 无缝集成
- **自动配置**：Spring Boot Starter 自动配置
- **Environment 同步**：配置变更自动同步到 Spring Environment
- **@Value 注入**：支持 Spring 的 @Value 注解自动更新
- **声明式订阅**：配置文件中声明订阅的配置DataId

## 项目架构

```
┌─────────────────────────────────────────────────────────┐
│                     Nacos 配置中心                       │
│              (配置存储、变更监听、版本管理)                │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Config-Server (配置中心服务端)              │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Nacos Listener: 监听Nacos配置变更事件              │  │
│  │  Change Detector: 配置变更检测，仅推送变更KV       │  │
│  │  gRPC Server: 长连接推送服务                        │  │
│  │  Session Manager: 客户端会话管理                    │  │
│  └────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Client A     │  │ Client B     │  │ Client C     │
│ (服务实例1)  │  │ (服务实例2)  │  │ (服务实例3)  │
│ - gRPC Channel │  │ - gRPC Channel │  │ - gRPC Channel │
│ - Config Cache │  │ - Config Cache │  │ - Config Cache │
│ - Change Listnr│  │ - Change Listnr│  │ - Change Listnr│
└──────────────┘  └──────────────┘  └──────────────┘
```

## 模块说明

| 模块 | 说明 |
|------|------|
| `nacos-grpc-config-protocol` | gRPC协议定义，protobuf消息和服务接口 |
| `nacos-grpc-config-server` | 配置中心服务端，集成Nacos和gRPC服务 |
| `nacos-grpc-config-client` | 客户端SDK，支持长连接订阅和主动拉取 |
| `nacos-grpc-config-spring-boot-starter` | Spring Boot Starter自动配置 |
| `nacos-grpc-config-example` | 使用示例 |

## 快速开始

### 前置条件

- JDK 11+
- Maven 3.6+
- Nacos Server 2.0+ (本地默认端口: 8848)

### 1. 编译项目

```bash
cd nacos-grpc-config
mvn clean install -DskipTests
```

### 2. 启动Nacos

```bash
# 下载并启动Nacos
# 或者使用Docker
docker run --name nacos-standalone -e MODE=standalone -p 8848:8848 nacos/nacos-server:latest
```

### 3. 在Nacos中创建配置

登录Nacos控制台 (http://localhost:8848/nacos)，创建以下配置：

**DataId: app-config, Group: DEFAULT_GROUP**
```properties
app.name=config-center-demo
app.version=1.0.0
app.env=dev
app.feature.enabled=true
```

**DataId: db-config, Group: DEFAULT_GROUP**
```properties
db.url=jdbc:mysql://localhost:3306/test
db.username=root
db.password=123456
db.max-active=100
```

### 4. 启动配置中心服务端

```bash
cd nacos-grpc-config-server
mvn spring-boot:run
```

gRPC服务默认端口: 9090

### 5. 启动示例应用

```bash
cd nacos-grpc-config-example
mvn spring-boot:run
```

### 6. 测试API

```bash
# 获取配置
curl http://localhost:8080/api/config

# 健康检查
curl http://localhost:8080/api/config/health

# 主动拉取配置
curl -X POST http://localhost:8080/api/config/pull/app-config?fullPull=true
```

## Spring Boot 集成使用

### 1. 添加依赖

```xml
<dependency>
    <groupId>com.configcenter</groupId>
    <artifactId>nacos-grpc-config-spring-boot-starter</artifactId>
    <version>1.0.0</version>
</dependency>
```

### 2. 配置文件

```yaml
# application.yml
config:
  center:
    enabled: true                    # 启用配置中心
    server-host: localhost           # 配置中心服务端地址
    server-port: 9090               # gRPC端口
    service-name: your-service       # 服务名称
    namespace: public                # Nacos命名空间
    group: DEFAULT_GROUP             # 配置分组
    auto-startup: true               # 自动启动客户端
    subscribe-data-ids:              # 订阅的配置DataId列表
      - app-config
      - db-config
      - feature-flags
```

### 3. 使用配置

```java
@RestController
public class MyController {

    // 直接使用@Value注入
    @Value("${app.name:default}")
    private String appName;

    @Value("${db.url:}")
    private String dbUrl;

    // 注入客户端进行高级操作
    @Autowired
    private ConfigServiceClient configClient;

    @GetMapping("/config")
    public Map<String, Object> getConfig() {
        Map<String, Object> result = new HashMap<>();
        result.put("appName", appName);
        result.put("dbUrl", dbUrl);
        result.put("allConfigs", configClient.getAllConfigs());
        return result;
    }
}
```

### 4. 监听配置变更

```java
@Component
public class MyConfigChangeListener implements ConfigChangeListener {

    @Override
    public void onChange(ConfigChangeEvent event) {
        System.out.println("配置变更: " + event.getDataId());
        
        // 获取变更的配置项
        for (ConfigChangeEvent.ChangeItem change : event.getChanges()) {
            System.out.println("Key: " + change.getKey());
            System.out.println("OldValue: " + change.getOldValue());
            System.out.println("NewValue: " + change.getNewValue());
            System.out.println("ChangeType: " + change.getChangeType());
        }

        // 检查特定key是否变更
        if (event.hasChanged("db.url")) {
            // 重新初始化数据库连接池
            reloadDataSource();
        }
    }

    private void reloadDataSource() {
        // 自定义处理逻辑
    }
}
```

## 独立客户端SDK使用

不依赖Spring Boot也可以直接使用客户端SDK：

```java
public class StandaloneClient {
    public static void main(String[] args) {
        // 1. 创建客户端
        ConfigServiceClient client = ConfigServiceClient.builder()
                .serverHost("localhost")
                .serverPort(9090)
                .serviceName("my-service")
                .namespace("public")
                .group("DEFAULT_GROUP")
                .build();

        // 2. 启动客户端
        client.start();

        // 3. 订阅配置
        client.subscribe("app-config", "db-config");

        // 4. 添加变更监听器
        client.addChangeListener(event -> {
            System.out.println("配置变更: " + event.getDataId());
        });

        // 5. 获取配置
        String appName = client.getConfig("app.name");
        Map<String, String> allConfig = client.getAllConfigs();

        // 6. 主动拉取（备选方案）
        Map<String, String> freshConfig = client.pullConfig("app-config", true);

        // 7. 关闭客户端
        // client.close();
    }
}
```

## gRPC协议说明

### 服务定义

```protobuf
service ConfigService {
    // 长连接订阅 - 服务端流式推送配置变更
    rpc Subscribe(SubscribeRequest) returns (stream SubscribeResponse) {}

    // 客户端主动拉取（长连接断开时的备选方案）
    rpc PullConfig(PullConfigRequest) returns (PullConfigResponse) {}

    // 心跳保活 - 双向流式
    rpc Heartbeat(stream HeartbeatRequest) returns (stream HeartbeatResponse) {}
}
```

### 消息结构

**配置变更项**
```protobuf
message ConfigItem {
    string key = 1;
    string value = 2;
    ConfigChangeType change_type = 3;  // ADDED, MODIFIED, DELETED
    int64 version = 4;
}
```

**订阅响应**
```protobuf
message SubscribeResponse {
    string request_id = 1;
    string data_id = 2;
    string group = 3;
    repeated ConfigItem changed_items = 4;  // 仅推送变更的KV
    int64 version = 5;
    ResponseStatus status = 6;
    string message = 7;
    int64 timestamp = 8;
}
```

## 配置推送流程

### 1. 正常流程

```
Nacos配置变更
       ↓
Nacos ConfigListener 接收事件
       ↓
ConfigChangeDetector 计算配置差异
       ↓
只保留变更的KV（ADDED/MODIFIED/DELETED）
       ↓
SessionManager 查找所有订阅该DataId的客户端
       ↓
通过gRPC Stream推送 SubscribeResponse
       ↓
客户端应用配置变更，触发 ChangeListener
       ↓
Spring Environment 同步更新
```

### 2. 异常处理

- **长连接断开**：客户端自动重连，重连后自动拉取全量配置
- **Nacos连接异常**：使用本地缓存的配置
- **推送失败**：支持客户端主动拉取作为备选

## 性能优化

### 1. 增量推送
- 只推送变更的KV，减少网络传输
- 平均配置变更大小减少 80% 以上

### 2. 版本控制
- 基于版本号避免重复推送
- 客户端本地版本与服务端版本对比

### 3. 本地缓存
- 客户端本地缓存配置
- 连接异常时使用缓存配置

### 4. 心跳优化
- 30秒心跳间隔，减少网络开销
- 心跳超时自动重连

## 最佳实践

### 1. 配置命名规范
- DataId使用业务维度划分：`app-config`, `db-config`, `redis-config`
- Group使用环境维度：`DEV_GROUP`, `TEST_GROUP`, `PROD_GROUP`
- 命名空间按部门/业务线划分

### 2. 配置变更监听
```java
// 只处理关心的配置项
if (event.hasChanged("db.url") || event.hasChanged("db.password")) {
    reloadDataSource();
}
```

### 3. 容灾处理
```java
// 连接异常时降级处理
if (!configClient.isConnected()) {
    // 使用本地缓存配置
    Map<String, String> backupConfig = loadBackupConfig();
    // 或使用默认值
}
```

### 4. 监控告警
- 监控客户端连接状态
- 监控配置变更频率
- 异常变更触发告警

## 常见问题

### Q1: gRPC连接失败怎么办？
A: 检查服务端是否启动、端口是否开放、网络是否连通。客户端会自动重连。

### Q2: 配置变更后没有推送？
A: 1. 检查Nacos配置是否正确保存；2. 检查客户端是否订阅了该DataId；3. 查看服务端日志确认变更事件。

### Q3: 如何保证配置一致性？
A: 服务端推送时带版本号，客户端校验版本，版本落后时主动拉取全量配置。

### Q4: 长连接断开期间的配置变更怎么办？
A: 重连后客户端会自动拉取全量配置，保证不会丢失变更。

## 许可证

MIT License
