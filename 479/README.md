# 客户对话情感分析系统

一个实时客服对话情感分析系统，支持多轮对话上下文、情感转折检测和实时多渠道告警功能。

## ✨ 功能特性

### 核心功能
- 🎯 **四种情感分类**: 满意、愤怒、失望、焦虑
- 🧠 **BERT模型**: 使用中文BERT进行高精度情感分析
- 🔄 **滑动窗口+摘要机制**: 智能保留关键对话信息
- 📊 **动态阈值检测**: 根据用户历史情绪波动自适应调整阈值
- ⚠️ **5种告警类型**: 高负面情绪、急剧恶化、负面趋势、持续负面、焦虑上升
- 📡 **多渠道告警**: 企业微信、邮件、短信
- 🔌 **WebSocket通信**: 实时双向数据传输
- 📈 **可视化仪表盘**: 雷达图、折线图、用户画像

### 🆕 新增功能
1. **滑动窗口+摘要机制**
   - 自动提取重要对话轮次
   - 关键词提取和主题识别
   - 对话重要性评分

2. **动态阈值情感转折检测**
   - 用户情绪画像建立
   - 基于历史波动率自适应调整阈值
   - 情绪异常检测（Z-score）

3. **多渠道告警支持**
   - 企业微信 Webhook
   - 邮件通知（SMTP）
   - 短信通知（API）
   - 可配置告警级别过滤

## 🏗️ 项目结构

```
479/
├── app.py                      # Flask主应用 + WebSocket服务
├── run.py                      # 启动脚本
├── requirements.txt            # Python依赖
├── .env                        # 环境配置
├── README.md                   # 说明文档
├── models/
│   ├── __init__.py
│   └── sentiment_analyzer.py   # BERT情感分析模型
├── core/
│   ├── __init__.py
│   ├── context_encoder.py      # 滑动窗口 + 摘要机制
│   ├── context_manager.py      # 对话上下文管理
│   ├── dynamic_detector.py     # 动态阈值检测
│   ├── alert_channels.py       # 多渠道告警模块
│   └── sentiment_detector.py   # 告警管理器
└── templates/
    └── index.html              # 前端界面
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）

编辑 `.env` 文件配置告警渠道：

```env
# 企业微信
ALERT_CHANNELS=wechat_work
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx

# 邮件
ALERT_CHANNELS=email
EMAIL_SMTP_SERVER=smtp.example.com
EMAIL_SMTP_PORT=587
EMAIL_SENDER=alert@example.com
EMAIL_PASSWORD=your-password
EMAIL_RECIPIENTS=admin@example.com,manager@example.com

# 短信
ALERT_CHANNELS=sms
SMS_API_URL=https://sms-api.example.com/send
SMS_API_KEY=your-api-key
SMS_RECIPIENTS=13800138000,13900139000
```

### 3. 启动服务

```bash
python run.py
```

或直接运行:

```bash
python app.py
```

### 4. 访问系统

打开浏览器访问: http://localhost:5000

## 🎮 使用说明

### 界面布局

1. **对话面板** (左侧)
   - 选择说话角色（客户/客服）
   - 输入对话内容，按Enter发送
   - 实时显示情感分析结果

2. **情感分析仪表盘** (中间)
   - 统计数据：对话轮数、告警次数
   - 用户情绪画像：基线状态、波动率等
   - 对话摘要：关键主题标签
   - 情感趋势指示器
   - 情感变化曲线（折线图）
   - 当前情感分布（雷达图）
   - 实时告警列表

3. **告警配置** (右侧)
   - 启用/禁用告警渠道
   - 配置各渠道参数
   - 测试渠道连通性
   - 设置最低告警级别

### 告警类型说明

| 告警类型 | 级别 | 触发条件 |
|---------|------|---------|
| 高负面情绪 | 高 | 单一负面情感分数超过动态阈值 |
| 情绪急剧恶化 | 高 | 短时间内情感大幅下降（动态阈值） |
| 负面情绪趋势 | 中 | 连续多轮情感持续下降 |
| 持续负面情绪 | 中 | 多轮对话持续出现负面情绪 |
| 焦虑情绪上升 | 中 | 焦虑情绪持续上升 |

## 🔌 API接口

### REST API

**会话管理**
- `GET /api/health` - 健康检查
- `POST /api/sessions` - 创建新会话
- `DELETE /api/sessions/<session_id>` - 结束会话
- `GET /api/sessions/<session_id>/history` - 获取对话历史（含归因、质量分析）
- `GET /api/sessions/<session_id>/summary` - 获取对话摘要
- `POST /api/analyze` - 分析文本情感

**归因分析**
- `GET /api/sessions/<session_id>/attribution` - 获取会话归因分析

**话术建议**
- `GET /api/sessions/<session_id>/suggestions` - 获取回复建议和质量分析

**趋势看板**
- `GET /api/trends/daily` - 获取日趋势数据
- `GET /api/trends/weekly` - 获取周趋势数据
- `GET /api/trends/analysis?period=7d|30d|90d` - 获取趋势分析
- `GET /api/trends/hourly` - 获取时段分布

**告警管理**
- `GET /api/alerts/channels` - 获取可用告警渠道
- `POST /api/alerts/config` - 更新告警配置
- `POST /api/alerts/test/<channel>` - 测试告警渠道

**用户画像**
- `GET /api/users/<user_id>/profile` - 获取用户情绪画像

### WebSocket事件

**基础事件**
- `connect` / `disconnect` - 连接事件
- `join_session` / `leave_session` - 会话管理
- `send_message` - 发送消息
- `message_received` - 接收消息
- `get_history` / `history_response` - 历史记录

**实时推送**
- `trend_update` - 趋势更新
- `context_update` - 上下文摘要更新
- `profile_update` - 用户画像更新
- `alert` - 告警通知
- `attribution_update` - 归因分析结果推送
- `suggestions_update` - 话术建议推送

## ⚙️ 配置说明

### 滑动窗口参数

在 `.env` 文件中可配置:

```env
CONTEXT_WINDOW=8       # 滑动窗口大小
SUMMARY_SIZE=5         # 摘要保留的重要对话数
```

### 动态阈值参数

```env
TURN_THRESHOLD=0.4     # 基础转折阈值
ALERT_THRESHOLD=0.7    # 基础告警阈值
```

### 重要性评分权重

- 情感极端度: 30%
- 情感变化: 25%
- 关键词密度: 20%
- 文本长度: 10%
- 转折点标记: 15%

## 📊 技术栈

- **后端**: Flask + Flask-SocketIO + Eventlet
- **NLP**: PyTorch + Transformers (BERT)
- **前端**: 原生JavaScript + Chart.js
- **通信**: WebSocket
- **告警渠道**: 企业微信Webhook / SMTP / SMS API

## 📝 注意事项

1. 首次运行会自动下载BERT模型（约400MB），需要网络连接
2. 如果未安装PyTorch和Transformers，系统会自动降级为基于关键词的规则匹配
3. BERT推理需要一定计算资源，建议在有GPU的机器上运行
4. 演示使用关键词匹配也可以快速体验功能
5. 多渠道告警需要配置相应的服务凭证

## 🔧 扩展开发

### 添加新的告警渠道

1. 在 `core/alert_channels.py` 中继承 `AlertChannel` 类
2. 实现 `send()` 和 `is_enabled()` 方法
3. 在 `MultiChannelAlertManager._init_channels()` 中注册新渠道

### 自定义重要性评分

修改 `core/context_encoder.py` 中 `ImportanceScorer` 类的权重分配。

### 调整动态阈值策略

修改 `core/dynamic_detector.py` 中 `UserEmotionProfile` 类的阈值计算逻辑。
