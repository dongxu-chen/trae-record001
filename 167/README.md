# FastAPI 任务调度系统

一个基于 FastAPI 的任务调度系统，支持 6 字段 cron 表达式调度，可执行 Shell 或 Python 脚本，具备超时中断、自动重试、任务依赖和 Webhook 通知功能。

## 功能特性

- **任务管理**: 创建、读取、更新、删除任务
- **调度引擎**: 基于 APScheduler，支持 6 字段 cron 表达式（含秒）
- **脚本执行**: 支持 Shell 和 Python 脚本，支持超时中断
- **自动重试**: 任务失败后可自动重试，可配置重试次数和延迟
- **任务依赖**: 支持任务间依赖关系，依赖任务成功后才执行
- **Webhook 通知**: 任务完成后自动发送通知
- **日志管理**: 完整记录任务执行历史，支持按大小和时间轮转
- **RESTful API**: 完整的 API 接口
- **实时调度**: 支持任务暂停、恢复和立即执行

## 项目结构

```
.
├── main.py              # FastAPI 主应用
├── database.py          # 数据库配置
├── models.py            # SQLAlchemy 数据模型
├── schemas.py           # Pydantic 数据验证
├── crud.py              # 数据库操作
├── scheduler.py         # 调度引擎
├── executor.py          # 脚本执行器（含超时中断）
├── webhook.py           # Webhook 通知模块
├── log_rotation.py      # 日志轮转管理
├── log_config.py        # 日志配置
├── requirements.txt     # 依赖包
└── task_scheduler.db    # SQLite 数据库（自动生成）
```

## 安装运行

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 启动服务：
```bash
python main.py
```

3. 访问 API 文档：
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API 接口

### 任务管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/tasks/` | 创建任务 |
| GET | `/tasks/` | 获取所有任务 |
| GET | `/tasks/{id}` | 获取任务详情 |
| PUT | `/tasks/{id}` | 更新任务 |
| DELETE | `/tasks/{id}` | 删除任务 |

### 任务依赖管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/tasks/{id}/dependencies/{dep_id}` | 添加任务依赖 |
| DELETE | `/tasks/{id}/dependencies/{dep_id}` | 移除任务依赖 |
| GET | `/tasks/{id}/dependencies` | 获取任务依赖列表 |
| GET | `/tasks/{id}/dependents` | 获取依赖此任务的任务列表 |

### 任务操作

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/tasks/{id}/execute` | 立即执行任务 |
| POST | `/tasks/{id}/pause` | 暂停任务调度 |
| POST | `/tasks/{id}/resume` | 恢复任务调度 |

### 日志管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/logs/` | 获取所有日志 |
| GET | `/tasks/{id}/logs/` | 获取指定任务的日志 |
| POST | `/logs/cleanup` | 手动触发日志清理 |
| GET | `/logs/stats` | 获取日志统计信息 |

### Webhook

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/webhook/test` | 测试 Webhook 连接 |

### 调度器

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/scheduler/jobs` | 获取当前调度的任务 |

## 使用示例

### 1. 创建带重试和 Webhook 的任务

```bash
curl -X POST "http://localhost:8000/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "数据同步任务",
    "description": "每分钟执行，失败后重试3次",
    "task_type": "python",
    "script_content": "import datetime\nprint(\"Current time:\", datetime.datetime.now())",
    "cron_expression": "0 * * * * *",
    "timeout": 60,
    "retry_count": 3,
    "retry_delay": 30,
    "webhook_url": "https://your-webhook-url.com/notify",
    "webhook_method": "POST",
    "webhook_headers": {"Authorization": "Bearer your-token"},
    "is_active": true
  }'
```

### 2. 创建任务依赖链

```bash
# 创建任务1
curl -X POST "http://localhost:8000/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "第一步 - 数据下载",
    "task_type": "shell",
    "script_content": "echo downloading data...",
    "cron_expression": "0 0 * * * *",
    "timeout": 300,
    "retry_count": 2,
    "is_active": true
  }'

# 创建任务2并设置依赖任务1
curl -X POST "http://localhost:8000/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "第二步 - 数据处理",
    "task_type": "python",
    "script_content": "print(\"processing data...\")",
    "cron_expression": "0 0 * * * *",
    "timeout": 600,
    "is_active": true,
    "dependency_ids": [1]
  }'

# 或者后续添加依赖
curl -X POST "http://localhost:8000/tasks/2/dependencies/1"
```

### 3. 立即执行任务

```bash
curl -X POST "http://localhost:8000/tasks/1/execute"
```

### 4. 查看日志统计

```bash
curl "http://localhost:8000/logs/stats"
```

### 5. 测试 Webhook

```bash
curl -X POST "http://localhost:8000/webhook/test" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-webhook-url.com/test",
    "method": "POST",
    "headers": {"Content-Type": "application/json"}
  }'
```

## Cron 表达式格式

```
* * * * * *
│ │ │ │ │ │
│ │ │ │ │ └── 星期 (0-6, 0=周日)
│ │ │ │ └──── 月份 (1-12)
│ │ │ └────── 日期 (1-31)
│ │ └──────── 小时 (0-23)
│ └────────── 分钟 (0-59)
└──────────── 秒 (0-59)
```

常用示例：
- `*/5 * * * * *` - 每 5 秒
- `0 * * * * *` - 每分钟
- `0 0 * * * *` - 每小时
- `0 0 9 * * *` - 每天早上 9 点
- `0 0 9 * * 1-5` - 工作日早上 9 点
- `0 */30 9-18 * * *` - 每天 9-18 点每 30 分钟

## 超时配置

- 每个任务可以独立配置超时时间（秒）
- 默认超时：300 秒（5 分钟）
- 超时范围：1 - 3600 秒
- 超时时会强制终止进程及其子进程

## 重试配置

- `retry_count`: 最大重试次数（0-10，默认 0）
- `retry_delay`: 重试延迟秒数（默认 60 秒）
- 重试会记录在任务日志中，每次重试有独立的日志记录

## 任务依赖

- 支持任务间建立依赖关系
- 只有所有依赖任务成功执行后，才会触发当前任务
- 循环依赖检测（任务不能依赖自己）
- 支持链式依赖：A → B → C

## Webhook 通知

当任务配置了 `webhook_url` 时，任务执行完成（成功或失败）后会自动发送通知。

通知 payload 格式：
```json
{
  "event": "task_execution",
  "task_id": 1,
  "task_name": "任务名称",
  "status": "success | failed",
  "started_at": "2024-01-01T00:00:00",
  "completed_at": "2024-01-01T00:00:05",
  "execution_time": 5,
  "retry_attempt": 0,
  "output": "脚本输出",
  "error": "错误信息（失败时）",
  "triggered_by": null,
  "timestamp": "2024-01-01T00:00:05"
}
```

## 日志轮转配置

在 `log_config.py` 中配置，或通过环境变量配置：

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| max_logs_per_task | LOG_MAX_LOGS_PER_TASK | 100 | 每个任务保留的最大日志数 |
| max_log_age_days | LOG_MAX_LOG_AGE_DAYS | 30 | 日志保留天数（null 表示不限制） |
| max_total_logs | LOG_MAX_TOTAL_LOGS | 10000 | 全局最大日志总数 |
| enable_rotation | LOG_ENABLE_ROTATION | true | 是否启用日志轮转 |

日志轮转触发时机：
1. 每次创建新日志时自动检查
2. 每天凌晨 1 点定时清理
3. 手动调用 `/logs/cleanup` API

## 技术栈

- **FastAPI**: Web 框架
- **SQLAlchemy**: ORM
- **SQLite**: 数据库
- **APScheduler**: 任务调度
- **Pydantic**: 数据验证
- **Pydantic Settings**: 配置管理
- **HTTPX**: 异步 HTTP 客户端