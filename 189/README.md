# 城市空气质量预测系统

基于LSTM时序预测模型的城市空气质量预测系统，支持输入历史空气质量数据和气象数据，预测未来24小时各指标AQI，并提供健康建议。

## 功能特性

- **多污染物预测**: 支持PM2.5、PM10、SO2、NO2、O3等污染物浓度预测
- **AQI计算**: 按照国家标准自动计算空气质量指数
- **LSTM模型**: 基于多层LSTM的深度时序预测模型
- **健康建议**: 根据预测的AQI等级提供分时段健康建议
- **可视化报告**: 生成详细的24小时预测报告

## 项目结构

```
.
├── config.py                  # 配置文件
├── data_preprocessing.py      # 数据预处理模块
├── model.py                   # LSTM模型定义
├── health_advice.py           # 健康建议模块
├── predict.py                 # 预测主模块
├── generate_sample_data.py    # 示例数据生成
├── main.py                    # 程序入口
├── requirements.txt           # 依赖包
├── data/                      # 数据目录
├── models/                    # 模型保存目录
└── predictions/               # 预测结果目录
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 生成示例数据

```bash
python main.py --mode generate_data
```

### 2. 训练模型

```bash
python main.py --mode train --data_path data/air_quality_data.csv --model_path models/aqi_lstm.h5
```

### 3. 进行预测

```bash
python main.py --mode predict --data_path data/air_quality_data.csv --model_path models/aqi_lstm.h5
```

### 4. 完整流程（生成数据+训练+预测）

```bash
python main.py --mode full
```

## 数据格式

输入数据CSV文件应包含以下列：

| 列名 | 说明 | 单位 |
|------|------|------|
| timestamp | 时间戳 | YYYY-MM-DD HH:MM:SS |
| PM2.5 | 细颗粒物 | μg/m³ |
| PM10 | 可吸入颗粒物 | μg/m³ |
| SO2 | 二氧化硫 | μg/m³ |
| NO2 | 二氧化氮 | μg/m³ |
| O3 | 臭氧 | μg/m³ |
| WIND | 风速 | m/s |
| TEMP | 温度 | °C |
| HUM | 湿度 | % |

## AQI等级说明

| AQI范围 | 等级 | 颜色 | 健康影响 |
|---------|------|------|----------|
| 0-50 | 优 | 绿色 | 空气质量令人满意 |
| 51-100 | 良 | 黄色 | 空气质量可接受 |
| 101-150 | 轻度污染 | 橙色 | 易感人群症状加剧 |
| 151-200 | 中度污染 | 红色 | 影响健康人群 |
| 201-300 | 重度污染 | 紫色 | 心脏病肺病患者症状加剧 |
| 301-500 | 严重污染 | 褐红色 | 健康人群普遍出现症状 |

## 模型架构

- 输入层: (SEQUENCE_LENGTH, N_FEATURES)
- LSTM层: 3层，分别为128、64、32个单元
- Dropout层: 防止过拟合
- 全连接层: 64个单元
- 输出层: (PREDICTION_LENGTH, N_TARGETS)

## 配置参数

可在 `config.py` 中调整以下参数：

- `SEQUENCE_LENGTH`: 输入序列长度（默认24小时）
- `PREDICTION_LENGTH`: 预测长度（默认24小时）
- `BATCH_SIZE`: 批次大小
- `EPOCHS`: 训练轮数
- `LSTM_UNITS`: LSTM各层单元数
- `DROPOUT_RATE`: Dropout比率
