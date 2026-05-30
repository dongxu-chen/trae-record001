# 医疗知识问答系统

基于医疗知识图谱和BERT的智能医疗问答系统，支持症状查询、疾病诊断、用药咨询等功能。

## 技术栈

- **后端**: Python + FastAPI
- **数据库**: Neo4j (知识图谱)
- **AI模型**: BERT (意图识别)
- **前端**: React + Ant Design

## 功能特性

1. **问题意图识别** - 自动识别用户问题类型（症状查询、疾病诊断、用药咨询等）
2. **知识图谱查询** - 基于Neo4j的医疗知识图谱进行智能问答
3. **证据溯源** - 显示回答的来源和置信度
4. **免责声明** - 每条回答附带医疗免责声明
5. **实体提取** - 自动提取问题中的疾病、症状、药物等实体

## 项目结构

```
medical-qa-system/
├── backend/                 # 后端代码
│   ├── main.py             # FastAPI主入口
│   ├── config.py           # 配置文件
│   ├── neo4j_db.py         # Neo4j数据库操作
│   ├── intent_recognition.py  # BERT意图识别
│   ├── qa_engine.py        # 问答引擎
│   ├── init_knowledge_graph.py  # 知识图谱初始化
│   └── requirements.txt    # Python依赖
└── frontend/               # 前端代码
    ├── src/
    │   ├── App.js          # 主应用组件
    │   ├── index.js        # 入口文件
    │   └── index.css       # 样式文件
    ├── public/
    │   └── index.html      # HTML模板
    └── package.json        # Node.js依赖
```

## 快速开始

### 前置要求

- Python 3.8+
- Node.js 16+
- Neo4j 4.4+ 或 Neo4j Aura

### 1. 启动Neo4j数据库

确保Neo4j服务正在运行，或使用Neo4j Desktop创建数据库。

### 2. 初始化知识图谱

```bash
cd backend
pip install -r requirements.txt
python init_knowledge_graph.py
```

### 3. 启动后端服务

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端API文档: http://localhost:8000/docs

### 4. 启动前端服务

```bash
cd frontend
npm install
npm start
```

前端访问: http://localhost:3000

## API接口

### 问答接口

```
POST /api/qa
Content-Type: application/json

{
  "question": "感冒有什么症状？"
}
```

响应:
```json
{
  "question": "感冒有什么症状？",
  "intent": "symptom_query",
  "intent_confidence": 0.95,
  "answer": "...",
  "evidence": [...],
  "disclaimer": "...",
  "entities": [...]
}
```

### 健康检查

```
GET /api/health
```

### 获取免责声明

```
GET /api/disclaimer
```

## 知识图谱数据模型

### 节点类型

- **Disease** - 疾病节点
  - name: 疾病名称
  - description: 疾病描述
  - department: 所属科室

- **Symptom** - 症状节点
  - name: 症状名称
  - description: 症状描述

- **Medicine** - 药物节点
  - name: 药物名称
  - category: 药物分类
  - usage: 用法用量
  - description: 药物描述

- **Department** - 科室节点
  - name: 科室名称

### 关系类型

- `HAS_SYMPTOM` - 疾病有症状
- `TREATED_BY` - 疾病用药物治疗
- `BELONGS_TO` - 疾病属于科室

## 意图类型

1. `symptom_query` - 症状查询
2. `disease_query` - 疾病诊断
3. `medicine_query` - 用药咨询
4. `treatment_query` - 治疗建议
5. `diagnosis_query` - 诊断检查
6. `general_query` - 通用查询

## 示例问题

- "感冒有什么症状？"
- "发烧可能是什么病？"
- "高血压吃什么药？"
- "糖尿病怎么治疗？"
- "胃炎有哪些表现？"

## 注意事项

1. 本系统仅供参考和教育目的，不能替代专业医生的诊断和治疗建议
2. 用药请遵医嘱，切勿自行用药
3. 如有健康问题，请及时咨询专业医疗人员

## 许可证

MIT License
