# Schema Registry Manager

一个完整的Schema注册中心管理工具，支持管理Avro、Protobuf、JSON Schema的版本和兼容性检查。

## 功能特性

### 核心功能
- **多格式支持**: Avro、Protobuf、JSON Schema
- **版本管理**: Schema版本控制和历史追踪
- **兼容性检查**: 支持向前、向后、完全兼容性检查
- **Schema对比**: 可视化对比不同版本的差异
- **演进推荐**: 智能分析Schema变更并提供演进建议

### 兼容性级别
- `NONE`: 无兼容性检查
- `FORWARD`: 向前兼容（新数据可被旧消费者读取）
- `BACKWARD`: 向后兼容（旧数据可被新消费者读取）
- `FULL`: 完全兼容（向前+向后）
- `*_TRANSITIVE`: 传递性兼容检查

## 技术栈

### 后端
- Java 17
- Spring Boot 3.2
- Apache Avro
- Google Protocol Buffers
- Everit JSON Schema
- H2 Database (内存数据库)

### 前端
- React 18
- Material-UI (MUI)
- React Router
- Axios

## 项目结构

```
schema-registry-manager/
├── backend/                 # Java后端项目
│   ├── src/
│   │   └── main/
│   │       ├── java/com/schemaregistry/
│   │       │   ├── compatibility/     # 兼容性检查引擎
│   │       │   ├── controller/        # REST API控制器
│   │       │   ├── dto/               # 数据传输对象
│   │       │   ├── model/             # 实体模型
│   │       │   ├── repository/        # 数据访问层
│   │       │   ├── service/           # 业务逻辑层
│   │       │   └── config/            # 配置类
│   │       └── resources/
│   │           └── application.properties
│   └── pom.xml
│
└── frontend/                # React前端项目
    ├── src/
    │   ├── components/      # React组件
    │   └── services/        # API服务
    └── package.json
```

## 快速开始

### 后端启动

```bash
cd backend
mvn clean install
mvn spring-boot:run
```

后端服务将在 `http://localhost:8080` 启动

### 前端启动

```bash
cd frontend
npm install
npm start
```

前端应用将在 `http://localhost:3000` 启动

## API文档

### Schema管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/schemas` | 获取所有Schema列表 |
| GET | `/api/schemas/{subject}` | 获取指定Schema详情 |
| POST | `/api/schemas` | 创建新Schema |
| DELETE | `/api/schemas/{subject}` | 删除Schema |
| PUT | `/api/schemas/{subject}/compatibility` | 更新兼容性级别 |

### 版本管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/schemas/{subject}/versions` | 获取所有版本 |
| GET | `/api/schemas/{subject}/versions/{version}` | 获取指定版本 |
| POST | `/api/schemas/{subject}/versions` | 添加新版本 |

### 兼容性检查

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/schemas/compatibility/check` | 检查Schema兼容性 |

### Schema对比

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/schemas/{subject}/diff` | 对比两个版本差异 |
| POST | `/api/schemas/diff` | 直接对比两个Schema |

### 演进推荐

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/schemas/evolution/recommendation` | 获取演进建议 |

## 使用示例

### 1. 创建Avro Schema

```bash
curl -X POST http://localhost:8080/api/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-events",
    "type": "AVRO",
    "schema": "{\"type\":\"record\",\"name\":\"User\",\"fields\":[{\"name\":\"id\",\"type\":\"string\"},{\"name\":\"name\",\"type\":\"string\"}]}",
    "compatibilityLevel": "BACKWARD"
  }'
```

### 2. 检查兼容性

```bash
curl -X POST http://localhost:8080/api/schemas/compatibility/check \
  -H "Content-Type: application/json" \
  -d '{
    "type": "AVRO",
    "level": "BACKWARD",
    "oldSchema": "{...}",
    "newSchema": "{...}"
  }'
```

### 3. 获取演进推荐

```bash
curl -X POST http://localhost:8080/api/schemas/evolution/recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "type": "AVRO",
    "oldSchema": "{...}",
    "newSchema": "{...}"
  }'
```

## 前端功能模块

### 1. Schema列表页面
- 查看所有注册的Schema
- 创建新Schema
- 删除Schema
- 快速查看类型和兼容性级别

### 2. Schema详情页面
- 查看Schema基本信息
- 管理兼容性级别
- 查看版本历史
- 添加新版本
- 版本间对比跳转

### 3. 兼容性检查页面
- 选择Schema类型和兼容性级别
- 输入新旧Schema进行对比
- 查看详细的错误和警告信息

### 4. Schema对比页面
- 可视化展示字段添加、删除、修改
- 支持直接输入Schema对比
- 支持从版本历史跳转对比

### 5. 演进推荐页面
- 智能分析变更影响级别
- 提供分步操作建议
- 推荐合适的兼容性级别
- 显示警告和注意事项

## 兼容性检查规则

### Avro
- 向后兼容: 新Schema能读取旧数据
  - 可以添加带默认值的字段
  - 可以删除字段
  - 不能移除必填字段
- 向前兼容: 旧Schema能读取新数据
  - 可以删除字段
  - 添加字段需要默认值

### Protobuf
- 永远不要重用field number
- 新增字段应该使用optional
- 删除字段会破坏兼容性

### JSON Schema
- 必填字段变更会影响兼容性
- 字段类型变更需要谨慎
- 新增可选字段通常是安全的

## 开发说明

### 添加新的Schema类型支持

1. 实现 `CompatibilityChecker` 接口
2. 在 `SchemaType` 枚举中添加新类型
3. 更新前端的类型选择器

### 自定义兼容性规则

在 `compatibility` 包下扩展现有检查器或创建新的检查器实现。

## License

MIT License
