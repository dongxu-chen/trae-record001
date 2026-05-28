# 电影推荐与票房预测系统

结合用户画像和电影特征，使用协同过滤和LightGBM实现个性化电影推荐与票房预测。

## 功能特性

### 1. 个性化电影推荐
- **协同过滤算法**: 支持基于用户、基于物品和混合推荐
- **上下文特征融合**: 结合用户画像（年龄、性别、职业、类型偏好）
- **推荐列表**: 输出Top-N推荐电影及预测评分

### 2. 票房预测
- **LightGBM模型**: 梯度提升树回归预测
- **多维度特征**: 预算、导演、演员、类型、上映时间等
- **置信区间**: 输出预测区间（支持80%/90%/95%置信度）

### 3. 用户观影偏好分析
- **类型偏好统计**: 各类型观看数量与平均评分
- **导演/演员偏好**: 喜爱的导演和演员分析
- **评分分布**: 用户评分习惯分析
- **用户对比**: 多用户偏好相似度计算

## 项目结构

```
.
├── data_generator.py      # 模拟数据生成模块
├── recommender.py         # 协同过滤推荐模块
├── boxoffice_predictor.py # LightGBM票房预测模块
├── preference_analyzer.py # 用户偏好分析模块
├── main.py                # FastAPI主应用
├── test_system.py         # 系统测试脚本
├── requirements.txt       # 依赖包列表
├── data/                  # 数据文件目录
└── models/                # 模型保存目录
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行系统测试

```bash
python test_system.py
```

### 3. 启动FastAPI服务

```bash
python main.py
```

服务启动后访问:
- API文档: http://localhost:8000/docs
- 接口地址: http://localhost:8000

## API接口

### 推荐接口
```
GET /api/recommend/{user_id}?top_n=10&method=hybrid&include_boxoffice=true
```

### 票房预测接口
```
GET /api/boxoffice/predict/{movie_id}?confidence=0.9
```

### 用户偏好分析
```
GET /api/user/{user_id}/preferences
```

### 相似用户
```
GET /api/user/{user_id}/similar?top_n=5
```

### 相似电影
```
GET /api/movie/{movie_id}/similar?top_n=5
```

### 特征重要性
```
GET /api/boxoffice/feature-importance
```

## 技术栈

- **Python 3.8+**
- **FastAPI**: Web框架
- **LightGBM**: 梯度提升树
- **scikit-learn**: 机器学习工具
- **pandas/numpy**: 数据处理
- **SciPy**: 科学计算

## 算法说明

### 协同过滤推荐
1. 构建用户-物品评分矩阵
2. 计算余弦相似度（用户/物品维度）
3. K近邻加权预测评分
4. 融合用户画像特征进行调优

### 票房预测特征
- 基础特征: 预算、时长、上映年份
- 类型特征: 10种电影类型one-hot编码
- 人员特征: 导演、制片公司
- 上下文特征: 上映月份、节假日、营销投入、银幕数
- 衍生特征: 每分钟预算、上映周年数等

## 数据说明

系统包含模拟数据生成器，生成以下数据：
- 200部电影（含类型、导演、演员、预算等）
- 100位用户（含年龄、性别、职业、类型偏好）
- 6000条评分记录
- 对应票房数据

可通过 `POST /api/data/regenerate` 重新生成数据。
