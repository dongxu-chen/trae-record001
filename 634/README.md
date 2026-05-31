# 新闻话题演化追踪系统

一个基于Python + 在线聚类 + 话题模型 + Neo4j + WebSocket + React的新闻话题演化追踪系统。

## 功能特性

- 📰 **实时话题检测**：从新闻流中实时检测新话题
- 📊 **话题聚类**：基于文本相似度的在线聚类算法
- 📈 **影响力计算**：五维度影响力评估（传播度、参与度、速度、动量、社交热度）
- 🔄 **生命周期追踪**：萌芽→成长→爆发→衰退→稳定的全生命周期追踪
- 🗺️ **演化路径可视化**：基于Neo4j的话题演化图谱
- ⚡ **实时推送**：WebSocket实时推送话题更新和新闻流
- 🔥 **爆发检测**：自动识别快速增长的爆发话题
- ⚠️ **话题预警**：6种信号综合检测，爆发初期提前预警
- 🔍 **传播溯源**：识别引爆点源头，构建完整传播路径
- 📊 **话题对比**：多话题生命周期对比分析
- 📈 **平滑动画**：6种节点和边的过渡动画
- 🔄 **增量更新**：版本号追踪，仅推送差异数据
- 🎯 **自适应聚类**：根据话题规模、密度、生命周期动态调整阈值

## 技术栈

### 后端
- **FastAPI**: Web API框架
- **Neo4j**: 图数据库，存储话题和演化关系
- **scikit-learn**: 机器学习工具库
- **sentence-transformers**: 文本向量化模型
- **jieba**: 中文分词
- **WebSocket**: 实时通信

### 前端
- **React 18**: UI框架
- **Material-UI**: 组件库
- **vis-network**: 图谱可视化
- **Recharts**: 图表库
- **Axios**: HTTP客户端

## 快速开始

### 前置要求

- Python 3.8+
- Node.js 16+
- Neo4j 4.x/5.x

### 1. 启动Neo4j数据库

使用Docker启动（推荐）：

```bash
docker-compose up -d neo4j
```

或手动安装Neo4j后，创建环境变量：
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### 2. 启动后端服务

```bash
cd backend

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

后端API将在 http://localhost:8000 启动

API文档: http://localhost:8000/docs

### 3. 启动前端服务

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm start
```

前端将在 http://localhost:3000 启动

### 使用Docker Compose一键启动

```bash
docker-compose up -d
```

## 系统架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   新闻数据流    │────▶│  在线聚类引擎   │────▶│  Neo4j数据库    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                 │                       │
                                 ▼                       ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │  影响力计算器   │     │  演化追踪器     │
                        └─────────────────┘     └─────────────────┘
                                 │                       │
                                 └───────────┬───────────┘
                                             ▼
                                    ┌─────────────────┐
                                    │  WebSocket服务  │
                                    └─────────────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │   React前端     │
                                    └─────────────────┘
```

## 核心模块说明

### 1. 文本向量化 (text_embedding.py)
- 使用Sentence-Transformers生成文本嵌入
- TF-IDF提取关键词
- 支持中英文双语处理

### 2. 在线聚类 (online_clustering.py)
- 基于余弦相似度的增量聚类
- 动态更新话题质心
- 自动合并相似话题
- 话题生命周期状态管理

### 3. 影响力计算 (influence_calculator.py)
- **传播度(Reach)**: 话题覆盖的文章数量
- **参与度(Engagement)**: 单位时间内的增长速率
- **速度(Velocity)**: 话题增长速度
- **动量(Momentum)**: 增长趋势变化

### 4. 演化追踪 (topic_evolution.py)
- 检测话题间的演化关系
- 分类：growth, shrink, continuation, split, merge, emergence
- 构建演化路径链

### 5. 数据存储 (neo4j_store.py)
- Topic节点：存储话题信息
- Article节点：存储新闻文章
- BELONGS_TO关系：文章-话题归属
- EVOLVES_TO关系：话题间演化关系

## API接口

### 新闻相关
- `POST /api/news` - 提交新闻文章
- `POST /api/mock/generate` - 生成模拟新闻

### 话题相关
- `GET /api/topics` - 获取话题列表
- `GET /api/topics/{topic_id}` - 获取话题详情
- `GET /api/topics/{topic_id}/articles` - 获取话题相关文章
- `GET /api/bursting` - 获取爆发话题

### 演化相关
- `GET /api/evolution/graph` - 获取演化图谱
- `GET /api/evolution/chain/{topic_id}` - 获取话题演化链

### WebSocket
- `ws://localhost:8000/ws` - 实时消息推送
  - `topic_update`: 话题更新事件
  - `evolution`: 话题演化事件
  - `new_article`: 新文章事件

## 使用说明

1. **启动系统**：按照快速开始步骤启动所有服务
2. **生成测试数据**：点击前端顶部"生成模拟数据"按钮
3. **查看话题**：在"话题列表"页查看所有检测到的话题
4. **查看演化**：在"演化图谱"页查看话题间的演化关系
5. **查看详情**：点击话题查看详细信息和影响力指标
6. **实时监控**：在"实时动态"页查看新闻流

## 话题生命周期

| 阶段 | 描述 | 颜色 |
|------|------|------|
| 萌芽 (Emerging) | 新创建的小话题 | 绿色 |
| 成长 (Growing) | 稳定增长的话题 | 蓝色 |
| 爆发 (Bursting) | 快速增长的热门话题 | 红色 |
| 衰退 (Declining) | 增长放缓的话题 | 橙色 |
| 稳定 (Stable) | 趋于稳定的话题 | 灰色 |

## 配置说明

主要配置项在 `backend/config.py`：

```python
# 基础配置
CLUSTER_THRESHOLD = 0.75      # 聚类相似度阈值
MIN_CLUSTER_SIZE = 3          # 最小话题大小
NEWS_BATCH_SIZE = 50          # 批处理大小
BURST_THRESHOLD = 2.0         # 爆发检测阈值
INFLUENCE_DECAY = 0.95        # 影响力衰减系数

# 自适应阈值配置
ADAPTIVE_THRESHOLD_ENABLED: bool = True
ADAPTIVE_THRESHOLD_MIN: float = 0.65
ADAPTIVE_THRESHOLD_MAX: float = 0.85
ADAPTIVE_SIZE_WEIGHT: float = 0.3
ADAPTIVE_DENSITY_WEIGHT: float = 0.4
ADAPTIVE_LIFECYCLE_WEIGHT: float = 0.3

# 影响力权重配置
SHARE_WEIGHT: float = 0.25
REACH_WEIGHT: float = 0.25
ENGAGEMENT_WEIGHT: float = 0.2
VELOCITY_WEIGHT: float = 0.15
MOMENTUM_WEIGHT: float = 0.15
```

## 自适应阈值算法

聚类阈值根据以下因素动态计算：

1. **话题规模因子**：话题越大，阈值越高（防止过大话题吞并其他）
2. **内聚密度因子**：话题内文章相似度越高，阈值越高（高质量话题更独立）
3. **生命周期因子**：越成熟的话题（衰退>稳定>爆发>成长>萌芽），阈值越高

最终阈值公式：
```
adjustment = size_factor * 0.3 + density_factor * 0.4 + lifecycle_factor * 0.3
threshold = MIN + adjustment * (MAX - MIN)
```

## 社交热度计算

社交热度（Share Score）综合考虑：
- 平均转发量（权重50%）
- 平均点赞量（权重30%）
- 平均评论量（权重20%）

并叠加社交指标增速因子，反映近期热度变化趋势。

## 增量更新机制

系统使用版本号追踪节点和边的变更：
- 每次变更时版本号+1
- 仅推送有差异的数据（新增/更新/删除）
- 前端使用requestAnimationFrame实现60fps平滑动画

## 项目结构

```
.
├── backend/
│   ├── main.py                 # FastAPI主应用
│   ├── config.py               # 配置文件
│   ├── models.py               # 数据模型
│   ├── text_embedding.py       # 文本向量化
│   ├── online_clustering.py    # 在线聚类
│   ├── influence_calculator.py # 影响力计算
│   ├── topic_evolution.py      # 演化追踪
│   ├── neo4j_store.py          # Neo4j存储
│   ├── websocket_server.py     # WebSocket服务
│   ├── news_stream_processor.py# 新闻流处理器
│   ├── topic_warning.py        # 话题预警系统
│   ├── propagation_tracker.py  # 传播路径溯源
│   ├── topic_comparison.py     # 话题对比引擎
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/         # React组件
│   │   │   ├── TopicWarnings.js  # 话题预警组件
│   │   │   ├── PropagationTracker.js # 传播溯源组件
│   │   │   ├── TopicComparison.js  # 话题对比组件
│   │   │   └── ...
│   │   ├── services/           # API和WebSocket服务
│   │   ├── App.js
│   │   └── index.js
│   ├── public/
│   └── package.json
├── docker-compose.yml
└── README.md
```

## 许可证

MIT License
