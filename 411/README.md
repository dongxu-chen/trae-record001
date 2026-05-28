# 配置热更新中心

基于 Spring Cloud Config + Bus + RabbitMQ + Git + Eureka 实现的配置热更新中心，支持动态刷新应用配置，无需重启应用。

## 功能特性

- ✅ **配置动态刷新** - 通过消息总线实现配置实时推送
- ✅ **版本管理** - 完整的配置版本历史，支持版本对比
- ✅ **灰度发布** - 支持IP白名单/百分比灰度策略
- ✅ **变更审计** - 记录所有配置变更操作，支持多维度查询
- ✅ **配置回滚** - 一键回滚到任意历史版本
- ✅ **Git集成** - 配置持久化到Git仓库

## 项目结构

```
config-hot-update-center/
├── eureka-server/       # 服务注册中心 (端口: 8761)
├── config-server/       # 配置中心服务端 (端口: 8888)
│   ├── entity/          # 实体类
│   ├── repository/      # 数据访问层
│   ├── service/         # 业务逻辑层
│   └── controller/      # REST API控制器
├── config-client/       # 配置客户端示例 (端口: 8080)
├── config-admin/        # 配置管理后台 (端口: 8081)
└── config-repo/         # 本地Git配置仓库
    └── master/
        ├── config-client.yml
        └── config-client-dev.yml
```

## 技术栈

- Spring Boot 2.7.18
- Spring Cloud 2021.0.8
- Spring Cloud Config Server/Client
- Spring Cloud Bus + RabbitMQ
- Spring Cloud Netflix Eureka
- Git (JGit)
- H2 Database (用于审计日志和版本管理)
- Thymeleaf (管理后台)

## 环境要求

- JDK 11+
- Maven 3.6+
- RabbitMQ 3.8+
- Git

## 快速开始

### 1. 启动RabbitMQ

使用Docker快速启动RabbitMQ：

```bash
docker run -d \
  --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:3-management
```

管理界面: http://localhost:15672 (guest/guest)

### 2. 配置Git仓库

创建Git仓库用于存储配置：

```bash
cd config-repo
git init
git add .
git commit -m "初始化配置仓库"
```

修改 `config-server/src/main/resources/application.yml` 中的Git仓库地址：

```yaml
spring:
  cloud:
    config:
      server:
        git:
          uri: file:///${user.dir}/config-repo
```

### 3. 编译项目

```bash
mvn clean package -DskipTests
```

### 4. 启动服务

按顺序启动以下服务：

```bash
# 1. 启动Eureka注册中心
cd eureka-server
mvn spring-boot:run

# 2. 启动配置中心
cd config-server
mvn spring-boot:run

# 3. 启动客户端示例 (可选)
cd config-client
mvn spring-boot:run

# 4. 启动管理后台 (可选)
cd config-admin
mvn spring-boot:run
```

### 5. 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| Eureka | http://localhost:8761 | 服务注册中心 |
| Config Server | http://localhost:8888 | 配置中心 |
| Config Client | http://localhost:8080 | 示例客户端 |
| Admin Dashboard | http://localhost:8081 | 管理后台 |
| H2 Console | http://localhost:8888/h2-console | 数据库控制台 |

## API文档

### 配置版本管理

#### 创建版本
```http
POST /api/config/versions
Content-Type: application/json

{
  "application": "config-client",
  "profile": "default",
  "label": "master",
  "configContent": "app:\n  feature:\n    enabled: true\n  threshold:\n    max-requests: 200",
  "changeSummary": "更新阈值配置",
  "operator": "admin"
}
```

#### 发布版本
```http
POST /api/config/versions/{id}/publish?operator=admin
```

#### 回滚版本
```http
POST /api/config/versions/{id}/rollback?operator=admin
```

#### 查询版本历史
```http
GET /api/config/versions/history?application=config-client&profile=default&label=master
```

#### 查询已发布版本
```http
GET /api/config/versions/published?application=config-client&profile=default&label=master
```

### 灰度发布

#### 创建灰度发布
```http
POST /api/config/gray
Content-Type: application/json

{
  "application": "config-client",
  "profile": "default",
  "label": "master",
  "configContent": "app:\n  feature:\n    enabled: true",
  "strategy": "IP_LIST",
  "grayIps": "192.168.1.100,192.168.1.101",
  "createdBy": "admin"
}
```

#### 审批灰度发布
```http
POST /api/config/gray/{id}/approve?approvedBy=admin
```

#### 全量发布
```http
POST /api/config/gray/{id}/full-release?operator=admin
```

#### 回滚灰度发布
```http
POST /api/config/gray/{id}/rollback?operator=admin
```

### 审计日志

#### 查询审计日志
```http
GET /api/config/audit?application=config-client
GET /api/config/audit/operator/admin
GET /api/config/audit/action/PUBLISH
```

### Bus消息总线

#### 刷新指定应用配置
```http
POST /api/config/bus/refresh/config-client
```

#### 刷新所有应用配置
```http
POST /api/config/bus/refresh-all
```

## 配置示例

### 数据库连接配置
```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/mydb
    username: admin
    password: secret
    driver-class-name: com.mysql.cj.jdbc.Driver
```

### 开关配置
```yaml
app:
  feature:
    enabled: true
    dark-mode: false
    new-ui: true
```

### 阈值配置
```yaml
app:
  threshold:
    max-requests: 1000
    timeout-ms: 5000
    retry-count: 3
    rate-limit: 100
```

## 工作原理

### 配置刷新流程
1. 管理员通过API或管理后台更新配置
2. 配置中心将配置提交到Git仓库
3. 配置中心通过Spring Cloud Bus发送刷新消息
4. RabbitMQ将消息广播到所有客户端
5. 客户端收到消息后重新拉取配置
6. @RefreshScope注解的Bean自动刷新

### 灰度发布流程
1. 创建灰度发布记录
2. 审批人审批通过
3. 灰度配置生效（仅对符合条件的请求）
4. 验证无误后全量发布
5. 如有问题可随时回滚

## 注意事项

- 生产环境建议使用持久化数据库替代H2
- Git仓库需要有正确的读写权限
- RabbitMQ需要配置适当的用户名密码
- 配置内容变更后记得触发Bus刷新

## License

MIT License
