# 云成本优化工具 (Cloud Cost Optimizer)

一个基于Python的云成本优化工具，支持分析云资源使用情况、识别闲置资源、推荐降配或释放，并提供审批工作流和Grafana可视化。

## 功能特性

- 🔍 **资源分析**: 自动收集ECS/EIP等云资源信息
- 📊 **利用率分析**: 分析CPU、内存、网络等指标的利用率趋势
- 🎯 **闲置资源识别**: 自动检测低利用率实例和未绑定的EIP
- 💰 **成本优化推荐**: 智能推荐释放或降配方案
- 📋 **审批工作流**: 优化操作需要审批后才能执行
- 📈 **Grafana可视化**: 提供资源利用率趋势和成本对比图表
- 🔄 **多云支持**: 支持阿里云、AWS等主流云厂商

## 项目结构

```
.
├── cloud_collector/          # 云资源采集模块
│   ├── base_collector.py     # 采集器基类
│   ├── aliyun_collector.py   # 阿里云采集器
│   ├── aws_collector.py      # AWS采集器
│   └── mock_collector.py     # 模拟采集器(用于演示)
├── analyzers/                # 分析模块
│   ├── resource_analyzer.py  # 资源利用率分析
│   ├── idle_detector.py      # 闲置资源检测
│   └── cost_optimizer.py     # 成本优化引擎
├── database/                 # 数据库模块
│   ├── models.py             # 数据模型
│   └── db_manager.py         # 数据库管理
├── api/                      # API接口
│   └── app.py                # Flask API服务器
├── grafana/                  # Grafana配置
│   └── dashboards/
│       └── cloud_cost_optimizer.json  # 仪表盘模板
├── config.yaml               # 配置文件
├── requirements.txt          # 依赖列表
├── main.py                   # 主程序
└── demo.py                   # 演示脚本
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行演示

```bash
python demo.py
```

这将使用模拟数据运行完整的成本优化分析。

### 3. 启动API服务器

```bash
python main.py --api
```

启动后可以访问:
- http://localhost:5000/metrics - Prometheus指标
- http://localhost:5000/api/analysis - 分析结果API
- http://localhost:5000/api/idle-resources - 闲置资源列表
- http://localhost:5000/api/optimization-plan - 优化方案

## 命令行使用

### 完整分析

```bash
# 使用模拟数据
python main.py

# 使用真实阿里云数据
python main.py --provider aliyun

# 导出分析报告
python main.py --export

# 启用数据库保存优化请求
python main.py --db
```

### 审批管理

```bash
# 查看待审批请求
python main.py --show-requests --db

# 通过API审批
curl -X POST http://localhost:5000/api/requests/<request_id>/approve

# 批量自动审批(月度节省低于100元的)
curl -X POST http://localhost:5000/api/requests/auto-approve \
  -H "Content-Type: application/json" \
  -d '{"threshold": 100}'
```

## 配置说明

编辑 `config.yaml` 配置文件:

```yaml
cloud_providers:
  aliyun:
    enabled: true
    access_key_id: ${ALIYUN_ACCESS_KEY_ID}
    access_key_secret: ${ALIYUN_ACCESS_KEY_SECRET}
    regions:
      - cn-hangzhou

optimization_rules:
  idle_resources:
    cpu_threshold: 10.0      # CPU低于10%视为闲置
    memory_threshold: 20.0   # 内存低于20%视为闲置
    idle_days: 7

approval:
  enabled: true
  auto_approve_below: 100.0  # 月度节省低于100元自动审批
```

## Grafana配置

1. 确保Prometheus正在抓取 `http://localhost:5000/metrics`
2. 在Grafana中导入 `grafana/dashboards/cloud_cost_optimizer.json`
3. 选择Prometheus数据源

仪表盘包含:
- 成本概览面板(当前成本、节省金额、节省比例)
- CPU/内存利用率趋势图
- 优化前后成本对比图

## API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /metrics | Prometheus指标导出 |
| GET | /api/health | 健康检查 |
| GET | /api/analysis | 获取分析摘要 |
| GET | /api/resources/ecs | 获取ECS资源列表 |
| GET | /api/resources/eip | 获取EIP资源列表 |
| GET | /api/idle-resources | 获取闲置资源 |
| GET | /api/optimization-plan | 获取优化方案 |
| GET | /api/requests | 获取审批请求列表 |
| POST | /api/requests | 创建优化请求 |
| POST | /api/requests/:id/approve | 审批通过 |
| POST | /api/requests/:id/reject | 拒绝审批 |
| POST | /api/requests/:id/execute | 执行优化 |
| POST | /api/requests/auto-approve | 批量自动审批 |
| POST | /api/refresh | 刷新分析数据 |

## 核心模块说明

### 资源采集器 (cloud_collector)

- **MockCollector**: 生成模拟数据用于演示和测试
- **AliyunCollector**: 调用阿里云SDK采集真实数据
- **AWSCollector**: 调用AWS SDK采集真实数据

### 分析器 (analyzers)

- **ResourceAnalyzer**: 计算资源利用率统计指标(平均值、最大值、P95等)
- **IdleResourceDetector**: 根据配置的阈值识别闲置资源
- **CostOptimizer**: 计算成本、推荐降配方案、生成优化计划

### 审批工作流

优化操作的生命周期:
1. **pending**: 待审批
2. **approved**: 已审批
3. **executed**: 已执行
4. **rejected**: 已拒绝

## 扩展开发

### 添加新的云服务商

1. 继承 `BaseCollector` 类
2. 实现 `get_ecs_instances`, `get_eip_addresses`, `get_metric_data` 方法
3. 在 `main.py` 的 `get_collector` 函数中注册新的采集器

### 添加新的优化规则

在 `analyzers/cost_optimizer.py` 中添加新的检测逻辑,或修改 `config.yaml` 中的阈值配置。

## 注意事项

1. **生产环境使用前请充分测试,建议先在测试环境验证优化建议**
2. **执行释放操作前务必备份重要数据**
3. **建议设置合理的审批阈值,避免误操作**
4. **定期检查云厂商API调用配额**

## License

MIT
