# 服务网格故障注入测试平台

基于 Go + Istio + Jaeger + React 构建的服务网格故障注入测试平台，用于测试系统韧性。

## 功能特性

- **故障类型支持**
  - 延迟故障注入 - 测试系统在高延迟下的表现
  - 异常中断注入 - 模拟服务不可用场景
  - 错误码注入 - 测试错误处理逻辑

- **场景编排**
  - 多故障步骤组合
  - 时间控制（前置等待、持续时间）
  - 顺序执行

- **影响范围控制**
  - 按服务筛选
  - 影响比例配置
  - 标签和Header匹配

- **观测指标采集**
  - Jaeger链路追踪集成
  - 延迟分布（Avg/P95/P99）
  - 错误率统计
  - 请求计数
  - 时间窗口对齐对比 - 故障前后精准对比分析
  - 时间序列数据可视化

- **故障场景库（新增）**
  - 12个预置常见故障场景，分4大类
  - 网络故障：固定延迟、正态分布、指数分布
  - 服务故障：503/500/404错误，不同影响比例
  - 数据库故障：慢查询、连接失败
  - 混沌测试：极端延迟、级联故障、随机混合
  - 一键注入，自动配置智能回滚

- **智能回滚保护（新增）**
  - 实时监控系统指标（P99延迟、错误率）
  - 可配置阈值触发自动回滚
  - 连续失败检测，避免误判
  - 手动检查接口，支持即时验证
  - 默认开启，安全第一

- **韧性评分系统（新增）**
  - 4维度综合评分：恢复速度、稳定性、错误处理、性能恢复
  - S-A-B-C-D-F六级评级
  - 恢复趋势图可视化
  - 智能优化建议
  - 量化系统恢复能力

## 技术栈

### 后端
- Go 1.21+
- Gin Web框架
- GORM + SQLite
- Istio Client Go
- Jaeger Query API

### 前端
- React 18
- Material UI
- Chart.js
- React Router

### 基础设施
- Kubernetes
- Istio 服务网格
- Jaeger 分布式追踪
- Docker 容器化

## 项目结构

```
.
├── backend/                 # Go后端
│   ├── cmd/
│   │   └── main.go         # 主入口
│   ├── config/              # 配置
│   ├── internal/
│   │   ├── api/            # API处理器
│   │   ├── istio/          # Istio客户端
│   │   ├── jaeger/         # Jaeger客户端
│   │   ├── model/          # 数据模型
│   │   └── storage/        # 存储层
│   ├── pkg/
│   │   └── logger/         # 日志工具
│   ├── Dockerfile
│   └── go.mod
├── frontend/               # React前端
│   ├── src/
│   │   ├── components/     # 组件
│   │   ├── pages/          # 页面
│   │   ├── services/       # API服务
│   │   ├── App.js
│   │   └── index.js
│   ├── public/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── k8s/                    # Kubernetes配置
│   ├── namespace.yaml
│   ├── backend-deployment.yaml
│   ├── frontend-deployment.yaml
│   ├── configmap.yaml
│   ├── jaeger.yaml
│   └── sample-app.yaml
├── scripts/                # 部署脚本
│   ├── deploy.sh
│   └── deploy.ps1
└── README.md
```

## 快速开始

### 前置要求

- Kubernetes 集群 (v1.24+)
- Istio 已安装 (v1.18+)
- Docker
- kubectl 配置正确

### 本地开发

#### 后端开发

```bash
cd backend
go mod download
go run cmd/main.go
```

#### 前端开发

```bash
cd frontend
npm install
npm start
```

### Kubernetes 部署

#### Windows (PowerShell)

```powershell
cd scripts
.\deploy.ps1
```

#### Linux/Mac (Bash)

```bash
cd scripts
chmod +x deploy.sh
./deploy.sh
```

### 访问平台

获取 Istio Ingress Gateway 地址：

```bash
kubectl get service istio-ingressgateway -n istio-system
```

使用浏览器访问该 IP 地址。

## API 文档

### 故障管理 API

#### 创建故障
```http
POST /api/v1/faults
Content-Type: application/json

{
  "name": "延迟故障测试",
  "description": "测试服务延迟场景",
  "type": "delay",
  "target_service": "sample-service-a",
  "percentage": 100,
  "duration": 60,
  "delay_config": {
    "fixed_delay_ms": 1000
  }
}
```

#### 启动故障
```http
POST /api/v1/faults/{id}/start
```

#### 停止故障
```http
POST /api/v1/faults/{id}/stop
```

### 场景编排 API

#### 创建场景
```http
POST /api/v1/scenarios
Content-Type: application/json

{
  "name": "复杂测试场景",
  "description": "多步骤故障测试",
  "steps": [
    {
      "fault_id": "fault-uuid-1",
      "delay_before_seconds": 0,
      "duration_seconds": 30
    },
    {
      "fault_id": "fault-uuid-2",
      "delay_before_seconds": 10,
      "duration_seconds": 60
    }
  ]
}
```

#### 执行场景
```http
POST /api/v1/scenarios/{id}/execute
```

### 服务监控 API

#### 获取服务指标
```http
GET /api/v1/services/{name}/metrics?lookback=5m
```

## 故障类型配置

### 延迟故障 (delay)

```json
{
  "type": "delay",
  "delay_config": {
    "fixed_delay_ms": 1000,
    "exponential_delay": false
  }
}
```

### 中断故障 (abort)

```json
{
  "type": "abort",
  "abort_config": {
    "http_status": 500,
    "message": "Service Unavailable"
  }
}
```

### 错误故障 (error)

```json
{
  "type": "error",
  "error_config": {
    "error_rate": 0.1,
    "error_type": "random"
  }
}
```

## 影响范围配置

```json
{
  "scope": {
    "namespace": "default",
    "labels": {
      "version": "v1"
    },
    "headers": {
      "cookie": "^(.*?;)?(user=test)(;.*)?$"
    },
    "source_labels": {
      "app": "frontend"
    }
  }
}
```

## 监控指标

平台自动采集以下指标：

| 指标名称 | 说明 | 单位 |
|---------|------|------|
| avg_latency_ms | 平均延迟 | 毫秒 |
| p95_latency_ms | P95延迟 | 毫秒 |
| p99_latency_ms | P99延迟 | 毫秒 |
| request_count | 请求总数 | 个 |
| error_count | 错误数 | 个 |
| error_rate | 错误率 | % |

## 故障注入示例

### 示例1: 延迟注入

测试服务在1秒延迟下的表现：

```bash
curl -X POST http://localhost:8080/api/v1/faults \
  -H "Content-Type: application/json" \
  -d '{
    "name": "1s延迟测试",
    "type": "delay",
    "target_service": "sample-service-a",
    "percentage": 100,
    "duration": 120,
    "delay_config": {
      "fixed_delay_ms": 1000
    }
  }'
```

### 示例2: 500错误注入

模拟50%的请求返回503错误：

```bash
curl -X POST http://localhost:8080/api/v1/faults \
  -H "Content-Type: application/json" \
  -d '{
    "name": "503错误测试",
    "type": "abort",
    "target_service": "sample-service-b",
    "percentage": 50,
    "duration": 60,
    "abort_config": {
      "http_status": 503
    }
  }'
```

## 最佳实践

1. **从小比例开始**：首次测试使用10-20%的影响比例
2. **设置超时**：始终设置故障持续时间，避免忘记恢复
3. **监控关键指标**：故障注入期间密切关注系统指标
4. **生产环境谨慎**：生产环境测试需制定详细的回滚计划
5. **自动化测试**：将故障注入集成到CI/CD流水线

### 延迟分布模式使用建议（新增）

6. **选择合适的分布模式**：
   - **固定延迟**：适合精确的基准测试和回归测试
   - **正态分布**：模拟真实网络波动，适合日常韧性测试
   - **指数分布**：模拟极端长尾延迟，适合压力测试

7. **分布参数设置**：
   - 正态分布的标准差建议为均值的20-30%
   - 指数分布适合模拟突发流量下的延迟表现
   - 始终设置合理的最大延迟，避免无限增大

### 可视化拓扑选择器（新增）

8. **使用拓扑图选择服务**：
   - 点击服务节点可查看服务详情和版本信息
   - 悬停连线可高亮服务间的依赖关系
   - 选择特定版本进行精确故障注入

### 时间窗口对比（新增）

9. **对比分析最佳实践**：
   - 故障前后窗口时长建议保持一致（如各5分钟）
   - 确保故障前窗口内系统处于稳定状态
   - 关注P95/P99延迟变化，而非仅看平均延迟
   - 结合时间序列图分析延迟变化趋势
   - 多次重复测试验证结果的一致性

### 故障场景库（新增）

10. **场景库使用建议**：
    - **快速上手**：新用户可从预置场景开始测试，了解各种故障的影响
    - **分类选择**：根据测试目标选择对应分类（网络/服务/数据库/混沌）
    - **严重程度递进**：从低严重程度场景开始，逐步提升
    - **一键注入**：场景库预置场景已包含智能回滚保护配置

11. **场景测试顺序建议**：
    - 第一阶段：网络延迟类场景（500ms固定延迟 → 正态分布波动）
    - 第二阶段：服务错误类场景（10% → 50%错误率）
    - 第三阶段：数据库相关场景（慢查询 → 连接失败）
    - 第四阶段：混沌极端场景（极端延迟 → 级联故障 → 随机混合）

### 智能回滚保护（新增）

12. **安全测试保障**：
    - **默认启用**：建议始终开启智能回滚，特别是生产环境
    - **阈值配置**：根据业务SLA设置合理的延迟和错误率阈值
    - **连续检测**：使用连续失败触发机制，避免单次异常误判
    - **最小请求数**：设置合理的最小请求数，确保统计显著性

13. **回滚参数配置指南**：
    - **低风险业务**：延迟阈值 = SLA的150%，错误率阈值 = 5%
    - **中风险业务**：延迟阈值 = SLA的200%，错误率阈值 = 10%
    - **高风险业务**：延迟阈值 = SLA的300%，错误率阈值 = 20%
    - 连续失败次数建议为3-5次，检测间隔5-15秒

### 韧性评分系统（新增）

14. **有效利用韧性评分**：
    - **基线建立**：对关键服务执行标准场景测试，建立韧性基线
    - **定期复测**：每次架构变更后重新测试，对比评分变化
    - **目标设定**：设定评分目标（如核心服务A级以上）
    - **建议采纳**：关注评分报告中的优化建议，持续改进

15. **评分解读指南**：
    - **S/A级**：系统韧性优秀，可放心进行生产环境测试
    - **B级**：系统韧性良好，建议针对低分维度进行优化
    - **C级**：系统韧性一般，需要针对性改进薄弱环节
    - **D/F级**：系统韧性较差，建议暂停复杂场景测试，先进行架构优化

## 故障排除

### Istio 权限问题

确保服务账号有足够的权限访问 VirtualService：

```bash
kubectl describe clusterrole fault-injection-istio-role
```

### Jaeger 连接失败

检查 Jaeger 服务是否正常运行：

```bash
kubectl get pods -n observability
kubectl logs -n observability jaeger-xxx
```

### 前端无法连接后端

检查 API 代理配置和 VirtualService 路由规则。

## 贡献指南

欢迎提交 Issue 和 Pull Request。

## 许可证

MIT License
