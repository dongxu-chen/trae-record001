# 文档协作审核系统

基于 Operational Transformation + React + Node.js + MongoDB 实现的多人实时协作文档审核系统。

## 功能特性

### 核心功能
- ✅ **实时协作编辑** - 多人同时编辑同一文档，支持 Operational Transformation (OT) 算法
- ✅ **修订痕迹** - 完整记录所有增删改操作，支持查看修订历史
- ✅ **审核工作流** - 编辑者提交审核，审核人通过/拒绝修订
- ✅ **版本对比** - 可视化展示不同版本之间的差异
- ✅ **批注评论** - 支持对文档内容添加批注和回复讨论
- ✅ **实时协作** - WebSocket 实时同步，显示在线用户和光标位置

### 技术架构

**后端 (Node.js):**
- Express.js - RESTful API 服务器
- MongoDB + Mongoose - 数据存储
- Socket.io - 实时通信
- ShareDB - Operational Transformation 支持
- JWT - 身份认证
- bcryptjs - 密码加密
- diff - 文本差异计算

**前端 (React):**
- React 18 + React Router - UI 框架和路由
- Material-UI (MUI) - UI 组件库
- Zustand - 状态管理
- Axios - HTTP 客户端
- Socket.io-client - WebSocket 客户端

## 项目结构

```
doc-collab-system/
├── server/                          # 后端服务
│   ├── server.js                    # 服务器入口
│   ├── package.json
│   ├── .env
│   ├── models/                      # 数据模型
│   │   ├── User.js
│   │   ├── Document.js
│   │   ├── Revision.js
│   │   └── Comment.js
│   ├── routes/                      # API 路由
│   │   ├── auth.js
│   │   ├── documents.js
│   │   ├── reviews.js
│   │   └── comments.js
│   ├── controllers/                 # 控制器
│   │   └── otController.js
│   ├── middleware/                  # 中间件
│   │   └── auth.js
│   └── ot/                          # OT 引擎
│       └── otEngine.js
└── client/                          # 前端应用
    ├── package.json
    ├── public/
    │   └── index.html
    └── src/
        ├── index.js
        ├── App.jsx
        ├── context/                 # React Context
        │   └── AuthContext.jsx
        ├── services/                # 服务层
        │   ├── api.js
        │   └── socket.js
        ├── store/                   # 状态管理
        │   └── useStore.js
        ├── components/              # 通用组件
        │   └── Navbar.jsx
        └── pages/                   # 页面组件
            ├── Login.jsx
            ├── Register.jsx
            ├── Dashboard.jsx
            ├── DocumentEditor.jsx
            └── ReviewQueue.jsx
```

## 快速开始

### 环境要求
- Node.js >= 16.0.0
- MongoDB >= 4.0
- npm 或 yarn

### 安装和运行

#### 1. 启动 MongoDB

确保 MongoDB 服务已启动，默认连接地址: `mongodb://localhost:27017`

#### 2. 安装后端依赖

```bash
cd server
npm install
```

#### 3. 启动后端服务

```bash
npm run dev
```

后端服务将在 `http://localhost:5000` 启动

#### 4. 安装前端依赖

```bash
cd ../client
npm install
```

#### 5. 启动前端应用

```bash
npm start
```

前端应用将在 `http://localhost:3000` 启动

## API 接口

### 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 用户注册 |
| POST | /api/auth/login | 用户登录 |
| GET | /api/auth/me | 获取当前用户信息 |
| GET | /api/auth/users | 获取所有用户列表 |

### 文档接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/documents | 创建新文档 |
| GET | /api/documents | 获取我的文档列表 |
| GET | /api/documents/:docId | 获取文档详情 |
| PUT | /api/documents/:docId | 更新文档 |
| DELETE | /api/documents/:docId | 删除文档 |
| GET | /api/documents/:docId/revisions | 获取文档修订历史 |
| POST | /api/documents/:docId/submit-review | 提交文档审核 |

### 审核接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/reviews/:revisionId/approve | 通过修订 |
| POST | /api/reviews/:revisionId/reject | 拒绝修订 |
| GET | /api/reviews/pending | 获取待审核列表 |
| POST | /api/reviews/document/:docId/final-approve | 最终通过文档 |
| POST | /api/reviews/document/:docId/final-reject | 最终拒绝文档 |

### 批注接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/comments | 添加批注 |
| GET | /api/comments/document/:docId | 获取文档批注列表 |
| POST | /api/comments/:commentId/reply | 回复批注 |
| POST | /api/comments/:commentId/resolve | 标记批注已解决 |
| DELETE | /api/comments/:commentId | 删除批注 |

## 使用说明

### 1. 用户角色

- **编辑者 (editor)**: 可以创建、编辑文档，提交审核
- **审核人 (reviewer)**: 可以审核文档，通过/拒绝修订，最终审批文档
- **管理员 (admin)**: 拥有所有权限

### 2. 工作流程

1. **编辑者** 创建文档并编辑内容
2. **编辑者** 提交文档审核，指定审核人
3. **审核人** 收到待审核通知
4. **审核人** 查看修订历史和差异
5. **审核人** 逐条通过/拒绝修订
6. **审核人** 最终审批文档（通过/拒绝）

### 3. 实时协作

- 多个用户可以同时打开同一文档
- 编辑内容会实时同步给所有在线用户
- 可以看到其他在线用户列表
- 支持查看每个修订的详细差异

## 数据模型

### User (用户)
```javascript
{
  username: String,      // 用户名
  email: String,         // 邮箱
  password: String,      // 加密后的密码
  role: String,          // 角色: editor/reviewer/admin
  avatar: String         // 头像
}
```

### Document (文档)
```javascript
{
  title: String,         // 文档标题
  content: String,       // 文档内容
  docId: String,         // 唯一文档ID
  author: ObjectId,      // 作者ID
  collaborators: [ObjectId],  // 协作者列表
  reviewers: [ObjectId],      // 审核人列表
  status: String,        // 状态: draft/in_review/approved/rejected
  version: Number        // 当前版本号
}
```

### Revision (修订)
```javascript
{
  document: ObjectId,    // 关联文档ID
  author: ObjectId,      // 提交者ID
  version: Number,       // 版本号
  operations: Array,     // OT 操作数组
  diff: String,          // 差异数据 (JSON字符串)
  contentBefore: String, // 修订前内容
  contentAfter: String,  // 修订后内容
  status: String,        // 状态: pending/approved/rejected/applied
  reviewedBy: ObjectId,  // 审核人ID
  reviewedAt: Date,      // 审核时间
  reviewComment: String  // 审核意见
}
```

### Comment (批注)
```javascript
{
  document: ObjectId,    // 关联文档ID
  author: ObjectId,      // 批注者ID
  revision: ObjectId,    // 关联修订ID (可选)
  content: String,       // 批注内容
  startPos: Number,      // 起始位置
  endPos: Number,        // 结束位置
  selectedText: String,  // 选中的文本
  resolved: Boolean,     // 是否已解决
  replies: Array         // 回复列表
}
```

## 开发说明

### Operational Transformation (OT)

系统使用 OT 算法解决多人协作编辑的冲突问题：

1. 每个操作都包含版本号
2. 服务器根据版本号判断是否需要转换操作
3. 使用 `ot-json0` 类型支持文本编辑操作
4. 操作通过 WebSocket 实时广播给所有协作者

### 实时同步流程

```
客户端编辑 → 生成OT操作 → WebSocket发送 → 服务器应用 → 广播给其他客户端
```

## 注意事项

1. **WebSocket 连接**: 确保端口 5000 可以正常访问
2. **CORS 配置**: 前端默认连接 `http://localhost:5000`，如需修改请调整代理配置
3. **数据持久化**: 文档内容和修订历史都存储在 MongoDB 中
4. **生产部署**: 部署时请修改 `.env` 中的 JWT_SECRET 和其他敏感配置

## 扩展建议

- [ ] 集成更丰富的富文本编辑器 (Quill/ProseMirror)
- [ ] 添加文档导出功能 (PDF/Word)
- [ ] 实现离线编辑支持
- [ ] 添加邮件通知功能
- [ ] 实现更细粒度的权限控制
- [ ] 添加操作日志和审计功能
- [ ] 支持文档模板
