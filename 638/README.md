# K8s Autoscaler - Kubernetes 副本数自动调优工具

基于 Go + React 的 Kubernetes 自动扩缩容工具，支持 HPA 策略推荐、预测性扩缩容和成本优化。

## 功能特性

### 1. 多指标采集
- **CPU/内存使用率** - 通过 K8s Metrics API 获取
- **QPS (每秒请求数)** - 通过 Prometheus 采集
- **P99 延迟** - 通过 Prometheus 直方图计算

### 2. HPA 策略推荐
- 加权多指标分析（CPU:1.0, 内存:0.8, QPS:0.9, 延迟:0.7）
- **多指标融合阈值** - CPU+内存+QPS 加权组合负载指数
  - 融合权重：CPU 0.4, 内存 0.3, QPS 0.3
  - 综合负载指数 = Σ(指标使用率 × 权重)
  - 当融合负载 > 0.75 时触发扩容
  - 当融合负载 < 0.375 时触发缩容
  - 相比单指标阈值，更准确反映真实业务压力
- 自动计算目标副本数
- 冷却时间保护（ScaleUp/ScaleDown Cooldown）
- 最大扩缩容比率限制
- 推荐策略评分（0-100分）

### 3. 预测性扩缩容
- **移动平均 (Moving Average)** - 平滑波动
- **指数平滑 (Exponential Smoothing)** - 短期趋势
- **双指数平滑 (Double Exponential)** - 带趋势预测
- **线性回归 (Linear Regression)** - 长期趋势
- **周期性模式识别** - 基于自相关分析检测业务周期
  - 支持 1小时/6小时/12小时/24小时(日)/168小时(周) 周期检测
  - **傅里叶变换 (DFT)** - 频域分析提取主要频率分量
  - **周期性预测** - 趋势 + 周期分量叠加预测
  - Pearson 相关系数 > 0.6 判定为强周期模式
- **加权集成 (Weighted Ensemble)** - 多算法融合
- 提前 30 分钟预测负载，提前扩容

### 4. 成本优化
- **SLA 约束保障** - 服务水平下限约束
  - 支持约束类型：MinReplicas（最小副本数）、Availability（可用性）、LatencyP99（延迟）、Throughput（吞吐量）
  - 优先级机制：高优先级约束先保障
  - 违规检测：自动识别 SLA 违反并计算严重程度
  - **SLA 分数**：0-100 分，违规扣分（严重 -20，警告 -5）
  - 优化时自动提升副本数以满足 SLA 约束
  - 延迟 SLA 违规时不降低 CPU 请求
- 资源浪费分析（P95 使用率 vs 请求值）
- 月度成本估算
- 潜在节省计算
- Right-sizing 建议
- 基于节点定价模型的成本计算

### 5. 滚动窗口自动调参
- **持续优化扩缩容参数** - 基于历史表现自动调整
  - 可调参数：扩容阈值、缩容阈值、融合目标、最大扩容比率、融合权重
  - 奖励函数：`0.4×(1-SLA违规) + 0.3×(1-延迟偏差) + 0.3×(1-成本变化率)`
  - 滚动窗口大小：100 样本
- **探索与利用（Exploration vs Exploitation）**
  - 初始探索率 30%，随时间衰减至 5%
  - 每 10 个样本进行一次参数更新
  - 以历史最优参数为基准，±20% 随机扰动探索
- **多臂老虎机策略**
  - 选择窗口内奖励最高的参数组合
  - 探索率概率下尝试新参数组合
  - 自动记录参数变更历史和奖励曲线

### 6. 扩容联动
- **服务依赖关系图** - 支持多服务级联扩容
  - 依赖配置：源服务 → 目标服务，相关强度 0-1
  - 权重系数：目标服务扩容比例 = 源服务变化 × 权重
  - 延迟生效：源服务扩容后 N 秒再触发目标服务
  - 最小触发阈值：至少变更 N 个副本才触发联动
- **示例链路**：
  ```
  web-frontend (+2) → api-server (+1, 30s延迟) → payment-service (+1, 60s延迟)
  ```
- **自动相关发现** - 基于历史数据计算 Pearson 相关系数
- **pending 队列** - 延迟生效的联动决策队列，可查看和取消

### 7. 成本收益分析
- **收益模型** - 量化扩容带来的业务价值
  - 每 QPS 收益：$0.005/QPS/小时
  - 延迟惩罚：$10/秒P99超阈值/小时
  - 停机成本：$1000/分钟
  - SLA 违规罚金：$5000/次
- **成本分析**
  - 额外计算成本：新增副本的小时成本
  - 资源浪费成本：未使用资源的成本
- **决策指标**
  - **净收益（Net Benefit）**：总收益 - 总成本
  - **收益成本比（B/C Ratio）**：
    - > 2.0 → **APPROVE**（绿色，强烈推荐）
    - 1.2-2.0 → **CAUTION**（黄色，谨慎执行）
    - < 1.2 → **REJECT**（红色，不推荐）
  - **投资回收期（Payback Period）**：收回成本所需小时数
  - **盈亏平衡QPS**：覆盖成本所需的最低QPS增量
- **置信度评分** - 0-100%，基于SLA改善和QPS提升幅度

## 项目结构

```
k8s-autoscaler/
├── cmd/
│   └── main.go                 # 程序入口
├── pkg/
│   ├── metrics/
│   │   └── collector.go        # 指标采集器（K8s Metrics API + Prometheus）
│   ├── predictor/
│   │   └── engine.go           # 时序预测引擎（4种算法）
│   ├── recommender/
│   │   └── hpa.go              # HPA 策略推荐引擎
│   ├── scaler/
│   │   └── predictive.go       # 预测性扩缩容算法
│   ├── cost/
│   │   └── optimizer.go        # 成本优化引擎
│   ├── controller/
│   │   └── controller.go       # 主控制器（调度协调整合）
│   └── api/
│       └── server.go           # REST API 服务器
└── web/                        # React 前端
    ├── src/
    │   ├── components/         # UI 组件
    │   │   ├── MetricCard.js
    │   │   ├── HPARecommendation.js
    │   │   ├── PredictionChart.js
    │   │   ├── CostAnalysis.js
    │   │   └── DeploymentCard.js
    │   ├── hooks/              # React Hooks
    │   ├── utils/              # API 工具
    │   ├── App.js
    │   └── index.js
    └── package.json
```

## 快速开始

### 后端启动

```bash
# 开发模式（使用 Mock 数据）
AUTOSCALER_MODE=demo go run cmd/main.go

# 生产模式
AUTOSCALER_MODE=live \
KUBECONFIG=~/.kube/config \
PROMETHEUS_URL=http://prometheus:9090 \
go run cmd/main.go
```

API 服务器运行在 `http://localhost:8080`

### 前端启动

```bash
cd web
npm install
npm start
```

前端运行在 `http://localhost:3000`

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/dashboard` | 获取所有监控数据 |
| GET | `/api/v1/namespaces/{ns}/deployments/{name}/metrics` | 获取指标 |
| GET | `/api/v1/namespaces/{ns}/deployments/{name}/recommendation` | 获取 HPA 推荐 |
| GET | `/api/v1/namespaces/{ns}/deployments/{name}/prediction` | 获取预测结果 |
| GET | `/api/v1/namespaces/{ns}/deployments/{name}/cost` | 获取成本分析 |
| GET | `/api/v1/namespaces/{ns}/deployments/{name}/autotune` | 获取完整调优结果 |
| POST | `/api/v1/namespaces/{ns}/deployments/{name}/scale` | 手动扩缩容 |
| POST | `/api/v1/namespaces/{ns}/deployments/{name}/watch` | 加入监控列表 |
| DELETE | `/api/v1/namespaces/{ns}/deployments/{name}/watch` | 移除监控 |
| GET | `/api/v1/tuning` | 获取自动调参状态 |
| GET | `/api/v1/tuning/history` | 获取调参历史样本 |
| GET | `/api/v1/linkages` | 获取服务依赖关系 |
| POST | `/api/v1/linkages` | 添加服务依赖 |
| GET | `/api/v1/linkages/pending` | 获取待执行的联动决策 |
| GET | `/api/v1/cost-benefit/history` | 获取成本收益分析历史 |

## 核心算法

### 预测性扩缩容流程

```
采集历史指标 → 多算法预测 → 加权集成 → 
提取预测峰值 → 计算单副本容量 → 
确定目标副本数 → 稳定性检查 → 执行扩缩容
```

### 成本优化模型

- **CPU 单元成本**: 从节点总价的 50% 分摊
- **内存单元成本**: 从节点总价的 50% 分摊
- **优化目标**: P95 使用率 * (1 + 15% 余量)
- **月度估算**: 单价 × 730 小时 × 副本数

## 技术栈

**后端:**
- Go 1.21+
- K8s Client-Go
- K8s Metrics API
- Prometheus HTTP API
- Gorilla Mux (路由)

**前端:**
- React 18
- Recharts (图表)
- Lucide React (图标)
- CSS Grid / Flexbox
