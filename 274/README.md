# 电商搜索意图识别系统

基于BERT微调、知识图谱和Elasticsearch的电商搜索意图识别系统，实现搜索意图识别、商品属性抽取、搜索词改写，提升搜索召回率。

## 功能特性

### 1. 搜索意图识别
- 识别用户搜索意图：购买意向、比价、知识查询
- 基于BERT微调的分类模型
- 支持规则-based fallback方案

### 2. 商品属性抽取
- 品牌抽取（Brand）
- 品类抽取（Category）
- 规格抽取（Spec）
- 基于BERT的序列标注模型

### 3. 搜索词改写
- 拼写纠错
- 同义词扩展
- 知识图谱查询词扩展
- 多种查询变体生成

### 4. 智能搜索召回
- Elasticsearch全文检索
- 语义搜索增强
- 知识图谱扩展召回
- 多维度过滤

## 项目结构

```
ecommerce-search-intent/
├── bert_module/              # BERT模型模块
│   ├── __init__.py
│   ├── intent_classifier.py  # 意图分类器
│   ├── attribute_extractor.py # 属性抽取器
│   └── train.py              # 训练脚本
├── knowledge_graph/          # 知识图谱模块
│   ├── __init__.py
│   ├── knowledge_graph.py    # 知识图谱
│   └── synonym_manager.py    # 同义词管理器
├── es_search/                # Elasticsearch搜索模块
│   ├── __init__.py
│   └── product_search.py     # 商品搜索
├── query_rewriter/           # 查询改写模块
│   ├── __init__.py
│   └── query_rewriter.py     # 查询改写器
├── search_service/           # 搜索服务
│   ├── __init__.py
│   └── ecommerce_search.py   # 主搜索服务
├── data/                     # 数据目录
│   ├── intent_data.json      # 意图训练数据
│   ├── attribute_data.json   # 属性训练数据
│   ├── knowledge_graph.json  # 知识图谱数据
│   ├── synonyms.txt          # 同义词词典
│   └── products.json         # 商品数据
├── models/                   # 模型保存目录
├── config.py                 # 配置文件
├── main.py                   # FastAPI服务
├── test_search.py            # 测试脚本
├── requirements.txt          # 依赖包
└── .env                      # 环境变量
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

### 1. 运行测试

```bash
python test_search.py
```

这将：
- 初始化搜索服务
- 加载示例商品数据
- 运行6项功能测试
- 显示系统状态和测试结果

### 2. 启动API服务

```bash
python main.py
```

服务启动后访问：
- API文档：http://localhost:8000/docs
- 根路径：http://localhost:8000

## API接口

### 综合搜索
```http
POST /search
Content-Type: application/json

{
    "query": "苹果手机",
    "top_n": 10
}
```

响应包含：
- 意图分析结果
- 属性抽取结果
- 查询改写详情
- 搜索结果
- 召回率提升统计

### 意图识别
```http
POST /intent
Content-Type: application/json

{
    "query": "我想买iPhone 15"
}
```

### 属性抽取
```http
POST /attributes
Content-Type: application/json

{
    "query": "苹果iPhone 15 256G手机"
}
```

### 查询改写
```http
POST /rewrite
Content-Type: application/json

{
    "query": "苹果手机"
}
```

### 系统状态
```http
GET /stats
```

## 训练BERT模型

### 训练意图分类器
```python
from bert_module import IntentClassifier

classifier = IntentClassifier()
classifier.train('data/intent_data.json', 'models/intent_classifier')
```

### 训练属性抽取器
```python
from bert_module import AttributeExtractor

extractor = AttributeExtractor()
extractor.train('data/attribute_data.json', 'models/attribute_extractor')
```

### 使用训练好的模型
```python
from search_service import EcommerceSearchService

# 使用预训练模型
service = EcommerceSearchService(use_pretrained=True)
```

## Elasticsearch配置（可选）

系统支持在没有Elasticsearch的情况下运行（使用fallback模式）。如需启用Elasticsearch：

1. 安装并启动Elasticsearch
2. 安装IK分词器插件
3. 修改 `.env` 文件：

```env
ES_HOST=localhost
ES_PORT=9200
ES_INDEX=ecommerce_products
```

## 召回率提升机制

### 1. 查询词扩展
- 同义词扩展：手机 → 智能手机、移动电话
- 知识图谱扩展：苹果 → 手机、笔记本、耳机、Apple
- 扩展倍率：2-5倍词汇量

### 2. 多维度过滤
- 品牌过滤：苹果、华为、小米等
- 品类过滤：手机、耳机、笔记本等
- 规格过滤：256G、4K、27寸等

### 3. 多查询策略
- 主查询：修正后的查询词
- 增强查询：标准化查询 + 扩展词汇
- 变体查询：多种表述方式

## 技术架构

```
用户搜索词
    ↓
┌─────────────────────────────────┐
│   查询改写模块                    │
│   ├─ 拼写纠错                    │
│   ├─ 同义词扩展                  │
│   └─ 知识图谱扩展                │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│   BERT模块                       │
│   ├─ 意图识别 (分类)             │
│   └─ 属性抽取 (序列标注)         │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│   知识图谱模块                    │
│   ├─ 实体查询                    │
│   ├─ 关系查询                    │
│   └─ 查询词扩展                  │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│   Elasticsearch搜索              │
│   ├─ 全文检索                    │
│   ├─ 过滤条件                    │
│   └─ 结果排序                    │
└─────────────────────────────────┘
    ↓
搜索结果 + 召回率提升统计
```

## 数据说明

### 意图分类标签
- **购买意向**：用户有明确购买需求
- **比价**：用户在对比不同商品
- **知识查询**：用户在了解产品信息

### 属性标注标签 (BIO)
- `B-BRAND` / `I-BRAND`：品牌
- `B-CATEGORY` / `I-CATEGORY`：品类
- `B-SPEC` / `I-SPEC`：规格
- `O`：其他

### 知识图谱实体类型
- **品牌**：苹果、华为、小米等
- **品类**：手机、耳机、笔记本等
- **规格**：256G、4K、27寸等

## 性能指标

| 功能 | 精确率 | 召回率 | F1值 |
|------|--------|--------|------|
| 意图识别 | 92% | 90% | 91% |
| 品牌抽取 | 95% | 93% | 94% |
| 品类抽取 | 94% | 92% | 93% |
| 规格抽取 | 88% | 85% | 86.5% |
| 搜索召回提升 | - | +45% | - |

*注：上述指标为基于BERT微调模型的预期值，实际效果取决于训练数据规模和质量。*

## 扩展开发

### 添加新品牌到知识图谱
```python
from knowledge_graph import KnowledgeGraph

kg = KnowledgeGraph()
kg.add_entity('brand_11', 'OPPO', '品牌', ['OPPO'])
kg.add_relation('brand_11', 'category_1', '生产')
kg.save()
```

### 添加同义词
```python
from knowledge_graph import SynonymManager

sm = SynonymManager()
sm.add_synonym('显示器', '荧幕')
sm.save()
```

### 自定义搜索逻辑
```python
from search_service import EcommerceSearchService

class CustomSearchService(EcommerceSearchService):
    def custom_search(self, query, **kwargs):
        # 自定义搜索逻辑
        pass
```

## 常见问题

### Q: 没有Elasticsearch可以运行吗？
A: 可以。系统会自动切换到fallback模式，使用内置的简单搜索实现。

### Q: 不训练BERT模型可以使用吗？
A: 可以。系统提供规则-based fallback方案，但准确率会稍低。

### Q: 如何提升准确率？
A: 
1. 增加训练数据量
2. 优化知识图谱实体和关系
3. 调整BERT模型训练参数
4. 扩充同义词词典

## License

MIT License
