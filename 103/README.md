# Code Snippet Platform

一个基于 Next.js 14 + Prisma + PostgreSQL + TailwindCSS 构建的在线代码片段分享平台。

## 功能特性

- ✅ 用户注册和登录（NextAuth）
- ✅ 代码片段的创建、编辑、删除
- ✅ 按语言分类和搜索功能
- ✅ 代码语法高亮（highlight.js）
- ✅ 一键复制代码功能
- ✅ 支持公开/私有代码片段
- ✅ 响应式设计，支持移动端
- ✅ 服务端组件优先，性能优化

## 技术栈

- **框架**: Next.js 14 (App Router)
- **数据库**: PostgreSQL
- **ORM**: Prisma
- **认证**: NextAuth.js
- **样式**: TailwindCSS
- **代码高亮**: highlight.js
- **语言**: TypeScript

## 快速开始

### 前置要求

- Node.js 18+
- PostgreSQL 数据库

### 安装步骤

1. 安装依赖
```bash
npm install
```

2. 配置环境变量
创建 `.env` 文件，参考 `.env.example`：
```env
DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/code_snippets?schema=public"
NEXTAUTH_SECRET="your-secret-key-here"
NEXTAUTH_URL="http://localhost:3000"
```

生成 NEXTAUTH_SECRET：
```bash
openssl rand -hex 32
```

3. 初始化数据库
```bash
npx prisma migrate dev --name init
```

4. 启动开发服务器
```bash
npm run dev
```

5. 打开浏览器访问 http://localhost:3000

## 项目结构

```
src/
├── app/                    # App Router 页面
│   ├── api/               # API 路由
│   │   ├── auth/         # 认证相关
│   │   ├── register/     # 注册
│   │   ├── snippets/     # 代码片段 CRUD
│   │   └── languages/    # 语言列表
│   ├── login/            # 登录页
│   ├── register/         # 注册页
│   ├── snippets/         # 代码片段相关页面
│   ├── my-snippets/      # 我的代码片段
│   └── page.tsx          # 首页
├── components/           # React 组件
│   ├── Navbar.tsx
│   ├── SnippetCard.tsx
│   ├── CodeBlock.tsx
│   ├── SearchFilter.tsx
│   ├── DeleteButton.tsx
│   └── SessionProvider.tsx
├── lib/                  # 工具库
│   └── prisma.ts        # Prisma 客户端
└── types/               # TypeScript 类型定义
```

## 数据库模型

### User
- id: String (cuid)
- name: String?
- email: String (unique)
- password: String (hashed)
- createdAt: DateTime
- updatedAt: DateTime

### Snippet
- id: String (cuid)
- title: String
- description: String?
- code: String
- language: String
- isPublic: Boolean
- authorId: String (foreign key to User)
- createdAt: DateTime
- updatedAt: DateTime

## 支持的编程语言

- JavaScript, TypeScript, Python, Java, C, C++, C#
- Go, Rust, Ruby, PHP, Swift, Kotlin
- HTML, CSS, SQL, Bash, JSON, YAML, Markdown

## 部署

### Vercel

1. 推送代码到 GitHub
2. 在 Vercel 导入项目
3. 配置环境变量
4. 部署！

## 开发命令

```bash
npm run dev          # 启动开发服务器
npm run build        # 构建生产版本
npm run start        # 启动生产服务器
npm run lint         # 运行 ESLint
npx prisma studio    # 打开 Prisma Studio
npx prisma migrate dev  # 创建迁移
```

## 许可证

MIT
