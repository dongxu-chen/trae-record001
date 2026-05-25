# 社交图谱分析系统 (Social Graph Analyzer)

## 项目简介

社交图谱分析系统是一个集图数据管理、网络分析、可视化展示于一体的综合性社交网络分析平台。系统支持多维度的社交关系数据导入、存储、分析和可视化，帮助用户深入理解社交网络的结构特征、发现隐藏的社区结构、识别关键影响力节点，并通过时间维度分析网络演化规律。

## 功能特性

- 📊 **图数据管理** - 支持节点和边的增删改查，批量数据导入导出
- 🔍 **中心度分析** - 提供5种核心中心度算法（度中心性、介数中心性、接近中心性、特征向量中心性、PageRank）
- 🏘️ **社区划分** - 基于Louvain算法的高效社区检测，支持模块度计算
- ⭐ **影响力分析** - 多维度影响力排名与算法对比分析
- 🎨 **图可视化** - 基于D3.js的力导向布局，支持交互探索
- ⏱️ **时间切片分析** - 按时间窗口分析网络演化动态
- 🔗 **关系类型过滤** - 按关系类型筛选子图，支持多条件组合
- 📈 **指标监控** - 实时计算图密度、平均度、聚类系数等全局指标
- 🔄 **最短路径** - 快速查找两节点间的最短路径

---

## 技术栈说明

### 后端技术栈
| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.9+ | 核心开发语言 |
| **Flask** | 3.0.0 | Web框架，提供RESTful API |
| **NetworkX** | 3.2.1 | 图论算法库，提供核心图分析能力 |
| **python-louvain** | 0.16 | Louvain社区检测算法实现 |
| **Neo4j** | 5.16.0 | 图数据库，持久化存储图数据 |
| **Pandas** | 2.1.4 | 数据处理与分析 |
| **NumPy** | 1.26.2 | 数值计算支持 |

### 前端技术栈
| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 18.2.0 | 前端框架 |
| **D3.js** | 7.8.5 | 数据可视化，力导向图渲染 |
| **Ant Design** | 5.12.0 | UI组件库 |
| **Vite** | 5.0.8 | 构建工具 |
| **Axios** | 1.6.2 | HTTP客户端 |
| **Day.js** | 1.11.10 | 时间处理 |

### 基础设施
- **Docker** - 容器化部署
- **docker-compose** - 服务编排

---

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端展示层                                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │  图可视化  │  │  控制面板  │  │  分析结果  │  │  数据上传  │  │
│  │  (D3.js)   │  │  (AntD)   │  │  展示面板  │  │  组件      │  │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  │  RESTful API (HTTP/JSON)
                                  │
┌─────────────────────────────────▼───────────────────────────────┐
│                         后端服务层                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                      API 路由层                           │    │
│  │  健康检查 | 图数据 | 社区检测 | 影响力 | 时间分析 | 过滤 │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                     业务逻辑层                            │    │
│  │  ┌──────────────────┐  ┌────────────────────────────┐    │    │
│  │  │  GraphAnalyzer   │  │     图算法引擎              │    │    │
│  │  │  ·中心度计算     │  │  ·NetworkX 图操作           │    │    │
│  │  │  ·Louvain社区    │  │  ·Louvain 社区划分          │    │    │
│  │  │  ·时间序列分析   │  │  ·最短路径算法              │    │    │
│  │  │  ·影响力对比     │  │  ·相关性分析                │    │    │
│  │  └──────────────────┘  └────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                     数据访问层                            │    │
│  │                Neo4j 数据库连接器                         │    │
│  │  ·Cypher查询构建  ·数据导入导出  ·事务管理  ·连接池      │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  │  Bolt协议 (bolt://localhost:7687)
                                  │
┌─────────────────────────────────▼───────────────────────────────┐
│                         数据存储层                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                      Neo4j 图数据库                       │    │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │    │
│  │  │   节点     │  │    边      │  │  索引/约束       │    │    │
│  │  │ User/Post  │  │ FOLLOW/LIKE│  │  时间戳索引      │    │    │
│  │  │  属性索引  │  │ COMMENT     │  │  关系类型索引    │    │    │
│  │  └────────────┘  └────────────┘  └──────────────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 架构说明

1. **前端展示层**：基于React构建的单页应用，使用D3.js实现力导向图可视化，Ant Design提供UI组件支持。主要功能包括图的交互浏览、分析参数配置、分析结果展示、数据上传等。

2. **后端服务层**：
   - **API路由层**：基于Flask Blueprint实现RESTful API，统一处理请求路由和参数校验
   - **业务逻辑层**：核心是`GraphAnalyzer`类，封装了所有图分析算法，包括中心度计算、社区检测、时间序列分析等
   - **数据访问层**：`Neo4jDatabase`类封装了Neo4j数据库操作，提供Cypher查询构建、数据导入导出、事务管理等功能

3. **数据存储层**：使用Neo4j图数据库存储节点和关系数据，支持丰富的图查询和图遍历操作。节点和关系上建立时间戳和关系类型索引，提升查询性能。

---

## 功能模块说明

### 1. 图数据管理

提供完整的图数据生命周期管理功能：
- **节点管理**：支持创建、删除、查询节点，节点可包含自定义属性（姓名、年龄、地区、职业等）
- **边管理**：支持创建、删除、查询关系边，边可携带权重、时间戳、内容等属性
- **批量导入**：支持JSON格式的批量数据导入，自动解析节点和边结构
- **数据清空**：一键清空数据库，便于测试和数据重置
- **邻居查询**：查询指定节点的所有直接邻居节点

### 2. 中心度分析

系统实现了5种经典的中心度算法，用于识别网络中的关键节点：

| 算法 | 说明 | 适用场景 |
|------|------|----------|
| **度中心性 (Degree)** | 节点连接的边数，反映节点的直接影响力 | 发现活跃节点、社交达人 |
| **介数中心性 (Betweenness)** | 节点出现在其他节点最短路径上的次数，反映节点的信息中介作用 | 发现信息传播关键节点、桥梁人物 |
| **接近中心性 (Closeness)** | 节点到其他所有节点的平均距离的倒数，反映节点的信息传播速度 | 发现信息扩散效率高的节点 |
| **特征向量中心性 (Eigenvector)** | 考虑邻居节点的影响力，连接到高影响力节点的节点得分更高 | 发现权威节点、意见领袖 |
| **PageRank** | 基于链接结构的排名算法，考虑链接质量 | 发现综合影响力高的节点 |

### 3. 社区划分

基于**Louvain算法**实现高效的社区检测：
- 采用贪心优化策略最大化模块度（Modularity）
- 支持层次化社区发现，自动确定最优社区数量
- 返回每个社区的节点列表、大小和全局模块度
- 模块度范围：[-1, 1]，值越高表示社区结构越显著
- 可用于发现社交圈、兴趣群体、团队结构等

### 4. 影响力分析

提供多维度的影响力评估与对比：
- **单算法排名**：支持选择任意中心度算法进行影响力排名
- **多算法对比**：同时计算5种算法的排名结果，进行横向对比
- **相关性分析**：计算不同算法排名之间的皮尔逊相关系数
- **Top节点分析**：展示各算法排名前5的关键节点
- **排名一致性**：分析不同算法在Top10节点上的重叠度

### 5. 图可视化

基于D3.js实现交互式力导向图可视化：
- **力导向布局**：节点自动排布，边根据权重调整长度
- **社区着色**：不同社区的节点使用不同颜色标识
- **节点大小**：根据中心度得分动态调整节点大小
- **交互操作**：支持拖拽节点、缩放画布、悬停查看详情
- **关系展示**：不同类型的关系使用不同颜色和线型
- **点击高亮**：点击节点高亮显示其邻居和连接关系

### 6. 时间切片分析

支持按时间维度分析网络演化：
- **时间窗口划分**：将时间轴等分为多个窗口（默认10个）
- **窗口内分析**：每个窗口独立计算网络指标、社区结构
- **演化追踪**：追踪社区随时间的变化（新增、消失、合并、分裂）
- **节点动态**：记录每个时间窗口的新增节点和消失节点
- **趋势展示**：展示节点数、边数、社区数等指标的变化趋势

### 7. 关系类型过滤

支持灵活的子图筛选功能：
- **按关系类型过滤**：可选择一种或多种关系类型（FOLLOW、LIKE、COMMENT等）
- **按时间范围过滤**：指定开始和结束时间，筛选该时间段内的边
- **组合过滤**：支持关系类型和时间范围的组合筛选
- **实时分析**：过滤后的子图自动重新计算所有指标和社区

---

## 快速开始指南

### 环境要求

- Python 3.9+
- Node.js 16+
- Docker & docker-compose（推荐使用容器化部署）
- Neo4j 5.x（可使用Docker启动）

### 方式一：Docker快速启动（推荐）

1. **克隆项目**
```bash
git clone <repository-url>
cd 346
```

2. **启动所有服务**
```bash
docker-compose up -d
```

3. **验证启动**
- 前端地址：http://localhost:5173
- 后端API：http://localhost:5000
- Neo4j控制台：http://localhost:7474

4. **导入示例数据**
```bash
# 使用API导入
curl -X POST http://localhost:5000/api/import \
  -H "Content-Type: application/json" \
  -d @data/sample_social_relations.json
```

### 方式二：手动启动

#### 步骤1：启动Neo4j数据库

```bash
# 使用Docker启动Neo4j
docker run -d \
  --name neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.16.0
```

等待约30秒，访问 http://localhost:7474 确认Neo4j已启动。

#### 步骤2：配置环境变量

在 `backend` 目录下创建 `.env` 文件：
```env
SECRET_KEY=your-secret-key-here
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
DEBUG=True
```

#### 步骤3：启动后端服务

```bash
cd backend

# 创建虚拟环境
python -m venv venv

# Windows激活虚拟环境
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python run.py
```

后端服务将在 http://localhost:5000 启动。

#### 步骤4：启动前端服务

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务将在 http://localhost:5173 启动。

#### 步骤5：导入示例数据

通过前端的「数据上传」组件导入 `data/sample_social_relations.json` 文件，或使用API：

```bash
curl -X POST http://localhost:5000/api/import \
  -H "Content-Type: application/json" \
  -d @data/sample_social_relations.json
```

### 验证安装

1. 健康检查
```bash
curl http://localhost:5000/api/health
```

预期输出：
```json
{
  "status": "healthy",
  "database": true
}
```

2. 获取图数据
```bash
curl http://localhost:5000/api/graph
```

---

## API文档

所有API前缀为 `/api`

### 1. 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 检查服务健康状态 |

**响应示例：**
```json
{
  "status": "healthy",
  "database": true
}
```

---

### 2. 图数据接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/graph` | 获取完整图数据及全局指标 |
| `GET` | `/graph/metrics` | 获取图全局指标 |
| `GET` | `/graph/filtered` | 获取筛选后的图数据 |
| `GET` | `/graph/communities` | 获取社区划分结果 |
| `GET` | `/graph/influence` | 获取影响力排名 |
| `GET` | `/graph/influence/comparison` | 获取多算法影响力对比 |
| `GET` | `/graph/temporal` | 获取时间切片分析结果 |
| `GET` | `/graph/relationship-types` | 获取所有关系类型 |
| `GET` | `/graph/path` | 获取最短路径 |

#### 2.1 获取完整图数据

```
GET /api/graph?limit=1000
```

**查询参数：**
- `limit` (可选)：返回边的最大数量，默认1000

**响应示例：**
```json
{
  "nodes": [...],
  "edges": [...],
  "metrics": {
    "node_count": 20,
    "edge_count": 94,
    "density": 0.4947,
    "average_degree": 9.4,
    "max_degree": 14,
    "is_connected": true,
    "average_shortest_path": 1.5053,
    "diameter": 3,
    "clustering_coefficient": 0.7215
  }
}
```

#### 2.2 获取社区划分

```
GET /api/graph/communities
```

**响应示例：**
```json
[
  {
    "id": 0,
    "nodes": ["1", "8", "16", "11", "6", "4"],
    "size": 6,
    "modularity": 0.4128
  },
  {
    "id": 1,
    "nodes": ["2", "9", "15", "7", "14"],
    "size": 5,
    "modularity": 0.4128
  }
]
```

#### 2.3 获取影响力排名

```
GET /api/graph/influence?method=pagerank
```

**查询参数：**
- `method` (可选)：影响力算法，可选值 `degree`、`betweenness`、`closeness`、`eigenvector`、`pagerank`，默认 `degree`

**响应示例：**
```json
[
  {"node_id": "8", "score": 0.0892, "rank": 1},
  {"node_id": "1", "score": 0.0815, "rank": 2},
  {"node_id": "11", "score": 0.0789, "rank": 3}
]
```

#### 2.4 获取时间切片分析

```
GET /api/graph/temporal?start_time=1714531200000&end_time=1735785600000&time_windows=10
```

**查询参数：**
- `start_time` (可选)：开始时间戳（毫秒）
- `end_time` (可选)：结束时间戳（毫秒）
- `time_windows` (可选)：时间窗口数量，默认10，最小2

#### 2.5 获取筛选后的图数据

```
GET /api/graph/filtered?relationship_types=FOLLOW&relationship_types=LIKE&start_time=1714531200000&limit=500
```

**查询参数：**
- `relationship_types` (可选)：关系类型，可多次指定
- `start_time` (可选)：开始时间戳
- `end_time` (可选)：结束时间戳
- `limit` (可选)：返回边的最大数量

#### 2.6 获取最短路径

```
GET /api/graph/path?source=1&target=20
```

**查询参数：**
- `source` (必需)：起始节点ID
- `target` (必需)：目标节点ID

**响应示例：**
```json
{
  "path": ["1", "5", "18", "20"],
  "graph": {
    "nodes": [...],
    "edges": [...]
  }
}
```

---

### 3. 节点管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/nodes` | 创建新节点 |
| `DELETE` | `/nodes/<node_id>` | 删除节点 |
| `GET` | `/nodes/<node_id>/neighbors` | 获取节点的邻居 |

#### 3.1 创建节点

```
POST /api/nodes
Content-Type: application/json

{
  "label": "User",
  "properties": {
    "name": "张三",
    "age": 28,
    "location": "北京"
  }
}
```

#### 3.2 获取邻居

```
GET /api/nodes/1/neighbors
```

---

### 4. 边管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/edges` | 创建新边 |

#### 4.1 创建边

```
POST /api/edges
Content-Type: application/json

{
  "source": "1",
  "target": "2",
  "type": "FOLLOW",
  "properties": {
    "weight": 1,
    "timestamp": 1714531200000
  }
}
```

---

### 5. 数据导入接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/import` | 批量导入图数据 |
| `DELETE` | `/clear` | 清空数据库 |

#### 5.1 批量导入

```
POST /api/import
Content-Type: application/json

{
  "nodes": [
    {"id": "1", "label": "User", "name": "张三", "age": 28}
  ],
  "edges": [
    {"source": "1", "target": "2", "type": "FOLLOW", "weight": 1}
  ]
}
```

---

## 数据格式说明

### 节点格式

```json
{
  "id": "1",
  "label": "User",
  "name": "张三",
  "age": 28,
  "gender": "男",
  "location": "北京",
  "occupation": "软件工程师"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 节点唯一标识 |
| `label` | string | 节点类型标签，如 User、Post 等 |
| `*` | any | 其他自定义属性，可任意扩展 |

### 边格式

```json
{
  "source": "1",
  "target": "2",
  "type": "FOLLOW",
  "weight": 5,
  "timestamp": 1714531200000,
  "content": "这个技术方案设计得很严谨"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `source` | string | 源节点ID |
| `target` | string | 目标节点ID |
| `type` | string | 关系类型，如 FOLLOW、LIKE、COMMENT |
| `weight` | number | 边的权重，默认为1 |
| `timestamp` | number | 时间戳（毫秒），用于时间分析 |
| `content` | string | 可选，评论内容等 |
| `*` | any | 其他自定义属性 |

### 完整数据文件格式

```json
{
  "nodes": [
    {"id": "1", "label": "User", "name": "张三", ...},
    {"id": "2", "label": "User", "name": "李四", ...}
  ],
  "edges": [
    {"source": "1", "target": "2", "type": "FOLLOW", "weight": 1, "timestamp": 1714531200000},
    {"source": "1", "target": "2", "type": "LIKE", "weight": 5, "timestamp": 1717209600000}
  ]
}
```

### 关系类型说明

| 类型 | 说明 | 方向性 | 权重含义 |
|------|------|--------|----------|
| `FOLLOW` | 关注关系 | 单向 | 关注强度 |
| `LIKE` | 点赞关系 | 单向 | 点赞频率/重要度 |
| `COMMENT` | 评论关系 | 单向 | 评论互动深度 |
| `FRIEND` | 好友关系 | 双向 | 亲密程度 |
| `COLLEAGUE` | 同事关系 | 双向 | 工作关联度 |

### 示例数据说明

`data/sample_social_relations.json` 包含：
- **20个用户节点**：覆盖北京、上海、深圳、杭州、广州、成都6个城市
- **94条边**：
  - 32条 FOLLOW（关注）关系
  - 30条 LIKE（点赞）关系
  - 32条 COMMENT（评论）关系
- **时间跨度**：2024年5月 - 2025年6月（12个月）
- **社区结构**：
  - 技术社区（6人）：软件工程师、后端开发、全栈开发、架构师、技术总监、数据分析师
  - 产品设计社区（5人）：产品经理、UI设计师、算法工程师、前端开发、HR经理
  - 运营市场社区（6人）：设计师、运营经理、市场专员、内容运营、销售经理、用户研究
  - 其他（3人）：项目经理、测试工程师、实习生

---

## 常见问题解答

### Q1: 启动后端时提示无法连接Neo4j？

**A:** 请检查：
1. Neo4j服务是否已启动：`docker ps` 查看容器状态
2. 端口7687是否被占用：`netstat -ano | findstr 7687`
3. 配置文件中的连接信息是否正确
4. 等待Neo4j完全启动（通常需要20-30秒）

### Q2: 导入数据后前端不显示？

**A:** 请尝试：
1. 刷新前端页面
2. 检查浏览器控制台是否有报错
3. 调用 `/api/graph` 接口确认数据已导入
4. 检查Neo4j中是否有数据：访问 http://localhost:7474 执行 `MATCH (n) RETURN count(n)`

### Q3: PageRank计算报错？

**A:** PageRank要求图是强连通的。如果图中存在孤立节点或不连通分量：
1. 确保数据中没有孤立节点
2. 尝试使用其他中心度算法（如degree）
3. 检查边数据是否正确连接了所有节点

### Q4: 如何修改默认端口？

**A:** 
- 后端：修改 `backend/run.py` 中的端口配置
- 前端：修改 `frontend/vite.config.js` 中的 server.port
- Neo4j：修改 `docker-compose.yml` 中的端口映射

### Q5: 如何扩展支持更多关系类型？

**A:** 
1. 在导入数据时直接使用新的关系类型字符串即可
2. 前端会自动识别并显示新的关系类型
3. 过滤组件会自动添加新类型到选项中
4. 无需修改后端代码，系统动态支持任意关系类型

### Q6: 大数据量下性能如何优化？

**A:** 
1. 在Neo4j中为常用查询字段建立索引：
   ```cypher
   CREATE INDEX FOR (n:User) ON (n.location)
   CREATE INDEX FOR ()-[r:FOLLOW]-() ON (r.timestamp)
   ```
2. 前端可视化时使用 `limit` 参数限制显示边数
3. 时间分析时适当减少 `time_windows` 数量
4. 考虑使用Neo4j的Graph Data Science库进行大规模计算

### Q7: 如何导出分析结果？

**A:** 
- 所有API返回JSON格式数据，可直接保存
- 前端可通过浏览器开发者工具复制响应
- 图数据可从Neo4j导出为CSV或JSON格式
- 建议编写脚本定期备份重要分析结果

### Q8: 支持有向图分析吗？

**A:** 当前版本主要针对无向图进行分析。如果需要有向图分析：
1. 数据导入时保留方向信息
2. 修改 `GraphAnalyzer._build_graph` 使用 `nx.DiGraph()`
3. 相应算法需要调整为有向图版本

---

## 目录结构说明

```
346/
├── backend/                          # 后端服务
│   ├── app/
│   │   ├── analysis/
│   │   │   └── __init__.py          # 图分析算法核心（GraphAnalyzer类）
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py            # API路由定义
│   │   ├── database/
│   │   │   └── __init__.py          # Neo4j数据库连接器
│   │   ├── models/
│   │   │   └── __init__.py          # 数据模型定义（Node, Edge, GraphData等）
│   │   ├── utils/
│   │   │   └── __init__.py          # 工具函数
│   │   └── __init__.py              # Flask应用创建
│   ├── config.py                    # 配置文件
│   ├── requirements.txt             # Python依赖
│   └── run.py                       # 启动入口
├── data/                             # 示例数据
│   ├── sample_users.json            # 15个用户示例数据
│   ├── sample_relations.json        # 图关系示例数据
│   └── sample_social_relations.json # 20用户94边完整社交数据
├── frontend/                         # 前端应用
│   ├── src/
│   │   ├── components/              # React组件
│   │   │   ├── GraphVisualization.jsx    # 图可视化组件（D3.js）
│   │   │   ├── CommunityPanel.jsx        # 社区展示面板
│   │   │   ├── InfluencePanel.jsx        # 影响力分析面板
│   │   │   ├── InfluenceComparison.jsx   # 多算法对比面板
│   │   │   ├── TemporalAnalysis.jsx      # 时间分析面板
│   │   │   ├── TimeSlider.jsx            # 时间滑块组件
│   │   │   ├── RelationshipFilter.jsx    # 关系类型过滤
│   │   │   └── DataUpload.jsx            # 数据上传组件
│   │   ├── services/
│   │   │   └── api.js               # API请求封装
│   │   ├── styles/
│   │   │   └── global.css           # 全局样式
│   │   ├── utils/
│   │   │   └── graphUtils.js        # 图处理工具函数
│   │   ├── App.jsx                  # 根组件
│   │   └── main.jsx                 # 入口文件
│   ├── index.html
│   ├── package.json
│   └── vite.config.js               # Vite配置
├── .gitignore
├── docker-compose.yml               # Docker编排配置
└── README.md                        # 项目文档（本文件）
```

---

## 许可证

MIT License

---

## 联系方式

如有问题或建议，欢迎提交Issue或PR。
