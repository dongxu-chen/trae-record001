# Backup Tool - Go 高性能并发备份工具

一个高性能的数据库备份工具，支持 MySQL 和 PostgreSQL 的全量/增量备份，内置流水线处理和 Prometheus 监控。

## 功能特性

- ✅ **多数据库并行备份**: 支持 MySQL/PostgreSQL 多数据库并行备份
- ✅ **增量备份**: MySQL binlog 增量备份支持
- ✅ **流水线架构**: 备份 → 压缩 → 加密 → 上传 四阶段并发处理
- ✅ **S3 兼容存储**: 支持阿里云 OSS、腾讯云 COS、MinIO、AWS S3
- ✅ **AES-256 加密**: 备份文件端到端加密
- ✅ **Gzip 压缩**: 自动压缩备份文件节省空间
- ✅ **Prometheus Metrics**: 内置监控指标和 HTTP 接口
- ✅ **灵活配置**: YAML 配置文件，支持自定义各阶段参数

## 快速开始

### 1. 安装依赖

```bash
cd go
make deps
```

### 2. 构建

```bash
make build
```

### 3. 配置

编辑 `config.yaml`:

```yaml
server:
  http_port: 9090
  metrics_path: /metrics

database:
  mysql:
    host: localhost
    port: 3306
    user: root
    password: your_password
    databases:
      - database1
      - database2
    mysqldump_path: mysqldump
    mysqlbinlog_path: mysqlbinlog

  postgresql:
    host: localhost
    port: 5432
    user: postgres
    password: your_password
    databases:
      - database1
      - database2
    pg_dump_path: pg_dump

storage:
  type: s3
  s3:
    endpoint: oss-cn-hangzhou.aliyuncs.com
    region: cn-hangzhou
    bucket: your-bucket-name
    access_key: your-access-key
    secret_key: your-secret-key
    use_ssl: true
    path_style: false
    prefix: backups/

backup:
  local_dir: ./backups
  retention_days: 7
  compress: true
  encrypt: true
  encryption_key: your-32-byte-encryption-key-here
  enable_incremental: true
  enable_verify: true
  parallel_workers: 4
  pipeline_size: 10

logging:
  level: info
  file: backup.log
  max_size: 100
  max_backups: 3
  max_age: 28
```

### 4. 运行

```bash
# 单次备份
make run-once

# 守护进程模式
make run
```

## 架构说明

### 流水线架构

```
数据库 → 备份阶段 → 压缩阶段 → 加密阶段 → 上传阶段 → S3存储
```

每个阶段都是独立的 Worker Pool，支持并行处理，充分利用系统资源。

### 并发控制

- `parallel_workers`: 每个阶段的并发 Worker 数量
- `pipeline_size`: 管道缓冲区大小，控制内存占用

### 存储配置示例

#### 阿里云 OSS
```yaml
endpoint: oss-cn-hangzhou.aliyuncs.com
region: cn-hangzhou
path_style: false
```

#### 腾讯云 COS
```yaml
endpoint: cos.ap-beijing.myqcloud.com
region: ap-beijing
path_style: false
```

#### MinIO
```yaml
endpoint: localhost:9000
region: us-east-1
use_ssl: false
path_style: true
```

#### AWS S3
```yaml
endpoint: s3.amazonaws.com
region: us-east-1
path_style: false
```

## Prometheus 监控

访问 `http://localhost:9090/metrics` 查看监控指标:

- `backup_total_count`: 备份总次数
- `backup_success_count`: 备份成功次数
- `backup_failed_count`: 备份失败次数
- `backup_duration_seconds`: 备份耗时直方图
- `backup_size_bytes`: 备份文件大小
- `backup_active_count`: 当前活跃备份数

## Make 命令

```bash
make build      # 构建
make test       # 测试
make run        # 运行
make run-once   # 单次备份
make clean      # 清理
make install    # 安装到系统
make deps       # 下载依赖
```

## 项目结构

```
go/
├── cmd/
│   └── backupd/
│       └── main.go      # 主程序入口
├── pkg/
│   ├── backup/
│   │   ├── types.go     # 类型定义
│   │   ├── mysql.go     # MySQL 备份
│   │   ├── postgresql.go # PostgreSQL 备份
│   │   └── pipeline.go  # 流水线处理
│   ├── storage/
│   │   └── s3.go        # S3 存储接口
│   ├── config/
│   │   └── config.go    # 配置管理
│   ├── logger/
│   │   └── logger.go    # 日志管理
│   └── metrics/
│       └── metrics.go   # Prometheus 指标
├── config.yaml          # 配置文件
├── go.mod               # Go 模块
├── Makefile             # 构建脚本
└── README.md            # 文档
```

## 性能优化

1. **并行备份**: 多数据库同时备份，利用多核
2. **流水线处理**: 各阶段重叠执行，减少总耗时
3. **分片上传**: S3 分片上传，支持大文件断点续传
4. **流式压缩**: 边备份边压缩，减少磁盘 IO

## 要求

- Go 1.21+
- MySQL 5.7+ / PostgreSQL 10+
- mysqldump / pg_dump 命令行工具
- 足够的磁盘空间用于临时备份文件

## License

MIT
