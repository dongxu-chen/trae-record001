# API配额管理平台

一个基于Java + Redis + 令牌桶算法的API配额管理平台，支持多租户、多粒度限流、配额转移、预消耗和预警功能。

## 功能特性

### 核心功能
- ✅ **多租户管理** - 为不同租户设置独立的API调用配额
- ✅ **多粒度限流** - 支持分钟/小时/天三种粒度的配额限制
- ✅ **令牌桶算法** - 基于令牌桶实现平滑限流
- ✅ **超额处理策略** - 支持拒绝、降级、排队三种策略
- ✅ **配额预消耗** - 支持预消耗配额用于批量操作
- ✅ **配额转移** - 租户之间可以转移配额
- ✅ **配额预警** - 使用率超过阈值时自动触发预警

### 技术栈
#### 后端
- Java 11
- Spring Boot 2.7.x
- Redis + Lettuce
- Lombok

#### 前端
- React 18
- Vite
- Ant Design 5
- ECharts
- React Router

## 项目结构

```
.
├── backend/                 # Java后端项目
│   ├── src/
│   │   └── main/
│   │       ├── java/com/quota/management/
│   │       │   ├── algorithm/      # 令牌桶算法
│   │       │   ├── common/         # 通用类
│   │       │   ├── config/         # 配置类
│   │       │   ├── controller/     # API控制器
│   │       │   ├── entity/         # 实体类
│   │       │   └── service/        # 业务服务
│   │       └── resources/
│   │           └── application.yml # 配置文件
│   └── pom.xml
└── frontend/                # React前端项目
    ├── src/
    │   ├── pages/           # 页面组件
    │   ├── services/        # API服务
    │   ├── App.jsx
    │   └── main.jsx
    ├── index.html
    ├── package.json
    └── vite.config.js
```

## 快速开始

### 环境要求
- JDK 11+
- Node.js 16+
- Redis 5+

### 启动后端

1. 确保Redis服务已启动（默认端口6379）

2. 进入后端目录并启动：
```bash
cd backend
mvn spring-boot:run
```

后端服务将在 http://localhost:8080/api 启动

### 启动前端

1. 进入前端目录安装依赖：
```bash
cd frontend
npm install
```

2. 启动开发服务器：
```bash
npm run dev
```

前端服务将在 http://localhost:3000 启动

## API接口

### 租户管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/tenant | 创建租户配额 |
| GET | /api/tenant/{tenantId} | 获取租户配额 |
| PUT | /api/tenant | 更新租户配额 |
| DELETE | /api/tenant/{tenantId} | 删除租户配额 |
| GET | /api/tenant/list | 获取所有租户 |
| GET | /api/tenant/{tenantId}/usage | 获取配额使用情况 |

### 配额操作

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/tenant/transfer | 配额转移 |
| POST | /api/tenant/preconsume | 预消耗配额 |
| POST | /api/tenant/release | 释放预消耗配额 |

### 限流检查

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/ratelimit/check | 检查并消耗配额 |

## 使用示例

### 创建租户

```bash
curl -X POST http://localhost:8080/api/tenant \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "tenant001",
    "tenantName": "测试租户",
    "minuteLimit": 100,
    "hourLimit": 1000,
    "dayLimit": 10000,
    "overLimitStrategy": "REJECT",
    "warningThreshold": 0.8,
    "enabled": true
  }'
```

### 限流检查

```bash
curl -X POST http://localhost:8080/api/ratelimit/check \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "tenant001",
    "tokens": 1
  }'
```

## 前端功能页面

1. **仪表盘** - 概览租户状态、配额使用统计
2. **租户管理** - 租户CRUD、配额转移
3. **配额配置** - 配额预消耗/释放、限流测试
4. **监控中心** - 实时监控配额使用率、租户状态分布

## 核心实现说明

### 令牌桶算法
- 每个租户每个粒度维护独立的令牌桶
- 令牌按时间平滑补充
- Redis存储保证分布式环境一致性

### 多粒度限流
- 依次检查分钟、小时、日配额
- 任一粒度超限则触发限流策略
- 失败回滚已消耗的令牌

### 配额预警
- 定时检查所有租户配额使用率
- 超过阈值触发预警（日志/邮件）
- 5分钟内同一租户不重复预警

### 超额处理策略
- **REJECT**：直接拒绝请求
- **DOWNGRADE**：延迟处理后放行
- **QUEUE**：返回需要排队标识
