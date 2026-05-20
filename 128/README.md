# 敏捷项目管理工具

基于 Django + Celery + WebSocket + PostgreSQL 的全栈敏捷项目管理系统。

## 功能特性

### 1. 看板管理 (Kanban Board)
- 多列表看板视图
- 卡片拖拽排序
- 实时更新 (WebSocket)
- 优先级标记
- 故事点估算
- 负责人分配

### 2. Sprint 管理
- Sprint 创建和规划
- Sprint 状态管理 (规划中/进行中/已完成)
- 卡片关联到 Sprint
- Sprint 时间范围设置

### 3. 燃尽图 (Burndown Chart)
- 自动生成燃尽数据
- 剩余故事点追踪
- 已完成故事点统计
- 每日更新

### 4. 工时登记
- 按卡片登记工时
- 日期和工时记录
- 工作描述
- 个人工时追踪

## 技术栈

- **后端框架**: Django 4.2
- **API**: Django REST Framework
- **数据库**: PostgreSQL
- **异步任务**: Celery + Redis
- **实时通信**: Django Channels + WebSocket
- **前端**: HTML5 + Bootstrap 5 + 原生 JavaScript

## 安装与配置

### 前置要求
- Python 3.8+
- PostgreSQL
- Redis
- virtualenv (推荐)

### 安装步骤

1. **克隆项目并安装依赖**
```bash
cd agile-pm
pip install -r requirements.txt
```

2. **配置环境变量**
复制 `.env.example` 为 `.env` 并修改配置：
```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DB_NAME=agile_pm
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
```

3. **创建数据库**
```sql
CREATE DATABASE agile_pm;
```

4. **执行数据库迁移**
```bash
python manage.py makemigrations
python manage.py migrate
```

5. **创建超级用户**
```bash
python manage.py createsuperuser
```

6. **启动服务**

启动 Django 开发服务器：
```bash
python manage.py runserver
```

启动 Celery Worker：
```bash
celery -A agile_pm worker --loglevel=info
```

启动 Celery Beat (定时任务)：
```bash
celery -A agile_pm beat --loglevel=info
```

7. **访问应用**
- 前端页面: http://localhost:8000
- Admin 后台: http://localhost:8000/admin

## 项目结构

```
agile-pm/
├── agile_pm/              # 项目配置目录
│   ├── __init__.py
│   ├── asgi.py           # ASGI 配置 (WebSocket)
│   ├── celery.py         # Celery 配置
│   ├── settings.py       # Django 配置
│   ├── urls.py           # URL 路由
│   └── wsgi.py           # WSGI 配置
├── core/                  # 核心应用 (项目管理)
├── board/                 # 看板应用
├── sprint/                # Sprint 管理应用
├── timetracking/          # 工时登记应用
├── templates/             # HTML 模板
├── static/                # 静态文件
├── requirements.txt       # Python 依赖
├── .env.example          # 环境变量示例
└── manage.py             # Django 管理脚本
```

## API 端点

### Core (核心)
- `GET /api/core/projects/` - 项目列表
- `POST /api/core/projects/` - 创建项目
- `GET /api/core/users/` - 用户列表

### Board (看板)
- `GET /api/board/boards/` - 看板列表
- `GET /api/board/lists/` - 列表列表
- `GET /api/board/cards/` - 卡片列表
- `POST /api/board/cards/{id}/move/` - 移动卡片
- `GET /api/board/comments/` - 评论列表

### Sprint (迭代)
- `GET /api/sprint/sprints/` - Sprint 列表
- `POST /api/sprint/sprints/{id}/start/` - 开始 Sprint
- `POST /api/sprint/sprints/{id}/complete/` - 完成 Sprint
- `POST /api/sprint/sprints/{id}/generate_burndown/` - 生成燃尽数据

### Time Tracking (工时)
- `GET /api/timetracking/time-entries/` - 工时记录列表
- `POST /api/timetracking/time-entries/` - 登记工时

## WebSocket 连接

连接到看板实时更新：
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/board/{board_id}/');
```

消息类型:
- `card_moved` - 卡片被移动
- `card_updated` - 卡片被更新

## Celery 任务

- `generate_burndown_data(sprint_id)` - 生成指定 Sprint 的燃尽数据
- `update_all_active_sprints_burndown()` - 更新所有活跃 Sprint 的燃尽数据

## 开发说明

### 添加新功能
1. 在对应应用中添加模型
2. 创建序列化器 (serializers)
3. 创建视图 (views)
4. 配置 URL 路由
5. 添加前端交互代码

### 数据库模型关系
- `Project` 1:1 `Board`
- `Board` 1:N `BoardList`
- `BoardList` 1:N `Card`
- `Project` 1:N `Sprint`
- `Sprint` N:N `Card`
- `Card` 1:N `TimeEntry`
- `Card` 1:N `Comment`

## 许可证

MIT License
