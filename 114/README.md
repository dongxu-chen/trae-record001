# 容器镜像漏洞扫描器 v3.0

基于 Python + Trivy 的容器镜像漏洞扫描工具，支持离线数据库同步、增量扫描、钉钉告警、自动修复脚本生成。

## ✨ 新功能 v3.0

### 1. 离线数据库同步
- 🔄 支持从内网镜像仓库同步漏洞数据库
- 🌐 适合离线/内网环境使用
- ⚙️ 通过 `--mirror` 参数指定镜像地址

### 2. 增量扫描
- ⚡ 只扫描新增或变更的镜像层，大幅提升扫描速度
- 💾 本地缓存已扫描层的漏洞信息
- 📊 显示总层数和变更层数
- 🔍 支持多次重复扫描，无变更时直接返回缓存结果

### 3. 钉钉高危告警
- 🔔 自动检测 CVSS >= 7.0 的高危漏洞
- 📱 发送 Markdown 格式的告警消息
- 🔐 支持签名验证（可选 secret）
- 📋 包含漏洞统计和详细信息

### 4. 修复建议脚本
- 🛠️ 自动生成 Dockerfile 修复脚本
- 📝 包含 apt/yum/apk 等多种包管理器支持
- 🐳 两种修复方式：构建新镜像 和 运行时修复
- 📦 自动识别需要升级的软件包及版本

## 功能特性

- ✅ 扫描本地 Docker 镜像
- ✅ 生成 **CycloneDX SBOM** 清单（JSON 格式）
- ✅ 输出漏洞报告（CVE编号/严重等级/CVSS分数/修复版本/描述）
- ✅ 支持导出美观的 HTML 报告
- ✅ 彩色终端输出和加载动画
- ✅ 漏洞按严重等级排序显示
- ✅ 可配置超时时间（默认 10 分钟）
- ✅ 支持跳过数据库更新
- ✅ 可视化漏洞统计（条形图）

## 前置要求

### 1. 安装 Trivy

Trivy 是一个全面的容器漏洞扫描器。

**Windows (使用 Chocolatey):**
```bash
choco install trivy
```

**Linux:**
```bash
sudo apt-get install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy
```

**macOS:**
```bash
brew install aquasecurity/trivy/trivy
```

验证安装：
```bash
trivy --version
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

## 🚀 使用方法

### 基本扫描

```bash
python image_scanner.py scan <镜像名称>
```

**示例：**
```bash
python image_scanner.py scan nginx:latest
```

### 增量扫描（推荐）

```bash
python image_scanner.py scan nginx:latest --incremental
# 或简写
python image_scanner.py scan nginx:latest -i
```

### 使用内网镜像数据库

```bash
# 使用全局镜像配置
python image_scanner.py --mirror https://your-mirror.com/trivy-db scan nginx:latest

# 单独同步数据库
python image_scanner.py sync-db https://your-mirror.com/trivy-db
```

### 生成 CycloneDX SBOM

```bash
python image_scanner.py scan nginx:latest --sbom sbom.json
```

或单独生成：

```bash
python image_scanner.py sbom nginx:latest sbom.json
```

### 导出 HTML 报告

```bash
python image_scanner.py scan nginx:latest --html report.html
```

### 钉钉高危告警

```bash
python image_scanner.py scan nginx:latest --dingtalk-webhook "https://oapi.dingtalk.com/robot/send?access_token=xxx"
# 或简写
python image_scanner.py scan nginx:latest -d "https://oapi.dingtalk.com/robot/send?access_token=xxx"
```

### 生成修复建议脚本

```bash
python image_scanner.py scan nginx:latest --fix-script fix.sh
# 或简写
python image_scanner.py scan nginx:latest -f fix.sh

# 单独生成修复脚本
python image_scanner.py fix-script nginx:latest fix.sh
```

### 自定义超时时间（大镜像扫描）

```bash
# 设置 30 分钟超时
python image_scanner.py --timeout 1800 scan nginx:latest
```

### 跳过数据库更新

```bash
python image_scanner.py scan nginx:latest --no-db-update
```

### 手动更新数据库

```bash
python image_scanner.py update-db
```

### 完整功能 - 一次性执行所有操作

```bash
python image_scanner.py scan nginx:latest \
    --incremental \
    --sbom sbom.json \
    --html report.html \
    --json-output raw.json \
    --fix-script fix.sh \
    --dingtalk-webhook "https://oapi.dingtalk.com/robot/send?access_token=xxx"
```

## 命令选项

### 全局选项

| 选项 | 简写 | 说明 |
|------|------|------|
| `--timeout <秒>` | `-t` | 扫描超时时间，默认 600 秒（10分钟） |
| `--mirror <URL>` | `-m` | 内网漏洞数据库镜像仓库地址 |

### scan 命令

| 选项 | 简写 | 说明 |
|------|------|------|
| `--sbom <文件>` | `-s` | 生成 CycloneDX SBOM 并保存到指定文件 |
| `--html <文件>` | `-h` | 导出 HTML 报告到指定文件 |
| `--json-output <文件>` | `-j` | 导出原始 JSON 扫描结果 |
| `--no-db-update` | - | 跳过漏洞数据库更新检查 |
| `--incremental` | `-i` | 启用增量扫描（只扫描新增或变更的层） |
| `--dingtalk-webhook <URL>` | `-d` | 钉钉机器人 Webhook 地址，用于高危告警 |
| `--fix-script <文件>` | `-f` | 生成修复建议脚本并保存到指定文件 |

### sbom 命令

仅生成 CycloneDX SBOM 清单：

```bash
python image_scanner.py sbom <镜像名称> <输出文件>
```

### sync-db 命令

从内网镜像仓库同步漏洞数据库：

```bash
python image_scanner.py sync-db <镜像仓库URL>
```

### update-db 命令

手动更新 Trivy 漏洞数据库（从官方源）：

```bash
python image_scanner.py update-db
```

### fix-script 命令

单独生成修复建议脚本：

```bash
python image_scanner.py fix-script <镜像名称> <输出文件> [--dingtalk-webhook <URL>]
```

## 📋 输出说明

### 终端输出

- **旋转加载动画** 显示扫描进度
- **彩色表格** 显示漏洞列表
- **CVSS 分数** 显示漏洞严重程度
- **可视化统计** 条形图显示各等级漏洞数量
- **漏洞详情与修复建议** 前 5 个严重/高危漏洞的完整描述
- **增量扫描信息** 显示总层数和变更层数

### HTML 报告

- 美观的渐变头部设计
- 漏洞统计卡片（悬停动画效果）
- 漏洞详情表格（CVSS 彩色徽章）
- 漏洞描述与修复建议
- 响应式设计
- 严重等级颜色标识
- 空状态友好提示

### 修复脚本输出

脚本包含两种修复方式：

1. **Dockerfile 方式** - 构建新的安全镜像
2. **运行时方式** - 在运行的容器中执行升级

生成的脚本会自动创建 `Dockerfile.fix` 文件，包含所有需要升级的软件包。

### CycloneDX SBOM 格式

- **OWASP 标准格式** - CycloneDX v1.4+
- **完整组件列表** - 包含所有软件包
- **版本信息** - 完整版本号
- **组件关系** - 依赖关系描述
- **许可证信息** - 开源许可证
- **PURL 标识符** - Package URL 标准格式

## 严重等级说明

| 等级 | CVSS 分数范围 | 颜色 | 说明 |
|------|--------------|------|------|
| CRITICAL | 9.0 - 10.0 | 红色 | 严重漏洞，需立即修复 |
| HIGH | 7.0 - 8.9 | 橙色 | 高危漏洞，建议尽快修复 |
| MEDIUM | 4.0 - 6.9 | 黄色 | 中危漏洞，计划修复 |
| LOW | 0.1 - 3.9 | 蓝色 | 低危漏洞，可延后处理 |
| UNKNOWN | N/A | 灰色 | 未知等级 |

## 🔔 钉钉告警配置

### 创建钉钉机器人

1. 打开钉钉群设置
2. 进入"智能群助手"
3. 添加"自定义机器人"
4. 设置安全配置（建议使用"自定义关键词"，添加"漏洞"关键词）
5. 获取 Webhook 地址

### 告警内容

- 镜像名称
- 扫描时间
- 漏洞统计（严重/高危数量）
- 前 10 个高危漏洞详情（CVE编号、软件包、版本信息）
- 修复建议

## 💾 缓存说明

扫描缓存存储在用户目录下：

```
~/.trivy_scanner/cache/
└── scan_cache.json
```

缓存内容包括：
- 已扫描镜像的层信息
- 各层的漏洞信息
- 最后扫描时间

如需清除缓存，直接删除该目录即可。

## 项目结构

```
.
├── image_scanner.py      # 主程序 v3.0
├── requirements.txt      # Python 依赖
└── README.md            # 说明文档
```

## 核心类说明

### Spinner

旋转加载动画类，提供友好的用户体验：

- `start()` - 开始动画
- `stop(success, end_message)` - 停止动画并显示结果

### DingTalkNotifier

钉钉告警类：

- `__init__(webhook_url, secret)` - 初始化告警器
- `send_high_risk_alert(image_name, vulnerabilities)` - 发送高危漏洞告警

### ScanCacheManager

扫描缓存管理类：

- `get_image_layers(image_name)` - 获取镜像层列表
- `get_changed_layers(image_name)` - 获取变更的层
- `update_cache(image_name, vulnerabilities)` - 更新缓存

### TrivyScanner

主扫描器类，包含以下方法：

- `scan_image(image_name, download_db)` - 扫描镜像
- `scan_image_incremental(image_name)` - 增量扫描镜像
- `sync_database_from_mirror(mirror_url)` - 从内网镜像同步数据库
- `generate_cyclonedx_sbom(image_name, output_file)` - 生成标准 CycloneDX SBOM
- `get_vulnerabilities(scan_result)` - 提取漏洞列表（包含 CVSS、描述、修复建议）
- `print_vulnerability_report(vulnerabilities)` - 打印增强版终端报告
- `generate_fix_script(vulnerabilities, image_name, output_file)` - 生成修复脚本
- `export_html_report(vulnerabilities, image_name, output_file)` - 导出精美 HTML 报告

## 示例输出

### 增量扫描示例

```
正在检查镜像层变更: nginx:latest
  总层数: 7, 变更层数: 2
正在执行增量扫描...
正在扫描镜像: nginx:latest
⠋ 正在扫描镜像...
✓ 完成

========================================================
🔒 漏洞报告
========================================================
...
```

### 修复脚本示例 (fix.sh)

```bash
#!/bin/bash
# 修复脚本 - nginx:latest
# 生成时间: 2024-01-15 10:30:00

echo "正在修复镜像: nginx:latest"
echo ""

# Dockerfile 修复方式
echo "=== Dockerfile 修复方式 ==="
cat > Dockerfile.fix << 'EOF'
# 修复脚本 - nginx:latest
# 生成时间: 2024-01-15 10:30:00
# 漏洞数量: 5

FROM nginx:latest

# 修复系统包漏洞
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3=3.0.2-0ubuntu1.8 \
    libcurl4=7.81.0-1ubuntu1.10 \
    && rm -rf /var/lib/apt/lists/*
EOF

echo ""
echo "Dockerfile.fix 已生成，执行以下命令构建修复后的镜像:"
echo "  docker build -f Dockerfile.fix -t nginx:latest-fixed ."
```

## 注意事项

1. **首次运行** - 会自动下载漏洞数据库（约 50MB），请耐心等待
2. **增量扫描** - 需要 Docker 命令行工具来获取镜像层信息
3. **内网环境** - 请确保镜像仓库可访问，并使用 `--mirror` 参数
4. **大镜像扫描** - 对于大型镜像，建议使用 `--timeout` 增加超时时间
5. **钉钉告警** - 请确保网络可访问钉钉 OpenAPI
6. **修复脚本** - 生成的脚本需要根据实际镜像的包管理器进行调整

## CycloneDX SBOM 示例结构

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.4",
  "version": 1,
  "components": [
    {
      "type": "library",
      "name": "openssl",
      "version": "1.1.1",
      "purl": "pkg:deb/debian/openssl@1.1.1",
      "licenses": [...]
    }
  ],
  "dependencies": [...]
}
```

## 许可证

MIT License
