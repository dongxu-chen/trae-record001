# 服务依赖拓扑自动发现工具

通过分析服务间的调用链数据（Trace），自动构建服务拓扑图，标注调用量、错误率和延迟。支持服务分层展示、故障影响范围分析、历史拓扑变化对比。

## 技术栈

- **OpenTelemetry + Jaeger**: 分布式追踪数据采集与存储
- **Neo4j**: 图数据库存储服务拓扑关系
- **D3.js**: 前端拓扑图可视化
- **Flask**: 后端API服务

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                         前端 (D3.js)                        │
│   ┌──────────┬──────────┬──────────┬──────────┐            │
│   │ 拓扑视图  │ 分析面板  │ 故障分析  │ 历史对比  │            │
│   └──────────┴──────────┴──────────┴──────────┘            │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP API
┌──────────────────────────────▼──────────────────────────────┐
│                      Flask 后端 API                         │
│  ┌─────────────┬──────────────┬──────────────┐             │
│  │  拓扑查询API │  故障分析API  │  历史对比API  │             │
│  └─────────────┴──────────────┴──────────────┘             │
│  ┌─────────────────────────────────────────────┐            │
│  │         Trace Collector (Jaeger集成)         │            │
│  └─────────────────────────────────────────────┘            │
└──────┬──────────────────────────────────────────┬───────────┘
       │                                          │
┌──────▼───────┐                          ┌──────▼───────┐
│   Neo4j      │                          │   Jaeger     │
│  图数据库     │                          │  追踪存储     │
└──────────────┘                          └──────────────┘
```

## 快速开始

### 1. 使用 Docker Compose 一键部署

```bash
# 启动所有服务（Jaeger + Neo4j + 后端）
docker-compose up -d

# 等待服务启动完成后，生成演示数据
docker-compose --profile demo up demo-generator

# 访问前端界面
# http://localhost:5000
```

### 2. 本地开发模式

#### 前置要求
- Python 3.10+
- Neo4j 5.x
- Jaeger (all-in-one)

#### 启动依赖服务

```bash
# 启动 Neo4j
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/topology123 \
  neo4j:5.14-community

# 启动 Jaeger
docker run -d \
  --name jaeger \
  -p 16686:16686 -p 14268:14268 \
  jaegertracing/all-in-one:1.52
```

#### 启动后端服务

```bash
cd backend
pip install -r requirements.txt
python app.py
```

#### 生成演示数据

```bash
cd demo-services
pip install -r requirements.txt
python trace_generator.py
```

#### 访问应用

打开浏览器访问: http://localhost:5000

## 功能特性

### 1. 拓扑视图

- **实时拓扑图**: 基于D3.js力导向图展示服务依赖关系
- **分层展示**: 自动识别服务层级（入口层、中间层、数据层）
- **节点标注**: 显示服务名称、调用次数、错误率
- **连线标注**: 显示调用量、错误率、平均延迟
- **颜色编码**: 
  - 绿色: 正常
  - 黄色: 高延迟
  - 红色: 高错误率
- **交互功能**: 悬停查看详情、点击选择节点、拖拽调整位置、缩放平移

### 2. 分析面板

- **层级分布**: 柱状图展示各层级服务数量
- **关键路径**: 识别高风险调用路径（按错误率和延迟排序）
- **依赖指标**: 显示服务出入度、枢纽节点识别
- **异常检测**: 自动检测高错误率、高延迟服务

### 3. 故障分析

- **故障影响树**: 分析指定服务故障后的上下游影响范围
- **级联故障路径**: 识别可能的故障传播路径
- **传播风险评估**: 评估各服务的故障传播风险等级
- **影响分数**: 基于调用量和跳数计算影响程度

### 4. 历史对比

- **快照管理**: 创建、浏览拓扑快照
- **拓扑Diff**: 对比两个快照间的拓扑变化
  - 新增/移除服务
  - 新增/移除依赖关系
  - 依赖关系变化（调用量、错误量变化）

## API 文档

### 拓扑查询

```
GET /api/topology?time_window=60
```
返回指定时间窗口内的服务拓扑图。

```
GET /api/topology/layers?time_window=60
```
返回服务层级分析结果。

```
GET /api/topology/analysis?time_window=60
```
返回拓扑综合分析结果。

### 故障分析

```
GET /api/fault/impact/{service_name}?depth=5
```
返回指定服务的故障影响范围。

```
GET /api/fault/impact-tree/{service_name}?depth=5
```
返回树形结构的故障影响分析。

```
GET /api/fault/broadcast-risk?time_window=60
```
返回各服务的故障传播风险评估。

### 历史对比

```
POST /api/topology/snapshot
```
创建当前拓扑的快照。

```
GET /api/topology/snapshots?limit=10
```
获取快照列表。

```
GET /api/topology/diff?snapshot_a=xxx&snapshot_b=yyy
```
对比两个快照的差异。

### 数据采集

```
POST /api/collect/import
{
  "service": "optional-service-name",
  "lookback": "1h",
  "limit": 100
}
```
从Jaeger导入Trace数据到Neo4j。

## 项目结构

```
.
├── backend/
│   ├── app.py                 # Flask主应用
│   ├── config.py              # 配置管理
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── collector/
│   │   └── trace_collector.py  # Jaeger Trace采集器
│   ├── storage/
│   │   └── neo4j_store.py     # Neo4j图数据库操作
│   └── analysis/
│       ├── topology_analyzer.py  # 拓扑分析器
│       └── fault_analyzer.py     # 故障分析器
├── frontend/
│   ├── index.html             # 主页面
│   ├── css/
│   │   └── style.css          # 样式
│   └── js/
│       ├── topology.js        # 拓扑图组件
│       ├── analysis.js        # 分析面板组件
│       ├── fault.js           # 故障分析组件
│       ├── history.js         # 历史对比组件
│       └── app.js             # 主应用逻辑
├── demo-services/
│   ├── trace_generator.py     # 模拟Trace数据生成器
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml         # Docker Compose配置
├── config.yaml                # 应用配置
└── requirements.txt           # Python依赖
```

## 配置说明

`config.yaml` 配置文件:

```yaml
neo4j:
  uri: bolt://localhost:7687
  user: neo4j
  password: topology123

jaeger:
  query_endpoint: http://localhost:16686/api/traces
  collector_endpoint: http://localhost:14268/api/traces

flask:
  host: 0.0.0.0
  port: 5000

analysis:
  time_window_minutes: 60      # 默认分析时间窗口
  error_rate_threshold: 0.05   # 错误率阈值 (5%)
  latency_threshold_ms: 500    # 延迟阈值 (微秒)
```

## Neo4j 数据模型

### 节点 (Node)

```
(:Service {
  name: "service-name",
  service_type: "gateway|service|database|cache",
  layer: 0,
  call_count: 100,
  error_count: 2,
  first_seen: datetime(),
  last_seen: datetime()
})
```

### 关系 (Relationship)

```
(:Service)-[:CALLS {
  call_count: 50,
  error_count: 1,
  total_latency: 100000,
  max_latency: 5000,
  min_latency: 1000,
  last_updated: datetime()
}]->(:Service)
```

## 访问地址

部署完成后可访问以下服务:

| 服务 | 地址 | 说明 |
|------|------|------|
| 拓扑分析平台 | http://localhost:5000 | 主应用界面 |
| Neo4j Browser | http://localhost:7474 | Neo4j管理界面 |
| Jaeger UI | http://localhost:16686 | Jaeger追踪界面 |

## 常见问题

### Q: 如何连接真实的微服务环境？

A: 将微服务的OpenTelemetry SDK配置为导出到Jaeger，然后点击"导入Trace"按钮即可。

### Q: 支持哪些时间窗口？

A: 支持15分钟、30分钟、1小时、4小时、24小时的时间窗口。

### Q: 如何定期创建快照？

A: 可以设置cron任务定期调用 `POST /api/topology/snapshot` 接口。

### Q: 数据会占用多大空间？

A: 取决于服务数量和调用量。建议设置数据保留策略定期清理历史数据。

## License

MIT License
