# 消息中心聚合服务

聚合多个消息渠道的收件箱（邮件、钉钉、企业微信、Slack），提供统一接口进行消息管理。

## 功能特性

- **多渠道聚合**：统一管理邮件、钉钉、企业微信、Slack 等多个消息渠道
- **消息去重**：智能识别同一消息在多渠道的推送，自动合并
- **消息分类**：自动将消息分类为通知、审批、告警等类型
- **统一 API**：提供 RESTful API 进行消息拉取、标记已读/未读等操作
- **聚合推送**：定时汇总未读消息，推送到指定渠道
- **优先级管理**：支持消息优先级标识和排序
- **AI 智能摘要**：自动为长消息生成简洁摘要，支持中英文
- **智能提醒置顶**：识别待审批、待处理等重要消息，自动置顶提醒
- **模板解析**：自动识别消息模板，提取关键字段生成结构化卡片展示

## 技术栈

- **Node.js** - 服务端运行环境
- **Express** - Web 框架
- **MongoDB** - 消息数据持久化存储
- **Redis** - 缓存和去重
- **node-cron** - 定时任务调度

## 项目结构

```
src/
├── adapters/              # 渠道适配器
│   ├── BaseAdapter.js     # 适配器基类
│   ├── EmailAdapter.js    # 邮件适配器
│   ├── DingTalkAdapter.js # 钉钉适配器
│   ├── WeWorkAdapter.js   # 企业微信适配器
│   ├── SlackAdapter.js    # Slack 适配器
│   └── AdapterFactory.js  # 适配器工厂
├── config/                # 配置模块
│   └── index.js           # 配置加载
├── controllers/           # 控制器
│   ├── messageController.js
│   ├── channelController.js
│   ├── preferenceController.js
│   └── aggregationController.js
├── db/                    # 数据库连接
│   ├── mongoose.js        # MongoDB 连接
│   └── redis.js           # Redis 连接
├── models/                # 数据模型
│   ├── Message.js         # 消息模型
│   ├── Channel.js         # 渠道模型
│   ├── UserPreference.js  # 用户偏好模型
│   └── AggregationLog.js  # 聚合日志模型
├── routes/                # 路由
│   ├── messages.js
│   ├── channels.js
│   ├── preferences.js
│   └── aggregation.js
├── services/              # 业务服务
│   ├── MessageService.js       # 消息服务
│   ├── DeduplicationService.js # 去重服务
│   ├── ClassificationService.js # 分类服务
│   └── AggregationService.js   # 聚合服务
├── utils/                 # 工具类
│   └── logger.js          # 日志工具
└── app.js                 # 应用入口
scripts/
└── init-channels.js       # 初始化渠道脚本
```

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的配置信息：

```bash
cp .env.example .env
```

### 3. 初始化数据库渠道

```bash
node scripts/init-channels.js
```

### 4. 启动服务

```bash
# 开发模式
npm run dev

# 生产模式
npm start
```

服务默认运行在 `http://localhost:3000`

## API 文档

### 消息接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/messages` | 获取消息列表 |
| GET | `/api/messages/:messageId` | 获取消息详情 |
| GET | `/api/messages/stats` | 获取消息统计 |
| GET | `/api/messages/unread-count` | 获取未读消息数 |
| GET | `/api/messages/fetch` | 从渠道拉取消息 |
| POST | `/api/messages/:messageId/read` | 标记消息已读 |
| POST | `/api/messages/:messageId/unread` | 标记消息未读 |
| POST | `/api/messages/mark-all-read` | 批量标记已读 |
| POST | `/api/messages/:messageId/archive` | 归档消息 |
| DELETE | `/api/messages/:messageId` | 删除消息 |

### 渠道接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/channels` | 获取渠道列表 |
| POST | `/api/channels` | 创建渠道 |
| GET | `/api/channels/:id` | 获取渠道详情 |
| PUT | `/api/channels/:id` | 更新渠道配置 |
| DELETE | `/api/channels/:id` | 删除渠道 |
| POST | `/api/channels/:id/test` | 测试渠道连接 |
| POST | `/api/channels/:id/sync` | 同步渠道消息 |

### 聚合接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/aggregation/status` | 获取聚合服务状态 |
| GET | `/api/aggregation/logs` | 获取聚合日志 |
| POST | `/api/aggregation/trigger` | 触发聚合推送 |
| POST | `/api/aggregation/run` | 运行全局聚合任务 |

### 偏好接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/preferences/:userId?` | 获取用户偏好 |
| PUT | `/api/preferences/:userId?` | 更新用户偏好 |
| POST | `/api/preferences/:userId?/reset` | 重置用户偏好 |

## 核心功能说明

### 消息去重

系统使用两级去重策略：

1. **精确去重**：基于消息内容哈希值，30分钟内完全相同的消息会被自动合并
2. **相似去重**：使用编辑距离算法识别相似消息，相似度超过80%的消息会被合并

### 消息分类

基于关键词匹配的自动分类：

- **通知**：公告、提醒、系统通知等
- **审批**：请假、报销、合同审批等
- **告警**：错误、异常、故障告警等
- **其他**：无法分类的消息

### 聚合推送

定时汇总未读消息，支持推送到：

- 钉钉 Webhook
- 企业微信 Webhook
- Slack Webhook
- 邮件

## 配置说明

### 消息渠道配置

每个渠道需要在 `.env` 文件中配置对应的认证信息，然后运行初始化脚本创建渠道记录。

### 聚合推送配置

- `AGGREGATION_CRON`: 聚合任务执行时间，默认每30分钟执行一次
- `AGGREGATION_ENABLED`: 是否启用聚合推送

### 去重配置

- `DEDUP_WINDOW_MINUTES`: 去重时间窗口，默认30分钟
- `DEDUP_SIMILARITY_THRESHOLD`: 相似度阈值，默认0.8

## 开发说明

### 添加新的消息渠道

1. 在 `src/adapters/` 目录下创建新的适配器类，继承 `BaseAdapter`
2. 实现 `connect()`, `fetchMessages()`, `markAsRead()`, `normalizeMessage()` 等方法
3. 在 `AdapterFactory.js` 中注册新适配器
4. 在 `Channel.js` 模型中添加新的渠道类型

### 扩展消息分类

1. **添加训练数据**：在 `src/data/training_data.txt` 中添加标注数据，格式为 `__label__category 文本内容`
2. **添加同义词**：在 `src/data/synonyms.json` 中添加同义词映射
3. **动态添加**：通过 API 接口 `/api/classification/keywords` 和 `/api/classification/synonyms` 动态添加
4. **重新训练**：服务启动时会自动训练，也可以通过 API 触发重新训练

### 添加新的消息模板

在 `src/data/message_templates.json` 中添加新的模板配置：

```json
{
  "name": "template_name",
  "displayName": "模板显示名称",
  "category": "approval",
  "icon": "icon-name",
  "color": "#3b82f6",
  "priority": "high",
  "matchPatterns": ["关键词1", "关键词2"],
  "extractRules": {
    "fieldName": {
      "pattern": "正则表达式",
      "type": "string"
    }
  },
  "cardLayout": [
    { "key": "fieldName", "label": "字段显示名", "showInCard": true }
  ],
  "actionButtons": [
    { "action": "approve", "label": "同意", "style": "primary" }
  ]
}
```

也可以通过 API 接口 `/api/messages/enhanced/templates` 动态添加。

## 许可证

MIT
