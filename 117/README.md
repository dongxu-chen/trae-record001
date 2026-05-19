# 动态仪表盘低代码平台

基于 React + Ant Design + ECharts + GridStack 构建的动态仪表盘低代码平台。

## ✨ 功能特性

### 1. 📊 图表拖拽布局
- 使用 GridStack 实现12列灵活网格布局
- 支持拖拽调整图表位置
- 支持拖拽调整图表大小
- 拖拽后自动紧凑排列
- 布局自动保存到 localStorage

### 2. 🔌 数据源配置
- **静态数据**：内置固定示例数据
- **Mock API**：模拟API请求，每次返回随机数据
- 可配置API地址

### 3. 🎨 图表类型切换
- 折线图 (Line Chart)
- 柱状图 (Bar Chart)
- 饼图 (Pie Chart)
- 点击图表右上角下拉菜单实时切换

### 4. 🔄 实时刷新（定时轮询）
- 手动刷新按钮
- 支持开启自动刷新
- 可配置刷新间隔（5-3600秒）
- 实时刷新使用Mock API数据

### 5. 📝 数据过滤器（JS脚本）
- 支持自定义JavaScript脚本过滤数据
- 内置脚本验证功能
- 支持数据聚合、筛选、转换等操作
- 脚本示例：
  ```javascript
  // 数据筛选
  return data.filter(item => item.value > 100);
  
  // 数据聚合
  return data.reduce((acc, item) => acc + item.value, 0);
  
  // 数据转换
  return data.map(item => ({ ...item, value: item.value * 2 }));
  ```

### 6. 🔗 组件间联动
- 点击图表可触发联动刷新
- 可配置联动目标图表（支持全部或指定）
- 启用联动的图表会显示"联动中"标签
- 点击后显示选中数据信息

### 7. 🎭 主题配置
- 浅色/深色主题切换
- 主题导出（JSON格式）
- 主题导入（JSON格式）
- ECharts图表支持深色主题
- 平滑的主题切换动画

### 8. 🖥️ 大屏全屏模式
- 一键进入/退出全屏模式
- 全屏下自动调整布局高度
- 支持ESC键退出
- 大屏幕展示效果更佳

## 📁 项目结构

```
├── src/
│   ├── components/
│   │   ├── ChartComponent.jsx    # 图表组件（ECharts封装 + 过滤器 + 联动）
│   │   ├── ConfigPanel.jsx       # 配置抽屉面板（数据源/联动/主题/过滤）
│   │   └── Dashboard.jsx         # 仪表盘主组件（GridStack布局 + 全屏 + 主题）
│   ├── utils/
│   │   └── mockData.js           # Mock数据生成工具
│   ├── App.jsx                    # 应用入口
│   ├── main.jsx                   # React入口
│   └── index.css                  # 全局样式
├── package.json
├── vite.config.js
├── index.html
└── README.md
```

## 🚀 安装运行

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 🛠️ 技术栈

- **React 18** - 前端框架
- **Vite** - 构建工具
- **Ant Design 5** - UI组件库
- **ECharts 5** - 数据可视化图表库
- **GridStack** - 拖拽网格布局
- **lodash** - 工具函数库

## 💡 使用说明

### 基础操作
1. **添加图表**：点击顶部"添加图表"按钮
2. **移动/调整**：拖拽标题栏移动，拖拽边缘调整大小
3. **切换类型**：点击图表左上角下拉菜单
4. **配置图表**：点击设置图标打开配置面板
5. **刷新数据**：点击刷新按钮或开启自动刷新
6. **删除图表**：点击红色删除按钮
7. **保存/加载布局**：点击对应按钮

### 数据过滤器
1. 在配置面板中开启"启用数据过滤"
2. 编写自定义JavaScript过滤脚本
3. 点击"验证脚本"按钮检查语法
4. 保存配置后数据会自动应用过滤

### 组件联动
1. 在配置面板中开启"启用点击联动"
2. 选择要联动刷新的目标图表（可多选或全部）
3. 点击图表区域即可触发联动刷新
4. 启用联动的图表会显示"联动中"蓝色标签

### 主题配置
1. 点击顶部"浅色/深色"按钮快速切换全局主题
2. 点击"导出主题"按钮导出当前所有配置为JSON文件
3. 点击"导入主题"按钮选择JSON文件恢复配置
4. 主题配置包含：图表位置、类型、过滤脚本、联动设置等

### 大屏模式
1. 点击顶部"大屏模式"按钮进入全屏
2. 按ESC键或点击"退出全屏"按钮退出
3. 全屏模式下会自动调整布局高度
4. 适合大屏幕数据展示场景

## 📋 默认图表配置

系统预置4个示例图表：

| 图表ID | 标题 | 类型 | 数据源 | 联动 |
|--------|------|------|--------|------|
| widget-1 | 销售趋势 | 折线图 | 静态 | 联动 widget-2, widget-3 |
| widget-2 | 月度对比 | 柱状图 | 静态 | 无 |
| widget-3 | 流量来源 | 饼图 | 静态 | 无 |
| widget-4 | 利润分析 | 折线图 | Mock API | 联动全部图表 |

## 🔧 高级功能

### 自定义过滤器示例
```javascript
// 只显示值大于500的数据
if (data.series) {
  data.series.forEach(series => {
    series.data = series.data.map(val => val > 500 ? val : 0);
  });
}
return data;
```

### 联动刷新机制
- 点击图表时触发 `onChartClick` 事件
- 根据配置的 `linkTargets` 筛选目标图表
- 更新 `refreshTriggers` 状态触发目标图表重绘
- 图表组件监听 `triggerRefresh` prop变化重新渲染

### 主题导出格式
```json
{
  "globalTheme": "light",
  "widgets": [
    {
      "id": "widget-1",
      "title": "销售趋势",
      "theme": "light",
      "chartType": "line",
      "enableFilter": false,
      "enableLink": true,
      "linkTargets": ["widget-2", "widget-3"],
      "position": { "x": 0, "y": 0, "w": 6, "h": 2 }
    }
  ],
  "exportTime": "2024-01-01T00:00:00.000Z"
}
```
