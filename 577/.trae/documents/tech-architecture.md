## 1. 架构设计

```mermaid
flowchart TB
    subgraph "前端层"
        "A[React UI组件]" --> "B[Zustand状态管理]"
        "B" --> "C[Web Worker抽样引擎]"
    end
    subgraph "后端层"
        "D[Express API路由]" --> "E[文件解析服务]"
        "E" --> "F[分块读取引擎]"
    end
    subgraph "数据层"
        "G[临时文件存储]"
    end
    "A" --> "|上传文件|" "D"
    "D" --> "|返回元信息|" "A"
    "A" --> "|请求分块数据|" "D"
    "D" --> "|流式返回数据|" "C"
    "C" --> "|抽样结果|" "B"
    "D" --> "|存储文件|" "G"
    "F" --> "|读取文件|" "G"
```

## 2. 技术说明

- 前端：React@18 + TypeScript + TailwindCSS@3 + Vite + Zustand
- 初始化工具：vite-init
- 后端：Express@4 + TypeScript (ESM)
- 数据库：无（基于文件处理的临时存储）
- 图表库：recharts
- 文件解析：papaparse(CSV)、原生JSON解析、parquetjs(Parquet)
- Web Worker：内联Worker处理抽样算法，避免阻塞UI线程

## 3. 路由定义

| 路由 | 用途 |
|------|------|
| / | 数据抽样工作台主页面 |

## 4. API定义

### 4.1 文件上传

```typescript
POST /api/upload
Content-Type: multipart/form-data

Request: { file: File }
Response: {
  fileId: string
  fileName: string
  format: "csv" | "json" | "parquet"
  totalRows: number
  columns: Array<{ name: string; type: "string" | "number" | "boolean" | "date" }>
  fileSize: number
}
```

### 4.2 分块读取数据

```typescript
GET /api/data/:fileId/chunk?offset=0&limit=1000

Response: {
  offset: number
  limit: number
  totalRows: number
  data: Record<string, unknown>[]
}
```

### 4.3 获取列统计信息（用于分层抽样）

```typescript
GET /api/data/:fileId/column-stats?column=name

Response: {
  column: string
  uniqueValues: number
  distribution: Array<{ value: string; count: number }>
}
```

### 4.4 导出样本

```typescript
POST /api/export

Request: {
  fileId: string
  sampleIndices: number[]
  format: "csv" | "json"
}
Response: Binary file download
```

## 5. 服务器架构图

```mermaid
flowchart LR
    "A[路由层 routes]" --> "B[控制器层 controllers]"
    "B" --> "C[服务层 services]"
    "C" --> "D[文件系统临时存储]"
```

## 6. 数据模型

### 6.1 数据模型定义

```mermaid
erDiagram
    "UploadedFile" {
        string fileId PK
        string fileName
        string format
        number totalRows
        number fileSize
        string filePath
        datetime uploadedAt
    }
    "ColumnMeta" {
        string name
        string type
        number uniqueValues
    }
    "SampleConfig" {
        string method
        number ratio
        string stratifyColumn
        number stepSize
    }
    "SampleResult" {
        number[] indices
        number sampleSize
        number totalSize
    }
    "UploadedFile" ||--o{ "ColumnMeta" : "has"
    "SampleConfig" --> "UploadedFile" : "applies to"
    "SampleResult" --> "UploadedFile" : "derived from"
```

### 6.2 抽样算法设计

**随机抽样**：使用Fisher-Yates洗牌算法的部分洗牌实现，从N个元素中随机选取K个，时间复杂度O(K)

**分层抽样**：先按指定列的值分组，每组内按比例随机抽样，确保各层代表性

**系统抽样**：计算间隔 k=N/n，从随机起点开始每隔k个元素取一个，时间复杂度O(n)

### 6.3 Web Worker通信协议

```typescript
type WorkerMessage =
  | { type: "RANDOM_SAMPLE"; data: unknown[]; ratio: number }
  | { type: "STRATIFIED_SAMPLE"; data: unknown[]; ratio: number; column: string }
  | { type: "SYSTEMATIC_SAMPLE"; data: unknown[]; ratio: number; stepSize?: number }

type WorkerResponse = {
  type: "SAMPLE_RESULT"
  indices: number[]
  sampleData: unknown[]
  stats: {
    sampleSize: number
    totalSize: number
    distribution?: Record<string, number>
  }
}
```
