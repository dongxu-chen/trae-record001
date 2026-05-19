# 配置中心与热加载服务

基于 Spring Cloud Config + Bus + RabbitMQ 的配置中心与热加载服务后端API。

## 项目架构

```
├── config-center-parent/         # 父项目
├── config-server/                 # 配置中心服务端
├── config-client/                 # 配置客户端示例
└── config-repo/                   # Git配置仓库
    └── config-client/
        ├── config-client.yml      # 默认配置
        ├── config-client-dev.yml  # 开发环境配置
        └── config-client-prod.yml # 生产环境配置
```

## 技术栈

- **Spring Boot 2.7.18**
- **Spring Cloud 2021.0.8**
- **Spring Cloud Config Server** - 配置中心服务端
- **Spring Cloud Config Client** - 配置中心客户端
- **Spring Cloud Bus AMQP** - 消息总线实现配置广播
- **RabbitMQ** - 消息代理
- **Spring Boot Actuator** - 监控和端点暴露

## 核心功能

### 1. 配置文件Git存储和版本管理
- 配置文件存储在Git仓库中，支持版本控制
- 支持本地文件系统Git仓库（file://协议）
- 配置变更可追溯、可回滚

### 2. 配置动态刷新（/refresh端点）
- 使用 `@RefreshScope` 注解实现Bean的热加载
- 客户端暴露 `/actuator/refresh` 端点刷新配置
- 支持 `@ConfigurationProperties` 和 `@Value` 注解的配置刷新

### 3. 配置变更广播通知
- 集成 Spring Cloud Bus + RabbitMQ
- 服务端暴露 `/actuator/bus-refresh` 端点
- 调用一次即可广播通知所有客户端刷新配置
- 支持基于消息的异步配置更新

### 4. 多环境配置隔离（dev/prod）
- 支持 `{application}-{profile}.yml` 命名规则
- 默认配置：`config-client.yml`
- 开发环境：`config-client-dev.yml`
- 生产环境：`config-client-prod.yml`

### 5. GitLab/GitHub WebHook 集成
- GitLab WebHook: `/webhook/gitlab` (POST)
- GitHub WebHook: `/webhook/github` (POST)
- 监听 push 事件，自动触发配置拉取和刷新
- 支持 WebHook 签名验证，确保请求安全
- 自动解析变更文件，只刷新受影响的服务
- 手动刷新端点：`/webhook/refresh?service=xxx`

### 6. 配置刷新前校验
- 配置变更后，先进行校验再广播
- 防止配置风暴，确保系统稳定性
- 校验通过后才发布刷新事件
- 支持敏感配置加密检查

### 7. RabbitMQ Topic Exchange 选择性刷新
- 使用 RabbitMQ Topic Exchange 模式
- 支持按服务名（destination）精准推送刷新
- 格式：`{application-name}:{port}` 或 `{application-name}:*`
- 避免所有服务同时刷新，减少系统压力

### 8. 敏感配置加密存储
- 集成 JASYPT 加密框架
- 敏感配置使用 `ENC(xxx)` 格式加密存储
- 运行时自动解密后下发给客户端
- 支持数据库密码、API密钥、Token等敏感信息加密
- 加密API：`POST /api/encrypt` 进行配置加密

### 9. 灰度发布与金丝雀发布
- **按IP灰度**：指定的IP地址获取灰度配置
- **按实例灰度**：指定的服务实例获取灰度配置
- **按比例灰度**：按百分比随机分发灰度配置
- 支持规则状态管理（草稿/激活/暂停/完成）
- 灰度配置缓存，提升性能
- API端点：`/api/grayscale/*`

### 10. 配置变更审计与回滚
- 所有配置变更记录审计日志
- 支持变更类型分类（创建/更新/删除/回滚/灰度发布）
- 支持配置回滚到历史版本
- 按服务名、变更类型、时间范围查询审计日志
- 记录操作人和变更原因
- API端点：`/api/audit/*`

### 11. 配置差异对比
- 当前配置 vs 审计历史版本对比
- 两个历史审计版本之间的对比
- 当前配置 vs 提议配置的预对比
- 差异类型识别（新增/修改/删除）
- 敏感配置变更自动标记
- 差异统计信息展示
- API端点：`/api/audit/diff/*`

### 12. 多级审批流程
- 三级审批流程：LEVEL1 → LEVEL2 → LEVEL3
- 审批状态管理（待审批/审批中/已通过/已拒绝/已发布）
- 审批操作：批准/拒绝/要求修改/取消
- 审批历史记录
- 敏感配置或大量变更自动触发审批
- 审批通过后才能发布配置
- API端点：`/api/approval/*`

## 快速开始

### 前置条件

1. **安装并启动 RabbitMQ**
   ```bash
   # Docker方式启动
   docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
   ```

2. **初始化Git配置仓库**
   ```bash
   cd config-repo
   git init
   git add .
   git commit -m "Initial commit: add config files"
   git branch -M main
   ```

### 启动服务

1. **启动 Config Server**
   ```bash
   cd config-server
   mvn spring-boot:run
   ```
   服务地址：http://localhost:8888

2. **启动 Config Client**
   ```bash
   cd config-client
   mvn spring-boot:run
   ```
   服务地址：http://localhost:8080

## API端点

### Config Server 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/{application}/{profile}/{label}` | GET | 获取指定应用、环境、分支的配置 |
| `/{application}-{profile}.yml` | GET | 获取yml格式的配置 |
| `/actuator/bus-refresh` | POST | 广播刷新所有客户端配置 |
| `/actuator/health` | GET | 健康检查 |

### Config Client 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/config` | GET | 获取当前应用配置 |
| `/api/config/message` | GET | 获取配置消息 |
| `/actuator/refresh` | POST | 刷新当前客户端配置 |
| `/actuator/health` | GET | 健康检查 |

## 使用示例

### 1. 查看配置

```bash
# 查看开发环境配置
curl http://localhost:8888/config-client/dev/main

# 查看生产环境配置
curl http://localhost:8888/config-client/prod/main

# 客户端查看配置
curl http://localhost:8080/api/config
```

### 2. 手动刷新单个客户端配置

```bash
curl -X POST http://localhost:8080/actuator/refresh
```

### 3. 广播刷新所有客户端配置

```bash
curl -X POST http://localhost:8888/actuator/bus-refresh
```

### 4. 更新配置流程

1. 修改 `config-repo/config-client/config-client-dev.yml` 中的配置
2. 提交到Git仓库：
   ```bash
   cd config-repo
   git add .
   git commit -m "Update config: change message"
   ```
3. 调用广播刷新：
   ```bash
   curl -X POST http://localhost:8888/actuator/bus-refresh
   ```
4. 所有客户端自动刷新配置

### 5. 灰度发布示例

```bash
# 创建按IP灰度的规则
curl -X POST http://localhost:8888/api/grayscale/rules \
  -H "Content-Type: application/json" \
  -d '{
    "serviceName": "config-client",
    "profile": "dev",
    "label": "main",
    "type": "IP",
    "targetIps": ["192.168.1.100", "192.168.1.101"],
    "description": "灰度发布新功能到指定IP",
    "createdBy": "admin"
  }'

# 按比例灰度（30%的实例）
curl -X POST http://localhost:8888/api/grayscale/rules \
  -H "Content-Type: application/json" \
  -d '{
    "serviceName": "config-client",
    "profile": "dev",
    "label": "main",
    "type": "PERCENTAGE",
    "percentage": 30,
    "description": "30%流量灰度发布",
    "createdBy": "admin"
  }'

# 激活灰度规则
curl -X PUT http://localhost:8888/api/grayscale/rules/GR-xxx/activate

# 检查实例是否符合灰度条件
curl "http://localhost:8888/api/grayscale/check?serviceName=config-client&ip=192.168.1.100&instanceId=client-1"

# 查看灰度状态统计
curl http://localhost:8888/api/grayscale/status
```

### 6. 审计与回滚示例

```bash
# 查询服务的审计日志
curl "http://localhost:8888/api/audit/logs?serviceName=config-client"

# 查看单条审计日志详情
curl http://localhost:8888/api/audit/logs/AUD-xxx

# 查看审计变更的差异详情
curl http://localhost:8888/api/audit/diff/AUD-xxx

# 回滚到指定的审计版本
curl -X POST http://localhost:8888/api/audit/logs/AUD-xxx/rollback \
  -H "Content-Type: application/json" \
  -d '{"rollbackBy": "admin"}'

# 对比两个历史版本的差异
curl "http://localhost:8888/api/audit/diff/compare?serviceName=config-client&oldAuditId=AUD-001&newAuditId=AUD-002"

# 查看审计统计信息
curl http://localhost:8888/api/audit/stats
```

### 7. 多级审批流程示例

```bash
# 创建审批请求
curl -X POST http://localhost:8888/api/approval/requests \
  -H "Content-Type: application/json" \
  -d '{
    "serviceName": "config-client",
    "profile": "dev",
    "label": "main",
    "targetConfig": {
      "app.message": "Hello from Approved Config",
      "app.feature.enableCache": "true"
    },
    "requestedBy": "developer",
    "changeReason": "优化消息内容，启用缓存"
  }'

# 一级审批通过
curl -X PUT http://localhost:8888/api/approval/requests/APP-xxx/approve \
  -H "Content-Type: application/json" \
  -d '{
    "approver": "team-lead",
    "comment": "代码已review，同意发布",
    "level": "LEVEL1"
  }'

# 二级审批通过
curl -X PUT http://localhost:8888/api/approval/requests/APP-xxx/approve \
  -H "Content-Type: application/json" \
  -d '{
    "approver": "manager",
    "comment": "业务影响评估通过，同意发布",
    "level": "LEVEL2"
  }'

# 三级审批通过（最后一级）
curl -X PUT http://localhost:8888/api/approval/requests/APP-xxx/approve \
  -H "Content-Type: application/json" \
  -d '{
    "approver": "director",
    "comment": "整体风险可控，同意发布",
    "level": "LEVEL3"
  }'

# 发布已批准的配置
curl -X POST http://localhost:8888/api/approval/requests/APP-xxx/publish \
  -H "Content-Type: application/json" \
  -d '{"publishedBy": "admin"}'

# 拒绝审批请求
curl -X PUT http://localhost:8888/api/approval/requests/APP-xxx/reject \
  -H "Content-Type: application/json" \
  -d '{
    "approver": "manager",
    "comment": "配置有问题，请重新检查",
    "level": "LEVEL2"
  }'

# 查看审批统计
curl http://localhost:8888/api/approval/stats
```

## 配置说明

### Config Server 配置 (application.yml)

```yaml
server:
  port: 8888

spring:
  application:
    name: config-server
  cloud:
    config:
      server:
        git:
          uri: file:///${user.dir}/config-repo  # Git仓库地址
          search-paths: '{application}'           # 搜索路径
          default-label: main                      # 默认分支
          clone-on-start: true                     # 启动时克隆仓库
    bus:
      id: ${spring.application.name}:${server.port}  # 服务Bus ID
      enabled: true                                  # 启用Bus
      trace:
        enabled: true                                # 启用跟踪
  rabbitmq:
    host: localhost
    port: 5672
    username: guest
    password: guest
    virtual-host: /

# JASYPT 加密配置
jasypt:
  encryptor:
    password: ${JASYPT_ENCRYPTOR_PASSWORD:config-center-secret-key-2024}
    algorithm: PBEWithMD5AndDES
    iv-generator-classname: org.jasypt.iv.NoIvGenerator

# WebHook 配置
webhook:
  gitlab:
    secret: ${GITLAB_WEBHOOK_SECRET:}                # GitLab WebHook密钥
  github:
    secret: ${GITHUB_WEBHOOK_SECRET:}                # GitHub WebHook密钥

management:
  endpoints:
    web:
      exposure:
        include: bus-refresh, refresh, health, info, env, beans
  endpoint:
    health:
      show-details: always
```

### Config Client 配置 (bootstrap.yml)

```yaml
spring:
  application:
    name: config-client                              # 应用名称
  cloud:
    config:
      uri: http://localhost:8888                     # Config Server地址
      profile: dev                                    # 指定环境
      label: main                                     # 指定分支
    bus:
      id: ${spring.application.name}:${server.port}  # 服务Bus ID
      enabled: true                                  # 启用Bus
  rabbitmq:
    host: localhost
    port: 5672
    username: guest
    password: guest
    virtual-host: /

# JASYPT 加密配置（必须与Server一致）
jasypt:
  encryptor:
    password: ${JASYPT_ENCRYPTOR_PASSWORD:config-center-secret-key-2024}
    algorithm: PBEWithMD5AndDES
    iv-generator-classname: org.jasypt.iv.NoIvGenerator

server:
  port: 8080

management:
  endpoints:
    web:
      exposure:
        include: refresh, health, info, env, bus-refresh
  endpoint:
    health:
      show-details: always
```

### 配置仓库文件格式

```yaml
# config-client-dev.yml 示例
app:
  name: config-client
  version: 1.0.0
  environment: development
  message: Hello from Development Environment!
  feature:
    enable-cache: true
    enable-log: true
    max-connections: 100
  security:
    api-key: ENC(3z9mG+3Z1k5jR7xL9pQ==)        # 加密的API密钥
    secret-token: ENC(7xQ2z9mG+3Z1k5jR9pL==)   # 加密的Token

spring:
  datasource:
    url: jdbc:mysql://localhost:3306/dev_db
    username: dev_user
    password: ENC(4xR5z7mP+9Q2k3jL8pZ==)      # 加密的数据库密码
```

## 注意事项

1. **@RefreshScope 注解**：需要热加载的Bean必须添加此注解
2. **配置文件命名**：遵循 `{application}-{profile}.yml` 规则
3. **RabbitMQ连接**：确保RabbitMQ服务正常运行
4. **Git提交**：配置变更后必须提交到Git仓库才能被Config Server读取
5. **端口占用**：确保8888（Config Server）和8080（Config Client）端口未被占用
6. **加密密钥一致性**：Config Server和Client必须使用相同的JASYPT加密密码
7. **WebHook安全**：生产环境必须配置WebHook Secret防止非法调用
8. **选择性刷新**：建议使用按服务名选择性刷新，避免配置风暴

## 项目依赖关系

```
config-center-parent (pom)
├── config-server (jar)
│   ├── spring-cloud-config-server
│   ├── spring-cloud-starter-bus-amqp
│   └── spring-boot-starter-actuator
│
└── config-client (jar)
    ├── spring-cloud-starter-config
    ├── spring-cloud-starter-bus-amqp
    └── spring-boot-starter-actuator
```
