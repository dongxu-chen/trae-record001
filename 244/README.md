# 股票因子回测平台

一个基于 Python + Pandas + NumPy 的股票因子回测平台，支持因子表达式输入、分层回测、绩效分析和可视化。

## 功能特性

- ✅ **因子表达式解析**: 支持灵活的因子表达式输入
- ✅ **分层回测**: 按因子值分为N组进行回测
- ✅ **停牌退市处理**: 自动处理停牌和退市股票数据
- ✅ **绩效分析**: 年化收益、夏普比率、最大回撤、胜率等
- ✅ **IC分析**: 1日、5日、20日的IC/IR分析（支持按调仓周期计算）
- ✅ **可视化**: 分组收益曲线、回撤图、IC分布图等
- ✅ **行业市值中性化**: 通过回归剔除行业和市值影响
- ✅ **遗传编程因子挖掘**: 自动组合因子表达式并评估过拟合风险
- ✅ **WebSocket模拟交易**: 实时推送因子信号到模拟交易系统
- ✅ **归因分析**: 分解收益来源（行业暴露、风格暴露、特异性收益）

## 项目结构

```
.
├── config.py                  # 配置文件
├── data_loader.py             # 数据加载模块
├── factor_engine.py           # 因子计算引擎
├── backtest.py                # 回测引擎
├── performance.py             # 绩效分析模块
├── visualization.py           # 可视化模块
├── genetic_factor_mining.py   # 遗传编程因子挖掘
├── simulated_trading.py       # WebSocket模拟交易系统
├── attribution_analysis.py    # 归因分析模块
├── main.py                    # 主程序入口
├── requirements.txt           # 依赖包
├── data/                      # 数据目录
└── results/                   # 结果输出目录
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

### 1. 演示模式

运行预定义的因子回测演示：

```bash
python main.py --mode demo
```

### 2. 单因子回测

测试特定因子表达式：

```bash
python main.py --mode single --factor "1 / PE" --name EP
```

### 3. 交互模式

手动输入因子表达式进行回测：

```bash
python main.py --mode interactive
```

## 因子表达式说明

### 基础因子

- `PE`: 市盈率
- `PB`: 市净率  
- `ROE`: 净资产收益率
- `MKT_CAP`: 市值

### 可用函数

- `rank(x)`: 排序（百分位）
- `zscore(x)`: 标准化（Z-Score）
- `log(x)`: 自然对数
- `abs(x)`: 绝对值
- `sqrt(x)`: 平方根
- `mean(x, window)`: 移动平均
- `std(x, window)`: 移动标准差
- `delta(x, period)`: 差分
- `pct_change(x, period)`: 变化率

### 表达式示例

```python
# EP因子（市盈率倒数）
"1 / PE"

# ROE因子
"ROE"

# 排序后的EP因子
"rank(1 / PE)"

# ROE变化率（20日）
"delta(ROE, 20)"

# 复合因子：EP + ROE
"zscore(1 / PE) + zscore(ROE)"

# 市值因子（取对数）
"log(MKT_CAP)"
```

## 配置说明

在 `config.py` 中可以修改以下参数：

- `N_GROUPS`: 分组数量（默认10组）
- `REBALANCE_FREQ`: 调仓频率（默认月度）
- `TRADING_DAYS`: 年交易日数（默认252）
- `RISK_FREE_RATE`: 无风险利率（默认3%）
- `HANDLE_SUSPEND`: 是否处理停牌（默认True）
- `HANDLE_DELIST`: 是否处理退市（默认True）

## 输出说明

### 绩效指标

- **年化收益**: 年化收益率
- **波动率**: 年化波动率
- **夏普比率**: 风险调整后收益
- **最大回撤**: 历史最大回撤
- **胜率**: 正收益天数占比

### IC分析

- **Mean IC**: 平均信息系数
- **IR**: 信息比率（Mean IC / Std IC）
- **IC > 0**: IC为正的比例
- **T-Statistic/P-Value**: 统计显著性检验

### 图表输出

所有图表保存在 `results/` 目录下：

- `group_returns_*.png`: 分组累积收益曲线
- `spread_return_*.png`: 多空组合收益
- `ic_analysis_*.png`: IC时间序列
- `ic_histogram_*.png`: IC分布直方图
- `performance_metrics_*.png`: 各组合绩效指标
- `drawdown_*.png`: 回撤曲线

## API使用示例

```python
from data_loader import DataLoader
from factor_engine import FactorEngine
from backtest import BacktestEngine
from performance import PerformanceAnalyzer
from visualization import Visualizer

# 1. 加载数据
loader = DataLoader()
loader.generate_sample_data(n_stocks=100)
price, factors, suspend, delist = loader.load_data()
returns = loader.calculate_daily_returns()

# 2. 计算因子
engine = FactorEngine(factors)
factor = engine.calculate_factor('1 / PE')

# 3. 运行回测
backtest = BacktestEngine(returns, suspend, delist)
results = backtest.run_backtest(factor, rebalance_freq='M')

# 4. 绩效分析
analyzer = PerformanceAnalyzer()
report = analyzer.generate_report(results, factor, returns)
analyzer.print_report(report, 'EP')

# 5. 可视化
visualizer = Visualizer()
visualizer.generate_all_plots(results, report, 'EP')
```

## 自定义数据接入

如果要使用真实股票数据，可以按照以下格式准备CSV文件：

1. **价格数据** (`price_data.csv`):
   - 索引: 日期
   - 列名: 股票代码
   - 值: 收盘价

2. **因子数据** (`factor_*.csv`):
   - 索引: 日期
   - 列名: 股票代码
   - 值: 因子值

3. **停牌数据** (`suspend_data.csv`):
   - 索引: 日期
   - 列名: 股票代码
   - 值: True/False（是否停牌）

4. **退市数据** (`delist_data.csv`):
   - 索引: 股票代码
   - 值: 退市日期

5. **行业数据** (`industry_data.csv`):
   - 索引: 股票代码
   - 值: 行业名称

## 注意事项

1. 本平台内置模拟数据用于演示，使用真实数据时请替换CSV文件
2. 因子表达式解析使用eval，生产环境请添加安全检查
3. 回测结果仅供参考，不构成投资建议

## License

MIT License
