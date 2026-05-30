## 1. 架构设计

```mermaid
flowchart TB
    subgraph "前端层"
        "React App" --> "Monaco Diff Editor"
        "React App" --> "文件树组件"
        "React App" --> "差异导航组件"
        "React App" --> "Zustand 状态管理"
    end
    subgraph "后端层"
        "Express Server" --> "Diff 计算服务"
        "Express Server" --> "文件树解析服务"
        "Express Server" --> "文件上传处理"
    end
    subgraph "数据层"
        "内存存储" --> "文件内容缓存"
        "内存存储" --> "Diff 结果缓存"
    end
    "前端层" -->|"HTTP API"| "后端层"
    "后端层" -->|"读写"| "数据层"
```

## 2. 技术说明

- **前端**：React@18 + TypeScript + Tailwind CSS@3 + Vite
- **初始化工具**：vite-init（react-express-ts 模板）
- **核心依赖**：
  - `@monaco-editor/react`：Monaco Editor React 封装，提供 DiffEditor 组件
  - `zustand`：轻量状态管理，管理文件树、当前文件、差异列表等
  - `diff`：npm diff 库，用于计算文本差异
- **后端**：Express@4 + TypeScript（ESM）
- **数据库**：无（内存缓存 + 文件上传临时存储）

## 3. 路由定义

| 路由 | 用途 |
|------|------|
| `/` | 主页面，包含代码对比和目录树对比两个 Tab |
| `/compare` | 代码对比模式（默认视图） |
| `/tree` | 目录树对比模式 |

## 4. API 定义

### 4.1 计算文本差异

```
POST /api/diff/text
Request: { oldText: string, newText: string, language?: string }
Response: { hunks: Hunk[], stats: { additions: number, deletions: number, changes: number } }
```

### 4.2 上传目录文件

```
POST /api/diff/upload
Request: FormData (files[], basePath: string)
Response: { tree: FileTreeNode[], files: Record<string, string> }
```

### 4.3 计算目录差异

```
POST /api/diff/directory
Request: { oldTree: FileTreeNode[], newTree: FileTreeNode[] }
Response: { diffTree: DiffTreeNode[], changedFiles: string[] }
```

### 4.4 TypeScript 类型定义

```typescript
interface Hunk {
  oldStart: number;
  oldLines: number;
  newStart: number;
  newLines: number;
  changes: Change[];
}

interface Change {
  type: 'add' | 'delete' | 'normal';
  oldLineNumber?: number;
  newLineNumber?: number;
  content: string;
}

interface FileTreeNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileTreeNode[];
}

interface DiffTreeNode extends FileTreeNode {
  status: 'added' | 'deleted' | 'modified' | 'unchanged';
}
```

## 5. 服务端架构图

```mermaid
flowchart LR
    "Router" --> "DiffController"
    "DiffController" --> "DiffService"
    "DiffService" --> "DiffLib（diff 库）"
    "DiffService" --> "FileTreeParser"
```

## 6. 数据模型

本项目不使用持久化数据库，采用内存数据结构。核心数据模型如下：

### 6.1 前端状态模型（Zustand Store）

```typescript
interface DiffStore {
  mode: 'code' | 'directory';
  language: string;
  oldCode: string;
  newCode: string;
  oldTree: FileTreeNode | null;
  newTree: FileTreeNode | null;
  diffTree: DiffTreeNode | null;
  selectedFile: string | null;
  diffStats: { additions: number; deletions: number; changes: number } | null;
  currentDiffIndex: number;
  totalDiffs: number;
}
```
