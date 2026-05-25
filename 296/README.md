# 📈 时间序列预测 AutoML 平台

一个端到端的时间序列预测自动化机器学习平台，支持数据清洗、特征工程、多模型训练和自动超参数优化。

## ✨ 功能特性

### 🔧 数据清洗
- **缺失值填充**：支持插值、前向填充、均值、中位数等方法
- **异常检测**：支持 自适应IQR（默认）、标准IQR、Z-score、Isolation Forest
  - *自适应IQR*: 根据数据偏度（Medcouple）自动调整阈值，适合非对称分布
- **异常处理**：支持插值、删除、盖帽处理

### ⚙️ 特征工程
- **时间特征**：年、月、日、星期、节假日、周期性编码
- **滞后特征**：支持 **自动季节性探测**（ACF分析）或自定义滞后阶数
  - *自动探测*: 自动识别序列季节性周期，智能生成滞后特征和滚动窗口
- **滚动统计**：均值、标准差、最大最小值、指数加权移动平均
- **特征标准化**：StandardScaler / MinMaxScaler

### 🤖 模型库
- **ARIMA**：经典统计模型
- **Prophet**：Facebook 开源模型，适合强季节性数据
- **XGBoost**：梯度提升树，适合复杂非线性关系
- **LSTM**：深度学习模型，适合长序列依赖

### 🎯 AutoML 优化
- **两阶段分层次搜索**（默认启用）
  - *阶段1*: 粗略搜索 - 大步长/离散值快速定位最优区域
  - *阶段2*: 精细搜索 - 在最优区域附近小范围精确搜索
  - 相比传统单阶段搜索，**收敛速度提升约30-50%**
- **Optuna 超参数优化**
- **时间序列交叉验证**
- **多模型自动对比**
- **最佳模型自动选择**

### 💬 用户反馈
- 支持输入实际观测值
- 基于反馈数据在线更新模型
- 持续学习优化

### 🔍 模型解释
- **特征重要性分析**：支持XGBoost、LSTM等模型的特征重要性
- **梯度重要性**：LSTM模型梯度分析
- **排列重要性**：通用模型解释方法
- **可视化展示**：Top-N特征柱状图

### 🤝 集成预测
- **多模型加权平均**：4种权重计算方法
  - *排名加权*：按模型性能排名分配权重
  - *等权重*：所有模型权重相同
  - *得分倒数*：按RMSE倒数加权
  - *优化权重*：基于验证集最优权重
- **预测对比可视化**：多模型预测结果对比图
- **稳定性提升**：集成预测降低方差，提升鲁棒性

### 🏆 时序预测竞赛
- **排行榜系统**：实时排名展示
- **多指标评估**：RMSE、MAE、MAPE
- **团队提交**：支持团队名称和模型描述
- **竞赛统计**：参赛数、最佳成绩、平均水平
- **提交历史**：跟踪各团队最佳成绩

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动平台

```bash
streamlit run app.py
```

### 3. 使用流程

1. **上传数据**：在左侧边栏上传 CSV 文件，或勾选"使用示例数据"
2. **数据清洗**：选择缺失值填充和异常检测方法，执行数据清洗
3. **特征工程**：配置时间特征、滞后特征等，执行特征工程
4. **AutoML 训练**：选择模型类型、优化指标和试验次数，开始训练
5. **查看结果**：查看模型对比、最佳模型参数和预测结果
6. **用户反馈**：输入实际观测值，更新模型

## 📁 项目结构

```
.
├── app.py                    # Streamlit 前端应用
├── requirements.txt          # 依赖包列表
├── README.md                 # 项目说明文档
└── src/                      # 源代码目录
    ├── __init__.py          # 包初始化文件
    ├── data_cleaning.py     # 数据清洗模块
    ├── feature_engineering.py  # 特征工程模块
    ├── models.py            # 预测模型模块
    └── automl.py            # AutoML 优化器模块
```

## 📊 数据格式要求

- 文件格式：CSV
- 必须包含：日期时间列 + 数值列
- 示例：

| date       | value |
|------------|-------|
| 2023-01-01 | 100.5 |
| 2023-01-02 | 102.3 |
| 2023-01-03 | 98.7  |

## 🎛️ 模块说明

### DataCleaner
数据清洗类，提供缺失值填充和异常检测功能。

```python
from src.data_cleaning import DataCleaner

cleaner = DataCleaner()
cleaned_data, report = cleaner.clean_data(
    df,
    fill_method='interpolate',
    anomaly_method='isolation_forest',
    anomaly_strategy='interpolate'
)
```

### TimeSeriesFeatureEngineer
特征工程类，自动生成时间特征和滞后特征。

```python
from src.feature_engineering import TimeSeriesFeatureEngineer

engineer = TimeSeriesFeatureEngineer()
engineered_data, report = engineer.engineer_features(
    df,
    target_col='value',
    create_time=True,
    create_lag=True
)
```

### TimeSeriesAutoML
AutoML 优化器，自动进行模型选择和超参数优化。

```python
from src.automl import TimeSeriesAutoML

automl = TimeSeriesAutoML(
    model_types=['arima', 'prophet', 'xgboost', 'lstm'],
    n_trials=10,
    metric='rmse'
)
automl.fit(y_train, X_train, forecast_horizon=7)
predictions = automl.predict(horizon=7)
```

## 📈 支持的评估指标

- **RMSE**：均方根误差
- **MAE**：平均绝对误差
- **MAPE**：平均绝对百分比误差

## 🔧 技术栈

- **前端**：Streamlit + Plotly
- **AutoML**：Optuna
- **时间序列**：sktime + Prophet
- **机器学习**：XGBoost + TensorFlow/Keras
- **数据处理**：Pandas + NumPy + Scikit-learn

## 💡 使用提示

1. **数据质量**：确保数据时间序列连续，没有大段缺失
2. **模型选择**：
   - 数据量小、趋势明显：ARIMA
   - 强季节性、节假日效应：Prophet
   - 复杂非线性关系：XGBoost
   - 大量数据、长序列依赖：LSTM
3. **试验次数**：n_trials 建议 10-30，越多效果越好但时间越长
4. **预测步长**：根据业务需求设置，建议不超过历史数据的 1/3

## 📝 版本历史

- v1.0.0：初始版本，支持四种模型和完整的 AutoML 流程

## 📄 许可证

MIT License
