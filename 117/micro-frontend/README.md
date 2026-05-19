# 🎯 仪表盘微前端架构 (Web Components)

基于 Web Components 构建的下一代数据可视化仪表盘微前端方案。

## ✨ 核心特性

### 1. 📦 独立封装的 Web Components
每个图表都是独立的自定义元素，支持独立发布和版本管理

| 组件 | 标签 | 功能 |
|------|------|------|
| 折线图 | `<line-chart>` | ECharts 折线图封装 |
| 柱状图 | `<bar-chart>` | ECharts 柱状图封装 |
| 饼图 | `<pie-chart>` | ECharts 饼图封装 |

### 2. 📡 postMessage 跨组件通信
- 基于 `window.postMessage` 的消息总线
- 支持点对点消息发送
- 支持全局广播
- 自动处理图表间联动刷新

### 3. 🛠️ 完整的 SDK 支持
- 统一的 SDK 入口
- 支持动态创建图表
- 事件订阅/发布机制
- 配置导入/导出
- 主题管理

### 4. 🌐 框架无关嵌入
- ✅ React
- ✅ Vue
- ✅ Angular
- ✅ Svelte
- ✅ 原生 JavaScript
- ✅ 任何支持 HTML 的环境

## 🚀 快速开始

### 安装

```bash
npm install dashboard-micro-frontend
# 或者
yarn add dashboard-micro-frontend
```

### 原生 HTML 使用

```html
<!DOCTYPE html>
<html>
<body>
  <line-chart title="销售趋势" height="300px" smooth></line-chart>
  
  <script type="module">
    import 'dashboard-micro-frontend';
    
    // 所有图表已自动注册
    document.querySelector('line-chart').addEventListener('chart-click', (e) => {
      console.log('图表被点击:', e.detail);
    });
  </script>
</body>
</html>
```

### SDK 使用方式

```javascript
import { createDashboardSDK } from 'dashboard-micro-frontend';

const sdk = createDashboardSDK();

// 创建图表
const lineChart = sdk.createLineChart('#container', {
  title: '实时数据',
  theme: 'dark',
  smooth: true
});

// 事件监听
sdk.on('chart-click', (payload) => {
  console.log('点击事件:', payload);
});

// 全局控制
sdk.setGlobalTheme('dark');
sdk.refreshAll();
```

## 📖 API 文档

### 图表公共属性

| 属性 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `title` | String | 图表标题 | '图表' |
| `theme` | String | 主题：'light' / 'dark' | 'light' |
| `width` | String | 宽度 | '100%' |
| `height` | String | 高度 | '400px' |
| `enable-link` | Boolean | 启用点击联动 | false |
| `link-targets` | String | 联动目标 ID（逗号分隔或 'all'） | '' |

### LineChart 特有属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `smooth` | Boolean | 启用平滑曲线 |
| `show-legend` | Boolean | 显示图例 |

### BarChart 特有属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `horizontal` | Boolean | 水平柱状图 |
| `stacked` | Boolean | 堆叠柱状图 |

### PieChart 特有属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `doughnut` | Boolean | 环形图 |
| `rose-type` | String | 南丁格尔图模式 |

### DashboardSDK API

#### 图表管理

```javascript
// 创建图表
sdk.createLineChart(container, config);
sdk.createBarChart(container, config);
sdk.createPieChart(container, config);

// 图表查询
sdk.getChartById(id);
sdk.getAllCharts();
sdk.getChartsByType('line');
```

#### 全局操作

```javascript
// 刷新
sdk.refreshAll();
sdk.refreshById(id);

// 主题
sdk.setGlobalTheme('dark');

// 数据
sdk.setChartData(id, data);
sdk.setAllChartData(dataMap);
```

#### 消息通信

```javascript
// 事件监听
const unsubscribe = sdk.on('chart-click', (payload) => {
  console.log(payload);
});

// 取消监听
unsubscribe();
// 或
sdk.off('chart-click');

// 发送消息
sdk.send(targetId, 'update-data', { ... });
sdk.broadcast('refresh-chart', { ... });
```

#### 配置管理

```javascript
// 导出配置
sdk.exportConfig(); // 下载 JSON 文件

// 导入配置
sdk.importConfig(config);

// 销毁
sdk.destroy();
```

## 🧩 微前端架构说明

### 架构图

```
┌─────────────────────────────────────────────────────────┐
│                      宿主应用 (任意框架)                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐     ┌──────────────┐    ┌─────────┐ │
│  │ LineChart    │     │ BarChart     │    │ PieChart│ │
│  │ WebComponent │     │ WebComponent │    │  ...    │ │
│  └──────────────┘     └──────────────┘    └─────────┘ │
│         │                    │                 │       │
│         └──────────┬─────────┴─────────────────┘       │
│                    │                                     │
│           ┌────────▼─────────┐                          │
│           │  MessageBus      │ ←─ postMessage ─►        │
│           │  (消息总线)       │                          │
│           └──────────────────┘                          │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                    DashboardSDK                          │
│                 (统一入口封装)                           │
└─────────────────────────────────────────────────────────┘
```

### 通信机制

1. **消息格式**
   ```javascript
   {
     type: 'refresh-chart',      // 消息类型
     payload: { ... },           // 数据载荷
     targetId: 'chart-id' | 'all', // 目标图表
     timestamp: 1234567890,      // 时间戳
     sourceId: 'source-chart-id'  // 发送方ID
   }
   ```

2. **内置消息类型**
   - `refresh-chart`: 刷新图表
   - `update-data`: 更新图表数据
   - `update-theme`: 更新主题
   - `update-options`: 更新配置
   - `chart-click`: 图表被点击
   - `data-updated`: 数据已更新

## 📦 独立发布与版本管理

### 每个组件独立发布

```bash
# 发布折线图
npm publish --workspace=packages/line-chart

# 发布柱状图
npm publish --workspace=packages/bar-chart

# 发布饼图
npm publish --workspace=packages/pie-chart

# 发布完整SDK
npm publish --workspace=packages/sdk
```

### 版本管理策略

- 采用语义化版本 (SemVer)
- 核心基础库独立版本
- 每个图表组件独立版本号
- SDK 聚合所有组件并统一版本

## 🌐 在各框架中使用

### React

```jsx
import { useEffect, useRef } from 'react';
import { createDashboardSDK } from 'dashboard-micro-frontend';

function Dashboard() {
  const containerRef = useRef(null);
  const sdkRef = useRef(null);

  useEffect(() => {
    sdkRef.current = createDashboardSDK();
    sdkRef.current.createLineChart(containerRef.current, {
      title: '销售数据'
    });

    return () => sdkRef.current.destroy();
  }, []);

  return <div ref={containerRef} />;
}
```

### Vue 3

```vue
<template>
  <div ref="container"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { createDashboardSDK } from 'dashboard-micro-frontend';

const container = ref(null);
let sdk;

onMounted(() => {
  sdk = createDashboardSDK();
  sdk.createLineChart(container.value, { title: 'Vue3图表' });
});

onUnmounted(() => {
  sdk?.destroy();
});
</script>
```

### Angular

```typescript
import { Component, ElementRef, OnInit, OnDestroy } from '@angular/core';
import { DashboardSDK } from 'dashboard-micro-frontend';

@Component({ selector: 'app-dashboard', template: '<div #container></div>' })
export class DashboardComponent implements OnInit, OnDestroy {
  private sdk: DashboardSDK;
  
  constructor(private el: ElementRef) {}
  
  ngOnInit() {
    this.sdk = new DashboardSDK();
    this.sdk.createLineChart(this.el.nativeElement, { title: 'Angular图表' });
  }
  
  ngOnDestroy() {
    this.sdk.destroy();
  }
}
```

## 🔧 开发指南

### 本地开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 构建单独组件
npm run build:components
```

### 目录结构

```
micro-frontend/
├── src/
│   ├── core/
│   │   ├── BaseChart.js      # 基类组件
│   │   └── MessageBus.js     # 消息总线
│   ├── components/
│   │   ├── LineChart.js      # 折线图
│   │   ├── BarChart.js       # 柱状图
│   │   └── PieChart.js       # 饼图
│   └── sdk/
│       └── index.js           # SDK入口
├── examples/
│   ├── vanilla-js/            # 原生JS示例
│   ├── react-demo/           # React示例
│   └── vue-demo/             # Vue示例
├── dist/                      # 构建输出
├── package.json
├── vite.config.js
└── index.html                # 主演示页面
```

## 📋 浏览器兼容性

| Chrome | Firefox | Safari | Edge |
|--------|---------|--------|------|
| ✅ 54+ | ✅ 63+ | ✅ 10.1+ | ✅ 79+ |

需要支持的特性：
- Web Components (Custom Elements)
- Shadow DOM
- ES Modules
- ResizeObserver

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingChart`)
3. 提交更改 (`git commit -m 'Add some AmazingChart'`)
4. 推送到分支 (`git push origin feature/AmazingChart`)
5. 开启 Pull Request

## 📄 许可证

MIT License - 详见 LICENSE 文件

---

**🌟 如果这个项目对你有帮助，请给个 Star 支持一下！**
