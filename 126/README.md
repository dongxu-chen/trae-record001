# API聚合与编排引擎 v3.0

基于 BFF 网关模式的企业级 API 聚合与编排引擎，集成 GraphQL + gRPC 微服务 + 服务发现。

## ✨ 核心功能

### 🏗️ gRPC 微服务架构
- **3 个核心微服务**：用户服务、帖子服务、评论服务
- **Protocol Buffers**：高效的二进制序列化协议
- **服务注册发现**：Consul 集成支持健康检查
- **负载均衡**：轮询、随机、优先等多种策略

### 🔄 BFF 网关 (Backend for Frontend)
- **GraphQL 到 gRPC 转换**：自动将 GraphQL 查询转为 gRPC 调用
- **DataLoader 批处理**：解决 N+1 查询问题
- **统一 API 入口**：单一 GraphQL 端点聚合多个微服务
- **字段级解析**：按需获取数据，避免过度获取

### 📊 动态编排 DSL（预集成）
- **条件分支**：if/else 支持丰富的条件运算符
- **循环支持**：foreach、while 循环
- **并行执行**：parallel 并行步骤
- **错误处理**：try/catch/finally 错误捕获
- **表达式求值**：Handlebars 风格的模板语法

### 🔍 服务发现与健康检查
- **Consul 集成**：服务自动注册与发现
- **健康检查**：TCP 连接健康检查
- **缓存机制**：服务列表本地缓存
- **动态更新**：定时刷新服务实例

## 📁 项目结构

```
├── protos/                       # Protocol Buffers 定义
│   ├── user.proto               # 用户服务协议
│   ├── post.proto               # 帖子服务协议
│   └── comment.proto            # 评论服务协议
├── src/
│   ├── bff-gateway.js           # BFF 网关入口
│   ├── bff/
│   │   ├── grpc-client-factory.js  # gRPC 客户端工厂
│   │   ├── graphql-schema.js       # GraphQL Schema 定义
│   │   └── graphql-resolvers.js    # GraphQL Resolvers
│   ├── grpc/
│   │   ├── grpc-server.js          # gRPC 服务器基类
│   │   ├── grpc-utils.js           # gRPC 工具函数
│   │   ├── mock-db.js              # 模拟数据库
│   │   └── services/
│   │       ├── user-service.js     # 用户 gRPC 服务
│   │       ├── post-service.js     # 帖子 gRPC 服务
│   │       └── comment-service.js  # 评论 gRPC 服务
│   ├── discovery/
│   │   └── consul-client.js        # Consul 服务发现客户端
│   ├── orchestration/
│   │   └── orchestrator.js         # 编排引擎（可集成）
│   └── start-grpc-services.js      # 启动所有 gRPC 服务
├── package.json
└── README.md
```

## 🚀 快速开始

### 安装依赖

```bash
npm install
```

### 启动 gRPC 微服务

```bash
# 启动所有 gRPC 服务
npm run grpc:all

# 或单独启动
npm run grpc:user     # 用户服务 (端口 50051)
npm run grpc:post     # 帖子服务 (端口 50052)
npm run grpc:comment  # 评论服务 (端口 50053)
```

### 启动 BFF 网关

```bash
# 启动网关 (端口 4000)
npm start

# 开发模式（自动重启）
npm run dev
```

### 访问 GraphQL Playground

打开浏览器访问：http://localhost:4000

## 📋 gRPC 服务接口

### 用户服务 (UserService - 50051)

```protobuf
service UserService {
  rpc GetUser(GetUserRequest) returns (User);
  rpc GetUsers(GetUsersRequest) returns (GetUsersResponse);
  rpc ListUsers(ListUsersRequest) returns (ListUsersResponse);
  rpc CreateUser(CreateUserRequest) returns (User);
  rpc UpdateUser(UpdateUserRequest) returns (User);
  rpc DeleteUser(DeleteUserRequest) returns (DeleteUserResponse);
}
```

### 帖子服务 (PostService - 50052)

```protobuf
service PostService {
  rpc GetPost(GetPostRequest) returns (Post);
  rpc GetPosts(GetPostsRequest) returns (GetPostsResponse);
  rpc GetPostsByAuthor(GetPostsByAuthorRequest) returns (GetPostsResponse);
  rpc ListPosts(ListPostsRequest) returns (ListPostsResponse);
  rpc CreatePost(CreatePostRequest) returns (Post);
  rpc UpdatePost(UpdatePostRequest) returns (Post);
  rpc DeletePost(DeletePostRequest) returns (DeletePostResponse);
}
```

### 评论服务 (CommentService - 50053)

```protobuf
service CommentService {
  rpc GetComment(GetCommentRequest) returns (Comment);
  rpc GetComments(GetCommentsRequest) returns (GetCommentsResponse);
  rpc GetCommentsByPost(GetCommentsByPostRequest) returns (GetCommentsResponse);
  rpc ListComments(ListCommentsRequest) returns (ListCommentsResponse);
  rpc CreateComment(CreateCommentRequest) returns (Comment);
  rpc UpdateComment(UpdateCommentRequest) returns (Comment);
  rpc DeleteComment(DeleteCommentRequest) returns (DeleteCommentResponse);
}
```

## 🎮 GraphQL 查询示例

### 查询单个用户及其帖子

```graphql
query GetUserWithPosts {
  getUser(id: "1") {
    id
    name
    email
    posts {
      id
      title
      commentCount
    }
  }
}
```

### 查询帖子及其作者和评论

```graphql
query GetPostWithDetails {
  getPost(id: "1") {
    id
    title
    content
    author {
      id
      name
    }
    comments {
      id
      content
      author {
        name
      }
    }
  }
}
```

### 创建新用户

```graphql
mutation CreateUser {
  createUser(name: "张三", email: "zhang@example.com", role: "user") {
    id
    name
    email
  }
}
```

### 创建帖子

```graphql
mutation CreatePost {
  createPost(
    title: "GraphQL + gRPC 最佳实践"
    content: "使用 BFF 网关模式..."
    authorId: "1"
  ) {
    id
    title
  }
}
```

## 🔧 配置说明

### gRPC 服务地址配置

```javascript
// 默认配置
const defaultServiceAddresses = {
  user: 'localhost:50051',
  post: 'localhost:50052',
  comment: 'localhost:50053',
};

// 自定义配置
const gateway = new BffGateway({
  port: 4000,
  grpcAddresses: {
    user: '192.168.1.100:50051',
    post: '192.168.1.101:50052',
    comment: '192.168.1.102:50053',
  },
});
```

### Consul 服务发现配置

```javascript
// 启用 Consul 服务发现
const consul = new ConsulClient({
  host: 'localhost',
  port: 8500,
  refreshInterval: 30000,  // 30秒刷新缓存
});

// 获取服务地址
const address = await consul.getServiceAddress('user-service', 'round-robin');

// 支持的负载均衡策略
// - 'round-robin': 轮询（默认）
// - 'random': 随机
// - 'first': 第一个健康实例
```

### 服务健康检查

```javascript
// 检查 Consul 连接
const isHealthy = await consul.healthCheck();

// 发现服务实例
const instances = await consul.discoverService('user-service');
console.log('健康实例数:', instances.length);

// 清除服务缓存
consul.clearCache();
```

## 💡 架构设计

### BFF 网关模式优势

1. **前端友好**：统一的 GraphQL API，按需获取数据
2. **性能优化**：gRPC 二进制协议，高并发低延迟
3. **服务聚合**：多个微服务数据在网关层聚合
4. **边界隔离**：前端不直接访问后端微服务

### DataLoader 批处理机制

```javascript
// 同一查询中的多个用户 ID 会被批处理
userLoader.loadMany(["1", "2", "3"]);
// → 单次 gRPC 调用 GetUsers(["1", "2", "3"])
```

### 服务发现流程

```
1. 服务启动 → 2. 注册到 Consul → 3. 健康检查
   ↓
BFF 网关 → 4. 查询 Consul → 5. 获取健康实例 → 6. gRPC 调用
   ↓
7. 定时刷新服务列表（30秒）→ 返回步骤 4
```

## 🔌 编排引擎集成

BFF 网关支持动态编排引擎集成：

```javascript
import Orchestrator from './orchestration/orchestrator.js';

const orchestrator = new Orchestrator();

const gateway = new BffGateway({
  orchestrator,
});

// 在 GraphQL 中执行工作流
query {
  executeWorkflow(name: "myWorkflow", variables: { foo: "bar" }) {
    success
    data
    executionTime
  }
}
```

## 📊 性能优化建议

1. **启用 DataLoader 批处理**：默认已启用，可减少 N+1 查询
2. **配置适当的服务缓存**：Consul 刷新间隔建议 30-60 秒
3. **gRPC 连接池**：复用连接减少握手开销
4. **查询复杂度控制**：避免过深的嵌套查询
5. **水平扩展**：网关和微服务支持水平扩展

## 🧪 测试验证

### 启动完整环境

```bash
# 1. 启动 Consul（可选，用于服务发现）
consul agent -dev

# 2. 启动所有 gRPC 服务
npm run grpc:all

# 3. 启动 BFF 网关
npm start
```

### 验证 gRPC 服务

检查服务是否正常监听：

```bash
netstat -an | findstr "50051 50052 50053"
```

### 验证 GraphQL 端点

打开 http://localhost:4000 并执行测试查询：

```graphql
query HealthCheck {
  getUser(id: "1") {
    id
    name
  }
}
```

## 📄 License

MIT
