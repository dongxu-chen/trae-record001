# 🛡️ 垃圾邮件过滤系统后端

基于机器学习和规则引擎的实时垃圾邮件过滤系统，支持用户反馈和自定义规则。

## 功能特性

### 📧 核心分类功能
- **内容分析**: 基于邮件标题、正文、附件名进行TF-IDF特征提取
- **机器学习分类**: 使用RandomForest算法进行智能分类
- **发件人声誉系统**: 基于历史反馈动态调整发件人声誉评分
- **发送频率监控**: IP频率限制和异常检测

### 🎯 规则引擎
- 8种内置规则（黑名单关键词、发件人、IP、可疑附件等）
- 支持自定义规则：关键词匹配、正则匹配、发件人域名、附件名
- 可配置规则权重和启用/禁用状态

### 👥 用户反馈系统
- 支持标注分类错误（误报/漏报）
- 反馈自动影响发件人声誉
- 累积反馈数据用于模型再训练

### 📊 可视化与监控
- Web仪表盘实时展示分类统计
- 评分分布图表
- 垃圾率趋势分析
- 发件人声誉分布
- Top垃圾关键词展示

## 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| Web框架 | Flask | API服务 |
| 消息队列 | Celery + Redis | 异步任务处理 |
| 缓存/存储 | Redis | 数据存储和缓存 |
| 机器学习 | Scikit-learn | 邮件分类模型 |
| 可视化 | Matplotlib | 图表生成 |

## 项目结构

```
spam-filter/
├── app/
│   ├── __init__.py
│   ├── redis_store.py      # Redis数据存储层
│   ├── classifier.py       # 机器学习分类器
│   ├── rule_engine.py      # 规则引擎
│   ├── tasks.py            # Celery异步任务
│   ├── routes.py           # Flask API路由
│   └── visualization.py    # 可视化模块
├── models/                 # 模型文件存储目录
├── config.py               # 配置文件
├── celery_app.py           # Celery配置
├── main.py                 # 应用入口
├── requirements.txt        # Python依赖
├── .env.example            # 环境变量示例
└── README.md
```

## 快速开始

### 1. 环境要求
- Python 3.8+
- Redis 6.0+

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件配置Redis连接等参数
```

### 4. 启动服务

#### 启动Redis
确保Redis服务在本地运行，或配置远程Redis地址。

#### 启动Celery Worker
```bash
celery -A celery_app worker --loglevel=info -Q classification,training,reputation
```

#### 启动Flask API
```bash
python main.py
```

### 5. 访问服务
- API服务: http://localhost:5000
- 健康检查: http://localhost:5000/api/health
- 仪表盘: http://localhost:5000/api/dashboard

## API 文档

### 邮件分类

**POST /api/email/classify**

请求体:
```json
{
  "sender": "spammer@example.com",
  "subject": "FREE MONEY NOW!!!",
  "body": "Click here to claim your prize: http://scam.com",
  "attachments": ["invoice.exe"],
  "sender_ip": "192.168.1.1",
  "async": false
}
```

响应:
```json
{
  "email_id": "uuid",
  "is_spam": true,
  "spam_probability": 0.89,
  "ham_probability": 0.11,
  "model_result": {...},
  "rule_result": {...},
  "sender_reputation": 25.5,
  "score_breakdown": {...}
}
```

### 查询分类结果

**GET /api/email/{email_id}**

### 提交反馈

**POST /api/email/{email_id}/feedback**

请求体:
```json
{
  "is_correct": false,
  "corrected_label": "ham",
  "notes": "这是正常的工作邮件"
}
```

### 规则管理

**GET /api/rules** - 获取所有规则
**POST /api/rules** - 创建新规则
**GET /api/rules/{rule_id}** - 获取规则详情
**DELETE /api/rules/{rule_id}** - 删除规则

创建规则示例:
```json
{
  "name": "可疑域名拦截",
  "type": "sender_domain",
  "condition": {
    "domains": ["scam.com", "spam.net"]
  },
  "weight": 3.0,
  "enabled": true,
  "description": "拦截来自可疑域名的邮件"
}
```

### 黑名单管理

**GET /api/blacklist/{type}** - 获取黑名单
**POST /api/blacklist/{type}** - 添加到黑名单
**DELETE /api/blacklist/{type}/{value}** - 从黑名单移除

支持的类型: `keywords`, `senders`, `ips`

### 统计信息

**GET /api/stats** - 获取分类统计和Top垃圾关键词
**GET /api/classifications** - 获取最近分类记录

### 发件人声誉

**GET /api/reputation/{sender}** - 查询发件人声誉

### 模型训练

**POST /api/model/train** - 使用新数据训练模型

## 评分系统说明

### 综合评分计算
系统采用加权融合方式计算最终垃圾邮件概率:

- **机器学习模型评分 (60%)**: 基于内容的智能分析
- **规则引擎评分 (30%)**: 基于自定义规则的匹配结果
- **发件人声誉评分 (10%)**: 基于历史反馈的信誉值

### 风险等级
| 规则总分 | 风险等级 | 说明 |
|---------|---------|------|
| ≥ 10 | Critical | 极高风险，立即拦截 |
| 5-10 | High | 高风险，标记为垃圾邮件 |
| 2-5 | Medium | 中等风险，需要人工审核 |
| < 2 | Low | 低风险，正常投递 |

### 内置规则权重

| 规则 | 权重 |
|------|------|
| 黑名单发件人 | 5.0 |
| 黑名单IP | 5.0 |
| 黑名单关键词 | 3.0 |
| 可疑附件 | 2.5 |
| 过多特殊字符 | 2.0 |
| 过多链接 | 2.0 |
| 全大写标题 | 1.5 |
| 过短正文 | 1.0 |

## 自定义规则类型

### 1. keyword_match - 关键词匹配
```json
{
  "type": "keyword_match",
  "condition": {
    "field": "body",
    "keywords": ["免费", "中奖", "领奖"]
  }
}
```

### 2. regex_match - 正则匹配
```json
{
  "type": "regex_match",
  "condition": {
    "field": "subject",
    "pattern": "FREE.*MONEY|CLICK.*HERE"
  }
}
```

### 3. sender_domain - 发件人域名
```json
{
  "type": "sender_domain",
  "condition": {
    "domains": ["example.com", "test.org"]
  }
}
```

### 4. attachment_name - 附件名匹配
```json
{
  "type": "attachment_name",
  "condition": {
    "pattern": "invoice.*\\.exe|document.*\\.scr"
  }
}
```

## 发件人声誉系统

### 声誉计算
- 初始声誉: 50分
- 范围: 0-100分
- 正确分类反馈: +5分
- 错误分类反馈: -10分
- 声誉随时间衰减（30天周期）

### 声誉等级
- 80-100: 优秀 - 信任发件人
- 60-79: 良好 - 正常处理
- 40-59: 一般 - 加强检查
- 0-39: 较差 - 重点监控

## 开发说明

### 初始化默认黑名单
首次运行后，建议添加一些默认黑名单关键词:

```bash
curl -X POST http://localhost:5000/api/blacklist/keywords \
  -H "Content-Type: application/json" \
  -d '{"value": "free money"}'
```

### 模型持久化
- 模型文件默认存储在 `./models/` 目录
- 首次运行自动初始化模型
- 可通过API重新训练模型

## 部署建议

### 生产环境
- 使用Gunicorn或uWSGI作为WSGI服务器
- 配置Nginx反向代理
- 使用独立的Redis实例
- 配置Celery多Worker处理

### 监控
- 监控Redis内存使用
- 监控Celery任务队列长度
- 监控API响应时间和错误率

## License

MIT License
