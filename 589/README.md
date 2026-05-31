# 🛒 比价达人 - 商品比价导购平台

> 聚合多电商平台商品信息，智能比价，推荐最优购买渠道

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-00a393.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61dafb.svg)](https://react.dev/)
[![Scrapy](https://img.shields.io/badge/Scrapy-2.11+-60a839.svg)](https://scrapy.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178c6.svg)](https://www.typescriptlang.org/)

## ✨ 核心功能

### 🔍 多平台商品聚合
- 支持淘宝、京东、拼多多、苏宁四大主流电商平台
- 分布式爬虫架构，支持高并发数据采集
- 智能数据清洗和去重，确保数据准确性

### 📊 智能比价引擎
- 多维度价格比较（当前价、历史价、券后价）
- 综合评分算法（价格50% + 平台信誉20% + 评分15% + 销量15%）
- 实时计算最优购买渠道

### 📈 价格历史分析
- 支持7天/30天/90天/全年价格走势图表
- 线性回归价格趋势预测
- 月度价格模式分析，推荐最佳购买时机

### 🔔 降价提醒系统
- WebSocket实时推送价格更新
- 自定义目标价格，降价即时通知
- 支持站内推送、邮件、短信多种通知方式

### 🎫 优惠券自动匹配
- 自动识别各平台可用优惠券
- 智能计算最优券组合
- 实时更新券后到手价

## 🏗️ 技术架构

### 后端技术栈
```
Python 3.10+
├── FastAPI 0.109+       # RESTful API框架
├── Scrapy 2.11+         # 分布式爬虫框架
├── SQLAlchemy 2.0+      # ORM框架
├── Pydantic 2.5+        # 数据验证
├── python-socketio 5.10+ # WebSocket实时通信
├── APScheduler 3.10+    # 定时任务调度
├── Pandas 2.1+          # 数据分析
└── NumPy 1.26+          # 数值计算
```

### 前端技术栈
```
React 18+
├── TypeScript 5.8+      # 类型安全
├── Vite 6.3+            # 构建工具
├── Tailwind CSS 3.4+    # 原子化CSS
├── Zustand 5.0+         # 状态管理
├── Recharts 2.12+       # 图表库
├── Socket.IO Client 4.7+ # WebSocket客户端
├── React Router 7.3+    # 路由管理
└── Lucide React 0.511+  # 图标库
```

### 数据库
- **MySQL 8.0+** - 主业务数据存储
- **SQLite 3.x** - 价格历史数据存储
- **Redis 7.x** - 缓存和消息队列

## 📁 项目结构

```
price-comparison-platform/
├── backend/                    # 后端Python服务
│   ├── app/
│   │   ├── api/                # API路由
│   │   │   ├── products.py     # 商品接口
│   │   │   ├── coupon.py       # 优惠券接口
│   │   │   └── alert.py        # 提醒接口
│   │   ├── models/             # 数据模型
│   │   │   ├── product.py      # 商品模型
│   │   │   ├── price.py        # 价格模型
│   │   │   ├── coupon.py       # 优惠券模型
│   │   │   └── alert.py        # 提醒模型
│   │   ├── schemas/            # Pydantic模式
│   │   ├── services/           # 业务服务
│   │   │   ├── price_analyzer.py    # 价格分析引擎
│   │   │   ├── comparator.py       # 智能比价算法
│   │   │   ├── coupon_matcher.py   # 优惠券匹配
│   │   │   └── alert_service.py    # 降价提醒服务
│   │   ├── websocket/          # WebSocket服务
│   │   ├── database.py         # 数据库配置
│   │   └── main.py             # 应用入口
│   ├── crawler/                # Scrapy爬虫
│   │   ├── spiders/            # 爬虫文件
│   │   │   ├── taobao.py       # 淘宝爬虫
│   │   │   ├── jd.py           # 京东爬虫
│   │   │   ├── pdd.py          # 拼多多爬虫
│   │   │   └── suning.py       # 苏宁爬虫
│   │   ├── middlewares.py      # 爬虫中间件
│   │   ├── pipelines.py        # 数据管道
│   │   ├── items.py            # 数据项定义
│   │   └── settings.py         # 爬虫配置
│   ├── scripts/                # 工具脚本
│   │   ├── init_db.py          # 数据库初始化
│   │   ├── mock_data.py        # 模拟数据生成
│   │   └── run_crawler.py      # 爬虫运行脚本
│   ├── requirements.txt        # Python依赖
│   ├── .env                    # 环境配置
│   └── run_crawler.bat         # 爬虫启动脚本
├── frontend/                   # 前端React应用
│   ├── src/
│   │   ├── components/         # 组件
│   │   │   ├── Navbar.tsx           # 导航栏
│   │   │   ├── ProductCard.tsx      # 商品卡片
│   │   │   ├── PriceChart.tsx       # 价格图表
│   │   │   ├── PriceComparisonTable.tsx  # 比价表格
│   │   │   └── PriceAlertModal.tsx  # 提醒弹窗
│   │   ├── pages/              # 页面
│   │   │   ├── Home.tsx            # 首页
│   │   │   ├── SearchResults.tsx   # 搜索结果页
│   │   │   ├── ProductDetail.tsx   # 商品详情页
│   │   │   ├── HotDrops.tsx        # 热门降价页
│   │   │   ├── Coupons.tsx         # 优惠券页
│   │   │   ├── Favorites.tsx       # 我的收藏
│   │   │   └── Alerts.tsx          # 降价提醒
│   │   ├── services/           # 服务层
│   │   │   ├── api.ts              # API服务
│   │   │   └── websocket.ts        # WebSocket服务
│   │   ├── store/              # 状态管理
│   │   │   └── useAppStore.ts
│   │   ├── types/              # 类型定义
│   │   ├── utils/              # 工具函数
│   │   ├── App.tsx             # 应用根组件
│   │   ├── main.tsx            # 入口文件
│   │   └── index.css           # 全局样式
│   ├── package.json            # 前端依赖
│   ├── tailwind.config.js      # Tailwind配置
│   ├── vite.config.ts          # Vite配置
│   └── tsconfig.json           # TypeScript配置
├── start.bat                   # 一键启动脚本
└── README.md                   # 项目说明
```

## 🚀 快速开始

### 环境要求
- Python 3.10+
- Node.js 18+
- MySQL 8.0+ (可选，默认使用SQLite)
- Redis 7.x (可选)

### 一键启动（Windows）

```bash
# 克隆项目
git clone <repository-url>
cd price-comparison-platform

# 一键启动
start.bat
```

### 手动启动

#### 1. 配置后端
```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
# 编辑 .env 文件，配置数据库连接

# 初始化数据库
python -m scripts.init_db

# 生成模拟数据
python -m scripts.mock_data

# 启动后端服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. 配置前端
```bash
cd frontend

# 安装依赖
npm install

# 配置环境变量
copy .env.example .env

# 启动开发服务
npm run dev
```

### 访问地址
- 前端应用: http://localhost:5173
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs
- WebSocket: ws://localhost:8000

## 📡 API接口

### 商品接口
```
GET    /api/products/search              # 搜索商品
GET    /api/products/{id}                # 获取商品详情
GET    /api/products/{id}/prices         # 获取比价结果
GET    /api/products/{id}/history        # 获取价格历史
GET    /api/products/{id}/stats          # 获取价格统计
GET    /api/products/{id}/recommendation # 获取购买建议
GET    /api/products/hot                 # 获取热门降价商品
GET    /api/products/categories          # 获取分类列表
```

### 优惠券接口
```
GET    /api/coupons                      # 获取优惠券列表
POST   /api/coupons/match                # 匹配优惠券
GET    /api/coupons/stats                # 获取优惠券统计
```

### 提醒接口
```
GET    /api/alerts                       # 获取用户提醒列表
POST   /api/alerts                       # 创建降价提醒
DELETE /api/alerts/{id}                  # 删除提醒
PUT    /api/alerts/{id}/deactivate       # 停用提醒
POST   /api/alerts/check                 # 检查降价提醒
```

### 用户接口
```
GET    /api/user/favorites               # 获取收藏列表
POST   /api/user/favorites               # 添加收藏
DELETE /api/user/favorites/{id}          # 取消收藏
```

## 🧠 核心算法

### 智能比价算法
```python
PLATFORM_WEIGHTS = {
    "taobao": {"trust": 0.9, "shipping": 0.85, "return": 0.9},
    "jd": {"trust": 0.95, "shipping": 0.95, "return": 0.9},
    "pdd": {"trust": 0.75, "shipping": 0.8, "return": 0.7},
    "suning": {"trust": 0.85, "shipping": 0.85, "return": 0.85},
}

# 综合得分计算（满分1000）
score = (
    price_score(500) +       # 价格得分（权重50%）
    trust_score(200) +       # 平台信誉（权重20%）
    rating_score(150) +      # 用户评分（权重15%）
    sales_score(100) +       # 销量评分（权重10%）
    coupon_score(50)         # 优惠券（权重5%）
)
```

### 价格趋势预测
```python
def predict_future_price(history, days_ahead=7):
    """使用线性回归预测未来价格"""
    X = np.array(range(len(history))).reshape(-1, 1)
    y = np.array([h.price for h in history])
    
    model = LinearRegression()
    model.fit(X, y)
    
    future_X = np.array([len(history) + days_ahead]).reshape(-1, 1)
    return model.predict(future_X)[0]
```

## 🕷️ 爬虫架构

### 中间件
- **UserAgentMiddleware** - User-Agent随机轮换
- **ProxyMiddleware** - 代理IP池支持
- **RetryMiddleware** - 失败自动重试机制

### 数据管道
- **DataCleaningPipeline** - 数据清洗和格式化
- **DatabasePipeline** - 数据持久化到数据库
- **PriceHistoryPipeline** - 价格历史记录管理

## 🔔 WebSocket事件

```javascript
// 连接WebSocket
const socket = io('ws://localhost:8000');

// 订阅价格更新
socket.emit('subscribe', { productId: 'prod-001' });

// 监听价格更新
socket.on('price_update', (data) => {
    console.log('价格更新:', data);
});

// 监听降价提醒
socket.on('price_alert', (alert) => {
    console.log('降价提醒:', alert);
});
```

## 🛡️ 安全特性

- SQL注入防护（SQLAlchemy ORM）
- XSS防护（输入验证和输出编码）
- CORS跨域配置
- API速率限制
- 敏感信息脱敏
- 环境变量配置管理

## 📊 性能优化

- Redis缓存热点数据
- 数据库索引优化
- 前端代码分割和懒加载
- 图片懒加载和压缩
- WebSocket连接复用
- 爬虫并发控制和限速

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 开发规范

### 后端
- 遵循 PEP 8 代码规范
- 使用类型注解
- 编写单元测试
- API文档自动生成

### 前端
- 遵循 React 最佳实践
- TypeScript 严格模式
- 组件化开发
- 响应式设计

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙋‍♂️ 常见问题

**Q: 爬虫会不会被封IP？**
A: 内置了User-Agent轮换、代理IP支持、自动重试和请求限速机制，降低被封风险。

**Q: 价格数据更新频率是多少？**
A: 默认每5分钟检查一次价格变动，可通过配置调整。

**Q: 支持哪些通知方式？**
A: 目前支持站内推送和邮件通知，短信通知需要配置短信服务。

**Q: 可以自定义比价规则吗？**
A: 可以在 `backend/app/services/comparator.py` 中调整权重和评分规则。

## 📞 联系我们

- 项目地址: [GitHub Repository]
- 问题反馈: [Issues]
- 邮箱: contact@example.com

---

⭐ 如果这个项目对您有帮助，请给个Star支持一下！
