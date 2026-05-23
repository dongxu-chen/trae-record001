# 容器安全扫描工具

基于 Go + Trivy 实现的容器安全扫描工具，支持漏洞扫描（CVE）、敏感信息检测和配置风险分析。

## 功能特性

- 🔒 **漏洞扫描 (CVE)** - 扫描镜像中的已知安全漏洞
- 🔑 **敏感信息检测** - 检测密钥、密码、API Key等敏感信息泄露
- ⚙️ **配置风险分析** - 检查root用户运行、特权容器等安全配置问题
- 📊 **HTML报告** - 生成美观的HTML格式扫描报告
- 🎯 **分级阈值** - 三级阈值配置（阻断/警告/允许），完美集成CI/CD
- 💾 **本地缓存优先** - CVE数据库本地缓存，每日定时自动更新
- 📋 **敏感信息白名单** - 支持排除测试用占位符、示例密码等

## 快速开始

### 前置要求

1. 安装 Go 1.21+
2. 安装 Trivy:

```bash
# macOS
brew install aquasecurity/trivy/trivy

# Linux
sudo apt-get install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor | sudo tee /usr/share/keyrings/trivy.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update && sudo apt-get install trivy

# Windows (Chocolatey)
choco install trivy
```

### 编译安装

```bash
# 克隆项目
git clone <repository-url>
cd container-scanner

# 下载依赖
go mod download

# 编译
go build -o container-scanner ./cmd/
```

### 基本使用

```bash
# 扫描本地镜像
./container-scanner nginx:latest

# 扫描远程仓库镜像
./container-scanner registry.example.com/my-app:v1.0.0

# 指定输出文件
./container-scanner alpine:latest -o my-report.html

# 只扫描严重和高危漏洞
./container-scanner nginx:latest -s CRITICAL,HIGH

# 使用配置文件
./container-scanner my-image:latest -c scanner-config.yaml

# 跳过数据库更新
./container-scanner my-image:latest --skip-db-update
```

## 命令行参数

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--config` | `-c` | - | 配置文件路径 |
| `--output` | `-o` | `scan-report.html` | 输出报告文件路径 |
| `--severities` | `-s` | `CRITICAL,HIGH,MEDIUM,LOW` | 扫描的严重程度 |
| `--scanners` | - | `vuln,secret,config` | 启用的扫描器 |
| `--fail` | `-f` | `true` | 超过阻断阈值时以非零状态退出 |
| `--remote` | `-r` | `false` | 强制远程拉取镜像扫描 |
| `--skip-db-update` | - | `false` | 跳过CVE数据库更新 |

### 扫描器类型

- `vuln` - 漏洞扫描
- `secret` - 敏感信息扫描
- `config` - 配置风险扫描

### 严重程度

- `CRITICAL` - 严重
- `HIGH` - 高危
- `MEDIUM` - 中危
- `LOW` - 低危

## 配置文件

使用 YAML 配置文件可以更灵活地控制扫描行为：

```yaml
output: scan-report.html
format: html
severities:
  - CRITICAL
  - HIGH
  - MEDIUM
  - LOW
scanners:
  - vuln
  - secret
  - config
fail_on_error: true

# CVE数据库配置
database:
  cache_dir: ~/.trivy/db     # 本地缓存目录
  auto_update: true           # 启用自动更新
  update_hour: 2              # 每日更新时间（小时）
  update_minute: 0            # 每日更新时间（分钟）
  skip_update: false          # 跳过更新

# 分级阈值配置
thresholds:
  vulnerabilities:
    critical:
      action: block           # 阻断：构建失败
      max_count: 0            # 允许0个
    high:
      action: block
      max_count: 0
    medium:
      action: warn            # 警告：显示警告但不阻断
      max_count: -1           # -1表示不限制数量
    low:
      action: allow           # 允许：忽略
      max_count: -1

# 敏感信息白名单
secret_whitelist:
  rules: []                   # 按规则ID白名单
  files:                      # 按文件名白名单
    - "test_*.py"
    - "*_test.go"
  paths:                      # 按路径白名单
    - "/test/"
    - "/tests/"
  match_values:               # 按匹配内容白名单（测试占位符等）
    - "test"
    - "example"
    - "placeholder"
    - "dummy"
    - "changeme"
```

### 阈值动作说明

| 动作 | 说明 | CI行为 |
|------|------|--------|
| `block` | 阻断 | 构建失败，退出码非零 |
| `warn` | 警告 | 显示警告信息，构建继续 |
| `allow` | 允许 | 忽略此类问题 |

### 白名单配置说明

- **rules**: 按Trivy的规则ID白名单特定检测规则
- **files**: 按文件名模式白名单特定文件
- **paths**: 按路径关键字白名单特定目录下的文件
- **match_values**: 按匹配内容白名单（用于排除测试占位符、示例密码等）

## CI/CD 集成

### GitHub Actions

```yaml
name: Container Security Scan

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Go
        uses: actions/setup-go@v4
        with:
          go-version: '1.21'
      
      - name: Install Trivy
        run: |
          curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh
          
      - name: Build scanner
        run: go build -o container-scanner ./cmd/
        
      - name: Run scan
        run: ./container-scanner my-image:latest -c scanner-config.yaml
        
      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: security-report
          path: scan-report.html
```

### GitLab CI

```yaml
security_scan:
  stage: test
  image: golang:1.21
  before_script:
    - curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh
    - go build -o container-scanner ./cmd/
  script:
    - ./container-scanner $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  artifacts:
    when: always
    reports:
      html: scan-report.html
```

## 项目结构

```
container-scanner/
├── cmd/
│   └── main.go              # 主程序入口
├── pkg/
│   ├── scanner/
│   │   └── scanner.go       # Trivy扫描器封装
│   ├── config/
│   │   └── config.go        # 配置管理和阈值检查
│   └── report/
│       └── report.go        # HTML报告生成
├── scanner-config.yaml      # 示例配置文件
├── .github/workflows/       # GitHub Actions示例
├── .gitlab-ci.yml           # GitLab CI示例
└── go.mod
```

## 核心模块说明

### Scanner 模块

封装Trivy命令行工具，提供统一的扫描接口：

- `NewScanner()` - 创建扫描器实例
- `Scan(config)` - 执行扫描
- `UpdateDatabase(cacheDir)` - 更新CVE数据库
- `ScanLocalImage(image)` - 扫描本地镜像
- `ScanRemoteImage(image)` - 扫描远程镜像

### Config 模块

配置管理和阈值检查功能：

- `LoadConfig(path)` - 加载配置文件
- `DefaultConfig()` - 获取默认配置
- `ShouldUpdateDatabase()` - 判断是否需要更新数据库
- `IsSecretWhitelisted(secret)` - 检查敏感信息是否在白名单
- `FilterWhitelistedSecrets(report)` - 过滤白名单中的敏感信息
- `CheckThresholds(report)` - 分级阈值检查

### Report 模块

HTML报告生成：

- `GenerateHTMLReport(report, image, output, blocked, warnings, whitelisted)` - 生成HTML报告
- `PrintConsoleSummary(report, image)` - 打印控制台摘要

## CVE数据库缓存机制

### 本地缓存优先

1. 首次运行自动下载CVE数据库到本地缓存目录
2. 后续扫描优先使用本地缓存
3. 每日定时自动检查更新（默认凌晨2点）

### 更新策略

- 数据库不存在时：强制更新
- 数据库超过24小时：自动更新
- 到达配置的更新时间：自动更新
- 可通过 `--skip-db-update` 强制跳过更新

## 分级阈值示例

### 严格模式（生产环境）

```yaml
thresholds:
  vulnerabilities:
    critical: { action: block, max_count: 0 }
    high:     { action: block, max_count: 0 }
    medium:   { action: warn,  max_count: 5 }
    low:      { action: allow, max_count: -1 }
```

### 宽松模式（开发环境）

```yaml
thresholds:
  vulnerabilities:
    critical: { action: warn,  max_count: -1 }
    high:     { action: warn,  max_count: -1 }
    medium:   { action: allow, max_count: -1 }
    low:      { action: allow, max_count: -1 }
```

## 常见问题

### Q: 首次扫描很慢？

A: Trivy首次运行需要下载漏洞数据库，后续扫描会快很多。数据库缓存后扫描速度会显著提升。

### Q: 如何扫描私有仓库镜像？

A: 确保Docker已登录到私有仓库，Trivy会自动使用Docker的认证信息。

```bash
docker login registry.example.com
./container-scanner registry.example.com/private/image:latest
```

### Q: 可以在离线环境使用吗？

A: 可以，需要先在有网络的环境下载漏洞数据库，然后复制到离线环境的缓存目录。

### Q: 如何添加自定义的白名单规则？

A: 在配置文件的 `secret_whitelist` 部分添加自定义的规则、文件或匹配值。

### Q: 如何临时禁用阻断模式？

A: 使用 `--fail=false` 参数，超过阻断阈值时不会导致构建失败。

## 许可证

MIT License
