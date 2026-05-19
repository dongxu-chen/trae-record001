# 数据库死锁自动诊断器

一个基于 Python + pymysql 的数据库死锁自动诊断工具，提供死锁分析、可视化依赖图、SQL指纹提取、历史报告和自动kill功能。

## ✨ 新功能

### 1. 增强的死锁解析器
- 支持ROW格式的binlog完整信息提取
- 提取事务ID、锁模式、索引、表名等完整信息
- 提取锁的物理记录信息（space id、page no等）
- 识别死锁牺牲者

### 2. HTML+SVG交互式依赖图
- 支持拖拽移动节点
- 悬停显示事务详情（线程ID、SQL、锁信息）
- 缩放功能
- 切换标签显示
- 统计信息展示
- 优雅的可视化设计

### 3. 增强的SQL指纹
- 使用正则表达式归一化常量
- 支持字符串、数字、十六进制值替换
- IN子句和VALUES子句的智能归一化
- 关键字大小写标准化
- 空格规范化

### 4. 自动Kill功能
- 可配置的超时阈值
- 自动检测并终止阻塞事务
- 自动检测并终止长运行事务
- 支持排除特定用户
- 诊断模式（仅查看，不执行）
- 执行模式（自动kill）

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

复制 `.env.example` 为 `.env` 并修改数据库连接配置：

```env
# 数据库连接
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=information_schema

# 自动Kill配置
AUTO_KILL_ENABLED=false
AUTO_KILL_THRESHOLD_SECONDS=30
AUTO_KILL_EXCLUDE_USERS=root,replication

# Binlog配置
BINLOG_FORMAT=ROW
ENABLE_BINLOG_PARSING=false
```

## 使用方法

### 1. 分析当前死锁
```bash
python main.py analyze
```

该命令会：
- 连接到 MySQL 数据库
- 获取 INNODB 状态
- 解析死锁信息（事务ID、锁模式、索引、表名等）
- 保存死锁记录到历史文件
- 生成交互式HTML依赖图

### 2. 生成 SQL 指纹
```bash
python main.py fingerprint "SELECT * FROM users WHERE id = 123 AND name = 'test'"
```

输出示例：
```
============================================================
🔑 SQL指纹分析结果
============================================================
原始SQL: SELECT * FROM users WHERE id = 123 AND name = 'test'

SQL指纹: SELECT * FROM users WHERE id = ? AND name = ?
哈希值: a1b2c3d4e5f6...
查询类型: SELECT
涉及表: users
```

### 3. 生成死锁依赖图
```bash
# 使用当前死锁数据
python main.py graph

# 使用示例数据（测试用）
python main.py graph --use-sample
```

交互功能：
- 🖱️ 拖拽节点调整位置
- 🔍 悬停查看事务详情
- ➕/➖ 缩放视图
- 🏷️ 切换标签显示

### 4. 生成历史死锁报告
```bash
python main.py report
```

HTML报告包含：
- 死锁统计概览
- 涉及表统计
- 查询类型统计
- 高频SQL指纹
- 死锁历史记录详情

### 5. 添加示例死锁数据
```bash
python main.py add-sample
```

用于在没有真实死锁时测试报告生成功能。

### 6. 查看诊断器状态
```bash
python main.py status
```

### 7. 自动Kill功能
```bash
# 诊断模式：仅查看事务状态，不执行终止
python main.py auto-kill --diagnose

# 执行模式：自动终止超过阈值的事务
python main.py auto-kill --execute

# 手动终止指定线程
python main.py auto-kill --kill 12345
```

## 项目结构

```
.
├── config.py                  # 配置管理
├── deadlock_analyzer.py       # 增强的死锁日志分析模块
├── sql_fingerprint.py         # 增强的SQL指纹提取模块
├── dependency_graph.py        # HTML+SVG交互式依赖图模块
├── deadlock_report.py         # 历史死锁报告模块
├── auto_kill.py              # 自动Kill管理模块
├── main.py                   # 主程序入口
├── requirements.txt          # 依赖列表
├── .env.example              # 环境变量配置示例
└── README.md                 # 说明文档
```

## 输出文件

| 文件 | 说明 |
|------|------|
| `deadlock_history.json` | 死锁历史记录（JSON格式） |
| `deadlock_dependency_graph.html` | 交互式死锁依赖图 |
| `deadlock_report.html` | 完整的HTML死锁分析报告 |

## 模块说明

### DeadlockAnalyzer
- 连接 MySQL 数据库
- 获取 INNODB 状态
- 解析死锁事务信息（支持ROW格式）
- 提取锁信息：
  - 锁类型（RECORD/TABLE）
  - 锁模式（X/S/IX/IS等）
  - 表名和索引名
  - Space ID、Page No、Heap No
  - 物理记录数据
- 提供进程列表和锁等待信息查询

### SQLFingerprint
- SQL语句归一化：
  - 字符串常量替换
  - 数字常量替换（整数、浮点数、十六进制）
  - NULL/TRUE/FALSE替换
  - IN子句归一化
  - VALUES子句归一化
- 生成MD5哈希
- 提取SQL中涉及的表名
- 分类查询类型
- 空格规范化

### DependencyGraph
- 使用SVG绘制有向图
- 展示事务之间的等待关系
- 支持拖拽交互
- 悬停显示详情工具提示
- 缩放和标签切换
- 统计信息展示

### DeadlockReport
- 死锁历史的持久化存储
- 统计分析（表、查询类型、SQL指纹）
- 生成美观的HTML报告

### AutoKillManager
- 自动检测阻塞事务
- 自动检测长运行事务
- 可配置的超时阈值
- 用户排除列表
- 诊断和执行两种模式
- Kill历史记录

## 注意事项

⚠️ **重要提醒**

1. 需要有访问 `information_schema` 数据库的权限
2. 需要执行 `SHOW ENGINE INNODB STATUS` 的权限
3. 自动Kill功能默认禁用，启用前请充分测试
4. 建议定期清理历史记录文件
5. KILL操作需要PROCESS权限

## 故障排查

### 连接错误
- 检查 `.env` 文件中的数据库配置
- 确认MySQL服务正在运行
- 验证用户名和密码

### 权限错误
```sql
-- 授予必要权限
GRANT PROCESS ON *.* TO 'your_user'@'localhost';
GRANT SELECT ON information_schema.* TO 'your_user'@'localhost';
```

### 未检测到死锁
- 死锁已被MySQL自动处理
- 当前系统中没有发生死锁
- 检查用户权限是否足够

## 许可证

MIT License
