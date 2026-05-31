# 法律文书相似案例检索系统

基于 Python + BERT + 法律知识图谱 + Elasticsearch + React 实现的法律文书相似案例检索系统。

## 功能特性

- **案情描述输入**: 支持用户输入详细的案件描述
- **相似案例检索**: 基于 BERT 语义相似度算法检索相似判例
- **相似度排序**: 按综合相似度对案例进行排序展示
- **差异点分析**: 自动识别并展示本案与判例的关键差异
- **法律实体识别**: 自动识别原告、被告、金额、日期、证据等法律实体
- **裁判要点抽取**: 自动提取案件的核心裁判要点
- **引用法条推荐**: 基于法律知识图谱推荐相关法条

## 技术栈

### 后端
- **Python 3.8+**
- **FastAPI**: Web 框架
- **BERT (Sentence-Transformers)**: 语义向量模型
- **Elasticsearch**: 向量搜索引擎（可选，支持模拟模式）
- **NetworkX**: 知识图谱构建
- **jieba**: 中文分词

### 前端
- **React 18**
- **Material-UI (MUI)**: UI 组件库
- **Axios**: HTTP 客户端
- **React Router**: 路由管理

## 项目结构

```
legal-case-search/
├── backend/                 # 后端服务
│   ├── app.py              # FastAPI 主应用
│   ├── config.py           # 配置文件
│   ├── nlp_processor.py    # NLP 处理模块
│   ├── es_searcher.py      # Elasticsearch 搜索模块
│   ├── knowledge_graph.py  # 法律知识图谱模块
│   ├── similarity_calculator.py  # 相似度计算模块
│   ├── sample_data.py      # 示例数据
│   └── requirements.txt    # Python 依赖
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── components/     # React 组件
│   │   ├── pages/          # 页面组件
│   │   ├── services/       # API 服务
│   │   ├── App.js
│   │   └── index.js
│   ├── public/
│   └── package.json        # Node.js 依赖
└── README.md
```

## 快速开始

### 后端启动

1. 进入后端目录:
```bash
cd backend
```

2. 创建虚拟环境并安装依赖:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

3. 启动后端服务:
```bash
python app.py
```

后端服务将在 `http://localhost:8000` 启动

API 文档: `http://localhost:8000/docs`

### 前端启动

1. 进入前端目录:
```bash
cd frontend
```

2. 安装依赖:
```bash
npm install
```

3. 启动前端开发服务器:
```bash
npm start
```

前端应用将在 `http://localhost:3000` 启动

## 使用说明

1. 在搜索框中输入案情描述，或点击示例按钮快速填充
2. 选择案件类型（可选）
3. 点击"检索相似案例"按钮
4. 查看：
   - 本案的案情分析结果（实体识别、裁判要点）
   - 推荐的相关法条
   - 相似案例列表，按相似度排序
   - 每个案例的详细信息及与本案的差异分析
5. 点击"查看详情"可查看完整案例信息

## 系统架构

### 1. NLP 处理模块
- 基于正则表达式和规则匹配实现法律实体识别
- 支持原告、被告、金额、日期、证据、法条等实体类型
- 自动提取裁判要点和关键词
- 生成案件摘要

### 2. 相似度计算
- **语义相似度**: BERT 向量余弦相似度 (40%)
- **案件类型相似度**: 类型匹配度 (15%)
- **裁判要点相似度**: Jaccard 相似度 (25%)
- **法律实体相似度**: 实体重叠度 (20%)

### 3. 法律知识图谱
- 基于 NetworkX 构建有向图
- 节点类型: 案件类型、法条
- 关系类型: 适用、关联
- 支持法条推荐和关联查询

### 4. 搜索引擎
- 支持 Elasticsearch 向量搜索
- 提供模拟数据模式（无需安装 Elasticsearch）
- 支持按案件类型过滤

## 示例数据

系统内置 8 个示例案例，涵盖：
- 民间借贷纠纷 (4例)
- 合同纠纷 (1例)
- 买卖合同纠纷 (1例)
- 租赁合同纠纷 (1例)
- 劳动争议 (1例)

## Elasticsearch 配置（可选）

如需使用真实 Elasticsearch 服务:

1. 安装并启动 Elasticsearch 8.x
2. 确保服务运行在 `localhost:9200`
3. 系统会自动检测并使用 Elasticsearch
4. 如需修改配置，编辑 `backend/config.py`

## API 接口

### POST /api/search
检索相似案例

请求体:
```json
{
  "description": "案情描述...",
  "top_k": 10,
  "case_type": "民间借贷纠纷"
}
```

### GET /api/cases/{case_id}
获取案例详情

### GET /api/health
健康检查

## 扩展建议

1. **增强 NLP 能力**:
   - 集成专业法律 NER 模型
   - 使用 LLM 进行裁判要点生成
   - 训练领域专用 BERT 模型

2. **知识图谱扩展**:
   - 增加更多法条和案例关系
   - 支持罪名分类
   - 添加量刑预测

3. **搜索优化**:
   - 实现更多相似度算法
   - 支持多维度筛选
   - 添加搜索历史记录

4. **功能扩展**:
   - 支持案例对比功能
   - 添加文书自动生成
   - 集成真实裁判文书库

## License

MIT License
