## 1. 架构设计

```mermaid
graph TB
    subgraph "前端层"
        A["React Web UI"] --> B["配置面板"]
        A --> C["实时监控图表"]
        A --> D["测试报告展示"]
    end
    
    subgraph "通信层"
        E["Spring Boot WebSocket"]
        F["REST API"]
    end
    
    subgraph "后端核心层"
        G["压力测试引擎"] --> H["线程池管理"]
        G --> I["实时统计计算"]
        J["ID生成器工厂"] --> K["雪花算法"]
        J --> L["号段模式"]
        J --> M["随机ID算法"]
        N["唯一性校验器"]
    end
    
    subgraph "数据层"
        O["内存存储（测试数据）"]
        P["导出文件（JSON/CSV）"]
    end
    
    A --> E
    A --> F
    E --> G
    F --> G
    G --> J
    G --> N
    G --> I
    N --> O
    I --> O
    O --> P
```

## 2. 技术描述

### 2.1 前端技术栈
- **框架**: React@18
- **构建工具**: Vite@5
- **样式**: TailwindCSS@3
- **图表**: ECharts@5
- **状态管理**: Zustand@4
- **UI组件**: Ant Design@5
- **WebSocket**: SockJS + Stomp
- **路由**: React Router@6

### 2.2 后端技术栈
- **框架**: Spring Boot@3.2
- **多线程**: Java ExecutorService + CompletableFuture
- **WebSocket**: Spring WebSocket
- **构建工具**: Maven
- **JDK版本**: Java 17+

### 2.3 核心依赖
- Lombok（简化代码）
- FastJSON2（JSON处理）

## 3. 路由定义

| 路由 | 页面 | 功能 |
|------|------|------|
| / | 首页/配置页 | 测试参数配置、算法选择 |
| /monitor | 实时监控页 | 实时展示测试进度和性能指标 |
| /report | 测试报告页 | 展示测试结果和唯一性校验 |

## 4. API 定义

### 4.1 TypeScript 类型定义

```typescript
// 算法类型
type IdAlgorithm = 'SNOWFLAKE' | 'SEGMENT' | 'RANDOM';

// 测试配置
interface TestConfig {
  algorithm: IdAlgorithm;
  threadCount: number;
  durationSeconds: number;
  idCount?: number;
  snowflakeConfig?: {
    workerId: number;
    datacenterId: number;
  };
  segmentConfig?: {
    segmentSize: number;
  };
}

// 实时指标
interface RealtimeMetrics {
  timestamp: number;
  qps: number;
  avgLatency: number;
  p50Latency: number;
  p95Latency: number;
  p99Latency: number;
  generatedCount: number;
}

// 测试报告
interface TestReport {
  id: string;
  config: TestConfig;
  startTime: number;
  endTime: number;
  totalGenerated: number;
  avgQps: number;
  peakQps: number;
  latencyStats: {
    avg: number;
    min: number;
    max: number;
    p50: number;
    p95: number;
    p99: number;
  };
  uniquenessCheck: {
    isUnique: boolean;
    duplicateCount: number;
    duplicateRate: number;
    duplicateIds: string[];
  };
  metricsHistory: RealtimeMetrics[];
}
```

### 4.2 REST API

| 方法 | 路径 | 描述 | 请求 | 响应 |
|------|------|------|------|
| POST | /api/test/start | 启动压力测试 | TestConfig | {testId: string} |
| GET | /api/test/stop | 停止测试 | - | {success: boolean} |
| GET | /api/test/:testId | 获取测试报告 | - | TestReport |
| GET | /api/test/list | 获取历史报告列表 | - | TestReport[] |
| GET | /api/report/:testId/export | 导出报告 | format=json/csv | 文件流 |

### 4.3 WebSocket 消息

```typescript
// 订阅主题
// /topic/test/{testId}/metrics → RealtimeMetrics

// 发送消息
// /app/test/{testId}/start → 开始测试
```

## 5. 后端架构图

```mermaid
graph TB
    subgraph "Controller层"
        A["TestController"]
        B["WebSocketController"]
    end
    
    subgraph "Service层"
        C["TestEngineService"]
        D["IdGeneratorService"]
        E["MetricsService"]
        F["UniquenessCheckService"]
    end
    
    subgraph "Domain层"
        G["IdGenerator 接口"]
        H["SnowflakeIdGenerator"]
        I["SegmentIdGenerator"]
        J["RandomIdGenerator"]
        K["IdGeneratorFactory"]
    end
    
    subgraph "DTO/VO"
        L["TestConfig"]
        M["TestReport"]
        N["RealtimeMetrics"]
    end
    
    A --> C
    B --> C
    C --> D
    C --> E
    C --> F
    D --> K
    K --> G
    G --> H
    G --> I
    G --> J
    C --> L
    C --> M
    E --> N
```

## 6. 数据模型

### 6.1 核心类关系

```mermaid
classDiagram
    class TestEngine {
        -String testId
        -TestConfig config
        -ExecutorService threadPool
        -AtomicLong counter
        -ConcurrentHashMap idSet
        +startTest()
        +stopTest()
        +getReport()
    }
    
    class IdGenerator {
        <<interface>>
        +nextId()
    }
    
    class SnowflakeGenerator {
        -long workerId
        -long datacenterId
        -long sequence
    }
    
    class SegmentGenerator {
        -long segmentSize
        -AtomicLong current
    }
    
    class MetricsCollector {
        -List history
        -LongAdder successCount
        +recordLatency()
        +calculateStats()
    }
    
    class UniquenessChecker {
        -Set idSet
        +check()
        +getDuplicates()
    }
    
    TestEngine --> IdGenerator : uses
    IdGenerator <|-- SnowflakeGenerator
    IdGenerator <|-- SegmentGenerator
    TestEngine --> MetricsCollector
    TestEngine --> UniquenessChecker
```

### 6.2 项目目录结构

```
id-generator-benchmark/
├── backend/
│   ├── src/
│   │   └── main/
│   │       ├── java/
│   │       │   └── com/
│   │       │       └── benchmark/
│   │       │           ├── controller/
│   │       │           ├── service/
│   │       │           ├── generator/
│   │       │           ├── dto/
│   │       │           ├── config/
│   │       │           └── Application.java
│   │       └── resources/
│   │           └── application.yml
│   └── pom.xml
└── frontend/
    ├── src/
    │   ├── components/
    │   ├── pages/
    │   ├── store/
    │   ├── utils/
    │   └── App.tsx
    │   └── main.tsx
    ├── package.json
    └── vite.config.ts
    └── tailwind.config.js
```

