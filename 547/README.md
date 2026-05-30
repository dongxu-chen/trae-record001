# 地形图等高线提取工具

一个基于React + Node.js 的Web端地形图等高线提取工具。

## 功能特性

- 🗻 从DEM高程数据提取等高线
- 📊 支持多种DEM数据格式（ASC, DEM, GeoJSON等
- ⚙️ 可配置等高距设置
- 🔄 等高线平滑处理
- 🏷️ 高程标注生成
- 🗺️ 基于Leaflet的交互式地图展示
- 🎨 高程色彩图例

## 技术栈

### 后端
- Node.js + Express
- 等高线算法: Marching Squares
- 平滑处理: Chaikin算法

### 前端
- React 18
- Leaflet + React-Leaflet
- Turf.js

## 项目结构

```
.
├── backend/                 # 后端服务
│   ├── server.js       # 服务器入口
│   ├── services/
│   │   └── contourService.js  # 等高线处理服务
│   ├── package.json
│   └── uploads/       # 临时上传目录
│
└── frontend/             # 前端应用
    ├── src/
    │   ├── App.js     # 主应用组件
    │   ├── components/
    │   │   ├── MapComponent.js    # 地图组件
    │   │   ├── ControlPanel.js      # 控制面板
    │   │   └── Legend.js          # 图例组件
    │   └── index.css
    │   └── index.js
    ├── public/
    └── package.json
```

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
npm install
```

### 2. 启动后端服务

```bash
cd backend
npm start
```

后端服务将运行在 http://localhost:3001

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 启动前端应用

```bash
cd frontend
npm start
```

前端应用将运行在 http://localhost:3000

## 使用说明

1. **加载示例数据：点击"加载示例数据"按钮查看演示
2. **上传DEM文件**：支持 ASC, DEM, GeoJSON 格式
3. **调整参数**：
   - 等高距：控制等高线密度
   - 平滑程度：优化等高线外观
   - 高程标注：显示高程数值
4. **生成等高线**：点击"生成等高线"按钮
5. **查看结果**：在地图上查看生成的矢量等高线

## API接口

### 健康检查
```
GET /api/health
```

### 获取示例等高线
```
POST /api/sample-data
Content-Type: application/json

{
  "interval": 50,
  "smoothing": 1,
  "enableLabels": true,
  "labelInterval": 5
}
```

### 上传DEM并生成等高线
```
POST /api/generate-contours
Content-Type: multipart/form-data

demFile: DEM文件
interval: 等高距
smoothing: 平滑程度
enableLabels: 是否启用标注
labelInterval: 标注间隔
```

## 核心算法说明

### Marching Squares算法
- 用于从栅格DEM数据中提取等值线
- 基于网格单元（2x2像素)
- 16种可能的等值线穿越模式

### 平滑处理
- 支持多级平滑
- Chaikin切割算法
- 保留地形特征的同时优化线条外观

## 许可证

MIT
