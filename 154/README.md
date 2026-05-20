# Kubernetes Event Response Bot

一个基于 Python + Slack SDK 的 Kubernetes 事件响应机器人。

## 功能特性

### 核心功能
- :eyes: **监听 Pod 事件** - 实时监控 Kubernetes 集群中的事件
- :repeat: **自动重启 Pod** - 通过 Slack 交互式按钮一键重启 Pod（仅 OnFailure 策略）
- :page_facing_up: **抓取日志** - 一键获取 Pod 日志
- :information_source: **查看状态** - 获取 Pod 详细状态信息
- :no_entry_sign: **事件聚合去重** - 5分钟窗口聚合相同事件，避免告警风暴
- :lock: **Slack 签名验证** - 防止伪造请求，确保安全性
- :alarm_clock: **按钮超时机制** - 30秒超时自动禁用交互按钮

### 高级功能
- :speech_balloon: **自然语言解析** - 支持中英文命令，如"重启命名空间default的Pod"
- :bulb: **故障诊断知识库** - 自动识别10+常见K8s故障，给出原因和解决方案
- :calendar: **主动巡检和日报推送** - 每日自动推送集群健康状态报告
- :speech_balloon: **多渠道通知** - 支持 Slack、Microsoft Teams、钉钉

## 项目结构

```
.
├── main.py                 # 主程序入口
├── k8s_watcher.py          # Kubernetes 监听器模块
├── slack_integration.py    # Slack 集成和交互式按钮
├── event_deduplicator.py   # 事件去重和聚合模块
├── nlp_parser.py           # 自然语言解析模块
├── knowledge_base.py       # 故障诊断知识库
├── health_checker.py       # 主动巡检和日报模块
├── teams_integration.py    # Microsoft Teams 集成
├── dingtalk_integration.py # 钉钉集成
├── config.yaml             # 配置文件
├── .env.example            # 环境变量模板
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 镜像构建
└── k8s-deployment.yaml     # Kubernetes 部署配置
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# Slack 配置（必填）
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_CHANNEL_ID=your-channel-id
SLACK_APP_TOKEN=xapp-your-app-token

# Microsoft Teams 配置（可选）
TEAMS_WEBHOOK_URL=https://your-teams-webhook-url

# 钉钉配置（可选）
DINGTALK_WEBHOOK_URL=https://your-dingtalk-webhook-url
DINGTALK_SECRET=your-dingtalk-secret

# Kubernetes 配置
KUBECONFIG_PATH=~/.kube/config
```

### 3. 配置 Slack Bot

1. 创建 Slack App: https://api.slack.com/apps
2. 启用 Socket Mode
3. 添加 Bot Token Scopes: `channels:history`, `channels:read`, `chat:write`, `commands`
4. 启用 Interactivity & Shortcuts
5. 安装 App 到 Workspace

### 4. 运行

```bash
python main.py
```

## 配置说明 (config.yaml)

```yaml
event:
  namespaces:
    - default              # 要监控的命名空间列表
  watch_interval: 5        # 监听间隔（秒）
  dedup_ttl: 300           # 事件聚合窗口时间（秒，默认5分钟）

actions:
  restart:
    enabled: true
    max_retries: 3
  logs:
    enabled: true
    tail_lines: 100        # 日志获取行数

slack:
  bot_name: K8s Event Bot  # Bot 显示名称
  bot_icon: ':kubernetes:' # Bot 图标
```

## 自然语言命令示例

机器人支持以下自然语言命令（中英文混合）：

```
# 重启 Pod
重启 my-pod
重启命名空间 default 的 my-pod
restart pod my-pod

# 查看日志
查看 my-pod 的日志
logs my-pod

# 检查状态
检查 my-pod 的状态
status my-pod

# 列出 Pod
列出所有 Pod
list pods in default

# 获取帮助
help
帮助
```

## 故障诊断知识库

内置 10+ 常见 Kubernetes 故障诊断：

| 故障类型 | 严重程度 |
|---------|---------|
| OOMKilled (内存溢出) | 🔴 High |
| CrashLoopBackOff (启动循环崩溃) | 🔴 High |
| ImagePullBackOff (镜像拉取失败) | 🟠 Medium |
| Pending (调度失败) | 🟠 Medium |
| ReadinessProbeFailed (就绪检查失败) | 🟠 Medium |
| LivenessProbeFailed (存活检查失败) | 🔴 High |
| Evicted (Pod被驱逐) | 🔴 High |
| ConnectionRefused (连接被拒绝) | 🟠 Medium |
| Timeout (请求超时) | 🟠 Medium |
| ConfigError (配置错误) | 🟠 Medium |

每个故障诊断包含：
- 问题描述
- 可能原因（3-4个）
- 解决方案（3-4个）
- 排查命令

## 主动巡检和日报

机器人每天早上 9:00 自动推送日报，包含：

- 总事件数量
- 严重事件和警告事件统计
- Pod 重启次数
- 各命名空间 Pod 运行状态
- 发现的问题列表

## 多渠道通知

### Slack
- 交互式按钮（重启、日志、状态）
- 30秒超时自动禁用
- 签名验证防伪造

### Microsoft Teams
- Adaptive Cards 富文本消息
- 事件、诊断报告、日报

### 钉钉
- Markdown 格式消息
- 支持加签验证
- 事件、诊断报告、日报

## 核心功能说明

### 1. Slack 签名验证

- 使用 Slack Bolt 内置的 `request_verification_enabled=True`
- 自动验证所有传入请求的签名，防止伪造请求
- 需要正确配置 `SLACK_SIGNING_SECRET`

### 2. 5分钟事件聚合去重

- 相同事件（相同命名空间、Pod名、原因）在5分钟窗口内聚合
- 事件首次到达时仅记录不发送
- 窗口结束后聚合发送，显示累计次数
- 每10秒检查一次窗口状态

### 3. restartPolicy 检查

- 重启 Pod 前自动检查 Pod 的 `restartPolicy`
- 仅允许 `restartPolicy: OnFailure` 的 Pod 被重启
- 其他策略（Always/Never）会被拒绝并返回原因

### 4. 30秒按钮超时

- 每条消息的按钮仅在发送后30秒内有效
- 超时后自动替换按钮为提示信息
- 点击已超时的按钮不会执行任何操作
- 点击任意按钮后立即从超时队列中移除

## Docker 部署

```bash
# 构建镜像
docker build -t k8s-event-bot .

# 运行容器
docker run -v ~/.kube/config:/root/.kube/config \
           --env-file .env \
           k8s-event-bot
```

## Kubernetes 部署

```bash
# 创建 Secret
kubectl create secret generic k8s-event-bot-env \
  --from-literal=SLACK_BOT_TOKEN=xoxb-xxx \
  --from-literal=SLACK_SIGNING_SECRET=xxx \
  --from-literal=SLACK_CHANNEL_ID=xxx \
  --from-literal=SLACK_APP_TOKEN=xapp-xxx \
  --from-literal=TEAMS_WEBHOOK_URL=https://xxx \
  --from-literal=DINGTALK_WEBHOOK_URL=https://xxx \
  --from-literal=DINGTALK_SECRET=xxx

# 部署
kubectl apply -f k8s-deployment.yaml
```

## Slack 交互按钮

每个事件消息都会附带三个按钮：

- :repeat: **Restart Pod** - 重启 Pod（仅 OnFailure 策略允许）
- :page_facing_up: **Get Logs** - 获取 Pod 最新日志
- :information_source: **Status** - 查看 Pod 状态信息

:alarm_clock: *按钮将在发送后30秒超时*

## 权限说明

Kubernetes RBAC 权限：

- 事件和 Pod 读取权限
- 删除 Pod 权限
- Deployment 补丁权限
- Pod 日志读取权限
