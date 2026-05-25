# 服务器配置管理工具

一个功能完整的服务器配置管理工具，支持批量SSH操作、文件分发、模板渲染、任务调度和变更回滚。

## 功能特性

- **批量SSH命令执行**: 同时在多台服务器上执行命令
- **SSH连接池复用**: 减少握手开销，提高批量操作性能
- **并发执行控制**: 可配置并发数，防止目标服务器过载
- **文件分发**: 批量上传文件到多台服务器
- **配置模板渲染**: 使用Jinja2模板引擎渲染配置文件
- **Shell安全转义**: 防止命令注入攻击
- **执行结果差异对比**: 变更前后配置Diff展示
- **主机分组管理**: 按分组管理主机，支持批量操作
- **操作审计**: 完整记录所有操作日志
- **多版本回滚**: 保留历史版本，支持任意版本回退
- **版本对比**: diff两个历史版本的差异
- **Web Terminal**: 浏览器内交互式SSH终端
- **异步任务**: 使用Celery + Redis实现异步任务处理

## 技术栈

- Python 3.8+
- Paramiko: SSH客户端
- Jinja2: 模板引擎
- Celery: 分布式任务队列
- Redis: 消息代理和结果存储
- Click: 命令行界面
- Flask + Flask-SocketIO: Web服务和实时通信
- xterm.js: Web终端前端

## 安装

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 配置环境变量:
```bash
cp .env.example .env
```

3. 启动Redis服务

4. 启动Celery Worker:
```bash
celery -A celery_config worker --loglevel=info
```

## 使用说明

### 主机管理

添加主机:
```bash
python cli.py host add --hostname web01 --ip 192.168.1.10 --username root --password yourpass --groups web
```

列出主机:
```bash
python cli.py host list
```

列出分组:
```bash
python cli.py host groups
```

### 批量执行命令

在web分组的所有主机上执行命令（默认使用连接池）:
```bash
python cli.py exec command "@web" "uptime"
```

不使用连接池执行:
```bash
python cli.py exec command "@web" "uptime" --no-pool
```

在指定主机上执行命令:
```bash
python cli.py exec command "web01,web02" "df -h"
```

### 文件分发

分发文件到多台主机（默认版本化备份）:
```bash
python cli.py file distribute "@web" ./local_file.txt /tmp/remote_file.txt
```

禁用版本化备份:
```bash
python cli.py file distribute "@web" ./local_file.txt /tmp/remote_file.txt --no-versioned
```

### 模板渲染

列出可用模板:
```bash
python cli.py template list
```

渲染模板并分发:
```bash
python cli.py template distribute "@web" nginx.conf.j2 /etc/nginx/nginx.conf --context '{"worker_processes": "4", "gzip": "on"}'
```

启用自动Shell转义（防止注入）:
```bash
python cli.py template distribute "@web" script.sh.j2 /tmp/script.sh --auto-escape --context '{"user_input": "some value"}'
```

### 连接池管理

查看连接池状态:
```bash
python cli.py pool stats
```

关闭所有连接:
```bash
python cli.py pool close
```

### 差异对比

对比两个文本文件:
```bash
python cli.py diff text --old old.txt --new new.txt
```

对比文本内容:
```bash
python cli.py diff text --old-content "line1\nline2" --new-content "line1\nline2\nline3"
```

JSON格式输出:
```bash
python cli.py diff text --old old.txt --new new.txt --format json
```

### 版本管理

创建文件版本:
```bash
python cli.py version create web01 /etc/nginx/nginx.conf --description "修改前备份"
```

查看文件版本历史:
```bash
python cli.py version list web01 /etc/nginx/nginx.conf
```

查看所有版本:
```bash
python cli.py version list-all
```

恢复到指定版本:
```bash
python cli.py version restore web01 /etc/nginx/nginx.conf <version_id>
```

对比两个版本差异:
```bash
python cli.py version diff web01 /etc/nginx/nginx.conf <version_id1> <version_id2>
```

删除版本:
```bash
python cli.py version delete web01 /etc/nginx/nginx.conf <version_id>
```

### 任务管理

查看任务状态:
```bash
python cli.py task status <group_id>
```

### 审计日志

查看审计日志:
```bash
python cli.py audit logs
```

查看指定任务的日志:
```bash
python cli.py audit logs --task-id <task_id>
```

### 任务回滚

列出可回滚的任务:
```bash
python cli.py rollback list
```

执行任务回滚:
```bash
python cli.py rollback execute <task_id>
```

### Web服务和Web Terminal

启动Web服务:
```bash
python cli.py web start
```

指定端口启动:
```bash
python cli.py web start --port 8080
```

访问地址:
- 首页: http://localhost:5000
- Web Terminal: http://localhost:5000/terminal

## Web Terminal功能

- 浏览器内交互式SSH终端
- 实时命令输入和输出
- 终端自适应窗口大小
- 支持复制粘贴
- 内置Diff对比工具

## 并发控制

### 配置选项

在 `.env` 中配置:
```
BATCH_CONCURRENCY=5    # 批量操作最大并发数
HOST_CONCURRENCY=2     # 单主机最大并发连接数
```

### 并发特性

- **全局并发限制**: 防止同时发起过多SSH连接
- **单主机并发限制**: 防止单个服务器过载
- **分批执行**: 支持按批次执行任务，批次间可配置延迟
- **速率限制**: 支持调用频率限制

## 安全特性

### Shell转义过滤器

模板中可用的安全过滤器:

```jinja2
{# 基本Shell转义 #}
{{ user_input | shell_escape }}

{# 路径转义 #}
{{ file_path | shell_escape_path }}

{# 文件名清理 #}
{{ filename | sanitize_filename }}

{# 双引号转义 #}
{{ value | escape_double_quotes }}

{# 单引号转义 #}
{{ value | escape_single_quotes }}

{# 命令清理（移除危险字符） #}
{{ cmd | sanitize_command }}
```

示例模板 (`templates/script.sh.j2`):
```bash
#!/bin/bash
# 安全使用用户输入
USER_NAME={{ username | shell_escape }}
FILE_PATH={{ log_path | shell_escape_path }}

echo "Hello, $USER_NAME"
cat "$FILE_PATH"
```

### 自动转义

使用 `--auto-escape` 选项自动对所有字符串变量进行Shell转义:
```bash
python cli.py template distribute @web script.sh.j2 /tmp/script.sh --auto-escape --context '{"username": "test; rm -rf /"}'
```

## 项目结构

```
.
├── core/
│   ├── __init__.py
│   ├── host_manager.py      # 主机管理
│   ├── ssh_client.py        # SSH客户端
│   ├── ssh_pool.py          # SSH连接池
│   ├── concurrency.py       # 并发执行控制
│   ├── template_renderer.py # 模板渲染（含安全过滤）
│   ├── file_distributor.py  # 文件分发
│   ├── diff_tool.py         # 差异对比工具
│   ├── audit.py             # 审计日志
│   ├── rollback.py          # 多版本回滚管理
│   └── tasks/
│       ├── __init__.py
│       └── execution_tasks.py  # Celery任务
├── web/
│   ├── __init__.py
│   ├── app.py               # Flask Web应用
│   ├── ssh_session.py       # SSH会话管理
│   ├── templates/           # 前端模板
│   │   ├── index.html
│   │   └── terminal.html
│   └── static/              # 静态资源
├── templates/               # Jinja2配置模板目录
│   ├── nginx.conf.j2
│   ├── hosts.j2
│   └── script.sh.j2         # 安全转义示例
├── data/                    # 数据目录
│   ├── hosts.json           # 主机配置
│   ├── audit.log            # 审计日志
│   └── rollback/            # 回滚信息
│       └── versions.json    # 版本索引
├── cli.py                   # 命令行接口
├── config.py                # 配置文件
├── celery_config.py         # Celery配置
└── requirements.txt         # 依赖列表
```

## 性能优化

### 连接池优势

- **减少握手开销**: 批量操作时复用已建立的SSH连接
- **连接复用**: 同一主机的多个操作共享同一连接
- **活性检测**: 自动检测并清理失效连接
- **空闲超时**: 自动关闭长时间空闲的连接

### 并发控制优势

- **防止过载**: 限制并发数保护目标服务器
- **批量处理**: 支持大批量任务的分批执行
- **灵活配置**: 可根据实际情况调整并发参数
