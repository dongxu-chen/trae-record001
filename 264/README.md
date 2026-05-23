# 出租车OD需求预测可视化平台

基于 **Python + PyTorch + ECharts + Leaflet** 实现的出租车OD（起讫点）需求预测可视化系统。

## 功能特性

### 1. 时空特征提取
- **时间特征**: 小时、星期、节假日、高峰期识别
- **空间特征**: 网格位置、距离中心距离、边界识别
- **历史特征**: 均值、方差、趋势、分位数统计

### 2. 多任务学习模型
- 基于PyTorch实现的神经网络
- 同时预测所有起点的OD需求量
- 空间注意力机制 + 共享特征层
- 多任务头分别预测各起点的目的地分布

### 3. 动态需求变化趋势
- 24小时需求趋势预测
- 实时播放功能
- 峰值/谷值自动识别

### 4. 可视化展示
- **OD矩阵热力图**: ECharts实现，直观展示网格间流量
- **流向地图**: Leaflet地图，展示Top-K OD流向
- **分布柱状图**: 出发地/目的地需求分布
- **趋势折线图**: 24小时需求变化曲线

## 项目结构

```
├── backend/
│   ├── app.py              # Flask后端API
│   ├── config.py           # 配置文件
│   ├── data/
│   │   ├── data_generator.py   # 模拟数据生成
│   │   └── data_loader.py      # 数据加载器
│   ├── models/
│   │   ├── od_predictor.py     # 预测模型定义
│   │   └── model_trainer.py    # 模型训练器
│   └── utils/
│       └── feature_extractor.py # 时空特征提取
├── templates/
│   └── index.html          # 前端页面
├── static/
│   ├── css/style.css       # 样式文件
│   └── js/main.js          # 前端逻辑
├── run.py                  # 启动脚本
└── requirements.txt        # Python依赖
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python run.py
```

### 3. 访问平台

打开浏览器访问: `http://localhost:5000`

## 使用说明

### 控制面板
- **日期选择**: 切换不同日期的数据
- **时段滑块**: 选择具体小时(0-23)
- **模式切换**: 历史数据 / 预测数据
- **播放按钮**: 自动播放24小时趋势

### 图表说明

1. **OD矩阵热力图**
   - X轴: 目的地网格
   - Y轴: 出发地网格
   - 颜色深浅: 需求量大小

2. **流向地图**
   - 蓝色弧线: 低流量
   - 绿色弧线: 中流量
   - 红色弧线: 高流量

3. **需求趋势图**
   - 展示24小时总需求量变化
   - 自动标注峰值和谷值

4. **分布柱状图**
   - 左侧: 各网格出发需求
   - 右侧: 各网格到达需求

## 技术栈

### 后端
- **Flask**: Web框架
- **PyTorch**: 深度学习框架
- **NumPy/Pandas**: 数据处理

### 前端
- **ECharts**: 数据可视化
- **Leaflet**: 地图可视化(替代Mapbox开源方案)
- **原生JavaScript**: 交互逻辑

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/od_matrix` | GET | 获取历史OD矩阵 |
| `/api/pred_od_matrix` | GET | 获取预测OD矩阵 |
| `/api/flow_data` | GET | 获取流向数据 |
| `/api/trend` | GET | 获取24小时趋势 |
| `/api/grid_centers` | GET | 获取网格中心坐标 |

## 配置说明

在 `backend/config.py` 中可调整:
- `GRID_SIZE`: 网格划分数量
- `CITY_CENTER`: 城市中心坐标
- `CITY_RADIUS`: 城市半径
- `EPOCHS`: 训练轮数
- `LEARNING_RATE`: 学习率

## 注意事项

1. 首次运行会自动生成模拟数据和训练模型，需要等待几分钟
2. 使用Leaflet替代Mapbox，无需API Key即可使用地图功能
3. 数据基于上海市中心区域模拟生成
