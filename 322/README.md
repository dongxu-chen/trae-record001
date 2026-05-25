# 图表标注工具 (Chart Annotation Tool)

一个功能强大的 Web 端图表标注工具，支持多人协作、多种标注类型、质量检查和多种格式导出。

## 技术栈

- **前端框架**: Vue 3 + Vite
- **画布引擎**: Fabric.js
- **本地存储**: IndexedDB (idb 库)
- **实时协作**: WebSocket
- **标注类型**: 矩形框、箭头、文本注释

## 功能特性

### 核心功能
- ✅ **图片上传**: 支持本地图片上传进行标注
- ✅ **矩形框标注**: 用于框选数据区域、标题等
- ✅ **箭头标注**: 用于指向特定元素进行说明
- ✅ **文本注释**: 添加文字说明
- ✅ **标注分类**: 数据区域、标题、轴标签、图例四大类

### 多人协作
- ✅ **实时同步**: 所有标注操作实时同步到协作者
- ✅ **用户指针**: 显示协作者的鼠标位置
- ✅ **在线用户**: 显示当前房间的在线用户
- ✅ **房间管理**: 通过房间号加入不同的协作房间

### 导出功能
- ✅ **COCO 格式**: 导出为 Microsoft COCO JSON 格式
- ✅ **PASCAL VOC 格式**: 导出为 VOC XML 格式
- ✅ **JSON 格式**: 导出为通用 JSON 格式

### 质量检查
- ✅ **完整性检查**: 检查标注数量和必需分类
- ✅ **准确性检查**: 检查标注尺寸、重叠情况
- ✅ **丰富度检查**: 检查标签完整性和辅助标注
- ✅ **质量评分**: 0-100 分综合评分

### 其他功能
- ✅ **撤销/重做**: 支持操作历史
- ✅ **缩放/平移**: 画布缩放和平移
- ✅ **快捷键**: 丰富的键盘快捷键
- ✅ **本地存储**: 所有数据保存在浏览器本地 IndexedDB

## 项目结构

```
chart-annotation-tool/
├── src/
│   ├── components/          # Vue 组件
│   │   ├── Toolbar.vue      # 顶部工具栏
│   │   ├── CanvasArea.vue   # 画布区域
│   │   ├── Sidebar.vue      # 右侧边栏
│   │   ├── QualityCheckModal.vue  # 质量检查弹窗
│   │   └── ExportModal.vue  # 导出弹窗
│   ├── utils/               # 工具模块
│   │   ├── canvasManager.js # Fabric.js 画布管理
│   │   ├── db.js            # IndexedDB 存储
│   │   ├── websocket.js     # WebSocket 客户端
│   │   ├── export.js        # 导出功能
│   │   └── qualityCheck.js  # 质量检查
│   ├── constants/           # 常量定义
│   │   └── index.js
│   ├── styles/              # 样式文件
│   │   └── global.css
│   ├── App.vue              # 主应用组件
│   └── main.js              # 入口文件
├── server/                  # WebSocket 服务端
│   └── ws-server.js
├── index.html
├── vite.config.js
├── package.json
└── README.md
```

## 快速开始

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:5173 即可使用。

### 启动 WebSocket 协作服务器（可选）

```bash
npm run server
```

服务器将在 ws://localhost:8080 启动。

### 构建生产版本

```bash
npm run build
```

## 使用说明

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| `V` | 选择工具 |
| `R` | 矩形框工具 |
| `A` | 箭头工具 |
| `T` | 文本工具 |
| `H` | 平移工具 |
| `Ctrl+Z` | 撤销 |
| `Ctrl+Y` / `Ctrl+Shift+Z` | 重做 |
| `Delete` / `Backspace` | 删除选中标注 |
| `Ctrl+A` | 全选 |
| `Escape` | 取消当前操作 |

### 标注分类

| 分类 | 颜色 | 说明 |
|------|------|------|
| 数据区域 | 蓝色 (#409eff) | 图表中的数据展示区域 |
| 标题 | 绿色 (#67c23a) | 图表标题和副标题 |
| 轴标签 | 橙色 (#e6a23c) | X轴、Y轴标签和刻度 |
| 图例 | 红色 (#f56c6c) | 图表图例说明 |

### 多人协作

1. 点击右上角连接状态图标
2. 设置用户名和房间号
3. 输入 WebSocket 服务器地址（默认 ws://localhost:8080）
4. 点击"连接"按钮
5. 同一房间的用户可以实时协作标注

### 导出格式说明

#### COCO 格式
```json
{
  "info": { ... },
  "licenses": [ ... ],
  "categories": [
    {"id": 1, "name": "data_region", ...},
    ...
  ],
  "images": [ ... ],
  "annotations": [
    {
      "id": 1,
      "image_id": 1,
      "category_id": 1,
      "bbox": [x, y, width, height],
      "segmentation": [ ... ],
      "area": 12345,
      "attributes": { "label": "...", "type": "rectangle" }
    },
    ...
  ]
}
```

#### PASCAL VOC 格式
```xml
<annotation>
  <filename>chart.png</filename>
  <size>
    <width>800</width>
    <height>600</height>
    <depth>3</depth>
  </size>
  <object>
    <name>data_region</name>
    <bndbox>
      <xmin>100</xmin>
      <ymin>200</ymin>
      <xmax>500</xmax>
      <ymax>400</ymax>
    </bndbox>
    <label>销售数据</label>
  </object>
</annotation>
```

## 数据存储

所有数据保存在浏览器的 IndexedDB 中，包括：
- 项目信息
- 上传的图片（Base64 格式）
- 标注数据
- 操作历史

## 质量检查规则

1. **最小标注数量**: 至少 3 个矩形标注
2. **必需分类**: 必须包含标题、轴标签、数据区域
3. **最小尺寸**: 标注尺寸不小于 20px
4. **重叠检测**: 同类标注重叠不超过 80%
5. **标签完整性**: 建议所有标注都添加标签
6. **辅助标注**: 建议添加箭头或文本注释

## 浏览器兼容性

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## License

MIT
