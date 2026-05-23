# 销售数据可视化仪表板

基于 FastAPI + ECharts 实现的电商销售数据可视化仪表板

## 功能特性

- 📊 **核心指标卡片**: 总销售额、订单数、客单价、日环比增长率
- 📈 **每日销售额趋势**: 折线图展示销售额和订单数趋势
- 🥧 **各品类销售占比**: 饼图展示不同品类的销售分布
- 🏆 **各区域销售排行**: 柱状图展示各区域销售情况
- 🔍 **数据筛选**: 支持按日期范围和品类筛选数据，变更自动触发查询

## 性能优化

### 后端优化
- ✅ **数据库复合索引**: 添加 `idx_date_category`、`idx_date_region`、`idx_date_category_region` 索引
- ✅ **SQL聚合查询**: 使用单个聚合查询替代多次查询，减少数据传输量
- ✅ **合并API接口**: 新增 `/api/all-data` 接口，一次请求返回所有图表数据
- ✅ **双增长率计算**: 同时计算日环比（今日vs昨日）和期间环比

### 前端优化
- ✅ **ECharts增量更新**: 使用 `setOption({notMerge: false, lazyUpdate: true})` 仅更新变化数据
- ✅ **筛选联动**: 筛选条件变更自动触发数据刷新，带300ms防抖
- ✅ **数值动画**: 指标卡片数值平滑过渡动画
- ✅ **加载状态**: 数据请求时显示加载指示器

## 技术栈

- **后端**: Python + FastAPI + SQLAlchemy
- **前端**: HTML + CSS + ECharts
- **数据库**: MySQL

## 快速开始

### 1. 环境要求

- Python 3.8+
- MySQL 5.7+

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置数据库

编辑 `.env` 文件，配置MySQL连接信息：

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=sales_dashboard
```

### 4. 生成模拟数据

首次运行需要生成模拟数据：

```bash
python generate_data.py
```

这将创建数据库并生成90天的模拟订单数据。

### 5. 启动服务

```bash
python main.py
```

或直接运行 `start.bat`

### 6. 访问仪表板

在浏览器中打开: http://localhost:8000

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/summary` | GET | 获取汇总数据 |
| `/api/daily-sales` | GET | 获取每日销售趋势 |
| `/api/category-sales` | GET | 获取各品类销售数据 |
| `/api/region-sales` | GET | 获取各区域销售数据 |
| `/api/categories` | GET | 获取品类列表 |

### 查询参数

- `start_date`: 开始日期 (YYYY-MM-DD)
- `end_date`: 结束日期 (YYYY-MM-DD)
- `category`: 品类筛选

## 项目结构

```
.
├── main.py              # FastAPI主程序
├── database.py          # 数据库连接配置
├── models.py            # 数据模型定义（含复合索引）
├── generate_data.py     # 模拟数据生成脚本
├── migrate.py           # 数据库索引迁移脚本
├── requirements.txt     # Python依赖包
├── .env                 # 环境变量配置
├── start.bat            # Windows启动脚本
├── README.md            # 项目说明文档
└── static/
    └── index.html       # 前端页面（增量更新版）
```

## 数据字段说明

订单表包含以下字段：
- order_id: 订单编号
- order_date: 订单日期
- category: 商品品类
- region: 销售区域
- product_name: 商品名称
- quantity: 数量
- unit_price: 单价
- total_amount: 总金额
- customer_id: 客户ID
