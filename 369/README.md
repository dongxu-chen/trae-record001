# 召回率分析平台 (Recall Analysis Platform)

一个功能完整的搜索召回率评估平台，支持搜索召回率评估、命中率分析、Top-K准确率计算，提供用户人工标注相关文档功能，以及混淆矩阵、多模型对比曲线、失败案例分析等可视化分析。

## 技术栈

### 后端
- **Python 3.9+**
- **FastAPI** - 高性能 Web 框架
- **Elasticsearch 8.x** - 搜索引擎和数据存储
- **pydantic** - 数据验证
- **numpy, pandas, scikit-learn** - 科学计算和指标计算
- **httpx** - 异步 HTTP 客户端

### 前端
- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **Ant Design 5** - UI 组件库
- **ECharts** - 图表可视化
- **React Router** - 路由管理
- **Axios** - HTTP 客户端
- **Day.js** - 日期处理

## 功能特性

### 1. 核心评估指标
- **召回率 (Recall@K)** - 检索到的相关文档占总相关文档的比例
- **精确率 (Precision@K)** - 检索结果中相关文档的比例
- **F1 Score** - 召回率和精确率的调和平均
- **命中率 (Hit Rate)** - 至少有一个相关文档被检索到的查询比例
- **MRR (Mean Reciprocal Rank)** - 第一个相关文档排名的倒数的平均值
- **NDCG (Normalized Discounted Cumulative Gain)** - 考虑排序位置的综合指标
- **MAP (Mean Average Precision)** - 平均准确率的平均值

### 2. 人工标注系统
- 支持为查询-文档对标注相关性等级（0-3级）
- 0=不相关, 1=一般相关, 2=相关, 3=高度相关
- 批量标注功能
- 标注历史记录管理

### 3. 混淆矩阵分析
- TP (真阳性): 正确预测为相关
- FP (假阳性): 错误预测为相关
- FN (假阴性): 错误预测为不相关
- TN (真阴性): 正确预测为不相关
- 准确率、精确率、召回率、F1、特异性计算
- 可视化饼图和柱状图展示

### 4. 多模型对比
- 支持多个检索模型的横向对比
- 折线图展示各指标随 K 值变化趋势
- 雷达图展示综合指标对比
- 自动识别最优模型

### 5. 失败案例分析
- 自动识别召回率低于阈值的查询
- 分析遗漏的相关文档
- 分析错误返回的不相关文档
- 召回率分布图和错误类型分布
- 详细的案例详情展示

### 6. 数据管理
- 文档库管理（增删查）
- 查询集管理
- 标注数据管理
- 检索模型配置管理

## 项目结构

```
369/
├── backend/                 # 后端代码
│   ├── main.py             # FastAPI 主应用
│   ├── config.py           # 配置文件
│   ├── es_client.py        # Elasticsearch 客户端
│   ├── schemas.py          # Pydantic 数据模型
│   ├── metrics.py          # 评估指标计算
│   ├── sample_data.py      # 示例数据导入脚本
│   ├── requirements.txt    # Python 依赖
│   └── .env.example        # 环境变量示例
└── frontend/               # 前端代码
    ├── src/
    │   ├── pages/          # 页面组件
    │   │   ├── Dashboard.tsx
    │   │   ├── SearchEvaluation.tsx
    │   │   ├── Annotation.tsx
    │   │   ├── ConfusionMatrixPage.tsx
    │   │   ├── ModelComparison.tsx
    │   │   ├── FailureCases.tsx
    │   │   └── DataManagement.tsx
    │   ├── services/       # API 服务
    │   │   └── api.ts
    │   ├── types/          # TypeScript 类型定义
    │   │   └── index.ts
    │   ├── App.tsx         # 主应用组件
    │   ├── main.tsx        # 入口文件
    │   └── index.css       # 全局样式
    ├── package.json        # npm 依赖
    ├── tsconfig.json       # TypeScript 配置
    └── vite.config.ts      # Vite 配置
```

## 快速开始

### 前置要求

1. **Elasticsearch 8.x** - 确保 Elasticsearch 已安装并运行
   - 默认地址: `http://localhost:9200`
   - 默认用户名: `elastic`
   - 默认密码: `changeme`

2. **Python 3.9+**

3. **Node.js 18+** 和 **npm**

### 步骤 1: 启动 Elasticsearch

如果使用 Docker:
```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

验证 Elasticsearch 运行:
```bash
curl http://localhost:9200
```

### 步骤 2: 启动后端服务

```bash
# 进入后端目录
cd backend

# 创建虚拟环境 (可选)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 复制环境变量配置
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# 根据需要修改 .env 配置

# 启动后端服务
python main.py
```

后端服务将在 `http://localhost:8000` 启动

API 文档地址:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

健康检查:
```bash
curl http://localhost:8000/api/health
```

### 步骤 3: 导入示例数据 (可选)

```bash
# 在 backend 目录下
python sample_data.py
```

这将导入:
- 15 个示例文档（技术书籍相关）
- 7 个示例查询
- 17 个示例标注

### 步骤 4: 启动前端服务

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务将在 `http://localhost:5173` 启动

### 步骤 5: 访问应用

打开浏览器访问 `http://localhost:5173`

## API 接口列表

### 文档管理
- `POST /api/documents` - 创建文档
- `POST /api/documents/batch` - 批量创建文档
- `GET /api/documents` - 获取文档列表
- `GET /api/documents/{doc_id}` - 获取单个文档

### 查询管理
- `POST /api/queries` - 创建查询
- `POST /api/queries/batch` - 批量创建查询
- `GET /api/queries` - 获取查询列表

### 标注管理
- `POST /api/annotations` - 创建标注
- `POST /api/annotations/batch` - 批量创建标注
- `GET /api/annotations` - 获取标注列表
- `GET /api/annotations/query/{query_id}` - 获取查询的标注

### 搜索与评估
- `POST /api/search` - 执行搜索
- `POST /api/evaluate` - 搜索并评估
- `GET /api/evaluate/batch` - 批量评估所有查询

### 分析接口
- `GET /api/confusion-matrix` - 获取混淆矩阵
- `GET /api/model-comparison` - 多模型对比
- `GET /api/failure-cases` - 获取失败案例
- `GET /api/evaluations` - 获取评估历史

### 其他
- `GET /api/stats` - 获取统计数据
- `GET /api/models` - 获取模型列表
- `POST /api/models` - 创建模型
- `GET /api/health` - 健康检查

## 使用流程

### 典型工作流

1. **数据准备**
   - 在「数据管理」页面导入文档库
   - 导入评估查询集

2. **人工标注**
   - 在「人工标注」页面选择查询
   - 为搜索结果标注相关性等级
   - 保存标注数据

3. **搜索评估**
   - 在「搜索评估」页面输入查询
   - 选择模型和 K 值
   - 查看评估指标和搜索结果

4. **分析优化**
   - 在「混淆矩阵」页面查看分类效果
   - 在「模型对比」页面比较不同模型
   - 在「失败案例」页面分析问题查询
   - 根据分析结果优化检索模型

## 核心算法说明

### DCG (Discounted Cumulative Gain)
DCG 考虑了相关文档的排序位置，位置越靠前权重越高：
```
DCG = sum(rel_i / log2(i + 2))
```

### NDCG (Normalized DCG)
将 DCG 归一化到 [0, 1] 区间：
```
NDCG = DCG / IDCG
```
其中 IDCG 是理想情况下的 DCG（按相关性降序排列）。

### MRR (Mean Reciprocal Rank)
第一个相关文档的排名的倒数的平均值：
```
MRR = mean(1 / rank_i)
```

### MAP (Mean Average Precision)
每个查询的平均准确率的平均值：
```
AP = sum(P@k * rel_k) / total_relevant
MAP = mean(AP_i)
```

## 扩展开发

### 添加新的评估指标
在 `backend/metrics.py` 中添加新的指标计算函数，然后在 `schemas.py` 中更新 `EvaluationMetrics` 模型。

### 集成新的检索模型
1. 在前端「数据管理」-「模型管理」中添加模型配置
2. 修改 `backend/main.py` 中的 `search` 函数，根据 `model_name` 调用不同的检索接口

### 自定义数据格式
修改 `backend/schemas.py` 中的 Pydantic 模型来支持自定义字段。

## 常见问题

### 1. Elasticsearch 连接失败
- 检查 Elasticsearch 是否启动
- 检查 `.env` 中的连接配置
- 确保防火墙允许 9200 端口访问

### 2. 前端无法连接后端
- 检查后端是否在 8000 端口运行
- 检查 `frontend/vite.config.ts` 中的代理配置
- 查看浏览器控制台是否有 CORS 错误

### 3. 评估结果都是 0
- 确保已经为查询创建了标注数据
- 检查查询文本是否能匹配到相关文档
- 确认 Elasticsearch 索引中存在数据

### 4. 如何清空数据重新开始
```bash
# 删除 Elasticsearch 索引
curl -X DELETE http://localhost:9200/documents
curl -X DELETE http://localhost:9200/queries
curl -X DELETE http://localhost:9200/annotations
curl -X DELETE http://localhost:9200/evaluations
curl -X DELETE http://localhost:9200/models

# 重启后端服务（会自动重新创建索引）
```

## 生产部署

### 后端部署
```bash
# 使用 uvicorn 生产模式
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# 或使用 gunicorn
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 前端部署
```bash
# 构建生产版本
npm run build

# 使用 nginx 或其他静态文件服务器托管 dist 目录
```

## License

MIT License
