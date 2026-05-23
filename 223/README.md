# 数据库备份恢复工具

一个功能完整的数据库备份恢复工具，支持 MySQL 和 PostgreSQL，集成压缩、加密、阿里云 OSS 存储、自动验证和时间点恢复功能。

## 功能特性

- ✅ **多数据库支持**：MySQL / PostgreSQL
- ✅ **备份策略**：全量备份 / 增量备份
- ✅ **压缩存储**：Gzip 压缩，节省存储空间
- ✅ **数据加密**：AES-256 加密，保障数据安全
- ✅ **云存储**：阿里云 OSS / Rclone 支持
- ✅ **备份验证**：自动恢复至验证库并执行测试查询
- ✅ **时间点恢复**：基于 binlog (MySQL) / WAL (PostgreSQL) 回放

## 系统要求

- Python 3.8+
- MySQL 客户端工具（mysqldump, mysql, mysqlbinlog）
- PostgreSQL 客户端工具（pg_dump, pg_restore, psql, pg_waldump）
- Rclone（可选，用于 Rclone 存储模式）

## 安装

1. 克隆项目
2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 配置文件：

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`，填入数据库、OSS、加密等配置信息。

## 配置说明

### 数据库配置

```yaml
databases:
  mysql:
    host: localhost
    port: 3306
    user: root
    password: your_password
    database: your_database
    mysqldump_path: mysqldump
    mysql_path: mysql
    binlog_path: /var/lib/mysql
```

### 存储配置

阿里云 OSS 模式：

```yaml
storage:
  type: oss
  oss:
    endpoint: oss-cn-hangzhou.aliyuncs.com
    access_key_id: your_access_key
    access_key_secret: your_secret
    bucket_name: your-bucket-name
    prefix: backups/
```

Rclone 模式：

```yaml
storage:
  type: rclone
  rclone:
    remote_name: aliyunoss
    remote_path: backups/
```

### 加密配置

```yaml
encryption:
  enabled: true
  algorithm: AES-256-CBC
  key: your-32-byte-encryption-key-here
```

### 验证配置

```yaml
backup:
  verification:
    enabled: true
    verify_host: localhost
    verify_port: 3307
    verify_user: root
    verify_password: verify_password
    verify_database: verify_db
    test_queries:
      - "SELECT 1"
      - "SHOW TABLES"
```

## 使用说明

### 1. 测试数据库连接

```bash
python cli.py -d mysql test-connection
python cli.py -d postgresql test-connection
```

### 2. 创建备份

全量备份（默认）：

```bash
python cli.py -d mysql backup
python cli.py -d postgresql backup
```

增量备份：

```bash
python cli.py -d mysql backup -s incremental
python cli.py -d postgresql backup -s incremental
```

跳过验证：

```bash
python cli.py -d mysql backup --no-verify
```

### 3. 列出备份

```bash
python cli.py -d mysql list
python cli.py -d mysql list -s full
python cli.py -d mysql list -s incremental
```

### 4. 恢复备份

```bash
python cli.py -d mysql restore mysql_full_20240101_120000
```

恢复到指定数据库：

```bash
python cli.py -d mysql restore mysql_full_20240101_120000 \
  --target-host localhost \
  --target-port 3306 \
  --target-user root \
  --target-password new_password \
  --target-database new_database
```

### 5. 时间点恢复 (PITR)

```bash
python cli.py -d mysql pitr "2024-01-01T15:30:00"
```

指定基础全量备份：

```bash
python cli.py -d mysql pitr "2024-01-01T15:30:00" --full-backup-id mysql_full_20240101_120000
```

### 6. 验证备份

```bash
python cli.py -d mysql verify mysql_full_20240101_120000
```

## 项目结构

```
.
├── cli.py                 # 命令行入口
├── config.example.yaml    # 配置示例
├── requirements.txt       # Python 依赖
├── README.md             # 说明文档
└── dbbackup/             # 核心模块
    ├── __init__.py
    ├── config.py         # 配置管理
    ├── database.py       # 数据库连接器
    ├── backup.py         # 备份引擎
    ├── crypto.py         # 压缩加密
    ├── storage.py        # 存储模块
    ├── verify.py         # 备份验证
    ├── recovery.py       # 恢复模块
    └── utils.py          # 工具函数
```

## 工作流程

### 备份流程

1. 执行数据库备份（mysqldump / pg_dump）
2. Gzip 压缩备份文件
3. AES-256 加密压缩文件
4. 上传至阿里云 OSS
5. （可选）自动验证备份完整性

### 恢复流程

1. 从 OSS 下载加密备份
2. 解密备份文件
3. 解压备份文件
4. 恢复到目标数据库

### 时间点恢复流程

1. 查找目标时间点之前最近的全量备份
2. 恢复全量备份
3. 查找并应用该时间点之间的所有增量备份（binlog/WAL）

## 注意事项

1. **加密密钥安全**：请妥善保管加密密钥，丢失密钥将无法恢复备份数据
2. **数据库权限**：确保数据库用户有足够的权限执行备份操作
3. **binlog/WAL 启用**：增量备份需要启用 MySQL binlog 或 PostgreSQL WAL
4. **磁盘空间**：确保临时目录有足够空间存放备份文件
5. **网络带宽**：大文件上传到 OSS 可能需要较长时间

## 故障排除

### MySQL 备份失败

- 检查 mysqldump 路径配置
- 确认数据库用户有 RELOAD, REPLICATION CLIENT 权限
- 检查 binlog 是否启用（`SHOW VARIABLES LIKE 'log_bin';`）

### PostgreSQL 备份失败

- 检查 pg_dump 路径配置
- 确认 WAL 归档已启用
- 检查数据库用户权限

### OSS 上传失败

- 检查 access_key 和 access_key_secret 是否正确
- 确认 bucket 存在且有读写权限
- 检查网络连接和 endpoint 配置

## 许可证

MIT License
