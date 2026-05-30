# 知识图谱问答系统

基于医疗领域的知识图谱智能问答系统，支持多跳推理、模糊匹配、答案溯源等功能。

## 技术栈

- **Python** - 主编程语言
- **Neo4j** - 图数据库存储知识图谱
- **Cypher** - 图查询语言
- **BERT** - 意图识别（可选）
- **FastAPI** - Web API框架
- **jieba** - 中文分词
- **fuzzywuzzy** - 模糊匹配

## 项目结构

```
knowledge-graph-qa/
├── config/              # 配置模块
│   ├── __init__.py
│   └── settings.py      # 配置文件
├── kg/                  # 知识图谱模块
│   ├── __init__.py
│   ├── schema.py        # 图谱模式定义
│   ├── neo4j_client.py  # Neo4j客户端
│   └── data_init.py     # 数据初始化脚本
├── nlp/                 # 自然语言处理模块
│   ├── __init__.py
│   ├── intent_classifier.py  # 意图分类器
│   └── entity_extractor.py   # 实体提取器
├── query/               # 查询处理模块
│   ├── __init__.py
│   ├── cypher_generator.py   # Cypher查询生成器
│   └── answer_processor.py   # 答案处理器
├── services/            # 服务层
│   ├── __init__.py
│   └── qa_service.py    # 问答服务
├── api/                 # API层
│   ├── __init__.py
│   └── main.py          # FastAPI主文件
├── tests/               # 测试文件
│   ├── __init__.py
│   └── test_qa.py       # 问答测试
├── main.py              # 启动入口
├── requirements.txt     # 依赖包
├── .env.example         # 环境变量示例
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置Neo4j连接信息：

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### 3. 启动Neo4j数据库

确保Neo4j服务已启动并可访问。

### 4. 初始化知识图谱数据

```bash
python -m kg.data_init
```

### 5. 启动API服务

```bash
python main.py
```

或使用uvicorn直接运行：

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. 访问API文档

启动后访问：http://localhost:8000/docs

## API接口

### 问答接口

**POST** `/api/qa`

请求体：
```json
{
  "question": "感冒有什么症状？",
  "use_bert": false
}
```

响应：
```json
{
  "question": "感冒有什么症状？",
  "answer": "感冒的常见症状包括：发烧、咳嗽、头痛、乏力",
  "has_answer": true,
  "intent": {
    "predicted": "disease_symptom",
    "confidence": 0.8
  },
  "entities": [
    {
      "text": "感冒",
      "canonical_name": "感冒",
      "type": "Disease",
      "start": 0,
      "end": 2
    }
  ],
  "results": ["发烧", "咳嗽", "头痛", "乏力"],
  "source": {
    "type": "single_hop",
    "query_entity": "感冒",
    "query_relation": "HAS_SYMPTOM",
    "query_relation_label": "有症状",
    "target_type": "Symptom",
    "evidence_tuples": [...]
  }
}
```

### 实体详情查询

**POST** `/api/entity/detail`

请求体：
```json
{
  "entity_name": "感冒"
}
```

### 实体间路径查询

**POST** `/api/path`

请求体：
```json
{
  "entity1": "感冒",
  "entity2": "呼吸内科",
  "max_hops": 4
}
```

### 系统状态

**GET** `/api/health`

### 图谱模式

**GET** `/api/schema`

## 功能特性

### 1. 意图识别

- 支持BERT深度学习分类（需训练）
- 默认使用关键词规则分类（快速启动）
- 支持11种查询意图

### 2. 实体提取

- 基于词典匹配
- 支持模糊匹配
- 实体同义词扩展

### 3. 多跳推理

- 自动识别多跳问题
- 支持可变跳数查询
- 路径可视化

### 4. 模糊匹配

- 实体模糊匹配
- 关键词模糊搜索
- 相似度排序

### 5. 答案溯源

- 查询过程记录
- 推理路径展示
- 证据链构建

## 支持的意图类型

| 意图类型 | 描述 | 示例问题 |
|---------|------|---------|
| disease_symptom | 查询疾病症状 | 感冒有什么症状？ |
| disease_drug | 查询疾病用药 | 感冒吃什么药？ |
| disease_department | 查询所属科室 | 感冒挂什么科？ |
| disease_treatment | 查询治疗方法 | 感冒怎么治疗？ |
| disease_examination | 查询检查项目 | 感冒需要做什么检查？ |
| drug_disease | 查询药物治疗的疾病 | 阿莫西林治什么病？ |
| symptom_disease | 根据症状查疾病 | 发烧咳嗽是什么病？ |
| department_disease | 查询科室治疗的疾病 | 呼吸内科看什么病？ |
| doctor_disease | 查询医生擅长治疗的疾病 | 张医生治什么病？ |
| multi_hop | 多跳查询 | 感冒有什么症状然后用什么药？ |
| fuzzy_query | 模糊查询 | 关于感冒的信息 |

## 运行测试

```bash
python -m tests.test_qa
```

## 自定义知识图谱

### 添加新实体类型

编辑 `kg/schema.py` 中的 `ENTITY_TYPES`：

```python
ENTITY_TYPES = {
    "Disease": "疾病",
    "Symptom": "症状",
    # 添加新类型
    "YourType": "你的类型"
}
```

### 添加新关系类型

编辑 `kg/schema.py` 中的 `RELATION_TYPES` 和 `RELATION_INTENT_MAP`。

### 添加训练数据

编辑 `nlp/intent_classifier.py` 中的 `prepare_training_data` 方法。

## 注意事项

1. **Neo4j连接**：确保Neo4j服务正常运行，端口和认证信息正确
2. **BERT模型**：首次使用会下载预训练模型，需要网络连接
3. **数据初始化**：初始化会清空现有数据库，请确保已备份
4. **中文分词**：jieba分词首次运行会加载词典

## 许可证

MIT License
