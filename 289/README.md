# 城市公交车到站时间预测系统

基于 XGBoost + Kalman滤波 的智能公交车到站时间预测系统，使用 Python + Redis + WebSocket 实现。

## 功能特性

### 1. 实时到站预测
- 基于公交车GPS实时数据
- 结合路况信息
- 使用XGBoost机器学习模型
- Kalman滤波轨迹平滑
- 显示预计到达时间和置信度

### 2. 晚点预警
- 实时监控车辆运行状态
- 超过3分钟晚点自动预警
- 分等级显示预警严重程度
- 关联路况信息

### 3. 历史准点率分析
- 总班次统计
- 准点率计算
- 晚点班次统计
- 平均延误时间
- 各线路准点率对比

### 4. 路况信息展示
- 各路段拥堵等级
- 实时更新路况
- 影响到站时间预测

## 技术架构

### 预测算法
- **XGBoost**: 基于历史数据的机器学习预测模型
  - 特征：距离、路况、时段、星期、车速等
  - 目标：预测到站时间（秒）
  - 准确率：MAE约30-60秒

- **Kalman滤波**: 实时轨迹跟踪和预测
  - 状态：位置、速度、加速度
  - 测量：GPS数据
  - 输出：平滑轨迹和到达时间估计

- **混合预测**: 权重融合两种算法结果
  - XGBoost权重: 60%
  - Kalman权重: 40%

### 数据层
- **Redis**: 实时数据缓存
  - GPS数据（1小时过期）
  - 预测结果（5分钟过期）
  - 延误预警（有序集合）
  - 历史数据（列表）

### 通信层
- **WebSocket**: 实时数据推送
  - 服务器主动推送更新
  - 5秒更新间隔
  - 自动重连机制

### Web层
- **aiohttp**: HTTP服务器
- **原生JavaScript**: 前端交互
- **响应式设计**: 支持移动端

## 项目结构

```
bus-prediction-system/
├── main.py                 # 主入口文件
├── config.py               # 系统配置
├── requirements.txt        # 依赖包列表
├── README.md              # 项目文档
├── data/                   # 数据模块
│   ├── __init__.py
│   ├── data_models.py     # 数据模型定义
│   └── data_generator.py  # 模拟数据生成器
├── prediction/             # 预测模块
│   ├── __init__.py
│   ├── kalman_filter.py   # Kalman滤波器
│   ├── xgboost_predictor.py  # XGBoost预测器
│   └── hybrid_predictor.py   # 混合预测器
├── cache/                  # 缓存模块
│   ├── __init__.py
│   └── redis_cache.py     # Redis缓存实现
├── server/                 # 服务器模块
│   ├── __init__.py
│   ├── websocket_server.py   # WebSocket服务器
│   └── http_server.py     # HTTP服务器
├── static/                 # 静态文件
│   ├── index.html          # 主页面
│   ├── css/
│   │   └── style.css       # 样式文件
│   └── js/
│       └── app.js          # 前端逻辑
└── models/                 # 模型文件（自动生成）
    ├── bus_arrival_model.json
    └── scaler.pkl
```

## 安装和运行

### 环境要求
- Python 3.8+
- Redis 5.0+

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动Redis

确保Redis服务已启动：

```bash
redis-server
```

或修改 `config.py` 中的Redis配置。

### 运行系统

```bash
python main.py
```

### 访问系统

打开浏览器访问：
```
http://localhost:8080
```

## 配置说明

在 `config.py` 中可以配置：

```python
REDIS_HOST = 'localhost'      # Redis主机
REDIS_PORT = 6379             # Redis端口
WEBSOCKET_PORT = 8765         # WebSocket端口
HTTP_PORT = 8080              # HTTP端口
GPS_UPDATE_INTERVAL = 2       # GPS更新间隔（秒）
PREDICTION_INTERVAL = 5       # 预测更新间隔（秒）
DELAY_WARNING_THRESHOLD = 180 # 晚点预警阈值（秒）
```

### 公交线路配置

在 `Config.BUS_ROUTES` 中可以添加/修改公交线路：

```python
'101': {
    'name': '101路',
    'stations': [
        {'id': 'S001', 'name': '站点1', 'lat': 31.2304, 'lon': 121.4737, 'order': 1},
        # ... 更多站点
    ],
    'scheduled_interval': 15  # 发车间隔（分钟）
}
```

## 算法说明

### XGBoost特征工程

1. **route_encoded**: 线路编码（类别特征）
2. **current_station_idx**: 当前站点索引
3. **distance_to_next**: 到下一站距离（米）
4. **traffic_level**: 路况等级（0-3）
5. **hour**: 当前小时（0-23）
6. **day_of_week**: 星期几（0-6）
7. **speed**: 当前车速（km/h）
8. **dwell_time**: 停靠时间（秒）
9. **is_peak_hour**: 是否高峰时段
10. **distance_speed_ratio**: 距离速度比

### Kalman滤波状态向量

```
[纬度, 经度, 纬度速度, 经度速度, 纬度加速度, 经度加速度]
```

### 预测融合策略

```
最终预测 = Kalman估计 × 0.4 + XGBoost预测 × 0.6
```

## 扩展开发

### 添加真实数据源

修改 `data/data_generator.py` 中的 `DataGenerator` 类，替换为真实的：
- GPS数据接口
- 路况数据API
- 历史停靠记录数据库

### 模型优化

1. 收集真实历史数据
2. 调整XGBoost超参数
3. 增加更多特征（天气、节假日等）
4. 定期重新训练模型

### 功能扩展

- 增加地图可视化
- 实现用户订阅推送
- 添加数据导出功能
- 多语言支持

## License

MIT License
