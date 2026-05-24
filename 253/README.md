# 服务器配置基线检查工具

一个基于 Python + Ansible + Paramiko 实现的 Linux 服务器安全配置基线检查工具。

## ✨ 新功能 (v2.1)

- 🔧 **SSH配置智能解析**：自动解析 `sshd_config` 获取实际监听端口，端口检查更准确
- 📏 **内核参数单位标准化**：支持字节、秒等单位自动转换和比较
- 📋 **简化YAML语法**：新增 `ssh_config`、`port_listening`、`regex_match` 等检查类型
- 📚 **丰富模板库**：内置7种场景模板，覆盖通用、Web、数据库、K8s、网络安全等场景
- 🛠️ **自动修复模式**：一键修复文件权限、内核参数等可自动修复项
- 📦 **基线版本管理**：记录基线变更历史，支持版本回滚
- 📈 **趋势分析**：展示合规率变化趋势、TOP问题项、按类别表现

## 功能特性

- 🔍 **多维度安全检查**
  - SSH 安全配置检查
  - 防火墙规则检查
  - 内核参数检查
  - 用户权限检查
  - 文件权限检查

📊 **灵活的检查方式**
  - 基于 Paramiko 的单服务器实时检查
  - 基于 Ansible 的批量服务器检查

📝 **丰富的报告输出**
  - 控制台彩色输出报告
  - JSON 格式报告
  - 文本格式报告
  - 自动生成修复 Shell 脚本

🎨 **自定义基线模板**
  - 支持 YAML 格式自定义检查规则
  - 内置多种场景模板
  - 支持多种检查类型

## 项目结构

```
.
├── main.py                          # 主程序入口
├── requirements.txt                 # Python 依赖
├── hosts.yaml.example              # 主机配置示例
├── README.md                       # 项目文档
├── baseline_checker/
│   ├── __init__.py
│   ├── ssh_client.py             # Paramiko SSH 客户端
│   ├── check_engine.py           # 检查引擎（含单位标准化和SSH解析）
│   ├── report_generator.py      # 报告生成器
│   ├── ansible_runner.py       # Ansible 集成模块
│   ├── templates/              # 基线模板库
│   │   ├── default_baseline.yaml              # 默认基线（29项）
│   │   ├── minimal_baseline.yaml              # 最小化基线（10项）
│   │   ├── web_server_baseline.yaml           # Web服务器基线（11项）
│   │   ├── database_server_baseline.yaml      # 数据库服务器基线（12项）
│   │   ├── kubernetes_baseline.yaml           # K8s节点基线（12项）
│   │   ├── network_security_baseline.yaml     # 网络安全增强基线（22项）
│   │   └── custom_template_example.yaml        # 自定义模板示例（10项）
│   └── reports/                # 报告输出目录
└── logs/                       # 日志目录
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置主机信息

复制示例配置文件：

```bash
cp hosts.yaml.example hosts.yaml
```

编辑 `hosts.yaml`，添加目标服务器信息：

```yaml
hosts:
  - hostname: 192.168.1.100
    port: 22
    username: root
    password: your_password
    # 或者使用密钥认证
    # key_file: /path/to/id_rsa
```

### 3. 运行检查

#### 单服务器检查：

```bash
# 使用命令行参数
python main.py --host 192.168.1.100 --username root --password secret

# 使用配置文件
python main.py --hosts-config hosts.yaml
```

#### 指定检查类别：

```bash
# 只检查 SSH 和内核参数
python main.py --hosts-config hosts.yaml --categories ssh,kernel
```

#### 指定基线模板：

```bash
# 使用Web服务器基线
python main.py --hosts-config hosts.yaml --template web_server_baseline.yaml

# 使用K8s节点基线
python main.py --hosts-config hosts.yaml --template kubernetes_baseline.yaml

# 使用网络安全增强基线
python main.py --hosts-config hosts.yaml --template network_security_baseline.yaml
```

#### 使用 Ansible 批量检查：

```bash
python main.py --hosts-config hosts.yaml --ansible
```

#### 生成多种格式报告：

```bash
python main.py --hosts-config hosts.yaml --output json,text,script
```

#### 查看可用基线模板：

```bash
python main.py --list-templates
```

#### 启用自动修复：

```bash
# 检查并自动修复可修复项
python main.py --host 192.168.1.100 --auto-fix

# 不保存扫描结果到历史
python main.py --host 192.168.1.100 --no-save
```

#### 查看扫描历史：

```bash
# 查看所有历史记录
python main.py --history

# 查看指定主机的历史记录
python main.py --history --host 192.168.1.100

# 查看最近20条记录
python main.py --history --limit 20
```

#### 趋势分析：

```bash
# 查看文本趋势报告
python main.py --trend

# 查看指定主机的趋势（最近30天）
python main.py --trend --host 192.168.1.100 --limit 30

# 导出HTML趋势报告
python main.py --trend-html trend_report.html
```

#### 基线版本管理：

```bash
# 保存当前基线模板为新版本
python main.py --save-version default_baseline.yaml --version v2.1 --version-desc "添加新检查项"

# 查看基线版本历史
python main.py --list-versions default_baseline.yaml

# 回滚到指定版本
python main.py --rollback default_baseline.yaml --version v2.0
```

## 自动修复功能

### 可自动修复的检查类型

| 检查类型 | 是否可自动修复 | 说明 |
|---------|---------------|------|
| `file_permission` | ✅ 是 | 文件权限修复 |
| `file_content` | ✅ 是 | 文件内容修改 |
| `sysctl` | ✅ 是 | 内核参数设置 |
| `ssh_config` | ✅ 是 | SSH配置修改 |
| 其他类型 | ❌ 否 | 需要手动修复 |

### 自动修复工作流程

1. **扫描**：执行基线检查，识别失败项
2. **预览**：显示可自动修复项列表和修复命令
3. **确认**：用户确认后执行修复
4. **验证**：自动重新检查修复项，确认修复生效

### 安全机制

- Critical 严重级别的检查项默认不自动修复
- 所有修复操作执行前需要用户确认
- 修复历史记录保存在 `data/fixes/` 目录

## 基线版本管理

### 版本管理功能

- **保存版本**：将当前基线模板保存为带描述的历史版本
- **版本列表**：查看模板的所有历史版本
- **版本回滚**：一键回滚到任意历史版本

### 版本文件结构

所有版本保存在 `data/baselines/` 目录：
- `{template_name}.versions.json` - 版本元数据
- `{template_name}_{version}.yaml` - 版本备份文件

## 趋势分析功能

### 分析指标

1. **合规率趋势**：展示历史扫描的合规率变化
2. **TOP问题项**：统计出现频率最高的问题
3. **按类别表现**：各检查类别的通过率统计
4. **严重程度分布**：不同严重级别问题的分布

### 输出格式

- **文本报告**：控制台彩色输出
- **HTML报告**：美观的网页报告，支持分享

## 检查类型说明

### 支持的检查类型

| 检查类型 | 说明 | 适用场景 |
|---------|------|---------|
| `ssh_config` | 解析sshd_config检查配置项 | SSH安全检查 |
| `port_listening` | 检查端口是否在监听 | 端口监听检查，自动获取SSH实际端口 |
| `file_content` | 检查文件内容匹配 | 通用文件检查 |
| `file_permission` | 检查文件权限 | 关键文件权限检查 |
| `sysctl` | 检查内核参数 | 内核参数检查，支持单位转换 |
| `command` | 执行命令并检查输出 | 自定义命令检查 |
| `service_status` | 检查服务状态 | 系统服务检查 |
| `regex_match` | 正则匹配检查 | 复杂模式匹配 |

### 匹配类型 (match_type)

- `exact` - 精确匹配
- `contains` - 包含匹配
- `not_contains` - 不包含匹配
- `regex` - 正则匹配
- `matches` - 正则匹配（文件内容）
- `not_matches` - 正则不匹配
- `exists` - 存在即警告
- `not_exists` - 不存在即通过
- `exit_code` - 检查命令退出码

### 单位标准化 (unit)

内核参数检查支持自动单位转换：

**字节单位**：`b`, `kb`, `mb`, `gb`, `k`, `m`, `g`
**时间单位**：`s`, `sec`, `seconds`, `min`, `minutes`, `h`, `hours`, `d`, `days`
**数量单位**：`count` (无转换)

**比较类型 (compare)**：
- `eq` - 等于
- `ne` - 不等于
- `gt` - 大于
- `ge` - 大于等于
- `lt` - 小于
- `le` - 小于等于

### 严重程度 (severity)

- `critical` - 严重
- `high` - 高
- `medium` - 中
- `low` - 低

## 基线模板语法

### SSH配置检查 (ssh_config)

```yaml
- id: SSH-001
  name: 禁止root用户直接登录
  severity: high
  check_type: ssh_config
  sshd_key: PermitRootLogin      # sshd_config中的配置项名
  expected_value: "no"
  fix_command: sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && systemctl restart sshd
```

### 端口监听检查 (port_listening)

```yaml
- id: SSH-006
  name: SSH端口监听检查
  severity: high
  check_type: port_listening
  expected_status: listening     # listening 或 not_listening
  # 不指定port时自动从sshd_config读取
  fix_command: systemctl restart sshd
```

### 内核参数检查 (sysctl)

```yaml
- id: KERNEL-008
  name: 最大文件句柄数
  severity: medium
  check_type: sysctl
  parameter: fs.file-max
  expected_value: "65535"
  unit: count                    # 单位：count/bytes/seconds
  compare: ge                    # 比较类型：ge=大于等于
  fix_command: echo 'fs.file-max = 65535' >> /etc/sysctl.conf && sysctl -p
```

```yaml
- id: KERNEL-007
  name: TCP最大缓冲区大小
  severity: low
  check_type: sysctl
  parameter: net.ipv4.tcp_wmem
  expected_value: "4mb"          # 支持带单位的值
  unit: bytes
  compare: ge
  fix_command: echo 'net.ipv4.tcp_wmem = 4096 87380 4194304' >> /etc/sysctl.conf && sysctl -p
```

### 正则匹配检查 (regex_match)

```yaml
- id: WEB-003
  name: 禁用Nginx版本信息
  severity: medium
  check_type: regex_match
  file_path: /etc/nginx/nginx.conf
  pattern: server_tokens\s+off   # 正则表达式
  match_type: matches
  fix_command: sed -i '/http {/a\\    server_tokens off;' /etc/nginx/nginx.conf && nginx -s reload
```

## 内置模板库

| 模板文件 | 检查项 | 适用场景 |
|---------|--------|---------|
| `default_baseline.yaml` | 29项 | 通用Linux服务器 |
| `minimal_baseline.yaml` | 10项 | 快速扫描、关键检查 |
| `web_server_baseline.yaml` | 11项 | Nginx/Apache Web服务器 |
| `database_server_baseline.yaml` | 12项 | MySQL/PostgreSQL数据库 |
| `kubernetes_baseline.yaml` | 12项 | Kubernetes节点 |
| `network_security_baseline.yaml` | 22项 | 高安全要求服务器 |
| `custom_template_example.yaml` | 10项 | 自定义模板示例 |

## 自定义基线模板

创建自定义的 YAML 模板文件，放置在 `baseline_checker/templates/` 目录下：

```yaml
name: "我的自定义基线"
version: "1.0"
description: "自定义检查项"

checks:
  my_category:
    - id: MY-001
      name: "检查项名称"
      description: "检查项描述"
      severity: "high"
      check_type: "ssh_config"
      sshd_key: "PermitRootLogin"
      expected_value: "no"
      fix_command: "sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config"
```

## 输出说明

### 报告文件

检查完成后，报告将生成在 `baseline_checker/reports/` 目录下：

- `baseline_report_<hostname>_<timestamp>.txt` - 文本格式报告
- `baseline_report_<hostname>_<timestamp>.json` - JSON 格式报告
- `fix_script_<hostname>_<timestamp>.sh` - 自动修复脚本

### 修复脚本

生成的修复脚本包含所有失败检查项的修复命令，使用前请仔细审查！

```bash
# 审查修复脚本
cat baseline_checker/reports/fix_script_*.sh

# 执行修复（谨慎操作）
bash baseline_checker/reports/fix_script_*.sh
```

## 注意事项

1. **权限要求**：检查用户需要足够的权限才能读取系统文件和执行系统命令。

2. **修复脚本**：自动生成的修复脚本仅供参考，执行前请仔细审查每个命令。

3. **Ansible 模式**：Ansible 模式需要在控制端安装 Ansible。

4. **密钥认证**：推荐使用 SSH 密钥认证替代密码认证。

5. **SSH端口自动检测**：`port_listening` 类型会自动从 `sshd_config` 读取实际端口，无需手动指定。

6. **单位转换**：内核参数检查会自动进行单位标准化比较，如 `4mb` 会转换为 `4194304` 字节进行比较。

## 许可证

MIT License
