# Cloud Desktop Management API

基于 .NET Core 和 RDP 协议构建的云桌面管理服务后端 API。

## 功能特性

### 1. 桌面池管理 (Desktop Pool Management)
- 创建、读取、更新、删除桌面池
- 管理池内桌面虚拟机
- 配置桌面规格（CPU、内存、存储）
- 配置默认连接协议（RDP/VNC/SPICE）

### 2. 会话管理 (Session Management)
- 创建和终止用户会话
- 会话状态跟踪（连接中、活跃、断开、已登出）
- 会话时长统计
- 客户端 IP 和主机名记录

### 3. 连接代理 (Connection Broker)
- 自动分配可用桌面
- 基于用户配额的连接验证
- 生成 RDP 连接字符串
- 桌面可用性检查

### 4. 用户配额 (User Quotas)
- 最大并发会话数限制
- 每日使用时长限制
- 每月使用时长限制
- 自动重置使用统计

## 项目结构

```
CloudDesktop.Api/
├── Controllers/              # API 控制器
│   ├── DesktopPoolsController.cs
│   ├── SessionsController.cs
│   ├── ConnectionBrokerController.cs
│   └── UserQuotasController.cs
├── Models/                   # 数据模型
│   ├── Enums/
│   │   └── DesktopPoolStatus.cs
│   ├── DesktopPool.cs
│   ├── Desktop.cs
│   ├── Session.cs
│   ├── User.cs
│   └── UserQuota.cs
├── Dtos/                     # 数据传输对象
│   ├── DesktopPoolDtos.cs
│   ├── DesktopDtos.cs
│   ├── SessionDtos.cs
│   └── UserQuotaDtos.cs
├── Services/                 # 业务逻辑服务
│   ├── DesktopPoolService.cs
│   ├── SessionService.cs
│   ├── ConnectionBrokerService.cs
│   └── UserQuotaService.cs
├── Data/                     # 数据访问层
│   ├── ApplicationDbContext.cs
│   └── SeedData.cs
├── Program.cs
└── CloudDesktop.Api.csproj
```

## API 端点

### 桌面池
- `GET /api/DesktopPools` - 获取所有桌面池
- `GET /api/DesktopPools/{id}` - 获取指定桌面池详情
- `POST /api/DesktopPools` - 创建桌面池
- `PUT /api/DesktopPools/{id}` - 更新桌面池
- `DELETE /api/DesktopPools/{id}` - 删除桌面池

### 会话
- `GET /api/Sessions` - 获取所有会话（支持按用户/桌面池筛选）
- `GET /api/Sessions/{id}` - 获取指定会话详情
- `POST /api/Sessions` - 创建会话
- `PUT /api/Sessions/{id}` - 更新会话状态
- `POST /api/Sessions/{id}/terminate` - 终止会话

### 连接代理
- `POST /api/ConnectionBroker/connect` - 请求桌面连接
- `GET /api/ConnectionBroker/available-desktops/{poolId}` - 检查可用桌面
- `GET /api/ConnectionBroker/validate-quota` - 验证用户配额

### 用户配额
- `GET /api/UserQuotas` - 获取所有配额（支持按用户筛选）
- `GET /api/UserQuotas/{id}` - 获取指定配额详情
- `POST /api/UserQuotas` - 创建用户配额
- `PUT /api/UserQuotas/{id}` - 更新用户配额
- `DELETE /api/UserQuotas/{id}` - 删除用户配额
- `POST /api/UserQuotas/reset-daily` - 重置每日使用量
- `POST /api/UserQuotas/reset-monthly` - 重置每月使用量

## 快速开始

### 前置要求
- .NET 8.0 SDK

### 运行项目

```bash
# 恢复依赖
dotnet restore

# 构建项目
dotnet build

# 运行项目
dotnet run
```

### 访问 Swagger 文档

启动项目后，访问：`http://localhost:5000/swagger`

## 默认测试数据

项目启动时会自动创建以下测试数据：

**用户:**
- admin / admin@clouddesktop.com (IT部门)
- john.doe / john.doe@clouddesktop.com (工程部)
- jane.smith / jane.smith@clouddesktop.com (财务部)

**桌面池:**
- Engineering Pool (10个桌面限额，4核16GB)
- Finance Pool (5个桌面限额，2核8GB)

## 技术栈

- **框架**: ASP.NET Core 8.0
- **数据库**: Entity Framework Core (内存数据库，可切换到 SQL Server)
- **API 文档**: Swagger/OpenAPI
- **连接协议**: RDP (远程桌面协议)
