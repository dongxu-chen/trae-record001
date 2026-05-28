# 社交媒体舆情分析系统

一个基于 Python + Scrapy + SnowNLP + LDA + Kafka + Flask 构建的社交媒体舆情分析系统。

## 功能特性

### 📊 数据采集
- **微博爬虫**: 基于 Scrapy 采集微博热搜和关键词搜索结果
- **推特爬虫**: 采集推特实时讨论内容
- **论坛爬虫**: 支持虎扑、知乎、贴吧等主流论坛
- **模拟数据生成器**: 无需真实爬取即可测试系统功能

### 😊 情感分析
- **SnowNLP 中文情感分析**: 精准的中文情感识别
- **多语言支持**: 同时支持中英文文本分析
- **关键词匹配**: 基于情感词典的备选方案
- **三分类结果**: 正向/负向/中性，带置信度

### 📝 主题提取
- **LDA 主题模型**: 基于 gensim 的隐含狄利克雷分配
- **动态主题数**: 可配置的主题数量
- **关键词提取**: TF-IDF 关键词识别
- **模型持久化**: 支持模型保存和加载

### 🌐 传播路径分析
- **传播深度追踪**: 分析信息传播层级
- **关键节点识别**: PageRank 算法识别影响力用户
- **传播速度计算**: 量化信息扩散速率
- **可视化图谱**: NetworkX 构建传播网络

### 📈 舆情监控
- **实时趋势图**: Chart.js 绘制情感变化曲线
- **关键词云**: ECharts 词云展示热点话题
- **平台分布**: 多平台数据对比分析
- **预警推送**: 异常舆情自动告警

### 🚨 预警系统
- **负面占比预警**: 负面情绪超过阈值告警
- **热度激增预警**: 讨论量突增检测
- **情绪转变预警**: 快速情绪转向识别
- **多级告警**: 高/中/低三级严重程度

## 技术栈

| 模块 | 技术 | 版本 |
|------|------|------|
| 数据采集 | Scrapy | 2.8+ |
| 消息队列 | Kafka | 2.0+ |
| 情感分析 | SnowNLP | 0.12.3 |
| 主题模型 | Gensim | 4.3+ |
| Web框架 | Flask | 2.2+ |
| 实时通信 | Flask-SocketIO | 5.3+ |
| 数据存储 | SQLAlchemy + SQLite | 1.4+ |
| 可视化 | Chart.js + ECharts | 最新 |
| 网络分析 | NetworkX | 3.0+ |
| 中文分词 | Jieba | 0.42+ |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:5000` 启动。

### 3. 访问系统

打开浏览器访问 `http://localhost:5000`，点击「生成测试数据」按钮即可查看效果。

## 项目结构

```
.
├── main.py                 # 主入口文件
├── config.py               # 配置文件
├── requirements.txt        # 依赖清单
├── database.py             # 数据库模型
├── data_pipeline.py        # 数据处理管道
├── kafka_manager.py        # Kafka 管理
├── alert_manager.py        # 预警管理
├── crawlers/               # 爬虫模块
│   ├── __init__.py
│   ├── base_spider.py      # 爬虫基类
│   ├── weibo_spider.py     # 微博爬虫
│   ├── twitter_spider.py   # 推特爬虫
│   ├── forum_spider.py     # 论坛爬虫
│   └── data_generator.py   # 模拟数据生成器
├── analysis/               # 分析模块
│   ├── __init__.py
│   ├── text_processor.py   # 文本处理
│   ├── sentiment_analyzer.py  # 情感分析
│   ├── topic_modeler.py    # LDA主题模型
│   └── propagation_analyzer.py  # 传播分析
├── web/                    # Web服务
│   ├── __init__.py
│   └── app.py              # Flask应用
├── static/
│   └── templates/
│       └── index.html      # 前端仪表盘
└── data/                   # 数据目录
    ├── sentiment.db        # SQLite数据库
    ├── app.log             # 日志文件
    └── cache/              # 模型缓存
```

## API 接口

### 仪表盘数据
```
GET /api/dashboard?hours=24
```

### 情感分析
```
POST /api/analyze
Content-Type: application/json

{
    "text": "这个产品真的太棒了！"
}
```

### 批量分析
```
POST /api/analyze/batch
Content-Type: application/json

{
    "texts": ["文本1", "文本2", "文本3"]
}
```

### 生成测试数据
```
POST /api/data/generate
Content-Type: application/json

{
    "count": 50,
    "platform": "weibo"
}
```

### 数据接入
```
POST /api/data/ingest
Content-Type: application/json

{
    "platform": "weibo",
    "post_id": "123456",
    "content": "帖子内容",
    "author": "用户名",
    "timestamp": "2024-01-01T12:00:00Z",
    "likes": 100,
    "shares": 50,
    "comments": 30
}
```

### 预警相关
```
GET /api/alerts?limit=20&severity=high
POST /api/alerts/{id}/acknowledge
GET /api/alerts/summary?hours=24
```

### 其他接口
```
GET /api/sentiment?platform=weibo&hours=24
GET /api/trends?platform=weibo&hours=24
GET /api/keywords?platform=weibo&hours=24&top_k=20
GET /api/topics
GET /api/stats?hours=24
GET /api/health
```

## 配置说明

在 `config.py` 中可以配置：

### 数据库配置
```python
DATABASE_URL = 'sqlite:///data/sentiment.db'
```

### Kafka 配置
```python
ENABLE_KAFKA = False
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
```

### 情感阈值
```python
SENTIMENT_THRESHOLD = {
    'positive': 0.6,
    'negative': 0.4,
}
```

### LDA 配置
```python
LDA_NUM_TOPICS = 5
LDA_NUM_KEYWORDS = 10
```

### 预警配置
```python
ALERT_CONFIG = {
    'negative_ratio_threshold': 0.3,
    'volume_spike_threshold': 2.0,
    'check_interval': 300,
}
```

## Kafka 集成（可选）

### 启动 Kafka
```bash
# 启动 Zookeeper
bin/zookeeper-server-start.sh config/zookeeper.properties

# 启动 Kafka
bin/kafka-server-start.sh config/server.properties
```

### 启用 Kafka
设置环境变量：
```bash
export ENABLE_KAFKA=true
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### 主题说明
- `raw_social_data`: 原始采集数据
- `analyzed_data`: 分析后的数据
- `alerts`: 预警信息

## 爬虫使用

### 运行微博爬虫
```bash
cd crawlers
scrapy runspider weibo_spider.py -a keywords=舆情,热点 -a max_pages=5
```

### 运行推特爬虫
```bash
scrapy runspider twitter_spider.py -a keywords=#trending,#news
```

### 运行论坛爬虫
```bash
scrapy runspider forum_spider.py
```

## 使用示例

### Python SDK 风格使用

```python
from data_pipeline import DataPipeline
from crawlers.data_generator import MockDataGenerator

# 初始化管道
pipeline = DataPipeline()

# 生成测试数据
generator = MockDataGenerator()
posts = generator.generate_batch(count=100)

# 批量处理
results = pipeline.process_batch(posts)

# 获取情感分布
dist = pipeline.get_sentiment_distribution(hours=24)
print(f"正面: {dist['percentages']['positive']:.1%}")
print(f"负面: {dist['percentages']['negative']:.1%}")
print(f"中性: {dist['percentages']['neutral']:.1%}")

# 获取趋势数据
trends = pipeline.get_trend_data(hours=24)

# 获取热词
keywords = pipeline.get_top_keywords(hours=24, top_k=20)
```

### 单条文本分析

```python
from analysis import SentimentAnalyzer, TopicModeler

analyzer = SentimentAnalyzer()
result = analyzer.analyze("今天天气真好，心情也很好！")
print(f"情感: {result['sentiment']}")
print(f"正面分数: {result['positive']}")
print(f"负面分数: {result['negative']}")
```

## 常见问题

### Q: 爬虫无法采集到数据？
A: 社交媒体平台有反爬机制，建议：
1. 配置合理的下载延迟
2. 使用代理 IP 池
3. 添加 Cookie 认证
4. 使用模拟数据生成器进行测试

### Q: SnowNLP 安装失败？
A: 确保已安装 Visual C++ Build Tools，或使用预编译版本：
```bash
pip install --only-binary :all: snownlp
```

### Q: 如何处理大规模数据？
A: 建议：
1. 启用 Kafka 进行消息队列解耦
2. 使用 Redis 做缓存层
3. 替换 SQLite 为 PostgreSQL/MySQL
4. 增加 worker 进程数

### Q: 如何自定义预警规则？
A: 在 `alert_manager.py` 中扩展 `check_alerts` 方法，添加新的检测逻辑。

## 开发计划

- [ ] 支持更多社交媒体平台（抖音、小红书等）
- [ ] 引入 BERT 等深度学习模型提升情感分析精度
- [ ] 添加用户画像和影响力分析
- [ ] 支持邮件/短信/企业微信告警推送
- [ ] 新增历史数据对比分析
- [ ] 导出分析报告（PDF/Excel）
- [ ] 多租户支持
- [ ] 容器化部署（Docker + Kubernetes）

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎提交 Issue。
