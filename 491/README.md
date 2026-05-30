# 云资源成本优化推荐引擎

一个基于 Python 的云资源成本优化推荐引擎，提供智能的成本优化建议、执行计划和成本趋势预测。

## 功能特性

### 1. 数据采集模块 (`src/data_collector.py`)
- 支持 AWS、Azure、GCP 三大云厂商
- 生成模拟的历史成本数据
- 生成实例使用率数据（CPU、内存、网络）
- 生成 EBS 存储卷数据
- 预留实例推荐数据

### 2. 成本分析模块 (`src/cost_analyzer.py`)
- 成本汇总统计（按服务、地区、账号）
- 实例利用率分析（CPU、内存、网络）
- 存储优化分析
- 成本趋势分析
- 自动生成成本洞察和告警

### 3. 优化算法模块 (`src/optimizer.py`)
- **终止资源推荐**：识别空闲和停止的实例
- **实例降配推荐**：基于利用率数据推荐合适的实例类型
- **存储优化推荐**：未使用的EBS卷、gp2转gp3
- **预留实例推荐**：基于使用率的RI购买建议
- ROI计算和投资回收期分析
- 分阶段执行计划

### 4. 时序预测模块 (`src/forecasting.py`)
- 使用 Prophet 进行成本趋势预测
- 支持回退预测算法（趋势+季节性）
- 异常检测（成本突增/突降）
- 运行率计算（Run Rate）
- 按服务维度的预测

### 5. Streamlit Web 界面 (`app.py`)
- 📊 **成本概览**：Dashboard展示关键指标
- 💡 **优化推荐**：详细的优化建议和节省金额
- 🔮 **成本预测**：趋势预测和异常检测
- 🖥️ **资源分析**：实例和存储的利用率分析
- 📋 **执行计划**：分阶段实施路线图

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行测试脚本

```bash
python test_modules.py
```

### 3. 启动 Streamlit Web 界面

```bash
streamlit run app.py
```

## 项目结构

```
.
├── app.py                      # Streamlit 主应用
├── requirements.txt            # Python 依赖
├── test_modules.py            # 模块测试脚本
├── README.md                   # 项目说明文档
└── src/
    ├── __init__.py            # 包初始化
    ├── data_collector.py      # 数据采集模块
    ├── cost_analyzer.py       # 成本分析模块
    ├── optimizer.py           # 优化算法模块
    └── forecasting.py         # 时序预测模块
```

## 使用说明

### 侧边栏设置
- **云厂商选择**：支持 AWS、Azure、GCP
- **实例数量**：调整模拟数据的实例数量
- **预测天数**：设置成本预测的时间范围
- **数据源**：使用模拟数据或上传CSV

### 优化推荐类型

| 类型 | 描述 | 风险 | 难度 |
|------|------|------|------|
| 终止资源 | 停止或删除闲置资源 | 低 | 低 |
| 实例降配 | 下调实例规格 | 中 | 中 |
| 存储优化 | 释放无用存储、升级类型 | 低 | 低 |
| 预留实例 | 购买预留实例 | 中 | 低 |

### 成本预测
- 使用 Prophet 算法进行时序预测
- 自动检测周度和年度季节性
- 提供置信区间
- 异常点检测和告警

## 扩展开发

### 添加真实云厂商 API 支持

1. AWS Cost Explorer API:
```python
import boto3
ce = boto3.client('ce')
response = ce.get_cost_and_usage(...)
```

2. Azure Cost Management API
3. GCP Billing API

### 自定义优化规则

在 `optimizer.py` 中添加新的推荐类型：

```python
def generate_custom_recommendations(self) -> List[OptimizationRecommendation]:
    # 自定义优化逻辑
    pass
```

## 技术栈

- **Python 3.8+**
- **Streamlit** - Web 界面框架
- **Pandas/NumPy** - 数据处理
- **Plotly** - 可视化图表
- **Prophet** - 时序预测
- **Scikit-learn** - 机器学习

## License

MIT License
