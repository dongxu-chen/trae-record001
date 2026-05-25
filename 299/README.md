# 空气质量数值预报可视化系统

基于 Python + xarray + Flask + OpenLayers + WebGL 实现的空气质量数值预报可视化系统。

## 功能特性

- 🗺️ **AQI色斑图**：WebGL 加速渲染，支持色阶插值
- 📊 **等值线叠加**：Marching Squares 算法生成等值线
- 💨 **风矢量场**：粒子动画效果展示风向风速
- ⏱️ **时间滑动条**：72小时逐时预报，支持播放/暂停
- 📍 **格点详情**：点击格点显示6项污染物浓度
- 🎨 **图层控制**：图层显隐切换、透明度调节

## 技术栈

### 后端
- **Python 3.9+**
- **Flask**：Web 服务框架
- **xarray + netCDF4**：多维格点数据处理
- **numpy**：数值计算、AQI 换算

### 前端
- **OpenLayers 7+**：地图渲染引擎
- **WebGL**：色斑图硬件加速渲染
- **原生 JavaScript**：轻量无框架依赖
- **Canvas 2D**：风场粒子动画

## 快速开始

### 1. 安装依赖

```bash
pip install -r backend/requirements.txt
```

### 2. 生成模拟数据（可选）

```bash
python data/mock/generate_mock.py
```

如果没有真实的 NetCDF 数据，系统会自动使用内置模拟数据。

### 3. 启动服务

```bash
cd backend
python app.py
```

或者直接运行批处理文件：
```bash
run_server.bat
```

### 4. 访问系统

在浏览器中打开：http://localhost:5000

## 使用说明

### 时间控制
- **播放按钮**：自动播放预报时序动画
- **前进/后退**：逐时切换预报时次
- **滑动条**：拖动到任意预报时刻
- **速度选择**：0.5x / 1x / 2x / 4x 播放速度

### 图层控制
- **AQI色斑图**：空气质量指数空间分布
- **等值线**：AQI 数值等值线
- **风矢量场**：风场粒子动画
- **透明度**：调节叠加图层的透明度

### 格点查询
- 鼠标移动到数据区域时光标变为指针
- 点击任意格点查看污染物详细浓度

## 数据格式

### 输入数据格式
系统支持标准 NetCDF 格式的格点预报数据，变量包括：
- `PM25`: PM2.5 浓度 (μg/m³)
- `PM10`: PM10 浓度 (μg/m³)
- `O3`: 臭氧浓度 (μg/m³)
- `NO2`: 二氧化氮浓度 (μg/m³)
- `SO2`: 二氧化硫浓度 (μg/m³)
- `CO`: 一氧化碳浓度 (mg/m³)
- `u_wind`: 纬向风速 (m/s)
- `v_wind`: 经向风速 (m/s)

### AQI 分级标准

| AQI 范围 | 等级 | 颜色 |
|---------|------|------|
| 0-50 | 优 | #00E400 |
| 51-100 | 良 | #FFFF00 |
| 101-150 | 轻度污染 | #FF7E00 |
| 151-200 | 中度污染 | #FF0000 |
| 201-300 | 重度污染 | #99004C |
| 301-500 | 严重污染 | #7E0023 |

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 主页面 |
| `/api/metadata` | GET | 获取数据元信息 |
| `/api/aqi/<time_idx>` | GET | 获取指定时次 AQI 数据 |
| `/api/pollutants/<time_idx>/<lat>/<lon>` | GET | 获取格点污染物详情 |
| `/api/wind/<time_idx>` | GET | 获取风场数据 |
| `/api/contour/<time_idx>` | GET | 获取等值线数据 |

## 项目结构

```
aqi-forecast-viz/
├── backend/
│   ├── app.py              # Flask 主应用
│   ├── config.py           # 配置文件
│   ├── data_service.py     # 数据服务
│   ├── aqi_calculator.py   # AQI 计算
│   └── requirements.txt    # Python 依赖
├── data/
│   └── mock/
│       └── generate_mock.py # 模拟数据生成
├── static/
│   ├── css/
│   │   └── main.css        # 主样式
│   └── js/
│       ├── main.js         # 入口脚本
│       ├── map.js          # 地图初始化
│       ├── webgl_renderer.js # WebGL 渲染
│       ├── time_controller.js # 时间控制
│       ├── contour_layer.js # 等值线图层
│       └── popup.js        # 弹窗组件
├── templates/
│   └── index.html          # 主页面模板
└── run_server.bat          # 启动脚本
```

## 性能优化说明

### 1. 对数色标映射

为均衡各 AQI 等级的视觉差异，采用对数色标映射替代线性映射：
```
normalized_value = log(aqi + 1) / log(501)
```
使优、良、轻度污染、中度污染、重度污染、严重污染各等级在色标上占据更均衡的视觉空间。

### 2. 风矢量自适应采样

采用梯度敏感的四叉树自适应采样策略：
- 计算风场的梯度、切变和涡度作为特征强度指标
- 高梯度区域（如锋面、切变线）采样密度提高 2-4 倍
- 粒子总数动态控制在 500-2000 范围内
- 粒子生命周期与所在区域梯度强度关联

### 3. 瓦片缓存系统

实现 XYZ 标准瓦片预生成与缓存：
- **瓦片规格**：256x256 PNG，Zoom 4-10
- **缓存策略**：内存缓存（500张热点瓦片）+ 磁盘缓存
- **预生成**：支持后台预生成前 24 小时预报瓦片
- **按需生成**：后续时次首次访问时生成并缓存
- **浏览器缓存**：HTTP Cache-Control 头控制客户端缓存

## 浏览器兼容性

- Chrome 60+
- Firefox 55+
- Edge 79+
- Safari 12+

需要支持 WebGL 1.0 或更高版本。
