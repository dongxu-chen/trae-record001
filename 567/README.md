# 照片地理标记工具

一个Web端照片地理标记工具，支持批量为照片添加GPS信息。

## 功能特性

- 📸 **批量照片导入** - 支持拖放上传，自动解析EXIF信息
- 🗺️ **GPX轨迹导入** - 解析GPX文件，在地图上显示轨迹
- 🔗 **智能匹配** - 根据拍摄时间自动匹配照片位置
- ⚙️ **时间校正** - 支持时间偏移调整和自动计算
- 🎯 **手动调整** - 点击地图手动设置照片位置
- 📤 **多格式导出** - 支持JPEG、GPX、KML、CSV格式导出

## 技术栈

- **前端**: React 18 + TypeScript + Vite
- **地图**: Leaflet + React-Leaflet
- **状态管理**: Zustand
- **样式**: TailwindCSS
- **图标**: Lucide React
- **EXIF处理**: exif-js + piexifjs
- **GPX解析**: @tmcw/togeojson
- **后端**: Express + TypeScript

## 快速开始

### 安装依赖

```bash
npm run install:all
```

### 开发模式

```bash
npm run dev
```

前端运行在 http://localhost:3000
后端运行在 http://localhost:3001

### 构建生产版本

```bash
npm run build
```

## 使用说明

1. **导入照片** - 将照片拖放到左侧面板或点击上传
2. **导入轨迹** - 将GPX文件拖放到右侧面板或点击上传
3. **匹配设置** - 调整时间偏移和最大时间差
4. **开始匹配** - 点击"开始匹配"按钮自动匹配
5. **手动调整** - 选中照片后点击地图可手动设置位置
6. **导出结果** - 点击右下角导出按钮选择导出格式

## 项目结构

```
project/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Map/          # 地图组件
│   │   │   ├── PhotoPanel/   # 照片面板
│   │   │   ├── TrackPanel/   # 轨迹面板
│   │   │   └── ExportPanel/  # 导出面板
│   │   ├── utils/            # 工具函数
│   │   ├── types/            # 类型定义
│   │   ├── store/            # 状态管理
│   │   └── App.tsx
│   └── package.json
└── backend/
    ├── src/
    │   └── index.ts
    └── package.json
```
