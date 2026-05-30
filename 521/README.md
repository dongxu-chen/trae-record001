# TaskFlow - 分布式任务流平台

一个基于 Airflow 风格的分布式任务流调度平台，支持 DAG 工作流编排、任务重试、超时控制、并行执行。

## 技术栈

### 后端
- **Java 17** + **Spring Boot 3.2**
- **MySQL 8.0** - 数据存储
- **JPA/Hibernate** - ORM框架
- **线程池 + 任务队列** - 任务调度和并行执行

### 前端
- **React 18** + **Vite**
- **React Flow** - DAG 可视化编排
- **Ant Design 5** - UI组件库
- **React Router** - 路由管理

## 核心功能

### 1. DAG工作流编排
- 可视化拖拽式工作流设计
- 支持多种任务类型：Shell、Python、HTTP、数据同步、邮件通知
- 任务依赖关系可视化配置
- 工作流版本管理

### 2. 任务执行引擎
- **并行执行** - 基于拓扑排序的并行任务调度
- **任务重试** - 可配置重试次数和间隔
- **超时控制** - 每个任务可独立设置超时时间
- **任务队列** - 基于内存队列的任务分发

### 3. 执行监控
- 实时DAG执行状态展示
- 任务执行日志查看
- 执行历史记录
- 失败任务重试支持

### 4. 触发策略
- **定时触发** (Cron) - 支持标准Cron表达式
- **事件触发** - 基于Topic的事件驱动
- **手动触发** - 页面手动触发执行

## 项目结构

```
taskflow/
├── backend/                 # Java后端项目
│   ├── src/main/java/com/taskflow/
│   │   ├── controller/      # REST API控制器
│   │   ├── service/         # 业务逻辑层
│   │   ├── model/           # 数据模型
│   │   ├── repository/      # 数据访问层
│   │   ├── engine/          # DAG执行引擎
│   │   ├── config/          # 配置类
│   │   └── dto/             # 数据传输对象
│   └── src/main/resources/
│       ├── schema.sql       # 数据库初始化脚本
│       └── application.yml  # 应用配置
├── frontend/                # React前端项目
│   ├── src/
│   │   ├── pages/           # 页面组件
│   │   ├── components/      # 公共组件
│   │   ├── api/             # API调用
│   │   └── types/           # 类型定义
│   ├── Dockerfile
│   └── nginx.conf
└── docker-compose.yml       # Docker部署配置
```

## 快速开始

### 方式一：Docker Compose 部署（推荐）

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 访问前端: http://localhost:3000
# 访问后端API: http://localhost:8080
```

### 方式二：本地开发

#### 前置要求
- JDK 17+
- Maven 3.8+
- Node.js 18+
- MySQL 8.0+

#### 启动后端

```bash
cd backend

# 配置数据库连接 (application.yml)
# 修改 spring.datasource.url/username/password

# 构建并运行
mvn spring-boot:run
```

#### 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问: http://localhost:3000
```

## 数据库设计

| 表名 | 说明 |
|------|------|
| tf_workflow | 工作流定义表 |
| tf_task | 任务定义表 |
| tf_workflow_execution | 工作流执行记录表 |
| tf_task_execution | 任务执行记录表 |
| tf_trigger | 触发器配置表 |

## API 接口

### 工作流管理
- `GET /api/workflows` - 获取工作流列表
- `GET /api/workflows/:id` - 获取工作流详情
- `POST /api/workflows` - 创建工作流
- `PUT /api/workflows/:id` - 更新工作流
- `DELETE /api/workflows/:id` - 删除工作流
- `POST /api/workflows/:id/publish` - 发布工作流

### 执行管理
- `GET /api/executions` - 获取执行列表
- `GET /api/executions/:executionId` - 获取执行详情
- `POST /api/executions/trigger/:workflowId` - 触发执行
- `POST /api/executions/:executionId/retry` - 重试执行
- `POST /api/executions/:executionId/cancel` - 取消执行

### 触发策略
- `GET /api/triggers` - 获取触发器列表
- `POST /api/triggers` - 创建触发器
- `PUT /api/triggers/:id` - 更新触发器
- `DELETE /api/triggers/:id` - 删除触发器
- `POST /api/triggers/:id/toggle` - 开关触发器
- `POST /api/triggers/event/:topic` - 触发事件

## 使用指南

### 1. 创建工作流
1. 进入「工作流管理」页面
2. 点击「新建工作流」
3. 从左侧拖拽任务节点到画布
4. 连接节点建立依赖关系
5. 双击节点配置任务参数（重试、超时等）
6. 保存并发布工作流

### 2. 配置触发器
1. 进入「触发策略」页面
2. 点击「新建触发策略」
3. 选择关联的工作流（需已发布）
4. 配置触发类型（定时/事件）
5. 保存并启用触发器

### 3. 查看执行
1. 进入「执行监控」页面
2. 查看所有执行记录
3. 点击「详情」查看DAG执行状态和任务日志

## 核心架构

### DAG执行流程

```
用户触发
    ↓
任务队列 (TaskQueue)
    ↓
队列消费者 (QueueConsumer)
    ↓
DAG执行器 (DagExecutor)
    ├─ 拓扑排序确定执行顺序
    ├─ 线程池并行执行无依赖任务
    ├─ 每个任务支持: 超时控制 + 重试机制
    └─ 下游任务等待上游完成后执行
```

### 任务状态流转

```
PENDING (等待中)
    ↓
RUNNING (运行中)
    ├─ 成功 → SUCCESS
    └─ 失败 → 可重试?
              ├─ 是 → 等待 → RUNNING
              └─ 否 → FAILED
```

## 开发计划

- [ ] 支持分布式工作节点
- [ ] 任务插件系统（自定义任务类型）
- [ ] WebSocket实时推送执行状态
- [ ] 工作流变量和参数传递
- [ ] 告警通知（邮件/钉钉/企业微信）
- [ ] 执行统计报表和图表
- [ ] 权限管理和多租户

## License

MIT License
