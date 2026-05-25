# 低代码表单构建器

一个基于 Vue3 + TypeScript 的可视化低代码表单构建器，支持拖拽组件构建表单、数据校验、公式计算、条件显隐、多页签表单等高级功能。

## ✨ 功能特性

### 🎨 可视化设计
- **拖拽式组件**：从组件库拖拽组件到画布，或点击直接添加
- **实时预览**：所见即所得的设计体验
- **多页签管理**：支持创建多个页签，组织复杂表单
- **撤销/重做**：完整的历史记录功能

### 📋 丰富组件库
- **基础组件**：单行输入、多行输入、数字输入、下拉选择、单选框、多选框、开关
- **高级组件**：日期选择、时间选择、评分、滑块
- **布局组件**：分割线、静态文本

### ⚙️ 属性配置
- **基础属性**：字段名称、标识、占位符、默认值、必填设置
- **数据校验**：必填、最小值/最大值、邮箱格式、正则表达式、自定义错误提示
- **公式计算**：支持基本数学运算，可引用其他字段
- **条件显隐**：根据其他字段值动态控制显示/禁用

### 📦 输出能力
- **JSON Schema**：生成标准化的表单Schema
- **导出下载**：支持导出JSON文件
- **运行时渲染**：独立的表单渲染引擎
- **数据收集**：表单提交时自动收集和验证数据

## 🚀 快速开始

### 安装依赖
```bash
npm install
```

### 启动开发服务器
```bash
npm run dev
```

访问 `http://localhost:3000` 即可使用表单构建器。

### 构建生产版本
```bash
npm run build
```

## 📁 项目结构

```
src/
├── components/
│   ├── designer/          # 设计器组件
│   │   ├── ComponentPanel.vue    # 组件面板
│   │   ├── DesignCanvas.vue      # 设计画布
│   │   ├── PropertyPanel.vue     # 属性配置面板
│   │   ├── TabBar.vue            # 页签栏
│   │   └── ToolBar.vue           # 工具栏
│   ├── fields/            # 字段组件
│   │   └── DesignerField.vue     # 设计器字段组件
│   └── renderer/          # 渲染引擎
│       └── FormRenderer.vue      # 表单渲染器
├── config/
│   └── components.ts      # 组件配置
├── pages/
│   ├── Designer.vue       # 设计器页面
│   ├── Preview.vue        # 预览页面
│   └── SchemaView.vue     # Schema预览页面
├── router/
│   └── index.ts           # 路由配置
├── stores/
│   └── designer.ts        # Pinia状态管理
├── types/
│   └── form.ts            # 类型定义
├── utils/
│   └── schema.ts          # Schema工具函数
├── App.vue
├── main.ts
└── style.css
```

## 🎯 使用说明

### 1. 添加组件
- 从左侧组件库点击组件直接添加
- 或拖拽组件到中间画布区域

### 2. 配置属性
- 点击画布中的组件选中它
- 在右侧属性面板配置各项属性
- 支持配置数据校验、公式、条件显隐

### 3. 管理页签
- 点击顶部"添加页签"按钮创建新页签
- 双击页签名称可编辑
- 点击页签上的×可删除（至少保留1个）

### 4. 预览和导出
- 点击顶部"预览"按钮查看表单效果
- 点击"Schema"查看生成的JSON结构
- 点击"导出"下载JSON文件

## 🔧 技术栈

- **框架**：Vue 3.4 + TypeScript
- **构建工具**：Vite 5
- **状态管理**：Pinia
- **路由**：Vue Router 4
- **样式**：TailwindCSS 3
- **拖拽**：vuedraggable + SortableJS
- **图标**：lucide-vue-next
- **表单引擎**：FormKit + 自研渲染引擎

## 📄 Schema 结构

```json
{
  "id": "form_xxx",
  "name": "表单名称",
  "description": "表单描述",
  "version": "1.0.0",
  "createdAt": "2024-01-01T00:00:00.000Z",
  "updatedAt": "2024-01-01T00:00:00.000Z",
  "tabs": [
    {
      "id": "tab_xxx",
      "name": "页签名称",
      "icon": "file-text",
      "fields": [
        {
          "id": "field_xxx",
          "type": "input",
          "name": "field_name",
          "label": "字段标签",
          "placeholder": "请输入",
          "required": true,
          "validation": [],
          "formula": null,
          "conditional": null,
          "props": {}
        }
      ]
    }
  ]
}
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📝 License

MIT
