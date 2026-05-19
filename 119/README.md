# 🌤️ Terraform IaC 云成本管理工具

基于 Terraform 的多云成本监控与优化平台，支持 tfstate 静态分析、CI/CD 成本变更检查、可视化报告生成、多云统一成本分析。

## ✨ 核心功能

| 功能模块 | 描述 | 核心特性 |
|---------|------|---------|
| **TFState 分析** | 解析 Terraform 状态文件 | 🔍 资源识别、成本估算、标签合规检查 |
| **多云账单分析** | 对接三大云厂商 API | ☁️ AWS / Azure / GCP 统一接口 |
| **CI/CD 集成** | PR 级别成本变更检查 | 🔄 Infracost 差异对比、阻断阈值配置 |
| **可视化报告** | 交互式 HTML 报告 | 📊 Chart.js 图表、资源成本映射、多维度分析 |

## 📁 项目结构

```
terraform-iac-cost-manager/
├── main.py                          # 统一入口脚本
├── requirements.txt                 # Python 依赖
├── README.md                        # 项目文档
├── src/
│   ├── analyzers/
│   │   ├── tfstate_analyzer.py      # Terraform 状态解析引擎
│   │   └── multi_cloud_adapter.py   # 多云成本适配器 (AWS/Azure/GCP)
│   ├── reporters/
│   │   └── visual_report.py         # 可视化 HTML 报告生成器
│   └── ci/
│       └── infracost_check.py       # CI/CD 成本变更检查
└── .github/
    └── workflows/
        └── infracost-pr-check.yml   # GitHub Actions 工作流
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置云凭证

```bash
# AWS
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"

# Azure
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"

# GCP
export GCP_PROJECT_ID="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"
```

### 3. 安装 Infracost (可选)

```bash
curl -fsSL https://git.io/get-infracost | sh
infracost register
```

## 💻 使用方式

### 命令 1: 分析 Terraform 状态文件

```bash
# 基础分析
python main.py tfstate --state terraform.tfstate

# 生成 HTML 可视化报告
python main.py tfstate --state terraform.tfstate --html-report cost_report.html

# 导出详细 JSON
python main.py tfstate --state terraform.tfstate --output-json analysis.json
```

**输出示例:**
```
📊 TFSTATE COST ANALYSIS
============================================================
📁 Resources: 42
💰 Monthly Cost: $2,847.50
📅 Annual Cost: $34,170.00

🏢 Cost by Provider:
   AWS: $2,340.00
   AZURE: $507.50

📦 Top Resource Types:
   aws_instance: $980.00
   aws_rds_cluster: $650.00
   azurerm_linux_virtual_machine: $380.50

🏷️ Tag Compliance:
   Untagged/Incomplete Tags: 8 resources

✅ Analysis complete!
```

### 命令 2: 分析多云账单成本

```bash
# 分析最近 30 天所有云厂商
python main.py cloud --days 30

# 指定云厂商和时间范围
python main.py cloud --providers aws azure \
                   --start-date 2024-01-01 \
                   --end-date 2024-01-31

# 导出报告
python main.py cloud --output multi_cloud_report.json
```

### 命令 3: CI/CD 成本变更检查

```bash
# 对比两个 Terraform 环境
python main.py diff --base-path ./main \
                   --path ./feature-branch \
                   --threshold-percent 20 \
                   --threshold-amount 100

# 成本增幅过大时阻断合并
python main.py diff --base-path main --path pr \
                   --threshold-amount 200 \
                   --block-merge
```

### 命令 4: 生成可视化报告

```bash
# 从 tfstate 直接生成
python main.py report --state terraform.tfstate --output report.html

# 从 JSON 分析结果生成
python main.py report --analysis-json analysis.json
```

## 🔧 CI/CD 集成

### GitHub Actions

将 `.github/workflows/infracost-pr-check.yml` 复制到你的仓库：

```yaml
# 自动触发:
# - 每个 PR 提交时
# - 分析成本变更
# - 评论报告到 PR
# - 超阈值时标记失败
```

**功能:**
- 📊 自动计算月度成本变更
- ⚠️ 显著成本增加高亮显示
- 🚦 可配置的合并阻断阈值
- 💾 保存报告为 Artifact

## 📊 可视化报告特性

生成的 HTML 报告包含:

1. **摘要卡片**
   - 月度/年度总成本
   - 托管资源数量
   - 预估节省金额
   - 标签合规状态

2. **多维度图表**
   - 按云服务商分布 (饼图)
   - 按资源类型分布 Top 10 (水平柱状图)
   - 按区域分布 (柱状图)

3. **资源清单**
   - 按成本排序的资源列表
   - 成本构成明细
   - 标签状态标识

## ☁️ 支持的云厂商与资源

### AWS
- Compute: EC2, ECS, EKS, Lambda
- Database: RDS, ElastiCache, DynamoDB
- Storage: S3, EBS, EFS
- Network: ALB, CloudFront, Route53
- +更多

### Azure
- Virtual Machines, VMSS
- Azure SQL, Cosmos DB
- Storage Accounts, Blob Storage
- AKS, Functions, App Service

### GCP
- Compute Engine, GKE
- Cloud SQL, Cloud Spanner
- GCS, Persistent Disks
- Cloud Functions, Cloud Run

## 🔒 权限要求

### AWS
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ce:GetCostAndUsage",
      "ce:GetCostForecast"
    ],
    "Resource": "*"
  }]
}
```

### Azure
- Cost Management Reader 角色
- 或 Microsoft.CostManagement/* 权限

### GCP
- roles/billing.viewer 权限

## 📈 工作原理

```
                    ┌──────────────────┐
  Terraform State ─►│                  │
                    │  TFState Parser  │── Resource Inventory
  Cloud Billing API►│                  │── Cost Estimation
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │                  │
                    │  Cost Engine     │── Multi-Cloud Aggregation
                    │                  │── Service Breakdown
                    └────────┬─────────┘
                             │
        ┌────────────────────┼─────────────────────┐
        ▼                    ▼                     ▼
  ┌───────────┐       ┌───────────┐         ┌───────────┐
  │ CI/CD     │       │ Visual    │         │ Export    │
  │ Diff      │       │ Reports   │         │ Reports   │
  └───────────┘       └───────────┘         └───────────┘
```

## 🔮 规划功能

- [ ] 成本异常检测与告警
- [ ] 预留实例 (RI) 购买推荐
- [ ] 资源规格优化建议
- [ ] 预算管理与预测
- [ ] 自定义标签成本分摊

## 🤝 贡献

欢迎提交 Issue 和 Pull Request!

## 📄 许可证

MIT License

---

**注意**: 本工具提供的成本为估算值，实际费用以云服务商官方账单为准。
