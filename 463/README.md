# Slow Query Killer 慢查询自动终止工具

一个用 Go 语言编写的数据库慢查询监控和自动终止工具，保护数据库稳定性。

## 功能特性

- 🔄 **多数据库支持**: 支持 MySQL 和 PostgreSQL 数据库
- ⚡ **实时流式监控**: 100ms 高频检测，实时响应慢查询
- 📈 **趋势预测**: 基于历史数据预测查询执行时间变化，提前识别风险
- 💡 **自动索引建议**: 针对频繁被终止的查询推荐优化索引
- 📋 **审计日志**: 完整记录 KILL 操作和影响评估报告
- ⏳ **事务超时等待**: KILL 前先等待事务自然完成，避免误杀
- 🎯 **智能规则引擎**: 基于阈值、正则表达式等多种规则匹配
- 🛡️ **SQL 指纹白名单**: 基于标准化 SQL 哈希的精确白名单匹配
- 📊 **慢查询分析**: 自动分析和统计慢查询模式
- 📝 **详细日志**: 记录所有被终止的查询信息
- 🧪 **试运行模式**: 支持 dry-run 模式，不实际终止查询

## 架构设计

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Slow Query Killer                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐     ┌──────────────┐     ┌─────────────┐              │
│  │   Monitor    │────►│   Rules      │────►│  Database   │              │
│  │   Engine     │     │   Engine     │     │   Layer     │              │
│  └──────┬───────┘     └──────┬───────┘     └─────────────┘              │
│         │                    │                                           │
│         ▼                    ▼                                           │
│  ┌──────────────┐     ┌──────────────┐                                  │
│  │   Analyzer   │     │   Whitelist  │                                  │
│  │  (SQL指纹)   │     │  (指纹匹配)  │                                  │
│  └──────┬───────┘     └──────────────┘                                  │
│         │                                                               │
│         ├──────────────────────────────────────────────┐                │
│         │                                              │                │
│         ▼                                              ▼                ▼
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐              │
│  │  Predictor   │     │   Indexer    │     │   Auditor    │              │
│  │ (趋势预测)   │     │  (索引建议)  │     │  (审计日志)  │              │
│  └──────────────┘     └──────────────┘     └──────────────┘              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**核心模块说明**：
- **Monitor Engine**: 100ms 实时监控循环，协调各模块工作
- **Rule Engine**: 规则匹配与白名单检查
- **Analyzer**: SQL 标准化与指纹生成
- **Predictor**: 线性回归趋势预测
- **Indexer**: 查询模式分析与索引推荐
- **Auditor**: 操作审计与影响评估

## 快速开始

### 环境要求

- Go 1.18+
- MySQL 5.7+ 或 PostgreSQL 9.6+

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd slow-query-killer

# 下载依赖
go mod tidy

# 编译
go build -o slow-query-killer cmd/slow-query-killer/main.go
```

### 配置

编辑 `configs/config.yaml` 文件：

```yaml
databases:
  primary_mysql:
    type: mysql
    host: localhost
    port: 3306
    user: root
    password: your_password
    dbname: your_database

monitor:
  interval: 10s                    # 扫描间隔
  default_kill_mode: connection    # 默认终止模式 (query/connection)
  dry_run: true                    # 试运行模式

  threshold:
    max_execution_time: 30s        # 默认执行时间阈值

  whitelist:
    users:                         # 用户白名单
      - admin
    databases:                     # 数据库白名单
      - system
    query_prefix:                  # 查询前缀白名单
      - SHOW
      - SET

  rules:                           # 自定义规则
    - name: long_running_select
      enabled: true
      threshold: 60s
      query_regex: "(?i)^SELECT"
      kill_mode: query
```

### 运行

```bash
# 正常运行
./slow-query-killer -config configs/config.yaml

# 试运行模式（只记录不终止）
./slow-query-killer -dry-run

# 查看版本
./slow-query-killer -version

# 查看帮助
./slow-query-killer -help
```

## 核心模块说明

### 1. 配置模块 ([config.go](file:///d:/Trae/project/record001/463/internal/config/config.go))

支持 YAML 配置文件，包含：
- 多数据库连接配置
- 监控参数设置
- 阈值配置
- 白名单配置
- 自定义规则

### 2. 数据库层 ([db.go](file:///d:/Trae/project/record001/463/internal/db/db.go))

统一的数据库接口，支持：
- **MySQL**: 通过 `information_schema.PROCESSLIST` 获取慢查询
- **PostgreSQL**: 通过 `pg_stat_activity` 获取慢查询

### 3. 规则引擎 ([rules.go](file:///d:/Trae/project/record001/463/internal/rules/rules.go))

规则匹配逻辑：
1. 首先检查白名单
2. 按顺序匹配自定义规则
3. 最后应用默认阈值规则

### 4. 慢查询分析器 ([analyzer.go](file:///d:/Trae/project/record001/463/internal/analyzer/analyzer.go))

功能包括：
- 查询标准化（参数替换）
- 查询哈希计算
- 查询类型检测
- 表名提取
- 统计分析报告

### 5. 监控引擎 ([monitor.go](file:///d:/Trae/project/record001/463/internal/monitor/monitor.go))

核心监控循环：
- 定时扫描所有数据库
- 并发处理多个数据库
- 自动重连机制
- 统计和日志记录

## 终止模式

| 模式 | 说明 | MySQL | PostgreSQL |
|------|------|-------|------------|
| query | 只终止当前查询 | `KILL QUERY <id>` | `pg_cancel_backend(<pid>)` |
| connection | 终止整个连接 | `KILL <id>` | `pg_terminate_backend(<pid>)` |

## 权限要求

### MySQL

监控用户需要以下权限：
```sql
GRANT PROCESS ON *.* TO 'monitor_user'@'%';
GRANT SUPER ON *.* TO 'monitor_user'@'%';  -- 用于 KILL 命令
```

### PostgreSQL

监控用户需要以下权限：
```sql
-- pg_stat_activity 查看权限
GRANT pg_read_all_stats TO monitor_user;

-- 终止其他用户查询的权限
GRANT pg_signal_backend TO monitor_user;
```

## 日志说明

被终止的查询会记录到 `killed_queries.log` 文件：

```
2024/01/15 10:30:45 DB=primary_mysql | ConnID=12345 | User=app_user | Host=192.168.1.100:54321 | Time=1m30s | Rule=long_running_select | Mode=query | Query=SELECT * FROM orders WHERE ...
```

## 最佳实践

1. **先用试运行模式**: 建议先用 `dry_run: true` 运行一段时间，观察哪些查询会被终止
2. **合理设置阈值**: 根据业务特点设置合理的执行时间阈值
3. **使用 SQL 指纹白名单**:
   - 先在 dry-run 模式下运行，收集需要白名单的查询指纹
   - 从日志中获取查询指纹，精确添加到白名单
   - 比前缀匹配更精确，避免白名单范围过大
4. **启用事务等待**:
   - 对事务型数据库建议启用 `transaction_wait.enabled: true`
   - 根据典型事务时长设置 `wait_duration`
   - 减少不必要的连接中断，避免事务回滚
5. **实时监控调优**:
   - 100ms 间隔适合高并发场景
   - 资源受限环境可适当调大间隔
6. **定期分析日志**: 定期分析慢查询日志，优化索引和查询
7. **监控工具本身**: 监控工具的运行状态和资源使用

## 项目结构

```
slow-query-killer/
├── cmd/
│   └── slow-query-killer/
│       └── main.go              # 程序入口
├── internal/
│   ├── config/
│   │   └── config.go            # 配置管理
│   ├── db/
│   │   ├── db.go                # 数据库接口
│   │   ├── mysql.go             # MySQL 实现
│   │   └── postgresql.go        # PostgreSQL 实现
│   ├── rules/
│   │   └── rules.go             # 规则引擎
│   ├── analyzer/
│   │   └── analyzer.go          # 慢查询分析器
│   └── monitor/
│       └── monitor.go           # 监控引擎
├── configs/
│   └── config.yaml              # 配置文件示例
├── go.mod
├── go.sum
└── README.md
```

## License

MIT License
