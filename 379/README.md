# 客户生命周期价值预测系统

基于BG/NBD和Gamma-Gamma模型的客户生命周期价值(LTV)预测与分析平台，使用Python + Lifetimes + Scikit-learn + Streamlit实现。

## 📋 功能特性

### 核心模型
- **BG/NBD模型**：预测客户未来N个月的消费次数和活跃度
- **Gamma-Gamma模型**：预测客户客单价
- **LTV计算**：综合两个模型输出，计算客户生命周期价值

### 分析功能
- **LTV分位数分析**：查看不同分位的LTV值和分布
- **客户分群**：基于KMeans聚类将客户分为高价值、潜力、普通、低价值等客群
- **流失预警**：识别有流失风险的高价值客户
- **预算分配**：基于价值贡献推荐营销预算分配

### 策略建议
- 针对不同客群提供定制化运营策略
- 包含立即行动、短期行动、长期战略的行动计划
- 详细的客群画像和运营建议

## 📁 项目结构

```
.
├── src/
│   ├── __init__.py
│   ├── data_generator.py      # 数据生成模块（模拟交易、行为、画像）
│   ├── bg_nbd_model.py        # BG/NBD模型模块
│   ├── gamma_gamma_model.py   # Gamma-Gamma模型模块
│   ├── ltv_analysis.py        # LTV计算和客户分群模块
│   └── strategy_engine.py     # 策略建议引擎
├── app.py                     # Streamlit应用界面
├── main.py                    # 命令行运行入口
├── requirements.txt           # 依赖包
└── README.md                  # 项目说明
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动Streamlit界面

```bash
streamlit run app.py
```

### 3. 命令行运行

```bash
python main.py
```

## 📊 使用说明

### Streamlit界面
1. 在左侧侧边栏配置参数：
   - 模拟客户数量 (200-2000)
   - 预测未来月数 (1-24)
   - 客户分群数量 (3-6)
   - 折现率 (0-20%)
2. 点击"生成数据并运行分析"按钮
3. 在各个标签页查看分析结果：
   - **总览**：关键指标、LTV分布、帕累托曲线
   - **LTV分析**：分位数表、单客查询
   - **客户分群**：各客群统计、雷达图、详细画像
   - **策略建议**：各客群运营策略、流失预警、预算分配、行动计划
   - **模型详情**：模型参数、诊断图表
   - **原始数据**：查看和下载各类数据

### 作为Python库使用

```python
from src.data_generator import generate_customer_profiles, generate_transaction_history, prepare_model_data
from src.bg_nbd_model import BGNBDModel
from src.gamma_gamma_model import GammaGammaModel
from src.ltv_analysis import LTVAnalyzer
from src.strategy_engine import StrategyEngine

# 生成数据
profiles = generate_customer_profiles(n_customers=500)
transactions = generate_transaction_history(profiles)
model_data = prepare_model_data(profiles, transactions, None)

# 训练模型
bg_nbd = BGNBDModel()
bg_nbd.fit(model_data)

gg = GammaGammaModel()
gg.fit(model_data)

# 计算LTV
analyzer = LTVAnalyzer(bg_nbd, gg)
ltv_data = analyzer.calculate_ltv(model_data, future_months=12)

# 客户分群
ltv_data, segment_stats = analyzer.segment_customers(model_data, ltv_data, n_segments=4)

# 生成策略
engine = StrategyEngine()
for _, row in segment_stats.iterrows():
    profile = analyzer.get_segment_profile(model_data, ltv_data, row['segment'])
    strategy = engine.generate_segment_strategy(row['segment_name'], profile, row)
    print(strategy)
```

## 🧠 模型原理

### BG/NBD模型
BG/NBD（Beta-Geometric/Negative Binomial Distribution）模型假设：
- 每个客户的购买率服从Gamma分布
- 客户在购买后有一定概率流失，流失率服从Beta分布
- 可以预测客户未来的购买次数和仍活跃的概率

### Gamma-Gamma模型
Gamma-Gamma模型假设：
- 客户的单次购买金额服从Gamma分布
- 不同客户的平均购买金额也服从Gamma分布
- 可以预测客户未来的平均客单价

### LTV计算公式
```
LTV = 预测购买次数 × 预测客单价 × 折现因子
```

## 🛠️ 技术栈

- **Python 3.8+**
- **Lifetimes**：BG/NBD和Gamma-Gamma模型实现
- **Scikit-learn**：KMeans聚类、数据预处理
- **Streamlit**：Web应用界面
- **Plotly**：交互式图表
- **Pandas / NumPy**：数据处理

## 📈 输入输出示例

### 输入数据格式
1. **客户画像**：customer_id, age, gender, region, membership_level
2. **交易历史**：customer_id, transaction_date, amount, transaction_type
3. **行为日志**：customer_id, activity_date, activity_type, duration_seconds

### 输出结果
- 每个客户的预测LTV、购买次数、客单价、活跃度
- LTV分位数统计表
- 客户分群及各群特征
- 各客群运营策略建议
- 流失预警客户列表

## 📝 License

MIT License
