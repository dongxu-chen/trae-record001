## 1. 架构设计

```mermaid
graph TD
    subgraph "前端 (React)"
        A["React 应用"] --> B["ECharts 图表组件"]
        A --> C["Canvas 注释层"]
        A --> D["注释管理模块"]
        A --> E["WebSocket 客户端"]
        A --> F["导出/分享模块"]
    end
    
    subgraph "后端 (Node.js + Express)"
        G["Express API 服务"] --> H["注释 CRUD API"]
        G --> I["分享链接 API"]
        J["WebSocket 服务"] --> K["实时协作同步"]
        L["会话管理"]
    end
    
    subgraph "数据存储"
        M["内存存储 (开发)"]
        N["可扩展至 Redis/PostgreSQL"]
    end
    
    E --> J
    H --> L
    K --> L
    L --> M
```

## 2. 技术描述

- **前端**: React@18 + TypeScript + Vite + TailwindCSS@3 + Zustand + ECharts + lucide-react
- **后端**: Node.js + Express@4 + TypeScript + ws (WebSocket库)
- **初始化工具**: vite-init (react-express-ts模板)
- **通信**: REST API + WebSocket 双工通信
- **图标库**: lucide-react

## 3. 路由定义

| 路由 | 目的 |
|-------|---------|
| / | 主页面，图表展示和注释编辑器 |
| /share/:sessionId | 分享链接访问页面 |
| /api/annotations | 注释CRUD API |
| /api/share | 分享链接生成API |
| /ws | WebSocket连接端点 |

## 4. API 定义

### 4.1 TypeScript 类型定义

```typescript
// 注释类型
export type AnnotationType = 'text' | 'arrow' | 'highlight';

export interface Point {
  x: number;
  y: number;
  dataIndex?: number;
  seriesIndex?: number;
}

export interface Annotation {
  id: string;
  type: AnnotationType;
  position: Point;
  endPosition?: Point;
  content?: string;
  color: string;
  authorId: string;
  authorName: string;
  createdAt: number;
  updatedAt: number;
}

export interface User {
  id: string;
  name: string;
  color: string;
  cursor?: Point;
}

export interface Session {
  id: string;
  annotations: Annotation[];
  users: User[];
  chartData: any;
}

// WebSocket 消息
export interface WSMessage {
  type: 'user_join' | 'user_leave' | 'cursor_update' | 'annotation_add' | 'annotation_update' | 'annotation_delete';
  payload: any;
  userId: string;
  timestamp: number;
}
```

### 4.2 API 端点

| 方法 | 路径 | 请求 | 响应 |
|------|------|------|------|
| GET | /api/sessions/:id | - | Session |
| POST | /api/sessions | { chartData } | { sessionId } |
| GET | /api/sessions/:id/annotations | - | Annotation[] |
| POST | /api/sessions/:id/annotations | Annotation | Annotation |
| PUT | /api/sessions/:id/annotations/:aid | Partial<Annotation> | Annotation |
| DELETE | /api/sessions/:id/annotations/:aid | - | { success } |
| POST | /api/share | { sessionId, expiresIn } | { shareUrl, shareId } |

## 5. 服务器架构图

```mermaid
graph LR
    A["客户端"] -->|HTTP| B["Express Server"]
    A -->|WebSocket| C["WebSocket Server"]
    
    B --> D["Session Controller"]
    B --> E["Annotation Controller"]
    B --> F["Share Controller"]
    
    C --> G["Collaboration Service"]
    
    D --> H["Session Service"]
    E --> I["Annotation Service"]
    F --> J["Share Service"]
    G --> H
    G --> I
    
    H --> K["In-Memory Store"]
    I --> K
    J --> K
```

## 6. 数据模型

### 6.1 数据模型定义

```mermaid
erDiagram
    SESSION ||--o{ ANNOTATION : contains
    SESSION ||--o{ USER : has
    SESSION ||--o{ SHARE_LINK : has
    
    SESSION {
        string id PK
        object chartData
        datetime createdAt
    }
    
    ANNOTATION {
        string id PK
        string sessionId FK
        string type
        object position
        string content
        string color
        string authorId
        datetime createdAt
        datetime updatedAt
    }
    
    USER {
        string id PK
        string sessionId FK
        string name
        string color
        datetime lastActive
    }
    
    SHARE_LINK {
        string id PK
        string sessionId FK
        datetime expiresAt
        int accessCount
    }
```

### 6.2 内存存储结构

开发阶段使用内存存储，生产环境可迁移至数据库：

```typescript
interface Store {
  sessions: Map<string, Session>;
  shareLinks: Map<string, { sessionId: string; expiresAt: number }>;
}
```
