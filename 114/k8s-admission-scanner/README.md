# Trivy Admission Scanner - K8s Operator

基于Kubernetes Operator的容器镜像漏洞准入扫描器，使用Trivy进行安全扫描。

## 功能特性

1. **Admission Webhook拦截** - 拦截Pod创建/更新事件，扫描镜像漏洞
2. **准入控制** - 扫描通过才允许Pod启动，失败则拒绝并记录事件
3. **灵活配置** - 支持命名空间白名单、镜像白名单、漏洞阈值配置
4. **Prometheus指标** - 监控扫描次数、通过率、漏洞统计等
5. **CRD策略管理** - 通过ImageScanPolicy CRD动态配置扫描规则
6. **试运行模式** - DryRun模式只记录不拒绝，方便测试

## 架构

```
┌─────────────────────┐     ┌─────────────────────────┐
│  Kubernetes API     │────▶│  Admission Webhook      │
│  Server             │     │  (Validating)           │
└─────────────────────┘     └────────────┬────────────┘
                                         │
                                         ▼
                                ┌─────────────────┐
                                │  Trivy Scanner  │
                                └────────┬────────┘
                                         │
                                         ▼
                                ┌─────────────────┐
                                │  Policy Check   │
                                └────────┬────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    │                                         │
                    ▼                                         ▼
           ┌────────────────┐                       ┌─────────────────┐
           │  Allow (200)   │                       │  Deny (403)     │
           │  + K8s Event   │                       │  + K8s Event    │
           └────────────────┘                       └─────────────────┘
```

## 快速开始

### 1. 构建镜像

```bash
# 构建Docker镜像
docker build -t trivy-admission-scanner:latest .

# 推送到镜像仓库（修改为你的仓库）
docker tag trivy-admission-scanner:latest your-registry/trivy-admission-scanner:latest
docker push your-registry/trivy-admission-scanner:latest
```

### 2. 生成TLS证书

```bash
# 运行证书生成脚本
chmod +x scripts/gen_certs.sh
./scripts/gen_certs.sh

# 加载CA Bundle环境变量
source certs/ca_bundle.env
```

### 3. 部署Operator

```bash
# 使用kustomize部署
kubectl apply -k deploy/

# 或者逐个部署
kubectl apply -f deploy/namespace.yaml
kubectl apply -f deploy/service_account.yaml
kubectl apply -f deploy/role.yaml
kubectl apply -f deploy/role_binding.yaml
kubectl apply -f deploy/service.yaml

# 更新webhook配置（注入CA_BUNDLE）
envsubst < deploy/validating_webhook.yaml | kubectl apply -f -

# 最后部署应用
kubectl apply -f deploy/deployment.yaml
```

### 4. 验证部署

```bash
# 检查Pod状态
kubectl get pods -n trivy-admission-system

# 检查Service
kubectl get svc -n trivy-admission-system

# 检查CRD
kubectl get crd imagescanpolicies.security.trivy.io

# 查看默认策略
kubectl get imagescanpolicies
```

## 配置说明

### ImageScanPolicy CRD

创建自定义扫描策略：

```yaml
apiVersion: security.trivy.io/v1alpha1
kind: ImageScanPolicy
metadata:
  name: strict-policy
spec:
  enabled: true
  namespaceSelector:
    include: ["production", "staging"]
    exclude: ["kube-system"]
  severityThreshold:
    critical: 0      # 不允许严重漏洞
    high: 0          # 不允许高危漏洞
    medium: 5        # 最多5个中危漏洞
    low: 20          # 最多20个低危漏洞
    cvssScoreThreshold: 7.0  # CVSS分数超过7则拒绝
  scanTimeout: 120
  imageFilter:
    include: ["*"]
    exclude:
      - "registry.k8s.io/*"
      - "gcr.io/*"
  remediation:
    autoRemediate: false
    commentTemplate: "镜像 {image} 存在安全问题，请使用无漏洞镜像"
  dryRun: false
```

### 配置字段说明

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `enabled` | 是否启用扫描 | `true` |
| `namespaceSelector.include` | 包含的命名空间列表（支持通配符） | `["*"]` |
| `namespaceSelector.exclude` | 排除的命名空间列表 | `["kube-system", ...]` |
| `severityThreshold.critical` | 严重漏洞最大允许数量 | `0` |
| `severityThreshold.high` | 高危漏洞最大允许数量 | `2` |
| `severityThreshold.medium` | 中危漏洞最大允许数量 | `10` |
| `severityThreshold.low` | 低危漏洞最大允许数量 | `50` |
| `severityThreshold.cvssScoreThreshold` | CVSS分数阈值 | `7.0` |
| `scanTimeout` | 单镜像扫描超时时间（秒） | `120` |
| `imageFilter.include` | 包含的镜像仓库 | `["*"]` |
| `imageFilter.exclude` | 排除的镜像仓库 | `["registry.k8s.io/*"]` |
| `dryRun` | 试运行模式（只记录不拒绝） | `false` |

## Prometheus指标

| 指标名称 | 类型 | 说明 |
|----------|------|------|
| `trivy_admission_scan_requests_total` | Counter | 扫描请求总数 |
| `trivy_admission_scan_duration_seconds` | Histogram | 扫描持续时间 |
| `trivy_admission_active_scans` | Gauge | 当前活动扫描数 |
| `trivy_admission_scan_allowed_total` | Counter | 扫描通过总数 |
| `trivy_admission_scan_denied_total` | Counter | 扫描拒绝总数 |
| `trivy_admission_vulnerabilities_found` | Gauge | 各严重程度漏洞数量 |
| `trivy_admission_vulnerabilities_total` | Gauge | 总漏洞数量 |
| `trivy_admission_scan_skipped_total` | Counter | 跳过扫描总数 |

### 示例监控查询

```promql
# 扫描通过率
rate(trivy_admission_scan_allowed_total[5m]) / (rate(trivy_admission_scan_allowed_total[5m]) + rate(trivy_admission_scan_denied_total[5m]))

# 平均扫描时间
rate(trivy_admission_scan_duration_seconds_sum[5m]) / rate(trivy_admission_scan_duration_seconds_count[5m])

# 严重漏洞总数
sum(trivy_admission_vulnerabilities_found{severity="critical"}) by (namespace)
```

## 使用示例

### 1. 测试扫描拒绝

创建一个有漏洞的Pod：

```bash
# 这个镜像已知有漏洞
kubectl run vulnerable-pod --image=nginx:1.19.0 -n default

# 查看事件
kubectl get events -n default | grep ImageScan
```

### 2. 标记命名空间跳过扫描

```bash
# 给命名空间添加标签
kubectl label namespace test trivy-scanner-skip=true

# 验证：该命名空间下的Pod将不会被扫描
kubectl run safe-pod --image=nginx:latest -n test
```

### 3. 启用DryRun模式

```bash
# 编辑默认策略
kubectl edit imagescanpolicy default-image-scan-policy

# 修改dryRun为true
# spec:
#   dryRun: true
```

### 4. 查看扫描事件

```bash
# 查看所有扫描事件
kubectl get events -A | grep ImageScan

# 查看特定命名空间的事件
kubectl get events -n default --field-selector reason=ImageScanDenied
```

## 故障排查

### 1. 检查Operator日志

```bash
# 查看Operator日志
kubectl logs -f deployment/trivy-admission-scanner -n trivy-admission-system
```

### 2. 检查Webhook配置

```bash
# 查看ValidatingWebhookConfiguration
kubectl get validatingwebhookconfiguration trivy-admission-scanner -o yaml

# 验证CA Bundle
kubectl get validatingwebhookconfiguration trivy-admission-scanner -o jsonpath='{.webhooks[0].clientConfig.caBundle}' | base64 -d
```

### 3. 测试Trivy扫描

```bash
# 在Operator容器中测试扫描
kubectl exec -it deploy/trivy-admission-scanner -n trivy-admission-system -- trivy image nginx:latest
```

### 4. 常见问题

**问题：Webhook调用超时**
- 检查Service是否正常
- 检查Pod网络连通性
- 增加timeoutSeconds配置

**问题：证书错误**
- 重新运行证书生成脚本
- 验证Secret是否正确创建
- 检查CA Bundle是否正确注入

**问题：扫描速度慢**
- 增加扫描超时时间
- 配置Trivy缓存PVC
- 增加Operator副本数

## 高级配置

### 使用PVC缓存Trivy数据库

```yaml
# 在deployment.yaml中修改volume配置
volumes:
- name: trivy-cache
  persistentVolumeClaim:
    claimName: trivy-cache-pvc
```

### HA部署

```yaml
# 增加副本数
spec:
  replicas: 3
```

### 自定义环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `WEBHOOK_PORT` | Webhook服务端口 | `9443` |
| `METRICS_PORT` | Metrics服务端口 | `8080` |
| `FAIL_OPEN` | 失败时是否放行 | `false` |
| `TRIVY_CACHE_DIR` | Trivy缓存目录 | `/var/trivy-cache` |

## 清理

```bash
# 删除所有资源
kubectl delete -k deploy/
kubectl delete -f deploy/validating_webhook.yaml
kubectl delete secret trivy-admission-tls -n trivy-admission-system

# 删除CRD
kubectl delete crd imagescanpolicies.security.trivy.io
```

## 许可证

MIT License
