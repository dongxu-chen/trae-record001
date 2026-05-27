# Registry Sync - Docker镜像仓库同步工具

一个用Go语言编写的高性能Docker镜像仓库同步工具，支持在多个Registry之间同步镜像。

## 功能特性

- ✅ **多Registry支持**: Harbor、阿里云ACR、AWS ECR、通用Docker Registry
- ✅ **增量同步**: 跳过已存在且Digest相同的镜像
- ✅ **完整性校验**: SHA256 Digest校验确保镜像完整性
- ✅ **同步限速**: 支持并发数和传输速率限制
- ✅ **过滤规则**: 按命名空间、标签进行包含/排除过滤
- ✅ **进度监控**: 实时监控同步进度和传输速度
- ✅ **Goroutine并发**: 高性能并发同步
- ✅ **对称加密**: AES-GCM加密保护敏感凭证

## 快速开始

### 1. 编译

```bash
go mod tidy
go build -o registry-sync ./cmd
```

### 2. 配置

复制示例配置文件并修改：

```bash
cp config.example.json config.json
```

编辑 `config.json`，配置你的Registry信息和同步任务。

### 3. 加密配置（可选但推荐）

```bash
./registry-sync --encrypt --config config.json --key your-encryption-key
```

### 4. 运行同步

```bash
# 执行所有同步任务
./registry-sync --config config.json --key your-encryption-key

# 执行特定任务
./registry-sync --config config.json --job harbor-to-acr

# 试运行（不实际同步）
./registry-sync --config config.json --dry-run

# 详细输出
./registry-sync --config config.json --verbose
```

## 配置说明

### Registry配置

| 字段 | 说明 | 示例 |
|------|------|------|
| name | Registry名称标识 | harbor-source |
| type | Registry类型 | harbor/acr/ecr/generic |
| url | Registry地址 | https://harbor.example.com |
| username | 用户名 | admin |
| password | 密码 | password |
| access_key | 访问密钥（云厂商） | AKIAIOSFODNN7EXAMPLE |
| secret_key | 秘密密钥（云厂商） | your-secret-key |
| region | 区域 | cn-hangzhou |
| insecure | 是否跳过TLS验证 | false |

### 同步任务配置

| 字段 | 说明 | 默认值 |
|------|------|--------|
| source_registry | 源Registry名称 | - |
| target_registry | 目标Registry名称 | - |
| source_prefix | 源仓库前缀过滤 | - |
| target_prefix | 目标仓库前缀 | - |
| filter.include_namespaces | 包含的命名空间（支持通配符） | [] |
| filter.exclude_namespaces | 排除的命名空间（支持通配符） | [] |
| filter.include_tags | 包含的标签（支持通配符） | [] |
| filter.exclude_tags | 排除的标签（支持通配符） | [] |
| rate_limit.max_concurrent | 最大并发数 | 5 |
| rate_limit.bytes_per_sec | 每秒传输字节数（0为不限速） | 0 |
| incremental | 是否增量同步 | true |
| verify_digest | 是否校验Digest | true |
| dry_run | 试运行模式 | false |

## 命令行参数

```
  -c, --config string    Path to configuration file (default "config.json")
  -k, --key string       Encryption key for sensitive data
  -j, --job string       Specific sync job to run
  -n, --dry-run          Show what would be synced without actually syncing
  -v, --verbose          Enable verbose output
      --encrypt          Encrypt and save the configuration file
```

## 项目结构

```
registry-sync/
├── cmd/
│   └── main.go              # 主程序入口
├── pkg/
│   ├── config/
│   │   └── config.go        # 配置管理和加密
│   ├── registry/
│   │   ├── registry.go      # Registry接口和限速器
│   │   ├── generic.go       # 通用Registry客户端
│   │   ├── harbor.go        # Harbor客户端
│   │   ├── acr.go           # 阿里云ACR客户端
│   │   ├── ecr.go           # AWS ECR客户端
│   │   └── factory.go       # 客户端工厂
│   ├── filter/
│   │   └── filter.go        # 过滤规则
│   ├── progress/
│   │   └── progress.go      # 进度监控
│   └── sync/
│       └── sync.go          # 同步核心逻辑
├── config.example.json      # 示例配置
├── go.mod
├── go.sum
└── README.md
```

## 核心模块说明

### config - 配置管理

- 使用AES-GCM对称加密保护敏感凭证
- 支持配置文件的加密存储和读取
- 自动解密加密的配置项

### registry - Registry客户端

- 统一的Registry客户端接口
- 支持多种Registry类型
- 内置令牌桶限速器
- 支持断点续传（Blob上传）

### filter - 过滤规则

- 支持通配符匹配（`*`匹配任意字符，`?`匹配单个字符）
- 命名空间和标签的包含/排除过滤
- 正则表达式底层实现

### progress - 进度监控

- 原子操作保证并发安全
- 实时统计同步进度
- 支持单个镜像和全局进度追踪

### sync - 同步核心

- Goroutine池管理并发
- 增量同步：检查目标镜像Digest
- 完整性校验：传输中计算SHA256
- 自动跳过已存在的Blob层

## 使用示例

### Harbor 到 阿里云ACR同步

```json
{
  "registries": [
    {
      "name": "harbor",
      "type": "harbor",
      "url": "https://harbor.company.com",
      "username": "admin",
      "password": "secret"
    },
    {
      "name": "acr",
      "type": "acr",
      "url": "https://registry.cn-hangzhou.aliyuncs.com",
      "access_key": "LTAI5t7...",
      "secret_key": "your-secret-key",
      "region": "cn-hangzhou"
    }
  ],
  "sync_jobs": [
    {
      "source_registry": "harbor",
      "target_registry": "acr",
      "filter": {
        "include_namespaces": ["prod"],
        "include_tags": ["v*"]
      },
      "rate_limit": {
        "max_concurrent": 3,
        "bytes_per_sec": 52428800
      },
      "incremental": true,
      "verify_digest": true
    }
  ]
}
```

## 许可证

MIT License
