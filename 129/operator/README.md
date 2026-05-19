# Kubernetes Health Check Operator

基于 Kubebuilder 开发的 Kubernetes 资源巡检与自动修复 Operator。

## 功能特性

### 1. Pod/Node 健康检查
- Pod 状态监控：CrashLoopBackOff、ImagePullBackOff、Error、Pending 等
- Node 状态监控：Ready 状态、可调度性检查
- 支持命名空间和标签选择器过滤

### 2. 自动修复功能
- **崩溃 Pod 重启**：自动重启崩溃的 Pod，支持指数退避策略
- **节点驱逐**：自动标记并驱逐异常节点，支持 PDB 检查
- **可配置参数**：最大重启次数、退避时间、优雅关闭时间等

### 3. 资源配额建议
- 检查 Pod CPU/Memory 资源限制配置
- 分析 request/limit 比率是否合理
- 提供具体的优化建议

### 4. 镜像安全分析
- 检测 latest 标签使用
- 识别已知漏洞版本镜像
- 建议使用安全版本（alpine/slim/distroless）

### 5. Prometheus 告警集成
- 接收 Prometheus Alertmanager webhook
- 根据告警自动触发巡检和修复

### 6. 多渠道告警通知
- 钉钉（DingTalk）webhook
- 企业微信（WeCom）webhook
- 支持 Markdown 格式化消息

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    HealthCheck CRD                      │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐          │   │
│  │  │HealthCheck│  │HealthCheck│  │HealthCheck│          │   │
│  │  └───────────┘  └───────────┘  └───────────┘          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                               │                                 │
│                               ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                HealthCheck Controller                    │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  Reconcile Loop → Health Check → Auto Remediation        │   │
│  │                        ↓                                  │   │
│  │                  Metrics / Alerts                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                               │                                 │
│        ┌──────────────────────┼──────────────────────┐       │
│        ▼                      ▼                      ▼       │
│  ┌───────────┐          ┌───────────┐          ┌───────────┐ │
│  │ Prometheus│          │  DingTalk │          │  WeWork   │ │
│  │  Metrics  │          │ Webhook   │          │ Webhook   │ │
│  └───────────┘          └───────────┘          └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 快速开始

### 前置条件
- Kubernetes 集群 1.24+
- kubectl 配置完成
- Kustomize 5.0+
- Go 1.21+（如需本地开发）

### 安装 CRD 和 Operator

```bash
# 进入项目目录
cd operator

# 安装 CRD
make install

# 部署 Operator
make deploy IMG=your-registry/healthcheck-operator:v0.1.0
```

### 验证安装

```bash
# 检查 CRD 安装
kubectl get crd healthchecks.health.k8s.health.checker.io

# 检查 Operator Pod 运行状态
kubectl -n healthcheck-operator-system get pods

# 查看 CRD 详情
kubectl explain healthchecks.health.k8s.health.checker.io
```

### 创建 HealthCheck 实例

```bash
# 应用示例配置
kubectl apply -f config/samples/health_v1_healthcheck.yaml

# 查看 HealthCheck 状态
kubectl -n healthcheck-operator-system get healthchecks -o wide
kubectl -n healthcheck-operator-system describe healthcheck cluster-health-check
```

## 使用指南

### HealthCheck CR 配置示例

```yaml
apiVersion: health.k8s.health.checker.io/v1
kind: HealthCheck
metadata:
  name: cluster-health-check
spec:
  intervalMinutes: 5  # 巡检间隔
  
  # Pod 检查配置
  podCheck:
    enabled: true
    namespaces: []  # 空数组表示所有命名空间
    unhealthyStates:
      - CrashLoopBackOff
      - ImagePullBackOff
      - Error
      - Pending
    minRestartCount: 3  # 重启次数超过此值才被视为异常
  
  # Node 检查配置
  nodeCheck:
    enabled: true
    unschedulableAsUnhealthy: true  # 将不可调度节点视为异常
  
  # 自动修复配置
  autoRemediation:
    enabled: true
    restartCrashingPods:
      enabled: true
      maxRestarts: 5
      backoffSeconds: 60
      maxBackoffSeconds: 300
    drainNodes:
      enabled: false
      checkPDB: true
      gracePeriodSeconds: 300
      ignoreNamespaces:
        - kube-system
  
  # Prometheus 告警触发
  prometheusTrigger:
    enabled: false
    serverAddress: http://prometheus-server:9090
    triggerAlerts:
      - KubePodCrashLooping
      - KubeNodeNotReady
    webhookPort: 9094
  
  # 报告配置
  report:
    format: html
    saveToPVC: false
    dingTalkNotification:
      enabled: false
      webhookURL: "https://oapi.dingtalk.com/robot/send?access_token=xxx"
      secret: "your-secret"
      atAll: false
    weWorkNotification:
      enabled: false
      webhookURL: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
```

### 本地开发运行

```bash
# 安装依赖
go mod download

# 本地运行 Operator（使用 ~/.kube/config）
make run

# 或者使用 go 直接运行
go run cmd/main.go --log-level=debug
```

### 构建和推送镜像

```bash
# 构建 Docker 镜像
make docker-build IMG=your-registry/healthcheck-operator:v0.1.0

# 推送镜像
make docker-push IMG=your-registry/healthcheck-operator:v0.1.0
```

## 监控指标

Operator 暴露以下 Prometheus 指标（端口 8080）：

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `healthcheck_unhealthy_pods_total` | Gauge | 异常 Pod 数量 |
| `healthcheck_unhealthy_nodes_total` | Gauge | 异常 Node 数量 |
| `healthcheck_containers_restarted_total` | Gauge | 重启的容器数量 |
| `healthcheck_nodes_drained_total` | Gauge | 驱逐的节点数量 |
| `healthcheck_duration_seconds` | Histogram | 巡检执行时间 |
| `healthcheck_image_security_issues_total` | Gauge | 镜像安全问题数 |
| `healthcheck_quota_recommendations_total` | Gauge | 配额建议数 |

## 目录结构

```
operator/
├── api/
│   └── v1/                    # CRD API 定义
│       ├── groupversion_info.go
│       └── healthcheck_types.go
├── cmd/
│   └── main.go                # Operator 入口
├── config/
│   ├── crd/                   # CRD 定义
│   ├── rbac/                  # RBAC 配置
│   ├── manager/               # Operator 部署配置
│   ├── samples/               # CR 示例
│   └── default/               # 默认 Kustomize 配置
├── internal/
│   ├── controller/            # 控制器逻辑
│   │   └── healthcheck_controller.go
│   ├── metrics/               # Prometheus 指标
│   ├── remediation/           # 自动修复逻辑
│   └── notifications/         # 告警通知
├── Dockerfile
├── Makefile
├── go.mod
├── PROJECT                     # Kubebuilder 项目配置
└── README.md
```

## 常见问题

### Q: Operator 启动失败，提示权限不足？

A: 确保 RBAC 配置正确，检查 ServiceAccount 和 ClusterRoleBinding 是否已创建：

```bash
kubectl -n healthcheck-operator-system get sa
kubectl get clusterrolebinding healthcheck-operator
```

### Q: 如何开启 debug 日志？

A: 修改 Deployment 的启动参数，添加 `--log-level=debug`

### Q: 自动修复功能不会触发？

A: 检查 `spec.autoRemediation.enabled` 是否为 `true`，并确保相关子功能已启用。

## 卸载

```bash
# 删除 HealthCheck 实例
kubectl delete -f config/samples/health_v1_healthcheck.yaml

# 卸载 Operator
make undeploy

# 删除 CRD
make uninstall
```

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

Apache License 2.0
