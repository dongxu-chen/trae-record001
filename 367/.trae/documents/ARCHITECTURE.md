# 技术架构文档

## 1. 架构设计

```mermaid
flowchart LR
    "UI[React 视图层]" --> "Store[Zustand 状态管理]"
    "Store" --> "Worker[Web Worker 线程]"
    "Store" --> "ES[Elasticsearch 客户端]"
    "Worker" --> "Layout[力导向布局]"
    "Worker" --> "Path[最短路径计算]"
    "ES" --> "Index[内存倒排索引]"
    "UI" --> "D3[D3 SVG 渲染]"
```

## 2. 技术说明
- **前端**：React 18 + TypeScript + Vite + Tailwind CSS + Zustand
- **可视化**：D3.js（力导向图、缩放、拖拽、交互）
- **并发**：Web Worker（力导向布局迭代、BFS 最短路径）
- **数据层**：Elasticsearch 客户端封装（使用内存倒排索引 Mock，模拟 `_search` API）
- **状态**：Zustand 管理图谱数据、筛选状态、路径结果

## 3. 路由定义
| 路由 | 用途 |
|------|------|
| `/` | 主工作台：图谱画布、工具栏、详情面板 |

## 4. 数据模型

### 4.1 三元组数据结构
```ts
type Triple = {
  subject: string;
  predicate: string;
  object: string;
  subjectType?: string;
  objectType?: string;
  attributes?: Record<string, string>;
};

type GraphNode = {
  id: string;
  label: string;
  type: string;
  group: number;
  x?: number;
  y?: number;
  attributes?: Record<string, string>;
};

type GraphLink = {
  source: string;
  target: string;
  predicate: string;
  weight: number;
};
```

### 4.2 ES 索引
实体索引：`entities`，字段 `id`, `label`, `type`, `attributes`

## 5. 目录结构
```
src/
  components/
    GraphCanvas.tsx      D3 图谱画布
    Toolbar.tsx          顶部工具栏（导入/搜索/筛选）
    DetailPanel.tsx      实体详情侧边栏
    PathQuery.tsx        路径查询表单
    StatusBar.tsx        底部状态栏
    DataImport.tsx       数据导入对话框
  hooks/
    useGraphWorker.ts    Web Worker 封装
    useSearch.ts         搜索 Hook
  workers/
    graphWorker.ts       力导向 + 路径计算 Worker
  services/
    elasticsearch.ts     ES 客户端 (Mock)
  store/
    graphStore.ts        Zustand Store
  types/
    index.ts
  utils/
    sampleData.ts        示例三元组
```
