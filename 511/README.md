# 数据血缘自动解析工具

从SQL语句中解析表级、字段级血缘关系，构建数据流图的工具。

## 功能特性

- ✅ **SQL血缘解析** - 自动解析SQL语句中的数据血缘关系
- ✅ **支持复杂SQL** - 支持子查询、CTE(Common Table Expression)、UNION等
- ✅ **表级血缘** - 追踪表之间的数据流转关系
- ✅ **字段级血缘** - 精确追踪字段级别的数据依赖
- ✅ **图数据库存储** - 使用Neo4j存储血缘关系图
- ✅ **可视化查询** - React + ReactFlow实现的交互式血缘图谱
- ✅ **Docker部署** - 一键启动所有服务

## 技术栈

**后端**
- Python 3.11+
- Flask - Web框架
- SQLGlot - SQL解析器
- Neo4j - 图数据库

**前端**
- React 18
- Material UI
- ReactFlow - 图可视化

## 快速开始

### 方式一：Docker启动（推荐）

```bash
# 进入docker目录
cd docker

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

或者在Windows上直接运行：
```
start.bat
```

### 方式二：手动启动

#### 1. 启动Neo4j
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.13-community
```

#### 2. 启动后端
```bash
cd backend
pip install -r requirements.txt
python -m app.main
```

#### 3. 启动前端
```bash
cd frontend
npm install
npm start
```

## 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost:3000 | 主界面 |
| 后端API | http://localhost:5000 | API接口 |
| Neo4j Browser | http://localhost:7474 | 图数据库浏览器 |

默认Neo4j账号密码：`neo4j` / `password`

## API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/parse | 解析SQL（不保存） |
| POST | /api/lineage | 解析SQL并保存血缘 |
| GET | /api/lineage/table/{table_name} | 查询表级血缘 |
| GET | /api/lineage/column/{column_name} | 查询字段级血缘 |
| GET | /api/tables | 获取所有表 |
| GET | /api/tables/{table_name}/columns | 获取表字段 |
| GET | /api/graph | 获取完整图谱 |
| DELETE | /api/database | 清空数据库 |

## 使用示例

### 示例SQL 1: 基础CREATE TABLE AS SELECT

```sql
CREATE TABLE analytics.user_summary
AS
SELECT 
    u.user_id,
    u.user_name,
    COUNT(o.order_id) as order_count,
    SUM(o.amount) as total_amount
FROM raw.users u
JOIN raw.orders o ON u.user_id = o.user_id
GROUP BY u.user_id, u.user_name
```

### 示例SQL 2: CTE复杂查询

```sql
INSERT INTO analytics.monthly_report (user_id, month, revenue)
WITH user_orders AS (
    SELECT 
        user_id,
        order_id,
        amount,
        DATE_TRUNC('month', order_date) as order_month
    FROM raw.orders
    WHERE status = 'completed'
),
user_payments AS (
    SELECT 
        uo.user_id,
        uo.order_month,
        SUM(uo.amount) as monthly_revenue
    FROM user_orders uo
    GROUP BY uo.user_id, uo.order_month
)
SELECT 
    up.user_id,
    up.order_month as month,
    up.monthly_revenue as revenue
FROM user_payments up
JOIN raw.users u ON up.user_id = u.user_id
WHERE u.country = 'CN'
```

### 示例SQL 3: UNION多表合并

```sql
CREATE TABLE unified.transactions
AS
SELECT 
    t1.transaction_id,
    t1.user_id,
    t1.amount,
    t1.created_at,
    'source_a' as source
FROM source_a.transactions t1
WHERE t1.status = 'success'

UNION ALL

SELECT 
    t2.txn_id as transaction_id,
    t2.customer_id as user_id,
    t2.value as amount,
    t2.timestamp as created_at,
    'source_b' as source
FROM source_b.txns t2
WHERE t2.is_valid = 1
```

## 项目结构

```
.
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── models/         # 数据模型
│   │   ├── parsers/        # SQL解析器
│   │   ├── services/       # 服务层
│   │   ├── config.py       # 配置
│   │   └── main.py         # 入口文件
│   └── requirements.txt
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── components/     # 组件
│   │   ├── pages/          # 页面
│   │   ├── services/       # API服务
│   │   └── App.js
│   └── package.json
├── docker/                 # Docker配置
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── start.bat              # Windows启动脚本
└── stop.bat               # Windows停止脚本
```
