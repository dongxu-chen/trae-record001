# Cloud Migration Tool

跨云服务迁移工具，支持从 AWS 迁移到阿里云、腾讯云的资源（EC2、RDS、S3/OSS）。

## 功能特性

### 核心迁移功能
- **虚拟机镜像迁移**: EC2 -> ECS/CVM，基于快照技术，支持镜像格式标准化转换
- **数据库迁移**: RDS 快照导出导入
- **对象存储迁移**: S3 -> OSS/COS，支持全量和增量同步，支持断点续传
- **数据持续同步**: 基于 rsync 的文件实时同步

### 增强功能
- **断点续传**: 迁移中断后可从断点恢复，避免重新传输
- **沙箱演练环境**: 完全隔离的演练环境（独立VPC + 子账号），不影响生产
- **镜像格式标准化**: 自动转换为目标云厂商兼容格式（VMDK/QCOW2/RAW）
- **切换演练**: 连通性测试、数据流测试、割接演练、回滚演练
- **迁移报告**: 支持多种格式输出（文本、JSON、HTML、Markdown）

## 技术栈

- **语言**: Go 1.21+
- **AWS SDK**: aws-sdk-go-v2
- **阿里云 SDK**: alibaba-cloud-sdk-go, aliyun-oss-go-sdk
- **腾讯云 SDK**: tencentcloud-sdk-go, cos-go-sdk-v5
- **CLI 框架**: Cobra + Viper
- **数据同步**: rsync
- **镜像转换**: qemu-img (可选)

## 安装

```bash
# 克隆项目
git clone <repository-url>
cd cloud-migration-tool

# 安装依赖
go mod download

# 构建
go build -o cloud-migrate

# （可选）安装 qemu-img 用于镜像格式转换
# Ubuntu/Debian: sudo apt-get install qemu-utils
# CentOS/RHEL: sudo yum install qemu-img
# macOS: brew install qemu
```

## 快速开始

### 1. 准备配置文件

创建 `config.yaml`:

```yaml
source:
  provider: aws
  region: us-east-1

destination:
  provider: aliyun
  region: cn-hangzhou

resources:
  ec2:
    - instance_id: i-1234567890abcdef0
      name: web-server
      instance_type: ecs.t5.large
      target_zone: cn-hangzhou-i
  rds:
    - db_instance_id: prod-db
      target_db_name: migrated-prod-db
      db_type: mysql
  s3:
    - bucket: my-source-bucket
      target_bucket: my-target-bucket
      prefix: data/

rsync:
  source_path: /var/www/html/
  dest_path: /var/www/html/
  ssh_user: root
  ssh_host: 192.168.1.100
  ssh_port: 22
  ssh_key_path: ~/.ssh/id_rsa
  exclude_patterns:
    - "*.log"
    - "tmp/*"
  bandwidth_limit: "10000"
  continuous_sync: true
  sync_interval: 300

checkpoint:
  enabled: true
  directory: ~/.cloud-migration/checkpoints

image_conversion:
  enabled: true
  temp_directory: /tmp/cloud-migration-images
  target_formats:
    aliyun: raw
    tencent: vmdk
    aws: vmdk

sandbox:
  enabled: true
  vpc_cidr: 10.200.0.0/16
  subnet_cidr: 10.200.1.0/24
  auto_expiry_hours: 4
  enable_sub_account: true
  isolation_policies:
    - vpc_isolation
    - subnet_isolation
    - security_groups
    - iam_restrictions
```

### 2. 运行迁移演练（沙箱环境）

```bash
# 查看所有活跃沙箱
./cloud-migrate drill --list-sandboxes

# 在隔离沙箱中运行连通性测试
./cloud-migrate drill --type connectivity --name prod-drill

# 完整演练（含沙箱环境）
./cloud-migrate drill --type full --name production-migration-drill

# 清理沙箱
./cloud-migrate drill --cleanup-sandbox sandbox-1234567890

# 不使用沙箱（生产环境，谨慎使用）
./cloud-migrate drill --type connectivity --sandbox=false
```

### 3. 执行资源迁移（支持断点续传）

```bash
# 迁移所有资源
./cloud-migrate migrate --config config.yaml --all

# 只迁移计算资源（含镜像格式转换）
./cloud-migrate migrate --config config.yaml --compute

# 只迁移存储资源（支持断点续传）
./cloud-migrate migrate --config config.yaml --storage

# 查看待恢复的检查点
./cloud-migrate migrate --list-checkpoints

# 从断点恢复迁移
./cloud-migrate migrate --config config.yaml --resume storage-1234567890

# 禁用检查点
./cloud-migrate migrate --config config.yaml --storage --no-checkpoint

# 生成 HTML 报告
./cloud-migrate migrate --config config.yaml --all --output report.html --format html
```

### 4. 数据持续同步

```bash
# 单次同步
./cloud-migrate sync --source /data/ --dest /data/ --ssh-user root --ssh-host 10.0.0.1

# 持续同步（每5分钟一次）
./cloud-migrate sync --source /data/ --dest /data/ --ssh-user root --ssh-host 10.0.0.1 --continuous --interval 300

# 试运行
./cloud-migrate sync --source /data/ --dest /data/ --dry-run
```

### 5. 生成迁移报告

```bash
# 文本格式
./cloud-migrate report --format text

# HTML 格式
./cloud-migrate report --format html --output migration-report.html

# JSON 格式
./cloud-migrate report --format json --output report.json
```

## 命令详解

### migrate - 资源迁移

```bash
./cloud-migrate migrate [flags]

Flags:
      --all             迁移所有资源类型 (default true)
      --compute         迁移计算实例
      --database        迁移数据库
      --storage         迁移存储
      --config string   配置文件路径
      --output string   报告输出路径
      --format string   报告格式: text, json, html, markdown
      --resume string   从指定的检查点任务ID恢复迁移
      --list-checkpoints 列出所有待恢复的检查点
      --no-checkpoint   禁用检查点功能
      --convert-image   启用镜像格式转换 (default true)
```

### sync - 文件同步

```bash
./cloud-migrate sync [flags]

Flags:
      --source string       源路径
      --dest string         目标路径
      --ssh-user string     SSH 用户名
      --ssh-host string     SSH 主机地址
      --ssh-port int        SSH 端口 (default 22)
      --ssh-key string      SSH 私钥路径
      --continuous          持续同步模式
      --interval int        同步间隔(秒) (default 300)
      --dry-run             试运行
      --log string          日志文件路径
```

### drill - 迁移演练

```bash
./cloud-migrate drill [flags]

Flags:
      --type string            演练类型: connectivity, data_flow, cutover, rollback, full (default "connectivity")
      --name string            演练名称
      --output string          报告输出路径
      --sandbox                在隔离沙箱环境中运行 (default true)
      --list-sandboxes         列出所有活跃沙箱
      --cleanup-sandbox string 清理指定的沙箱（按ID）
      --sandbox-duration duration  沙箱自动过期时间 (default 4h)
```

### report - 报告生成

```bash
./cloud-migrate report [flags]

Flags:
      --format string        报告格式: text, json, html, markdown (default "text")
      --output string        输出文件路径
      --source-cloud string  源云厂商 (default "aws")
      --source-region string 源区域 (default "us-east-1")
      --dest-cloud string    目标云厂商 (default "aliyun")
      --dest-region string   目标区域 (default "cn-hangzhou")
```

## 核心功能说明

### 断点续传功能

工具自动记录迁移进度，支持中断后恢复：

1. 迁移过程中按 `Ctrl+C` 会自动保存当前进度
2. 使用 `--list-checkpoints` 查看所有待恢复的任务
3. 使用 `--resume <task-id>` 从断点恢复
4. 检查点文件默认保存在 `~/.cloud-migration/checkpoints/`

### 沙箱演练环境

默认在完全隔离的沙箱环境中执行演练：

- **独立 VPC**: 创建专用的虚拟私有云，与生产网络隔离
- **独立子网**: 在沙箱 VPC 内创建专用子网
- **安全组**: 配置受限的安全组规则
- **子账号**: 创建专用的受限权限子账号执行演练
- **自动过期**: 沙箱环境默认4小时后自动过期

**安全优势**:
- 演练操作完全不影响生产环境
- 权限最小化原则
- 资源自动清理，避免遗留成本

### 镜像格式标准化

自动处理不同云厂商的镜像格式差异：

| 云厂商 | 推荐格式 | 工具 |
|--------|----------|------|
| 阿里云 | RAW | qemu-img |
| 腾讯云 | VMDK | qemu-img |
| AWS | VMDK | qemu-img |

支持的源格式：VMDK, QCOW2, RAW, VHD, VHDX, OVA

## 项目结构

```
cloud-migration-tool/
├── cmd/                    # CLI 命令
│   ├── root.go            # 根命令
│   ├── migrate.go         # 迁移命令（含断点续传）
│   ├── sync.go            # 同步命令
│   ├── drill.go           # 演练命令（含沙箱）
│   └── report.go          # 报告命令
├── config/                 # 配置管理
│   └── config.go          # 配置结构体和加载
├── pkg/
│   ├── checkpoint/        # 检查点管理（断点续传）
│   │   └── checkpoint.go  # 进度记录和恢复
│   ├── sandbox/           # 沙箱环境管理
│   │   └── sandbox.go     # 独立VPC和子账号
│   ├── imageconv/         # 镜像格式转换
│   │   └── converter.go   # 标准化镜像格式
│   ├── dependency/        # 资源依赖分析
│   │   └── analyzer.go    # 依赖图构建和排序
│   ├── rollback/          # 回滚预案管理
│   │   └── rollback.go    # 自动/手动回滚
│   ├── cost/              # 成本对比分析
│   │   └── analyzer.go    # 费用估算和对比
│   ├── cloud/             # 云厂商 SDK 封装
│   │   ├── interface.go   # 通用接口定义
│   │   ├── aws/           # AWS SDK
│   │   ├── aliyun/        # 阿里云 SDK
│   │   └── tencent/       # 腾讯云 SDK
│   ├── migration/         # 迁移逻辑
│   │   ├── compute.go     # 计算资源迁移（含镜像转换）
│   │   ├── database.go    # 数据库迁移
│   │   └── storage.go     # 存储迁移（含断点续传）
│   ├── sync/              # 数据同步
│   │   └── rsync.go       # rsync 封装
│   ├── drill/             # 迁移演练（含沙箱集成）
│   │   └── drill.go       # 演练逻辑
│   └── report/            # 报告生成
│       └── report.go      # 报告生成器
├── examples/               # 示例
│   └── config.yaml        # 配置示例
├── main.go                # 程序入口
├── go.mod
└── README.md
```

## 认证配置

### AWS 认证

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-east-1"
```

### 阿里云认证

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID="your-access-key-id"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="your-access-key-secret"
```

### 腾讯云认证

```bash
export TENCENTCLOUD_SECRET_ID="your-secret-id"
export TENCENTCLOUD_SECRET_KEY="your-secret-key"
```

## 迁移流程

1. **准备阶段**: 配置云厂商认证，准备迁移配置文件
2. **沙箱演练阶段**: 在隔离沙箱中运行 `drill` 命令测试
3. **全量迁移**: 运行 `migrate` 命令执行全量资源迁移
4. **断点恢复**: 如果中断，使用 `--resume` 从断点恢复
5. **增量同步**: 运行 `sync --continuous` 保持数据实时同步
6. **割接演练**: 在沙箱中运行 `drill --type cutover` 模拟业务割接
7. **正式割接**: 停止源端业务，执行最终同步，切换流量
8. **验证阶段**: 验证目标端业务正常运行
9. **报告生成**: 生成详细的迁移报告

## 安全最佳实践

1. **始终使用沙箱演练**: 在正式迁移前，在沙箱环境中完成所有演练
2. **最小权限原则**: 演练使用子账号，仅授予必要权限
3. **资源隔离**: 演练资源使用专用VPC和安全组
4. **自动清理**: 沙箱资源配置自动过期，避免遗留成本
5. **断点保护**: 大型迁移启用检查点，避免重复传输

## 注意事项

1. 确保源端和目标端网络连通
2. 确保云账号有足够的权限（包括创建VPC、子账号等）
3. 迁移前建议创建源资源备份
4. 大型迁移建议分阶段进行，启用断点续传
5. 注意数据传输成本（出网流量费用）
6. 镜像转换需要安装 qemu-img 工具

## License

MIT
