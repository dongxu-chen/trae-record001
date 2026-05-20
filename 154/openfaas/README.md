# OpenFaaS Kubernetes Event Bot

基于 OpenFaaS 无服务器架构的 Kubernetes 事件响应机器人。

## 架构概览

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Kubernetes      │     │  OpenFaaS        │     │  Notification    │
│  Event Watcher   │────▶│  Event Trigger   │────▶│  Channels        │
│  (K8s API)       │     │  (Always On)     │     │  (Slack/Teams    │
└──────────────────┘     └──────────────────┘     │   /DingTalk)     │
        ▲                                              └──────────────────┘
        │
        ▼
┌──────────────────┐     ┌──────────────────┐
│  k8s-event-      │     │  k8s-event-      │
│  handler-python  │     │  handler-node    │
│  (Scale to 0)    │     │  (Scale to 0)    │
└──────────────────┘     └──────────────────┘
┌──────────────────┐
│  k8s-event-      │
│  handler-go      │
│  (Scale to 0)    │
└──────────────────┘
```

## 核心特性

✅ **事件驱动架构** - 按事件触发函数调用  
✅ **弹性伸缩** - 空闲时自动缩容到0，节省资源  
✅ **多语言支持** - Python、Node.js、Go 三个版本的处理函数  
✅ **事件去重** - 5分钟窗口内重复事件自动去重  
✅ **多渠道通知** - 同时支持 Slack、Microsoft Teams、钉钉  
✅ **自动重连** - K8s Watch 连接断开自动重连  

## 项目结构

```
openfaas/
├── stack.yml                          # OpenFaaS 函数定义
├── .env.example                       # 环境变量模板
├── k8s-rbac.yaml                      # RBAC 权限配置
│
├── functions/
│   ├── python/
│   │   ├── handler.py                # Python 版本处理器
│   │   ├── requirements.txt           # Python 依赖
│   │   └── requirements.txt           # Python 依赖
│   ├── nodejs/
│   │   ├── handler.js                # Node.js 版本处理器
│   │   └── package.json
│   └── go/
│       ├── handler.go                # Go 版本处理器
│       └── go.mod
│
└── trigger/
    ├── handler.go                      # K8s 事件触发器（常驻）
    └── go.mod
```

## 快速开始

### 1. 安装 OpenFaaS

```bash
# 安装 faas-cli
curl -sL https://cli.openfaas.com | sudo sh

# 安装 OpenFaaS（使用 arkade）
arkade install openfaas

# 或者使用 Helm
helm repo add openfaas https://openfaas.github.io/faas-netes/
helm upgrade openfaas --install openfaas/openfaas \
  --namespace openfaas \
  --set functionNamespace=openfaas-fn \
  --set basic_auth=true
```

### 2. 配置 RBAC 权限

```bash
kubectl apply -f k8s-rbac.yaml
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 Webhook URL
```

### 4. 登录 OpenFaaS Gateway

```bash
# 端口转发
kubectl port-forward -n openfaas svc/gateway 8080:8080 &

# 获取密码
PASSWORD=$(kubectl get secret -n openfaas basic-auth -o jsonpath="{.data.basic-auth-password}" | base64 --decode; echo)

# 登录
echo -n $PASSWORD | faas-cli login --username admin --password-stdin
```

### 5. 构建并部署函数

```bash
# 设置你的镜像仓库前缀（如 Docker Hub）
export OPENFAAS_PREFIX=your-docker-username

# 构建所有函数
faas-cli build -f stack.yml

# 推送镜像
faas-cli push -f stack.yml

# 部署
faas-cli deploy -f stack.yml
```

### 6. 验证部署

```bash
# 查看函数列表
faas-cli list

# 调用触发器（启动 Watch）
curl http://127.0.0.1:8080/function/k8s-event-trigger

# 查看函数日志
kubectl logs -n openfaas-fn -l faas_function=k8s-event-trigger -f
```

## 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL | - |
| `TEAMS_WEBHOOK_URL` | Microsoft Teams Webhook URL | - |
| `DINGTALK_WEBHOOK_URL` | 钉钉机器人 Webhook URL | - |
| `OPENFAAS_GATEWAY` | OpenFaaS Gateway 地址 | http://gateway.openfaas:8080 |
| `FUNCTION_NAME` | 要调用的处理函数名 | k8s-event-handler-python |
| `EVENT_NAMESPACES` | 监控的命名空间（逗号分隔） | default |
| `EVENT_DEDUP_WINDOW` | 事件去重窗口（秒） | 300 |

## 弹性伸缩配置

在 `stack.yml` 中，每个函数都配置了自动伸缩：

```yaml
annotations:
  com.openfaas.scale.min: 0      # 最小副本数，空闲时缩容到0
  com.openfaas.scale.max: 10     # 最大副本数，高负载时扩容
  com.openfaas.scale.factor: 50  # 扩容因子，每增加50%负载启动一个副本
  com.openfaas.scale.zero: true  # 启用缩容到0
```

**伸缩逻辑：**
- 无事件时：副本数 = 0，不消耗资源
- 少量事件：副本数 = 1
- 高负载（事件密集）：自动横向扩容到最多10个副本
- 事件平息后：自动缩容回0

## 选择处理函数

项目提供三种语言版本的处理函数，可根据需要选择：

| 语言 | 函数名 | 特点 | 建议场景 |
|------|--------|------|---------|
| Go | k8s-event-handler-go | 高性能，低内存，冷启动快 | 高负载生产环境 |
| Python | k8s-event-handler-python | 开发便捷，生态丰富 | 快速迭代开发 |
| Node.js | k8s-event-handler-node | 非阻塞IO | 高并发通知 |

**切换方式：** 修改 `FUNCTION_NAME` 环境变量即可。

## 测试函数

```bash
# 手动发送测试事件
curl http://127.0.0.1:8080/function/k8s-event-handler-python \
  -H "Content-Type: application/json" \
  -d '{
    "type": "Warning",
    "object": {
      "metadata": {
        "name": "test-pod-123",
        "namespace": "default"
      },
      "reason": "Failed",
      "message": "Container startup failed",
      "type": "Warning"
    }
  }'

# 查看触发器状态
curl http://127.0.0.1:8080/function/k8s-event-trigger
```

## 监控与调试

### 查看函数指标

```bash
# Prometheus 指标
kubectl port-forward -n openfaas svc/prometheus 9090:9090

# Grafana 面板
kubectl port-forward -n openfaas svc/grafana 3000:3000
```

### 查看日志

```bash
# 触发器日志
kubectl logs -n openfaas-fn -l faas_function=k8s-event-trigger -f

# 处理函数日志
kubectl logs -n openfaas-fn -l faas_function=k8s-event-handler-python -f
```

### 扩容测试

```bash
# 发送大量事件测试自动扩容
for i in {1..100}; do
  curl -X POST http://127.0.0.1:8080/function/k8s-event-handler-python \
    -H "Content-Type: application/json" \
    -d '{"type": "Normal", "object": {"reason": "Test"}}' &
done

# 查看副本数变化
kubectl get pods -n openfaas-fn -w
```

## 配置通知渠道

### Slack

1. 创建 Slack App：https://api.slack.com/apps
2. 启用 Incoming Webhooks
3. 添加新 Webhook，获取 URL
4. 填入 `SLACK_WEBHOOK_URL`

### Microsoft Teams

1. 打开 Teams 频道
2. 右键 → Connectors → Incoming Webhook
3. 创建并获取 URL
4. 填入 `TEAMS_WEBHOOK_URL`

### 钉钉

1. 群设置 → 智能群助手 → 添加机器人 → 自定义
2. 安全设置（可选择关键词或加签）
3. 获取 Webhook URL
4. 填入 `DINGTALK_WEBHOOK_URL`

## 性能优化建议

### 1. 选择 Go 版本处理函数
- 冷启动速度 < 100ms
- 内存占用 < 20MB
- 处理能力：1000+ 事件/秒

### 2. 调整去重窗口
```yaml
environment:
  EVENT_DEDUP_WINDOW: 60  # 60秒，适合高频率事件
```

### 3. 配置资源限制
```yaml
limits:
  memory: 128Mi
  cpu: 100m
requests:
  memory: 64Mi
  cpu: 50m
```

## 常见问题

### Q: 函数为什么没有被触发？
A: 检查：
1. 触发器 Pod 是否正常运行
2. RBAC 权限是否正确配置
3. EVENT_NAMESPACES 是否包含目标命名空间

### Q: 如何实现更复杂的事件过滤？
A: 修改 `trigger/handler.go` 中的 `handleEvent` 方法，添加自定义过滤逻辑。

### Q: 如何添加更多通知渠道？
A: 在处理函数中（如 Python 的 `handler.py`）添加新的 `sendXXXNotification` 方法。

## 清理

```bash
# 删除函数
faas-cli remove -f stack.yml

# 删除 RBAC
kubectl delete -f k8s-rbac.yaml

# 卸载 OpenFaaS（可选）
helm uninstall openfaas -n openfaas
```

## 许可证

MIT
