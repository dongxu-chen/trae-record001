# Gray Release Platform (灰度发布控制平台)

## 项目概述

灰度发布控制平台是一个基于 Spring Cloud Gateway + Prometheus + K8s API 构建的企业级灰度发布解决方案。支持多种发布策略，提供实时指标监控和自动回滚能力。

## 核心功能

### 发布策略

| 策略 | 说明 |
|------|------|
| **金丝雀发布 (Canary)** | 按比例逐步切换流量，默认: 5% → 10% → 25% → 50% → 100% |
| **A/B 测试** | 基于请求匹配规则（Header/Cookie）分流 |
| **蓝绿部署** | 全量切换到新版本，支持快速回滚 |

### 核心能力

- **K8s加权Service流量切分** - 基于K8s EndpointSlice的精确流量比例控制
- **动态基线异常检测** - 基于历史数据波动计算动态阈值，3倍标准差判断异常
- **镜像依赖检查** - 回滚前验证镜像存在性及依赖完整性
- **实验管理** - 多组实验并行运行，互不干扰
- **发布日历** - 发布窗口规划与锁定期管理
- **发布质量门禁** - 灰度期指标达标后自动扩大流量
- **实时指标监控** - 错误率、延迟(P95)、QPS、CPU、内存
- **自动回滚** - 指标异常持续超过阈值时自动触发回滚
- **版本管理** - 版本生命周期管理 (STABLE/CANARY/DEPRECATED/ARCHIVED)
- **K8s 集成** - Deployment 创建、扩缩容、版本切换

## 模块结构

```
gray-release-platform/
├── common/              # 公共模型、DTO、工具类
├── release-service/     # 发布控制服务 (8081)
│   ├── K8sWeightedRoutingService   # K8s加权Service流量管理
│   ├── ImageRegistryChecker         # 镜像依赖检查
│   ├── ExperimentManager            # 实验管理
│   ├── ReleaseCalendarManager       # 发布日历管理
│   ├── QualityGateService           # 质量门禁服务
│   └── ...
├── gateway-service/     # 网关服务 (8080)
├── monitor-service/     # 监控服务 (8082)
│   ├── DynamicBaselineAnalyzer    # 动态基线分析器
│   └── ...
├── k8s/               # K8s 部署配置
└── prometheus/         # Prometheus 配置
```

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Gateway Service | 8080 | Spring Cloud Gateway，流量路由与拆分 |
| Release Service | 8081 | 发布策略引擎、实验管理、日历、门禁、加权路由、镜像检查 |
| Monitor Service | 8082 | Prometheus 指标采集、动态基线异常检测 |

## 快速开始

### 前置要求

- JDK 17+
- Maven 3.8+
- Docker & Docker Compose (可选)
- Kubernetes (可选)

### 本地开发

```bash
# 构建所有模块
mvn clean package -DskipTests

# 启动本地服务
java -jar release-service/target/release-service-1.0.0.jar
java -jar gateway-service/target/gateway-service-1.0.0.jar
java -jar monitor-service/target/monitor-service-1.0.0.jar
```

### Docker Compose 启动

```bash
# Windows
start.bat

# Linux/Mac
./start.sh
```

### K8s 部署

```bash
./deploy-k8s.sh
```

## API 文档

### Release Service API

#### 创建发布

```http
POST /api/v1/releases
Content-Type: application/json

{
  "serviceName": "order-service",
  "strategy": "CANARY",
  "stableVersion": "v1.0.0",
  "canaryVersion": "v2.0.0",
  "canaryImage": "registry.example.com/order-service:v2.0.0",
  "stepTrafficPercents": [5, 10, 25, 50, 100],
  "threshold": {
    "metricType": "ERROR_RATE",
    "warningThreshold": 0.02,
    "criticalThreshold": 0.05,
    "durationSeconds": 60,
    "comparison": "gt"
  },
  "createdBy": "admin"
}
```

#### 推进发布

```http
POST /api/v1/releases/{releaseId}/progress?step=1
```

#### 完成发布

```http
POST /api/v1/releases/{releaseId}/complete
```

#### 回滚发布

```http
POST /api/v1/releases/{releaseId}/rollback?reason=manual
```

**回滚前检查响应示例:**
```json
{
  "image": "registry.example.com/order-service:v1.0.0",
  "imageExists": true,
  "dependenciesChecked": true,
  "canRollback": true,
  "allChecksPassed": true
}
```

#### 回滚预检查

```http
GET /api/v1/releases/{releaseId}/rollback/check
```

#### 镜像检查

```http
GET /api/v1/releases/images/check?image=registry.example.com/order-service:v1.0.0
```

**响应示例:**
```json
{
  "exists": true,
  "image": "registry.example.com/order-service:v1.0.0",
  "cached": false,
  "message": "Image exists in registry",
  "dependencies": [
    {
      "image": "base-image:jre-17-alpine",
      "type": "base-image",
      "optional": false
    }
  ]
}
```

#### 获取路由状态

```http
GET /api/v1/releases/routes/{serviceName}
```

**响应示例:**
```json
{
  "serviceName": "order-service",
  "stableVersion": "v1.0.0",
  "canaryVersion": "v2.0.0",
  "stableWeight": 90,
  "canaryWeight": 10,
  "mode": "weighted-endpointslice"
}
```

#### 版本管理

```http
POST /api/v1/releases/versions
GET  /api/v1/releases/versions/{serviceName}
GET  /api/v1/releases/versions/{serviceName}/stable
```

### 实验管理 API

#### 创建实验

```http
POST /api/v1/releases/experiments
Content-Type: application/json

{
  "name": "新结账流程实验",
  "description": "测试新的结账页面性能",
  "serviceName": "checkout-service",
  "experimentGroup": "payment-flow",
  "strategy": "CANARY",
  "stableVersion": "v1.0.0",
  "experimentVersion": "v2.0.0",
  "experimentImage": "registry.example.com/checkout:v2.0.0",
  "maxTrafficPercent": 30,
  "stepTrafficPercents": [5, 10, 20, 30],
  "trafficMatchRules": {
    "X-User-Group": "beta"
  },
  "successMetrics": [
    {
      "metricType": "ERROR_RATE",
      "criticalThreshold": 0.02,
      "durationSeconds": 120
    },
    {
      "metricType": "LATENCY",
      "criticalThreshold": 200.0,
      "durationSeconds": 120
    }
  ],
  "guardrailMetrics": [
    {
      "metricType": "ERROR_RATE",
      "criticalThreshold": 0.05,
      "durationSeconds": 60
    }
  ],
  "owner": "pm@example.com"
}
```

#### 启动实验

```http
POST /api/v1/releases/experiments/{experimentId}/start
```

#### 推进实验

```http
POST /api/v1/releases/experiments/{experimentId}/progress?step=1
```

#### 完成实验

```http
POST /api/v1/releases/experiments/{experimentId}/complete
```

#### 毕业实验（版本全量发布）

```http
POST /api/v1/releases/experiments/{experimentId}/graduate
```

#### 回滚实验

```http
POST /api/v1/releases/experiments/{experimentId}/rollback?reason=指标不达标
```

#### 获取实验列表

```http
GET /api/v1/releases/experiments
GET /api/v1/releases/experiments/service/{serviceName}
GET /api/v1/releases/experiments/running/{serviceName}
```

#### 获取实验质量门禁状态

```http
GET /api/v1/releases/experiments/{experimentId}/gate-status
```

**响应示例:**
```json
{
  "experimentId": "exp-123456",
  "checkCount": 15,
  "passCount": 12,
  "currentStep": 2,
  "currentTrafficPercent": 20,
  "observationMinutes": 15,
  "minObservationMinutes": 5,
  "autoProgressEnabled": true
}
```

### 发布日历 API

#### 创建发布日历

```http
POST /api/v1/releases/calendar
Content-Type: application/json

{
  "serviceName": "order-service",
  "name": "工作日发布窗口",
  "description": "每周一到周五 10:00-16:00 允许发布",
  "status": "OPEN",
  "startDate": "2026-01-01",
  "endDate": "2026-12-31",
  "startTime": "10:00:00",
  "endTime": "16:00:00",
  "allowedDays": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"],
  "excludedDates": ["2026-01-01", "2026-02-12"]
}
```

#### 获取当前发布窗口状态

```http
GET /api/v1/releases/calendar/{serviceName}/status
```

#### 检查是否可以发布

```http
GET /api/v1/releases/calendar/{serviceName}/can-release?time=1735689600
```

#### 获取即将到来的发布窗口

```http
GET /api/v1/releases/calendar/{serviceName}/upcoming?days=7
```

#### 创建锁定期

```http
POST /api/v1/releases/calendar/{serviceName}/locks
Content-Type: application/json

{
  "name": "春节冻结期",
  "reason": "春节假期，禁止发布",
  "startTime": "2026-02-09T18:00:00",
  "endTime": "2026-02-17T09:00:00",
  "createdBy": "ops@example.com"
}
```

#### 获取活动锁定期

```http
GET /api/v1/releases/calendar/{serviceName}/locks/active
```

#### 获取即将到来的锁定期

```http
GET /api/v1/releases/calendar/{serviceName}/locks/upcoming?days=30
```

#### 删除锁定期

```http
DELETE /api/v1/releases/calendar/{serviceName}/locks/{lockId}
```

### Gateway Service API

#### 获取路由配置

```http
GET /api/v1/gateway/routes
GET /api/v1/gateway/routes/{serviceName}
```

#### 更新路由

```http
POST /api/v1/gateway/routes
Content-Type: application/json

{
  "serviceName": "order-service",
  "stableVersion": "v1.0.0",
  "canaryVersion": "v2.0.0",
  "canaryWeight": 10,
  "stableHost": "order-service-stable.svc.cluster.local",
  "canaryHost": "order-service-canary.svc.cluster.local",
  "matchRules": {
    "X-User-Type": "vip"
  }
}
```

### Monitor Service API

#### 获取指标

```http
GET /api/v1/monitor/metrics/{serviceName}/{version}?metricType=ERROR_RATE
```

#### 注册监控目标

```http
POST /api/v1/monitor/targets?targetId=xxx&serviceName=xxx&version=xxx
```

#### 分析指标

```http
POST /api/v1/monitor/analyze?serviceName=xxx&version=xxx
```

#### 获取动态基线

```http
GET /api/v1/monitor/baseline/{serviceName}/{version}
```

**响应示例:**
```json
{
  "ERROR_RATE": {
    "available": true,
    "mean": 0.012,
    "standardDeviation": 0.003,
    "dynamicThreshold": 0.021,
    "dataPoints": 150,
    "min": 0.005,
    "max": 0.018,
    "percentile95": 0.017,
    "percentile99": 0.018
  },
  "LATENCY": {
    "available": true,
    "mean": 85.5,
    "standardDeviation": 12.3,
    "dynamicThreshold": 122.4,
    "dataPoints": 150,
    "min": 60.2,
    "max": 110.8,
    "percentile95": 105.3,
    "percentile99": 108.5
  }
}
```

#### 获取单个指标基线

```http
GET /api/v1/monitor/baseline/{serviceName}/{version}/{metricType}
```

#### 清除基线历史

```http
DELETE /api/v1/monitor/baseline/{serviceName}
```

## 配置说明

### 指标阈值配置

| 指标类型 | 单位 | 默认临界值 | 动态基线 | 说明 |
|---------|------|-----------|---------|------|
| ERROR_RATE | % | 5% | ✓ | 基于历史错误率波动计算 |
| LATENCY | ms | 1000ms | ✓ | 基于历史延迟波动计算 |
| QPS | req/s | 10000 | ✓ | 基于历史QPS波动计算 |
| CPU_USAGE | % | 80% | ✓ | 基于历史CPU使用率波动 |
| MEMORY_USAGE | % | 85% | ✓ | 基于历史内存使用率波动 |

### 动态基线配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| anomaly.detection.use-dynamic-baseline | true | 启用动态基线检测 |
| anomaly.detection.std-dev-multiplier | 3.0 | 标准差倍数阈值 |

**动态基线计算公式:**
```
动态阈值 = 历史平均值 + (标准差倍数 × 历史标准差)
```

默认使用3倍标准差，即当指标超过历史正常波动范围3倍时判定为异常。

### K8s加权Service配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| routing.use-k8s-weighted | true | 启用K8s加权路由 |
| kubernetes.use-endpointslice | true | 使用EndpointSlice实现加权 |

### 镜像检查配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| rollback.check-image-exists | true | 回滚前检查镜像存在 |
| rollback.force-on-automatic | true | 自动回滚时强制执行 |
| image.registry.url | http://registry:5000 | 镜像仓库地址 |
| image.registry.type | docker | 仓库类型(docker/harbor) |

### 质量门禁配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| quality-gate.min-observation-minutes | 5 | 最小观察时间(分钟) |
| quality-gate.auto-progress-enabled | true | 启用自动扩流 |

**质量门禁工作流程:**
1. 进入新流量档位后，启动观察期(默认5分钟)
2. 每30秒检查一次成功指标(错误率、延迟等)
3. 连续3次检查通过则自动进入下一个流量档位
4. 任何防护指标不达标则立即触发回滚

### 发布日历配置

**发布窗口检查优先级:**
1. 锁定期检查 → 如在锁定期内，禁止发布
2. 日期范围检查 → 是否在日历有效期内
3. 排除日期检查 → 是否为排除日期
4. 星期检查 → 是否为允许的星期
5. 时间段检查 → 是否在允许的时间段内

### 流量拆分规则

- **K8s加权Service**: 使用EndpointSlice注解精确控制流量比例
- **基于匹配规则**: Header/Cookie 匹配优先于权重
- **蓝绿模式**: 全量切换，不进行拆分
- **兜底机制**: K8s加权路由失败时自动降级为Kafka通知模式
- **多实验隔离**: 同服务不同分组的实验使用不同匹配规则，互不干扰

## 技术栈

- **Java 17** - 编程语言
- **Spring Boot 3.2** - 应用框架
- **Spring Cloud Gateway** - API 网关
- **Spring Kafka** - 消息队列
- **Prometheus** - 指标采集
- **K8s Fabric8 Client** - Kubernetes 集成
- **K8s EndpointSlice** - 加权流量路由
- **H2 Database** - 数据存储
- **Lombok** - 代码简化

## 架构设计

### 发布流程

```
创建发布 → 发布日历检查 → 部署金丝雀 → K8s加权路由 → 指标监控 → 动态基线检测 → 质量门禁 → 自动扩流 → 完成/回滚
```

### 自动回滚机制

```
指标采集 (15s) → 动态基线计算 → 异常检测 → 持续时间判断 → 镜像检查 → 触发回滚
```

### K8s加权路由流程

```
流量更新请求 → K8sWeightedRoutingService → 创建/更新EndpointSlice → K8s Service负载均衡
```

### 镜像检查流程

```
回滚请求 → ImageRegistryChecker → 检查镜像存在 → 检查依赖 → 检查版本健康 → 允许/阻止回滚
```

### 实验管理流程

```
创建实验 → 启动 → 质量门禁观察 → 指标达标 → 自动扩流 → 完成/毕业/回滚
```

### 质量门禁流程

```
流量进入新档位 → 观察期(5min) → 30秒周期检查 → 连续3次通过 → 自动进入下一档位
         ↓
      指标异常 → 立即回滚
```

### 发布日历流程

```
发布请求 → ReleaseCalendarManager → 锁定期检查 → 发布窗口检查 → 允许/拒绝发布
```

## 许可证

MIT License