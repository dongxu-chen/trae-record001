# 配置中心服务

基于 Spring Cloud Config + Git + RabbitMQ 实现的配置中心服务，支持配置的发布、回滚、监听功能。

## 项目结构

```
├── config-center-server/      # 配置中心服务端
│   ├── src/main/java/com/configcenter/
│   │   ├── ConfigCenterApplication.java    # 启动类
│   │   ├── controller/
│   │   │   └── ConfigController.java       # REST API控制器
│   │   ├── service/
│   │   │   ├── GitConfigService.java       # Git配置存储服务
│   │   │   ├── ConfigValidationService.java # 配置格式校验服务
│   │   │   ├── LongPollingService.java     # 长轮询服务
│   │   │   └── ConfigChangeNotifier.java   # 配置变更通知
│   │   ├── dto/
│   │   │   ├── ConfigDTO.java
│   │   │   ├── ConfigVersionDTO.java
│   │   │   └── Result.java
│   │   └── event/
│   │       └── ConfigChangeEvent.java      # 配置变更事件
│   ├── src/main/resources/
│   │   └── application.yml                 # 服务端配置
│   └── config-repo/                        # Git配置仓库
│       └── demo-app/
│           ├── dev/
│           ├── test/
│           └── prod/
└── config-center-client/      # 配置中心客户端示例
    ├── src/main/java/com/configcenter/
    │   ├── ConfigClientApplication.java
    │   ├── config/AppConfig.java           # 应用配置类
    │   ├── controller/ConfigDemoController.java
    │   └── listener/ConfigChangeListener.java
    └── src/main/resources/
        └── bootstrap.yml                   # 客户端配置
```

## 功能特性

### 1. 配置隔离
- 按应用名（application）隔离
- 按环境（dev/test/prod）隔离
- 支持多分支（label）管理

### 2. 配置版本管理
- 保留最近100个版本
- 支持查看版本历史
- 支持回滚到任意历史版本
- **回滚Diff校验**：高亮显示变更项
- **二次确认机制**：token有效期5分钟，防止误操作

### 3. 配置格式校验
- 支持 YAML 格式校验
- 支持 JSON 格式校验
- 支持格式转换（YAML ↔ JSON）
- 支持配置Diff比对

### 4. 配置变更通知
- RabbitMQ 消息总线（Spring Cloud Bus）
- 长轮询监听接口（**60秒超时，返回空响应**）
- 实时推送配置变更

### 5. 安全特性
- Git凭证**AES-256加密**存储
- 加密密钥从环境变量 `CONFIG_ENCRYPT_KEY` 读取

## API 接口

### 配置发布
```
POST /api/config/publish
Content-Type: application/json

{
    "application": "demo-app",
    "profile": "dev",
    "format": "yml",
    "content": "app:\n  name: demo-app\n  version: 1.0.0",
    "description": "更新配置",
    "createdBy": "admin"
}
```

### 获取配置
```
GET /api/config/{application}/{profile}?label={label}
```

### 获取版本历史
```
GET /api/config/{application}/{profile}/versions
```

### 获取指定版本配置
```
GET /api/config/{application}/{profile}/versions/{version}
```

### 配置回滚
```
POST /api/config/{application}/{profile}/rollback/{version}
```

### 长轮询监听
```
GET /api/config/{application}/{profile}/listen?currentVersion={version}
```

### 配置校验
```
POST /api/config/validate
Content-Type: application/json

{
    "content": "{\"key\": \"value\"}",
    "format": "json"
}
```

### 格式转换
```
POST /api/config/convert
Content-Type: application/json

{
    "content": "key: value",
    "from": "yaml",
    "to": "json"
}
```

### 灰度发布 - 创建
```
POST /api/config/gray/create
Content-Type: application/json

{
    "application": "demo-app",
    "profile": "dev",
    "strategy": "PERCENTAGE",
    "percentage": 10,
    "ipList": ["192.168.1.100"],
    "content": "app:\n  name: demo-app\n  version: 2.0.0",
    "format": "yml",
    "description": "灰度发布2.0版本"
}
```

### 灰度发布 - 列表
```
GET /api/config/gray/list?application=demo-app&profile=dev
```

### 灰度发布 - 更新比例
```
POST /api/config/gray/{id}/update
Content-Type: application/json

{
    "percentage": 30
}
```

### 灰度发布 - 全量发布
```
POST /api/config/gray/{id}/full
```

### 灰度发布 - 停止
```
POST /api/config/gray/{id}/stop
```

### 配置同步 - 预览
```
POST /api/config/sync/preview
Content-Type: application/json

{
    "application": "demo-app",
    "sourceProfile": "dev",
    "targetProfile": "test",
    "placeholderValues": {
        "DB_HOST": "test-db.example.com",
        "DB_PORT": "3306"
    }
}
```

### 配置同步 - 执行
```
POST /api/config/sync/execute
Content-Type: application/json

{
    "application": "demo-app",
    "sourceProfile": "dev",
    "targetProfile": "test",
    "placeholderValues": {
        "DB_HOST": "test-db.example.com"
    },
    "operator": "admin"
}
```

### 配置同步 - 批量
```
POST /api/config/sync/batch
Content-Type: application/json

{
    "syncs": [
        {
            "application": "demo-app",
            "sourceProfile": "dev",
            "targetProfile": "test",
            "placeholderValues": {"DB_HOST": "test-db"}
        }
    ],
    "operator": "admin"
}
```

### 审计 - 摘要
```
GET /api/config/audit/summary?application=demo-app&profile=dev
```

### 审计 - 活跃实例
```
GET /api/config/audit/instances?application=demo-app&profile=dev
```

### 审计 - 实例详情
```
GET /api/config/audit/instances/{instanceId}
```

### 审计 - 访问记录
```
GET /api/config/audit/access?application=demo-app&profile=dev
```

### 审计 - 使用统计
```
GET /api/config/audit/usage?application=demo-app&profile=dev
```

## 快速开始

### 环境要求
- JDK 11+
- Maven 3.6+
- RabbitMQ 3.8+

### 启动服务端

1. 启动 RabbitMQ
2. 编译并启动服务端：
```bash
cd config-center-server
mvn clean package
java -jar target/config-center-server-1.0.0.jar
```

服务端默认端口：8888

### 启动客户端

```bash
cd config-center-client
mvn clean package
java -jar target/config-center-client-1.0.0.jar
```

客户端默认端口：8080

## 配置说明

### 服务端配置（application.yml）

```yaml
spring:
  cloud:
    config:
      server:
        git:
          uri: ./config-repo          # Git仓库路径
          search-paths: '{application}/{profile}'
          default-label: master
    bus:
      enabled: true
  rabbitmq:
    host: localhost
    port: 5672
    username: guest
    password: guest

config:
  version:
    max-versions: 100               # 保留最大版本数
  long-polling:
    timeout: 30000                  # 长轮询超时时间(ms)
```

### 客户端配置（bootstrap.yml）

```yaml
spring:
  application:
    name: demo-app
  profiles:
    active: dev
  cloud:
    config:
      uri: http://localhost:8888
      profile: dev
      label: master
    bus:
      enabled: true
  rabbitmq:
    host: localhost
    port: 5672
    username: guest
    password: guest
```

## 使用示例

### 1. 发布配置

```bash
curl -X POST http://localhost:8888/api/config/publish \
  -H "Content-Type: application/json" \
  -d '{
    "application": "demo-app",
    "profile": "dev",
    "format": "yml",
    "content": "app:\n  name: demo-app\n  version: 1.0.1\n  env: dev",
    "description": "版本升级到1.0.1",
    "createdBy": "admin"
  }'
```

### 2. 查看版本历史

```bash
curl http://localhost:8888/api/config/demo-app/dev/versions
```

### 3. 回滚配置

```bash
curl -X POST http://localhost:8888/api/config/demo-app/dev/rollback/{version}
```

### 4. 长轮询监听配置变更

```bash
curl http://localhost:8888/api/config/demo-app/dev/listen?currentVersion={currentVersion}
```

### 5. 验证客户端配置刷新

```bash
# 查看客户端配置
curl http://localhost:8080/api/config

# 服务端发布新配置后，客户端配置会自动刷新
```

## Spring Cloud Config 原生接口

服务端同时支持 Spring Cloud Config 原生接口：

```
GET /{application}/{profile}[/{label}]
GET /{application}-{profile}.yml
GET /{label}/{application}-{profile}.yml
GET /{application}-{profile}.properties
GET /{label}/{application}-{profile}.properties
```

例如：
```
http://localhost:8888/demo-app/dev
http://localhost:8888/demo-app-dev.yml
```
