# Elasticsearch 分片均衡工具 - 技术架构文档

## 1. 技术选型

### 1.1 核心框架
- **React 18**：使用最新特性，包括并发渲染和自动批处理
- **TypeScript**：类型安全，提升代码可维护性
- **Vite**：极速开发体验，热更新速度快

### 1.2 状态管理
- **React Query (TanStack Query)**：服务端状态管理，缓存、重试、自动刷新
- **React Context**：全局 UI 状态（主题、配置面板）

### 1.3 UI 组件库
- **Tailwind CSS**：原子化 CSS，快速构建自定义 UI
- **Headless UI**：无样式可访问组件，配合 Tailwind 使用
- **Heroicons**：配套图标库

### 1.4 数据可视化
- **Recharts**：React 图表库，支持各种统计图表
- **自定义组件**：分片矩阵、环形进度条等特殊可视化

### 1.5 工具库
- **Axios**：HTTP 请求库
- **date-fns**：日期时间处理
- **clsx**：类名合并

## 2. 项目结构

```
frontend/
├── src/
│   ├── api/              # API 接口层
│   │   ├── client.ts     # Axios 客户端配置
│   │   ├── cluster.ts    # 集群相关 API
│   │   ├── balancer.ts   # 均衡器相关 API
│   │   └── settings.ts   # 设置相关 API
│   ├── components/       # 通用组件
│   │   ├── ui/           # 基础 UI 组件
│   │   │   ├── Card.tsx
│   │   │   ├── Button.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Progress.tsx
│   │   │   └── Badge.tsx
│   │   ├── charts/       # 图表组件
│   │   │   ├── DiskUsageChart.tsx
│   │   │   ├── ShardCountChart.tsx
│   │   │   └── ShardMatrix.tsx
│   │   └── layout/       # 布局组件
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       └── Container.tsx
│   ├── hooks/            # 自定义 Hooks
│   │   ├── useCluster.ts
│   │   ├── useBalancer.ts
│   │   └── useSettings.ts
│   ├── pages/            # 页面组件
│   │   ├── Dashboard.tsx
│   │   ├── Nodes.tsx
│   │   ├── Shards.tsx
│   │   ├── Migrations.tsx
│   │   └── Settings.tsx
│   ├── types/            # TypeScript 类型定义
│   │   ├── cluster.ts
│   │   ├── balancer.ts
│   │   └── index.ts
│   ├── utils/            # 工具函数
│   │   ├── format.ts
│   │   └── constants.ts
│   ├── App.tsx           # 应用入口组件
│   ├── main.tsx          # 应用入口
│   └── index.css         # 全局样式
├── public/               # 静态资源
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## 3. 核心模块设计

### 3.1 API 层设计

**接口划分原则：**
- 按业务领域划分模块
- 统一错误处理
- React Query 管理缓存

```typescript
// api/client.ts
export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

// api/cluster.ts
export const getClusterHealth = () => 
  apiClient.get<ClusterHealth>('/cluster/health');

export const getShardDistribution = () => 
  apiClient.get<ShardDistribution>('/cluster/distribution');
```

### 3.2 自定义 Hooks

```typescript
// hooks/useCluster.ts
export function useClusterHealth() {
  return useQuery({
    queryKey: ['cluster', 'health'],
    queryFn: getClusterHealth,
    refetchInterval: 5000,
  });
}

export function useShardDistribution() {
  return useQuery({
    queryKey: ['cluster', 'distribution'],
    queryFn: getShardDistribution,
    refetchInterval: 10000,
  });
}
```

### 3.3 组件设计原则

1. **单一职责**：每个组件只做一件事
2. **可组合**：组件可嵌套组合使用
3. **可测试**：组件逻辑与 UI 分离
4. **可访问**：支持键盘导航和屏幕阅读器

### 3.4 状态管理策略

- **服务端状态**：React Query 管理，自动缓存和刷新
- **UI 状态**：组件内 useState，提升到需要共享的最低公共祖先
- **全局状态**：React Context（主题、用户配置等）

## 4. 数据流架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  React Query    │────▶│  Custom Hooks   │────▶│  Components     │
│  (Cache Layer)  │     │  (Business)     │     │  (UI Layer)     │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
          │                                                       
          ▼                                                       
┌─────────────────┐                                               
│                 │                                               
│  API Client     │                                               
│  (HTTP Layer)   │                                               
│                 │                                               
└─────────────────┘                                               
          │                                                       
          ▼                                                       
┌─────────────────┐                                               
│                 │                                               
│  Go Backend     │                                               
│  (ES API)       │                                               
│                 │                                               
└─────────────────┘                                               
```

## 5. 关键功能实现方案

### 5.1 自动刷新机制
- 使用 React Query 的 `refetchInterval` 配置
- 不同数据不同刷新频率：
  - 集群健康状态：5秒
  - 分片分布：10秒
  - 迁移任务：3秒
  - 配置信息：60秒

### 5.2 分片矩阵可视化
- 二维网格布局展示分片分布
- 颜色编码表示分片类型和状态
- 悬停显示详细信息
- 点击选中可执行迁移操作

### 5.3 迁移操作流程
1. 生成迁移计划
2. 预览确认对话框
3. 执行迁移 API 调用
4. 显示执行结果
5. 自动刷新状态

### 5.4 错误处理策略
- 网络错误：重试 + 降级展示
- API 错误：友好提示 + 详细日志
- 表单验证：实时验证 + 错误提示

## 6. 性能优化策略

### 6.1 代码分割
- 按页面级代码分割
- 动态导入图表库等大型依赖

### 6.2 虚拟列表
- 节点列表、分片列表使用虚拟滚动
- 支持 1000+ 条数据流畅展示

### 6.3 缓存策略
- React Query 缓存服务端数据
- 组件 memo 避免不必要重渲染
- 列表项使用稳定 key

## 7. 开发规范

### 7.1 命名规范
- 组件：PascalCase
- 函数/变量：camelCase
- 常量：UPPER_SNAKE_CASE
- 类型：PascalCase

### 7.2 代码风格
- ESLint + Prettier 统一代码风格
- 严格的 TypeScript 类型检查
- 组件 Props 使用 interface 定义

### 7.3 Git 提交规范
- feat: 新功能
- fix: 修复 bug
- refactor: 重构
- chore: 构建/工具链变更
