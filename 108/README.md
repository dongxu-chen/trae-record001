# 实时协作文档编辑器

基于 Node.js + Express + Socket.io + React + ShareDB 构建的实时协作文档编辑器。

## 技术栈

- **后端**: Node.js + Express + Socket.io + ShareDB
- **前端**: React + Quill (富文本编辑器)
- **核心算法**: ShareDB 的 Operational Transformation (OT) 算法

## 功能特性

1. ✅ **富文本编辑器** - 基于 Quill，支持格式化、列表、链接、图片等
2. ✅ **多人实时编辑** - 使用 ShareDB 的 OT 算法实现并发编辑
3. ✅ **光标位置实时显示** - 实时显示其他用户的光标位置和用户名
4. ✅ **文档版本管理** - 保存历史版本，可随时回滚到任意版本
5. ✅ **用户加入/离开通知** - 实时显示用户进出文档的通知

## 项目结构

```
.
├── server/                 # 后端服务
│   ├── package.json
│   └── server.js          # 主服务器文件
├── client/                 # 前端应用
│   ├── package.json
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── index.js
│       ├── index.css
│       └── App.js
└── README.md
```

## 安装与运行

### 1. 安装后端依赖

```bash
cd server
npm install
```

### 2. 启动后端服务

```bash
npm start
# 或使用开发模式 (nodemon)
npm run dev
```

后端服务将运行在 `http://localhost:3001`

### 3. 安装前端依赖

打开新的终端窗口：

```bash
cd client
npm install
```

### 4. 启动前端应用

```bash
npm start
```

前端应用将运行在 `http://localhost:3000`

## 使用说明

1. 打开浏览器访问 `http://localhost:3000`
2. 输入您的用户名和文档ID（多人协作时请使用相同的文档ID）
3. 点击"加入文档"开始编辑
4. 打开多个浏览器窗口或邀请他人加入同一文档ID，体验实时协作

### 多人协作测试

1. 在浏览器A中打开 `http://localhost:3000`，输入用户名"用户A"，文档ID"test-doc"
2. 在浏览器B中打开 `http://localhost:3000`，输入用户名"用户B"，文档ID"test-doc"
3. 两个用户可以同时编辑，光标位置会实时同步，编辑内容也会实时更新

## 核心实现原理

### ShareDB OT 算法

ShareDB 使用 Operational Transformation (OT) 算法来处理并发编辑：

1. 每个用户的编辑操作被序列化为 delta 格式
2. 操作通过 WebSocket 发送到 ShareDB 服务器
3. 服务器对并发操作进行转换，确保所有客户端最终状态一致
4. 操作广播到所有连接的客户端

### 实时光标同步

- 使用 Socket.io 传输光标位置信息
- 使用 quill-cursors 插件显示多用户光标
- 每个用户有独特的颜色标识

## 端口说明

- **后端服务**: 3001
- **ShareDB WebSocket**: 3001/sharedb
- **前端应用**: 3000

## 注意事项

- 数据存储在内存中，重启服务后数据会丢失
- 如需持久化存储，可以集成 MongoDB 或其他数据库
- 当前版本为演示用途，生产环境建议添加用户认证和权限管理
