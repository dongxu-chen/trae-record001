# Container Security Monitor (CSM)

一个基于 Go + eBPF + Falco 规则的容器运行时安全监控工具。

## 功能特性

- **进程监控**: 监控容器内的进程创建、执行和终止
- **文件系统监控**: 监控敏感文件访问和修改
- **网络监控**: 监控网络连接和可疑通信
- **异常行为检测**:
  - 提权攻击检测
  - 反弹Shell检测
  - 敏感文件读取检测
- **自定义规则**: 支持 Falco 风格的自定义检测规则
- **多输出渠道**: stdout、文件、Webhook
- **可观测性**: Prometheus 指标 + Grafana 仪表盘

## 系统架构

```
┌─────────────────┐
│  eBPF Probes    │  内核态数据采集
│  (Process/File/ │
│   Network)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Go User Space  │  用户态处理
│  - Event Parser │
│  - Rule Engine  │
│  - Detector     │
└────────┬────────┘
         │
         ├──────────────────────┐
         │                      │
         ▼                      ▼
┌─────────────────┐   ┌─────────────────┐
│  Prometheus     │   │  Alert Outputs  │
│  Metrics        │   │  - stdout       │
│                 │   │  - file         │
│                 │   │  - webhook      │
└────────┬────────┘   └─────────────────┘
         │
         ▼
┌─────────────────┐
│  Grafana        │
│  Dashboard      │
└─────────────────┘
```

## 快速开始

### 前置要求

- Linux Kernel >= 5.8 (支持 eBPF)
- Docker 和 Docker Compose
- Go 1.21+
- Clang/LLVM (编译 eBPF 程序)

### 本地运行

```bash
# 克隆项目
git clone <repository-url>
cd container-security-monitor

# 下载依赖
go mod download

# 编译 eBPF 程序和 Go 二进制
make build

# 运行监控工具 (需要 root 权限)
sudo make run
```

### Docker 部署

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f csm

# 访问 Grafana
# http://localhost:3000 (admin/admin123)

# 访问 Prometheus
# http://localhost:9090
```

## 配置说明

### 主配置文件 (config/config.yaml)

```yaml
metrics_addr: ":9091"           # Prometheus 指标监听地址
rules_dir: "rules"              # 规则文件目录
log_level: "info"               # 日志级别

outputs:                        # 输出配置
  - type: stdout
    config: {}
  - type: file
    config:
      path: "/var/log/csm/alerts.json"
  - type: webhook
    config:
      url: "https://your-webhook-endpoint.com/alerts"
```

### 自定义规则

规则文件使用 YAML 格式，支持正则表达式匹配。

**规则字段说明:**

| 字段 | 描述 | 示例 |
|------|------|------|
| name | 规则名称 | `sensitive_file_access` |
| description | 规则描述 | `检测敏感文件访问` |
| severity | 严重级别 | `critical/high/medium/low` |
| event_type | 事件类型 | `process/file/network` |
| condition | 匹配条件 (正则) | `filename.*shadow` |
| output | 输出消息 | `访问了敏感文件: %filename%` |
| remediation | 处置建议 | `立即隔离容器` |
| tags | 标签 | `["file", "sensitive"]` |
| enabled | 是否启用 | `true/false` |

**事件字段变量:**

- Process 事件: `%pid%`, `%ppid%`, `%uid%`, `%comm%`, `%container_id%`
- File 事件: `%pid%`, `%comm%`, `%filename%`, `%container_id%`
- Network 事件: `%saddr%`, `%daddr%`, `%sport%`, `%dport%`, `%comm%`

## 内置检测规则

### 进程安全
- `unexpected_privileged_container`: 特权容器检测
- `suspicious_shell_spawn`: 可疑 Shell 生成
- `package_manager_execution`: 包管理器执行
- `crypto_miner_detection`: 加密货币矿工检测
- `suspicious_uid_change`: UID 变更检测

### 文件系统安全
- `etc_shadow_access`: /etc/shadow 访问
- `docker_socket_access`: Docker Socket 访问
- `ssh_key_access`: SSH 密钥访问
- `kubeconfig_access`: Kubernetes 配置访问
- `proc_mem_access`: 进程内存访问

### 网络安全
- `outbound_ssh_connection`: 出站 SSH 连接
- `suspicious_high_port_connection`: 可疑高端口连接
- `tor_network_connection`: Tor 网络连接
- `dns_tunneling_attempt`: DNS 隧道尝试

## 容器基线学习

系统支持自动学习容器正常行为基线，并检测偏离基线的异常行为。

**基线模式:**

| 模式 | 描述 |
|------|------|
| `learning` | 仅学习不检测，用于初始基线建立 |
| `detecting` | 基于已有基线检测异常 |
| `hybrid` | 同时学习和检测（默认） |

**学习内容:**
- 进程白名单（正常运行的进程及其 UID/GID）
- 文件访问模式（访问的文件路径、类型）
- 网络行为模式（连接的 IP、端口）
- 事件频率和时间间隔

**异常检测类型:**
- `baseline_anomaly_new_process`: 检测到基线外的新进程
- `baseline_anomaly_new_file_access`: 检测到基线外的文件访问
- `baseline_anomaly_new_outbound_ip`: 检测到基线外的出站连接
- `baseline_anomaly_suspicious_port`: 检测到可疑端口连接

**使用流程:**
1. 部署时设置 `mode: "learning"` 运行 24 小时建立基线
2. 切换到 `mode: "detecting"` 开始检测异常
3. 或使用 `mode: "hybrid"` 在学习的同时进行检测

## 事件关联分析 (攻击链还原)

系统通过多事件关联分析，自动识别和还原完整攻击链。

**内置攻击模式识别:**

| 模式 | MITRE 阶段 | 描述 |
|------|-----------|------|
| 提权链 | Privilege Escalation | 识别 UID 变更、特权进程 |
| 凭据窃取 | Credential Access | 识别敏感文件批量访问 |
| 反弹Shell链 | Command & Control | 识别 Shell + 外联的组合 |
| 容器逃逸 | Privilege Escalation | 识别 Docker Socket 访问 + 敏感操作 |
| 横向移动 | Lateral Movement | 识别多主机跳板连接 |
| 数据窃取 | Exfiltration | 识别异常大流量外联 |
| 恶意代码执行 | Execution | 识别挖矿程序 + 可疑Shell |

**攻击链输出示例:**
```
=== Attack Chain Summary ===
Chain ID: chain_abc123_1234567890
Container: abc123def456
Severity: critical
Confidence: 95.0%
Status: active
Duration: 45s

Attack Steps:
  Step 1: privilege_escalation (90.0%)
    Time: 14:30:12 -> 14:30:15
    Rules: [suspicious_uid_change, unexpected_privileged_container]
  Step 2: credential_access (85.0%)
    Time: 14:30:16 -> 14:30:20
    Rules: [etc_shadow_access, ssh_key_access]
  Step 3: command_control (95.0%)
    Time: 14:30:22 -> 14:30:57
    Rules: [reverse_shell_detected, suspicious_outbound_connection]
```

## 威胁情报集成

系统集成威胁情报源，自动检测与恶意IP/域名的通信。

**支持的情报源:**
- Emerging Threats Block IPs
- Abuse.ch Malware Domain List
- Tor Exit Nodes
- 自定义威胁情报源

**检测类型:**
- C2 服务器通信
- 僵尸网络节点通信
- 恶意软件分发点
- Tor 网络通信

**自动拦截:**
- 当 `auto_block: true` 时，自动隔离与恶意IP通信的容器
- 可配置 `block_threshold` 调整拦截灵敏度
- 拦截记录保存在隔离目录供审计

**配置示例:**
```yaml
threat_intel:
  enabled: true
  auto_block: true
  block_threshold: 0.7
  sources:
    - name: "emerging-threats"
      url: "https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt"
      type: "c2"
      interval: 1h
```

## Prometheus 指标

| 指标名称 | 描述 | 标签 |
|---------|------|------|
| `csm_security_alerts_total` | 安全告警总数 | `rule_name`, `severity`, `container_id` |
| `csm_process_events_total` | 进程事件总数 | - |
| `csm_file_events_total` | 文件事件总数 | - |
| `csm_network_events_total` | 网络事件总数 | - |
| `csm_alert_events_total` | 告警事件总数 | - |

## Grafana 仪表盘

仪表盘包含以下面板:
1. **Critical Security Alerts**: 严重级别告警趋势图
2. **Total Alerts (Last Hour)**: 最近一小时告警总数
3. **Process Event Rate**: 进程事件速率
4. **File Event Rate**: 文件事件速率
5. **Network Event Rate**: 网络事件速率
6. **Alerts by Rule**: 按规则统计的告警
7. **Alerts by Container**: 按容器统计的告警

## 安全事件处置建议

### 自动处置 (Auto Remediation)

系统支持自动处置功能，配置方式如下：

```yaml
remediation:
  auto_block: true
  block_severity: "critical"
  block_rules:
    - "privilege_escalation"
    - "reverse_shell_detected"
  network_isolate: true
```

**处置方式:**
- **网络隔离**: 使用 iptables 隔离容器网络（DOCKER-USER/FORWARD 链）
- **进程终止**: 直接 kill 可疑进程
- **容器暂停/停止**: 通过 Docker API 暂停或停止容器

**处置记录:**
- 所有处置操作记录在 `/var/run/csm/quarantine/` 目录
- 包含容器 ID、IP 地址、隔离规则、操作时间等信息

**释放隔离:**
- 可通过 API 或直接操作 iptables 释放容器
- 系统关闭时自动记录所有隔离状态

### Critical 级别
1. 立即隔离受影响的容器（自动处置会执行）
2. 终止可疑进程
3. 保留取证证据
4. 通知安全团队
5. 调查攻击来源和路径

### High 级别
1. 调查告警原因
2. 验证是否误报（检查白名单）
3. 检查容器配置
4. 记录事件并跟进

### Medium/Low 级别
1. 定期审查告警日志
2. 优化规则减少误报
3. 持续监控相关行为
4. 考虑添加白名单

## 开发指南

### 添加新的 eBPF 探针

1. 在 `bpf/` 目录创建 `.bpf.c` 文件
2. 更新 `Makefile` 添加编译规则
3. 在 `pkg/ebpf/manager.go` 中加载和处理事件

### 添加新的检测逻辑

1. 在 `pkg/detector/detector.go` 中添加检测函数
2. 在 `processProcessEvent/processFileEvent/processNetworkEvent` 中调用

### 添加新的输出渠道

1. 在 `pkg/output/manager.go` 中实现 `Output` 接口
2. 在 `NewManager` 中添加类型判断

## 注意事项

1. **权限要求**: eBPF 程序需要 root 权限运行
2. **内核版本**: 建议使用 Linux Kernel 5.15+ 以获得完整 eBPF 功能
3. **性能影响**: 监控会产生一定的性能开销，建议根据实际情况调整
4. **规则优化**: 正则表达式会影响性能，建议优化复杂规则
5. **误报处理**: 需要根据实际环境调整规则以减少误报

## 故障排查

### eBPF 程序加载失败
- 检查内核版本是否支持 eBPF
- 确认具有 root 权限
- 查看系统日志 `dmesg` 获取详细错误

### Prometheus 指标无法采集
- 检查防火墙设置
- 确认 `metrics_addr` 配置正确
- 访问 `http://localhost:9091/metrics` 验证

### Grafana 无数据
- 检查 Prometheus 数据源配置
- 确认 CSM 服务正常运行
- 查看 Prometheus Targets 状态

## License

MIT License
