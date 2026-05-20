# SaaS 表单构建器

基于 Laravel + Vue 3 + MySQL 的多租户表单构建系统，支持拖拽构建表单、多级审批流、数据收集与导出。

## 功能特性

### 1. 租户隔离（分库）
- 每个租户拥有独立的数据库
- 中央数据库管理租户信息
- 自动创建和迁移租户数据库

### 2. 表单引擎（拖拽构建）
- 支持多种字段类型：文本、数字、下拉、单选、多选、日期、开关等
- 拖拽式表单设计
- 字段属性配置（必填项、选项等）
- 表单发布管理

### 3. 多级审批流
- 可视化审批流程设计
- 支持多级审批步骤
- 审批人指定
- 审批状态追踪
- 审批意见记录

### 4. 数据收集与导出
- 表单数据提交与存储
- 数据列表展示与筛选
- CSV/JSON格式导出
- 提交详情查看

## 项目结构

```
saas-form-builder/
├── backend/                 # Laravel 后端
│   ├── app/
│   │   ├── Models/         # 数据模型
│   │   │   ├── Tenant.php       # 租户模型（中央库）
│   │   │   ├── TenantUser.php   # 租户用户
│   │   │   ├── Form.php         # 表单模型
│   │   │   ├── FormField.php    # 表单字段
│   │   │   ├── FormSubmission.php # 表单提交
│   │   │   ├── ApprovalFlow.php    # 审批流程
│   │   │   ├── ApprovalStep.php    # 审批步骤
│   │   │   └── Approval.php        # 审批记录
│   │   └── Http/
│   │       ├── Middleware/
│   │       │   └── TenantMiddleware.php # 租户识别中间件
│   │       └── Controllers/Api/
│   └── database/
│       └── migrations/
│           └── tenant/       # 租户数据库迁移
└── frontend/                # Vue 3 前端
    ├── src/
    │   ├── views/           # 页面组件
    │   │   ├── Forms/          # 表单管理
    │   │   ├── Submissions/    # 提交数据
    │   │   ├── Approvals/      # 审批管理
    │   │   └── ApprovalFlows/  # 审批流程
    │   ├── stores/          # Pinia 状态
    │   └── router/          # 路由配置
    └── package.json
```

## 技术栈

### 后端
- Laravel 10.x
- MySQL 8.0+
- JWT Authentication (tymon/jwt-auth)

### 前端
- Vue 3 (Composition API)
- Vite
- Pinia (状态管理)
- Vue Router
- Element Plus (UI组件库)
- vuedraggable (拖拽功能)

## 快速开始

### 环境要求
- PHP 8.1+
- Node.js 18+
- MySQL 8.0+
- Composer

### 后端安装

```bash
cd backend

# 安装依赖
composer install

# 复制环境变量
cp .env.example .env

# 生成应用密钥
php artisan key:generate

# 生成 JWT 密钥
php artisan jwt:secret

# 配置数据库连接（.env文件）
# DB_CONNECTION=mysql
# DB_HOST=127.0.0.1
# DB_PORT=3306
# DB_DATABASE=saas_builder_central
# DB_USERNAME=root
# DB_PASSWORD=

# 运行迁移
php artisan migrate
```

### 前端安装

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 开发服务器

后端默认: `http://localhost:8000`
前端默认: `http://localhost:3000`

## API 端点

### 租户管理（中央库）
- `GET /api/admin/tenants` - 获取租户列表
- `POST /api/admin/tenants` - 创建租户
- `GET /api/admin/tenants/{tenant}` - 查看租户详情
- `PUT /api/admin/tenants/{tenant}` - 更新租户
- `DELETE /api/admin/tenants/{tenant}` - 删除租户

### 认证（租户域）
- `POST /api/register` - 用户注册
- `POST /api/login` - 用户登录
- `POST /api/logout` - 退出登录
- `GET /api/me` - 获取当前用户
- `POST /api/refresh` - 刷新 Token

### 表单管理
- `GET /api/forms` - 获取表单列表
- `POST /api/forms` - 创建表单
- `GET /api/forms/{form}` - 查看表单
- `PUT /api/forms/{form}` - 更新表单
- `DELETE /api/forms/{form}` - 删除表单
- `POST /api/forms/{form}/publish` - 发布表单
- `POST /api/forms/{form}/submit` - 提交表单

### 审批管理
- `GET /api/approval-flows` - 获取审批流程列表
- `POST /api/approval-flows` - 创建审批流程
- `GET /api/approval-flows/{flow}` - 查看流程
- `PUT /api/approval-flows/{flow}` - 更新流程
- `DELETE /api/approval-flows/{flow}` - 删除流程
- `GET /api/my-approvals` - 我的待审批
- `POST /api/approvals/{approval}/approve` - 通过审批
- `POST /api/approvals/{approval}/reject` - 拒绝审批

### 数据导出
- `POST /api/submissions/export` - 导出提交数据

## 数据库设计

### 中央数据库
- `tenants` - 租户表

### 租户数据库
- `tenant_users` - 用户表
- `forms` - 表单表
- `form_fields` - 表单字段表
- `form_submissions` - 表单提交记录表
- `approval_flows` - 审批流程表
- `approval_steps` - 审批步骤表
- `approvals` - 审批记录表

## 开发说明

### 添加新的表单字段类型
1. 后端更新字段类型验证逻辑
2. 前端更新字段组件映射
3. 更新表单构建器的字段调色板

### 扩展审批功能
1. 添加新的审批状态
2. 更新审批流程控制器
3. 添加对应的前端页面

## License

MIT
