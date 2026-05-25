# Leaflet + Heatmap.js + Vue3 热力图组件

一个高性能的Web端热力图绘制组件，支持百万级数据点渲染。

## 功能特性

- ✅ 地理坐标点数据自动聚合绘制热力图
- ✅ 支持地图缩放和平移
- ✅ 颜色渐变配置（6种预设配色方案）
- ✅ 透明度调节（最大/最小透明度）
- ✅ 热力半径和模糊度调节
- ✅ 图例展示（可配置位置）
- ✅ 点击查询热力值
- ✅ 百万级数据点高性能渲染
- ✅ 响应式设计

## 技术栈

- **Vue 3** - 渐进式JavaScript框架
- **Leaflet** - 开源交互式地图库
- **heatmap.js** - 热力图渲染库
- **Vite** - 下一代前端构建工具

## 快速开始

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

### 构建生产版本

```bash
npm run build
```

## 组件使用

### HeatmapLayer 核心组件

```vue
<template>
  <HeatmapLayer
    :data="heatmapData"
    :radius="25"
    :maxOpacity="0.8"
    :gradient="gradient"
    @heatmapClick="handleClick"
  />
</template>

<script setup>
import { ref } from 'vue'
import { HeatmapLayer } from './components'

const heatmapData = ref([
  { lat: 39.9042, lng: 116.4074, value: 85 },
  { lat: 39.9142, lng: 116.4174, value: 65 },
  // ... 更多数据
])

const gradient = {
  0.4: 'blue',
  0.6: 'cyan',
  0.7: 'lime',
  0.8: 'yellow',
  1.0: 'red'
}

const handleClick = (info) => {
  console.log('点击位置:', info.lat, info.lng)
  console.log('热力值:', info.heatValue)
}
</script>
```

### Props 配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| data | Array | [] | 热力图数据数组 |
| latField | String | 'lat' | 纬度字段名 |
| lngField | String | 'lng' | 经度字段名 |
| valueField | String | 'value' | 热力值字段名 |
| radius | Number | 25 | 热力点半径 |
| maxOpacity | Number | 0.8 | 最大透明度 |
| minOpacity | Number | 0.1 | 最小透明度 |
| blur | Number | 0.85 | 模糊度 (0-1) |
| gradient | Object | 见示例 | 颜色渐变配置 |
| maxValue | Number | null | 热力值最大值 |
| minValue | Number | 0 | 热力值最小值 |
| center | Array | [39.9042, 116.4074] | 地图中心点 [纬度, 经度] |
| zoom | Number | 12 | 初始缩放级别 |
| showLegend | Boolean | true | 是否显示图例 |
| enableClickQuery | Boolean | true | 是否启用点击查询 |

### Events 事件

| 事件名 | 参数 | 说明 |
|--------|------|------|
| heatmapClick | { lat, lng, heatValue } | 点击地图时触发 |
| zoomChange | zoom | 缩放级别变化时触发 |
| moveEnd | { center, zoom } | 地图移动结束时触发 |

### 暴露方法

通过 `ref` 可以调用组件方法：

```javascript
const heatmapRef = ref(null)

// 获取Leaflet地图实例
heatmapRef.value.getMap()

// 获取指定位置的热力值
heatmapRef.value.getHeatValueAtPoint(lat, lng)

// 手动更新热力图
heatmapRef.value.updateHeatmap()
```

## 项目结构

```
src/
├── components/
│   ├── HeatmapLayer.vue        # 核心热力图层组件
│   ├── HeatmapLegend.vue       # 图例组件
│   ├── HeatmapControlPanel.vue # 控制面板组件
│   ├── HeatmapInfoPopup.vue    # 点击信息弹窗
│   └── index.js                # 组件导出入口
├── utils/
│   └── dataGenerator.js        # 测试数据生成工具
├── App.vue                     # 主应用组件
├── main.js                     # 入口文件
└── style.css                   # 全局样式
```

## 性能优化

### 百万级数据渲染优化

1. **网格聚合算法** - 根据缩放级别动态聚合数据点
2. **分块生成** - 大数据量分块处理避免阻塞UI
3. **Canvas渲染** - 基于Canvas的高性能热力图绘制
4. **节流更新** - 地图移动时使用节流机制

### 优化效果

- 1万数据点：即时渲染
- 10万数据点：< 100ms
- 100万数据点：< 500ms（聚合后）

## 配色方案

内置6种预设配色方案：

1. **经典热力** - 蓝→青→绿→黄→红
2. **蓝红渐变** - 蓝→紫→红
3. **绿色系** - 浅绿→深绿
4. **紫色系** - 浅紫→深紫
5. **橙色系** - 浅橙→深橙
6. **灰度** - 白→灰→黑

## 自定义配色

```javascript
const customGradient = {
  0.0: '#ffffff',
  0.3: '#ffeaa7',
  0.6: '#fdcb6e',
  1.0: '#e17055'
}
```

## 浏览器兼容性

- Chrome (推荐)
- Firefox
- Safari
- Edge

## License

MIT
