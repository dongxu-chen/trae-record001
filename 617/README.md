# 🎨 网页骨架屏生成器

一个基于 React + Puppeteer + Node.js 的网页骨架屏自动生成工具。

## ✨ 功能特性

- 🖼️ **自动布局分析**：基于 Puppeteer 自动分析页面 DOM 结构
- 🎯 **多种布局识别**：支持图片、文字、按钮、输入框、头像、卡片等元素识别
- 📱 **移动端适配**：支持桌面端和移动端两种视图模式
- 🎨 **颜色自定义**：可调节背景色和高亮色
- ✨ **动画效果**：支持骨架屏加载动画
- 📋 **一键复制**：快速复制生成的 HTML/CSS 代码
- ⬇️ **代码下载**：支持下载生成的骨架屏代码文件

## 🛠️ 技术栈

- **前端**：React 18 + Vite
- **后端**：Node.js + Express
- **页面分析**：Puppeteer
- **布局算法**：DOM 遍历 + 元素特征识别

## 📦 安装

```bash
npm install
```

## 🚀 运行

### 开发模式（同时启动前端和后端）

```bash
npm run dev
```

### 单独启动服务端

```bash
npm run server
```

### 单独启动前端

```bash
npm run client
```

## 📖 使用说明

1. 在输入框中输入目标网页的 URL
2. 选择设备类型（桌面端/移动端）
3. 自定义颜色设置（可选）
4. 点击「生成」按钮
5. 预览生成的骨架屏效果
6. 复制或下载生成的代码

## 📂 项目结构

```
├── client/                # 前端代码
│   ├── components/       # React 组件
│   │   ├── ConfigPanel.jsx    # 配置面板
│   │   └── PreviewPanel.jsx   # 预览面板
│   ├── App.jsx           # 主应用组件
│   ├── main.jsx          # 入口文件
│   └── index.css         # 全局样式
├── server/               # 后端代码
│   ├── index.js          # Express 服务器
│   └── skeletonGenerator.js  # 骨架屏生成核心逻辑
├── index.html            # HTML 模板
├── vite.config.js        # Vite 配置
└── package.json          # 项目配置
```

## 🔧 API 接口

### POST /api/generate-skeleton

生成骨架屏代码

**请求参数：**
```json
{
  "url": "https://example.com",
  "options": {
    "device": "desktop",
    "backgroundColor": "#f0f0f0",
    "highlightColor": "#e0e0e0",
    "animation": true,
    "removeImages": true,
    "removeText": true
  }
}
```

**响应：**
```json
{
  "html": "...",
  "css": "...",
  "layoutData": {...}
}
```

## 📝 License

MIT
