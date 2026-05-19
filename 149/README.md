# Security Patch Manager v3.0.0

基于Bash + Ansible的安全漏洞补丁管理工具，用于批量管理服务器的安全补丁。

## ✨ v3.0 新增功能

- 🔍 **安全基线扫描** - 与安全基线进行对比，生成合规性评估报告
- 🎯 **补丁预演模式** - Dry-run模拟，检测待安装补丁而不实际安装
- ⚡ **CVSS优先级排序** - 基于CVSS评分对补丁进行优先级排序
- 🔔 **钉钉/企业微信通知** - 自动推送报告到企业即时通讯工具

## 功能特性

| 功能 | 描述 |
|------|------|
| 🔍 CVE漏洞扫描 | 扫描目标主机的安全漏洞和待安装补丁 |
| 📏 安全基线评估 | SSH配置、密码策略、防火墙、内核参数、文件权限等 |
| 🎯 补丁预演模拟 | 模拟检测待安装补丁，CVSS优先级分类 |
| 📦 批量安装补丁 | 支持分批并行安装安全补丁，检测内核更新 |
| ⏪ 补丁回滚 | 安全回滚最近安装的补丁，支持依赖检查 |
| 📊 合规报表 | 生成HTML和JSON格式的合规性报告，含详细统计 |
| 🔔 通知推送 | 钉钉/企业微信Webhook报告推送 |

## 补丁状态说明

| 状态 | 颜色 | 说明 |
|------|------|------|
| FIXED | 🟢 绿色 | 无待安装安全补丁，系统已修复 |
| UNFIXED | 🔴 红色 | 有待安装的安全补丁 |
| NA | ⚪ 灰色 | 不适用（不支持的操作系统） |

## CVSS优先级等级

| 等级 | CVSS评分 | SLA修复期限 |
|------|----------|-------------|
| CRITICAL | ≥ 9.0 | 3 天内 |
| HIGH | ≥ 7.0 | 7 天内 |
| MEDIUM | ≥ 4.0 | 15 天内 |
| LOW | ≥ 0.0 | 30 天内 |

## 目录结构

```
.
├── patch-manager.sh              # 主命令行工具
├── config/
│   ├── patch-manager.conf        # 配置文件
│   ├── inventory.ini             # Ansible主机清单
│   └── security-baseline.yml     # 安全基线配置
├── ansible/
│   ├── ansible.cfg               # Ansible配置
│   └── playbooks/
│       ├── scan-vulnerabilities.yml    # 漏洞扫描playbook
│       ├── baseline-scan.yml           # 基线扫描playbook
│       ├── patch-simulation.yml        # 补丁预演playbook
│       ├── install-patches.yml         # 补丁安装playbook
│       ├── rollback-patches.yml        # 补丁回滚playbook
│       ├── generate-report.yml         # 报表生成playbook
│       └── send-notification.yml       # 通知推送playbook
├── reports/                     # 报告输出目录
└── logs/                        # 日志目录
```

## 快速开始

### 1. 前置要求

- Ansible 2.9+
- SSH访问目标主机的权限
- 目标主机的sudo权限
- （可选）jq - 用于格式化JSON报告输出

### 2. 配置主机清单

编辑 `config/inventory.ini`，添加需要管理的主机：

```ini
[web_servers]
web01.example.com ansible_user=admin
web02.example.com ansible_user=admin

[db_servers]
db01.example.com ansible_user=centos

[all:vars]
ansible_connection=ssh
```

### 3. 配置安全基线

编辑 `config/security-baseline.yml`，自定义安全基线配置：

```yaml
# SSH安全配置
permit_root_login: "no"
password_authentication: "yes"

# 防火墙要求
firewall_required: true

# 安全软件
required_packages:
  - fail2ban
  - auditd
```

### 4. 使用方法

#### 显示帮助信息

```bash
./patch-manager.sh help
```

#### 漏洞扫描

```bash
# 扫描所有主机
./patch-manager.sh scan

# 只扫描特定主机组
./patch-manager.sh scan --limit web_servers

# 详细输出
./patch-manager.sh scan -v
```

#### 安全基线扫描

```bash
# 评估所有主机的安全合规性
./patch-manager.sh baseline

# 只扫描数据库服务器
./patch-manager.sh baseline --limit db_servers
```

#### 补丁预演（Dry-run）

```bash
# 模拟检测所有待安装补丁
./patch-manager.sh simulate

# 按CVSS优先级显示补丁
./patch-manager.sh simulate --limit web_servers
```

#### 安装补丁

```bash
# 安装所有安全补丁
./patch-manager.sh install

# 只在数据库服务器上安装
./patch-manager.sh install --limit db_servers

# 禁用自动重启（即使检测到内核更新）
./patch-manager.sh install --no-reboot
```

#### 回滚补丁

```bash
# 安全回滚（包含依赖检查）
./patch-manager.sh rollback

# 强制回滚（跳过安全检查，谨慎使用）
./patch-manager.sh rollback --force-rollback
```

#### 生成合规报表

```bash
./patch-manager.sh report
```

#### 推送通知

```bash
# 推送到钉钉
./patch-manager.sh notify \
  --webhook "https://oapi.dingtalk.com/robot/send?access_token=XXX" \
  --webhook-type dingtalk \
  --report reports/patch_simulation_20240101_120000.json

# 推送到企业微信
./patch-manager.sh notify \
  --webhook "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=XXX" \
  --webhook-type wechat \
  --report reports/baseline_scan_20240101_120000.json
```

## 配置选项

编辑 `config/patch-manager.conf` 可以自定义以下配置：

```bash
# 主机清单文件
INVENTORY_FILE="${SCRIPT_DIR}/config/inventory.ini"

# 默认分批执行比例
BATCH_SIZE="30%"

# 只安装安全更新
ONLY_SECURITY_UPDATES=true

# 更新后自动重启
REBOOT_AFTER_UPDATE=false

# Ansible配置
ANSIBLE_FORKS=10
ANSIBLE_TIMEOUT=30

# 通知配置
DINGTALK_WEBHOOK=""
WECHAT_WEBHOOK=""
```

## 支持的操作系统

- 🐧 Debian/Ubuntu 系列
- 🔴 RHEL/CentOS 系列

## 安全基线检查项

### 🔐 身份认证安全
- SSH root登录限制
- 密码认证策略
- PAM密码质量要求

### 🛡️ 网络安全配置
- 防火墙状态检测
- 端口开放合规性

### 📁 文件系统安全
- 关键文件权限检查
- 敏感文件属主验证

### 🔧 服务安全配置
- Fail2ban防护
- Auditd审计服务

### 🧠 内核安全参数
- SYN Cookie保护
- ASLR内存保护
- IP转发限制
- 源路由禁用

## 报告格式

工具会生成两种格式的报告：

### JSON格式报告
- 完整的主机扫描结果
- 详细的统计数据
- 可用于自动化处理和集成

### HTML格式报告
- 可视化的合规仪表板
- 颜色编码的状态显示
- 详细的主机表格
- 汇总统计卡片

报告保存在 `reports/` 目录下。

## 安全最佳实践

1. 🧪 **测试先行** - 在生产环境前，先在测试环境验证补丁
2. 🎯 **预演检测** - 使用 `simulate` 命令在安装前检测补丁
3. 📋 **备份确认** - 执行补丁操作前确保系统备份完整
4. 🕐 **维护窗口** - 在低峰时段执行补丁安装
5. 🔍 **依赖检查** - 回滚操作会自动检查依赖关系
6. 🔒 **SSH安全** - 使用SSH密钥认证而非密码
7. 📧 **变更通知** - 执行补丁操作前通知相关团队
8. 📊 **基线对比** - 定期运行基线扫描确保合规

## 故障排除

### 问题：Ansible无法连接主机
- 检查SSH连通性：`ssh user@host`
- 验证主机清单配置
- 确认目标主机sudo权限

### 问题：yum/apt操作被锁定
- 等待其他包管理进程完成
- 手动检查：`ps aux | grep -E 'yum|apt|dpkg'`

### 问题：回滚报告警告
- 检查rollback报告中的警告信息
- 对于依赖问题，可能需要手动介入
- 考虑使用 `--force-rollback`（谨慎使用）

### 问题：内核更新后未重启
- 安装报告会显示需要重启的主机数量
- 手动执行重启：`ansible all -m reboot`

### 问题：通知推送失败
- 验证Webhook URL是否正确
- 检查网络连接是否可达
- 确认机器人IP白名单配置

## 版本历史

### v3.0.0 (2024)
- ✨ 新增安全基线扫描功能
- ✨ 新增补丁预演（Dry-run）模式
- ✨ 新增CVSS优先级排序功能
- ✨ 新增钉钉/企业微信通知推送
- 📊 增强报告汇总统计

### v2.0.0 (2024)
- ✨ 新增内核重启检测功能
- ✨ 新增补丁回滚安全检查
- ✨ 新增幂等操作保证
- ✨ 增强合规报表统计

### v1.0.0
- 🎉 初始版本发布
- 基础扫描、安装、回滚、报表功能

## License

本项目仅供内部安全管理使用。
