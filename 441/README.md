# 时间序列异常检测平台

基于 Prophet + 3-Sigma + 孤立森林的多指标联合异常检测系统

## 功能特性

### 检测指标
- **QPS (每秒查询率)**: 检测流量突增/突降
- **延迟 (Latency)**: 检测响应时间异常
- **错误率 (Error Rate)**: 检测错误率异常

### 检测算法
1. **Prophet**: Facebook开源的时间序列预测算法，擅长处理周期性数据
2. **3-Sigma**: 基于统计的异常检测，识别偏离均值3倍标准差的数据点
3. **孤立森林 (Isolation Forest)**: 基于树模型的异常检测算法，适合高维数据

### 高级功能
- **多指标联合检测**: 支持多个指标同时异常的联合检测
- **异常融合**: 加权融合三种算法的检测结果
- **根因分析**: 自动分析异常可能的原因
- **周期性破坏检测**: 检测时间序列的周期性模式变化

## 项目结构

```
.
├── app.py                      # Flask API服务
├── config.py                   # 配置文件
├── data_generator.py           # 数据生成模块
├── prophet_detector.py         # Prophet异常检测
├── three_sigma_detector.py     # 3-Sigma异常检测
├── isolation_forest_detector.py # 孤立森林异常检测
├── anomaly_fusion.py           # 异常融合模块
├── root_cause_analyzer.py      # 根因分析模块
├── es_storage.py               # Elasticsearch存储模块
├── main.py                     # 主入口脚本
├── requirements.txt            # 依赖包列表
├── .env                        # 环境变量
└── templates/
    └── index.html             # 前端界面
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行演示

```bash
# 命令行演示模式
python main.py --mode demo

# 启动Web服务
python main.py --mode server
# 或
python app.py
```

### 3. 访问界面

打开浏览器访问: `http://localhost:5000`

## API接口

### 数据管理
- `POST /api/generate-data` - 生成测试数据
- `GET /api/metrics` - 获取指标数据

### 异常检测
- `POST /api/detect/prophet` - Prophet算法检测
- `POST /api/detect/three-sigma` - 3-Sigma算法检测
- `POST /api/detect/isolation-forest` - 孤立森林检测
- `POST /api/detect/fusion` - 异常融合检测
- `POST /api/detect/full` - 完整检测(含根因分析)
- `POST /api/detect/joint` - 多指标联合检测

### 查询接口
- `GET /api/anomalies` - 查询异常记录
- `GET /api/anomaly/summary` - 异常统计摘要
- `POST /api/root-cause` - 根因分析
- `GET /api/time-series` - 获取带异常标记的时间序列

## 配置说明

在 `.env` 文件中配置以下参数:

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `THREE_SIGMA_THRESHOLD` | 3-Sigma检测阈值 | 3.0 |
| `ISOLATION_FOREST_CONTAMINATION` | 孤立森林污染率 | 0.05 |
| `PROPHET_ANOMALY_THRESHOLD` | Prophet异常阈值 | 0.95 |
| `ES_HOST` | Elasticsearch主机 | localhost |
| `ES_PORT` | Elasticsearch端口 | 9200 |

## 算法原理

### Prophet
- 使用加法模型拟合时间序列
- 自动检测年度、周度、日度季节性
- 基于置信区间识别异常点

### 3-Sigma
- 假设数据服从正态分布
- 超出 `[μ-3σ, μ+3σ]` 范围的数据点标记为异常
- 支持滚动窗口计算

### 孤立森林
- 通过随机划分隔离异常点
- 异常点路径更短，更容易被隔离
- 适用于无监督学习场景

### 异常融合
- 加权融合三种算法的异常分数
- Prophet: 35%
- 3-Sigma: 30%
- 孤立森林: 35%

## 根因分析维度

1. **相关性分析**: 指标间的强相关性
2. **趋势变化**: 异常点前后的趋势变化
3. **历史对比**: 与历史同期数据的对比
4. **领域知识**: 基于业务规则的推断

## 注意事项

- 本平台内置内存回退存储，无需Elasticsearch也可运行
- 生产环境建议配置真实的Elasticsearch实例
- 建议使用Python 3.8+版本
