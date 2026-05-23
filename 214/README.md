# 🚚 货运路线规划可视化工具

基于 Leaflet + React + Node.js 实现的货运路线规划工具，调用高德地图API计算最优路线。

## ✨ 功能特性

- 📍 **起点/终点输入**：支持经纬度坐标输入，提供预设城市快捷选择
- 🔄 **途经点管理**：最多支持10个途经点，可拖拽调整顺序
- 🗺️ **地图可视化**：使用Leaflet地图展示路线，不同路段用不同颜色区分
- 📊 **里程计算**：自动计算总里程和各段里程，预计行驶时间
- ⏱️ **路线优化**：基于高德地图API的最优路线规划算法

## 🛠️ 技术栈

- **前端**：React 18 + React Leaflet + @hello-pangea/dnd (拖拽)
- **后端**：Node.js + Express + Axios
- **地图API**：高德地图 Web服务API
- **地图底图**：OpenStreetMap

## 📦 项目结构

```
freight-route-planner/
├── client/                 # 前端React应用
│   ├── src/
│   │   ├── components/
│   │   │   ├── RouteForm.js      # 路线输入表单
│   │   │   ├── MapView.js        # Leaflet地图组件
│   │   │   └── RouteSummary.js   # 路线摘要展示
│   │   ├── App.js                # 主应用组件
│   │   ├── App.css               # 样式文件
│   │   └── index.js              # 入口文件
│   └── package.json
├── server/                 # 后端Node.js服务
│   ├── server.js           # 主服务文件
│   ├── .env                # 环境变量配置
│   └── package.json
└── package.json            # 根目录配置
```

## 🚀 快速开始

### 1. 获取高德地图API Key

1. 访问 [高德开放平台](https://lbs.amap.com/) 注册账号
2. 创建应用，选择 **Web服务** 类型
3. 获取API Key

### 2. 配置API Key

编辑 `server/.env` 文件：

```env
PORT=5000
GAODE_API_KEY=your_actual_api_key_here
```

### 3. 安装依赖

在项目根目录执行：

```bash
npm run install:all
```

或者分别安装：

```bash
# 根目录
npm install

# 后端
cd server
npm install

# 前端
cd ../client
npm install
```

### 4. 启动应用

#### 方式一：同时启动前后端（推荐）

在项目根目录执行：

```bash
npm run dev
```

#### 方式二：分别启动

**启动后端服务：**
```bash
npm run server
# 或
cd server
npm run dev
```

**启动前端应用：**
```bash
npm run client
# 或
cd client
npm start
```

### 5. 访问应用

打开浏览器访问：`http://localhost:3000`

## 📖 使用说明

### 基本操作

1. **输入起点**：在左侧面板输入起点经度和纬度，或点击预设城市按钮快速选择
2. **输入终点**：同样方式输入终点坐标
3. **添加途经点**（可选）：点击「+ 添加途经点」按钮，最多添加10个
4. **调整顺序**：拖拽途经点左侧的 `⋮⋮` 图标调整访问顺序
5. **计算路线**：点击「计算最优路线」按钮
6. **查看结果**：地图上会显示路线，下方展示路线摘要信息

### 示例路线

点击「🚀 加载示例路线 (北京→南京→杭州→上海)」按钮可快速加载演示数据。

### 坐标格式说明

- **经度 (Lng)**：东经为正，西经为负，范围 -180 ~ 180
- **纬度 (Lat)**：北纬为正，南纬为负，范围 -90 ~ 90
- 示例：北京 (116.4074, 39.9042)

## 🔌 API 接口说明

### POST /api/route

计算最优路线。

**请求体：**
```json
{
  "origin": { "lng": 116.4074, "lat": 39.9042 },
  "destination": { "lng": 121.4737, "lat": 31.2304 },
  "waypoints": [
    { "lng": 118.7969, "lat": 32.0603 },
    { "lng": 120.1551, "lat": 30.2741 }
  ]
}
```

**响应：**
```json
{
  "success": true,
  "route": {
    "totalDistance": 1350000,
    "totalDuration": 48600,
    "pathCoordinates": [[39.9042, 116.4074], ...],
    "segments": [
      {
        "from": { "lng": 116.4074, "lat": 39.9042 },
        "to": { "lng": 118.7969, "lat": 32.0603 },
        "distance": 1020000,
        "duration": 36720
      },
      ...
    ],
    "origin": {...},
    "destination": {...},
    "waypoints": [...]
  }
}
```

### GET /api/health

健康检查接口。

## 🎨 功能亮点

### 1. 拖拽排序
使用 `@hello-pangea/dnd` 实现流畅的拖拽交互，调整途经点顺序后自动重新计算路线。

### 2. 智能缩放
地图会根据路线范围自动调整缩放级别和中心点，确保完整展示整条路线。

### 3. 彩色路段
不同路段使用不同颜色绘制，点击路线可查看该路段的里程和预计时间。

### 4. 自定义标记
起点（绿色）、终点（红色）、途经点（彩色数字）使用自定义标记，直观易识别。

### 5. 实时验证
表单输入实时验证，无效坐标会高亮显示，避免无效请求。

## ⚠️ 注意事项

1. **高德API配额**：免费版有每日调用次数限制，生产环境建议购买商业版
2. **坐标系统**：高德地图使用GCJ-02坐标系，确保输入的坐标与此一致
3. **网络连接**：后端服务需要能访问互联网以调用高德API
4. **CORS配置**：开发环境已配置代理，生产环境需正确配置CORS

## 🔧 常见问题

### Q: 地图不显示？
A: 检查网络连接，确保能访问 OpenStreetMap 瓦片服务。

### Q: 路线计算失败？
A: 1. 检查 `server/.env` 中的API Key是否正确
   2. 查看后端控制台输出的错误信息
   3. 确认坐标格式是否正确

### Q: 拖拽功能不工作？
A: 确保 `@hello-pangea/dnd` 依赖已正确安装，尝试重新安装依赖。

### Q: 如何修改端口？
A: 后端端口在 `server/.env` 中修改，前端端口修改 `client/package.json` 中的启动脚本。

## 📝 开发说明

### 添加新的预设城市

编辑 `client/src/components/RouteForm.js` 中的 `PRESET_LOCATIONS` 对象：

```javascript
const PRESET_LOCATIONS = {
  // ... 现有城市
  cityName: { name: '城市名', lng: 经度, lat: 纬度 },
};
```

### 修改路线规划策略

编辑 `server/server.js` 中API URL的 `strategy` 参数：

- `strategy=10`：速度优先（不走高速）
- `strategy=11`：费用优先
- `strategy=12`：距离优先
- `strategy=13`：躲避拥堵（实时路况）

## 📄 License

MIT License
