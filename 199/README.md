# 电商直播数据大屏系统

基于 Python + Kafka + Flink + WebSocket + ECharts 构建的实时电商直播数据监控大屏。

## 功能特性

### 核心指标展示
- **累计观看人数**：实时统计进入直播间的观众总数
- **当前在线人数**：实时显示当前在线观众数
- **累计点赞数**：统计用户点赞总数及秒级速率
- **累计成交额**：实时展示GMV及分钟级成交趋势
- **商品点击转化率**：商品点击到购买的转化比例
- **累计订单数**：订单总量统计

### 实时数据可视化
- **实时流量趋势图**：多维度展示在线增量、点赞、订单、成交额的秒级趋势
- **弹幕热词云**：基于jieba分词的实时弹幕热词统计与可视化
- **弹幕情感分析**：基于SnowNLP的弹幕情感正/中/负面分类与统计
- **热销商品排行**：商品销售额与转化率双轴柱状图

### 智能分析功能
- **秒级流式聚合**：支持1秒级别的数据窗口聚合
- **弹幕情感分析**：实时分析观众情感倾向，负面预警
- **主播话术建议**：基于多维度数据的智能话术建议系统
  - 互动指数偏低时建议发起互动活动
  - 负面评价过高时建议引导与回应
  - 转化率优秀时建议趁热打铁
  - 热词分析捕捉观众关注点
  - 流量波动预警与承接建议
  - 爆款商品识别与运营建议

## 技术架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  直播数据源    │────▶│    Kafka        │────▶│   Flink / Python│
│  (模拟/真实)   │     │   消息队列      │     │   流处理引擎    │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   前端大屏      │◀────│   WebSocket     │◀────│  智能分析模块   │
│  (ECharts)      │     │   实时推送      │     │  话术建议引擎   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 技术栈
- **数据采集**：Kafka Producer 模拟实时直播数据
- **消息队列**：Apache Kafka 实现高吞吐消息传输
- **流处理引擎**：
  - 主选：纯Python流处理（零部署依赖，开箱即用）
  - 备选：PyFlink 分布式流处理（`use_pyflink=True`）
- **情感分析**：SnowNLP + 关键词规则双重引擎
- **分词处理**：jieba 中文分词
- **实时推送**：WebSocket 服务器
- **前端可视化**：ECharts 5.x + 原生JavaScript

## 项目结构

```
live-dashboard/
├── config/                 # 配置模块
│   ├── __init__.py
│   └── config.py          # 系统配置（Kafka/Flink/阈值等）
├── kafka/                  # Kafka模块
│   ├── __init__.py
│   ├── topics.py          # 消息Topic定义
│   └── producer.py        # 数据生产者
├── flink/                  # 流处理模块
│   ├── __init__.py
│   ├── job.py             # 流处理作业主入口
│   ├── aggregation.py     # 指标聚合器
│   ├── sentiment.py       # 情感分析器
│   └── hotwords.py        # 热词提取器
├── websocket/              # WebSocket模块
│   ├── __init__.py
│   └── server.py          # WebSocket服务器
├── suggestion/             # 话术建议模块
│   ├── __init__.py
│   └── advisor.py         # 智能建议引擎
├── frontend/               # 前端页面
│   ├── index.html         # 主页面
│   ├── css/style.css      # 样式文件
│   └── js/dashboard.js    # 前端逻辑
├── main.py                # 主入口文件
├── requirements.txt       # Python依赖
├── start.bat              # Windows启动脚本
└── start.sh               # Linux/Mac启动脚本
```

## 快速开始

### 环境要求
- Python 3.8+
- JDK 8+ （使用PyFlink时需要）
- Apache Kafka 2.8+ （本地或远程）

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
```
kafka-python==2.0.2          # Kafka客户端
pyflink==1.18.0              # Flink Python API（可选）
websockets==12.0             # WebSocket服务器
snownlp==0.12.3              # 中文情感分析
jieba==0.42.1                # 中文分词
fastapi==0.109.0             # 可选：REST API
```

### 2. 启动Kafka

确保Kafka服务已启动：

```bash
# 启动ZooKeeper
bin/zookeeper-server-start.sh config/zookeeper.properties

# 启动Kafka
bin/kafka-server-start.sh config/server.properties
```

### 3. 配置系统

编辑 `config/config.py`：

```python
KAFKA_CONFIG = {
    'bootstrap_servers': 'localhost:9092',  # Kafka地址
    # ...
}

FLINK_CONFIG = {
    'window_size': 1,       # 窗口大小（秒）
    'window_slide': 1,      # 滑动间隔（秒）
    # ...
}
```

### 4. 启动系统

#### 方式一：一键启动所有组件（推荐）

```bash
# Windows
start.bat

# Linux/Mac
chmod +x start.sh
./start.sh
```

然后选择 `4. 启动全部组件`

#### 方式二：命令行启动

```bash
# 启动全部组件
python main.py all

# 仅启动数据生产者
python main.py producer

# 仅启动流处理作业
python main.py stream

# 仅启动WebSocket服务
python main.py server
```

### 5. 访问数据大屏

直接在浏览器中打开：
```
frontend/index.html
```

## Kafka Topics 说明

| Topic名称          | 数据类型     | 说明                     |
|-------------------|-------------|--------------------------|
| live-viewer       | 观众进出     | 观众进入/离开直播间事件   |
| live-online       | 在线人数     | 当前在线人数（每秒更新） |
| live-like         | 点赞数据     | 用户点赞事件             |
| live-transaction  | 交易数据     | 订单成交事件             |
| live-product-click| 商品点击     | 用户点击商品事件         |
| live-danmu        | 弹幕数据     | 用户发送的弹幕           |

## 主播话术建议规则

### 触发条件与建议

| 触发条件 | 等级 | 建议话术方向 |
|---------|------|-------------|
| 互动指数 < 30% 且 在线 > 1000 | ⚠️ 警告 | 发起抽奖、问答、红包等互动 |
| 负面评价 > 15% | 🔴 危险 | 关注负面评论，及时回应 |
| 负面评价 > 8% | 🔵 提示 | 增加正向互动，强调优势 |
| 转化率 > 15% | 🟢 优秀 | 趁热打铁，增加库存/优惠 |
| 转化率 < 5% 且 在线 > 2000 | ⚠️ 警告 | 重点讲解爆款，强调性价比 |
| 热词包含价格/质量/发货等 | 🔵 提示 | 针对观众关注点重点讲解 |
| 观众流失 > 0 且 在线 > 5000 | ⚠️ 警告 | 提升节奏，推出爆点活动 |
| 每分钟新增 > 100人 | 🟢 优秀 | 做好新观众承接，介绍福利 |
| 商品转化率 > 20% | 🟢 优秀 | 爆款预警，延长讲解时间 |

## 数据流格式

### WebSocket 推送数据格式

```json
{
  "type": "metrics_update",
  "metrics": {
    "total_viewers": 12345,
    "current_online": 5678,
    "total_likes": 98765,
    "total_transactions": 1234,
    "total_amount": 567890.50,
    "conversion_rate": 0.085,
    "viewers_per_second": 15,
    "likes_per_second": 45,
    "transactions_per_minute": 20,
    "amount_per_minute": 15000,
    "timestamp": 1716888000.0
  },
  "sentiment": {
    "positive_count": 750,
    "neutral_count": 200,
    "negative_count": 50,
    "avg_score": 0.72,
    "positive_rate": 0.75,
    "negative_rate": 0.05
  },
  "hotwords": [
    {"word": "优惠", "count": 156, "rate": 0.15},
    {"word": "质量", "count": 89, "rate": 0.09}
  ],
  "trend": {
    "timestamps": [1716888000, ...],
    "viewers": [15, 18, ...],
    "likes": [45, 52, ...],
    "transactions": [2, 3, ...],
    "amount": [1500, 2200, ...]
  },
  "top_products": [
    {"product_id": "P001", "clicks": 1200, "orders": 120, "amount": 35880, "conversion_rate": 0.10}
  ],
  "latest_danmu": [
    {
      "user_name": "用户12345",
      "content": "主播好帅！",
      "is_vip": false,
      "timestamp": 1716888000.0,
      "sentiment": {"score": 0.85, "label": "positive"}
    }
  ],
  "suggestion": {
    "current": {
      "level": "warning",
      "category": "interaction",
      "message": "当前互动指数偏低（25%）",
      "action": "建议发起抽奖活动引导观众参与",
      "priority": 2,
      "timestamp": 1716888000.0
    },
    "history": [...]
  },
  "timestamp": 1716888000.0
}
```

## 性能优化建议

### 高并发场景
1. 增加Kafka分区数，提升消费并行度
2. 启用PyFlink模式，利用分布式计算能力
3. 调整Flink窗口大小与滑动间隔
4. 增加WebSocket服务器实例，使用负载均衡

### 数据持久化
可扩展对接：
- Redis：实时数据缓存
- InfluxDB / TDengine：时序数据存储
- Elasticsearch：全文检索与日志分析
- MySQL/PostgreSQL：指标数据持久化

## 常见问题

### 1. Kafka连接失败
- 检查Kafka服务是否正常运行
- 确认`bootstrap_servers`配置正确
- 检查防火墙是否开放9092端口

### 2. WebSocket连接断开
- 检查端口8765是否被占用
- 确认服务器防火墙设置
- 前端会自动尝试重连（最多10次）

### 3. 中文分词/情感分析不准确
- 可扩充自定义词典：`jieba.load_userdict()`
- 训练SnowNLP自定义模型
- 调整情感阈值参数

### 4. 前端图表不显示
- 检查浏览器控制台是否有报错
- 确认ECharts CDN可访问
- 检查WebSocket连接状态

## 许可证

MIT License
