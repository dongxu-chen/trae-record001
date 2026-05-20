# 代码片段高亮组件库

基于 React + TypeScript + Prism.js 构建的代码高亮组件库。

## 功能特性

- 🎨 **语法高亮**: 支持 JavaScript、TypeScript、Python、CSS、SQL、Java、Go、Rust 等多种编程语言
- 🔢 **行号显示**: 可选的行号显示功能，方便代码阅读和引用
- 📋 **一键复制**: 点击按钮即可将代码复制到剪贴板，复制成功有提示
- 🌓 **主题切换**: 支持暗色和亮色主题切换，适应不同阅读环境

## 安装和运行

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

### 基础用法

```tsx
import { CodeSnippet } from './components';

<CodeSnippet
  code={yourCode}
  language="javascript"
/>
```

### 完整配置

```tsx
import { CodeSnippet } from './components';

<CodeSnippet
  code={yourCode}
  language="typescript"
  showLineNumbers={true}
  showCopyButton={true}
  showThemeToggle={true}
  defaultTheme="dark"
/>
```

## 组件 Props

| 属性名           | 类型               | 默认值   | 说明                       |
| ---------------- | ------------------ | -------- | -------------------------- |
| code             | string             | 必填     | 要高亮显示的代码内容       |
| language         | string             | 必填     | 编程语言类型               |
| showLineNumbers  | boolean            | true     | 是否显示行号               |
| showCopyButton   | boolean            | true     | 是否显示复制按钮           |
| showThemeToggle  | boolean            | true     | 是否显示主题切换按钮       |
| defaultTheme     | 'dark' \| 'light'  | 'dark'   | 默认主题                   |

## 项目结构

```
├── src/
│   ├── components/
│   │   ├── CodeSnippet/
│   │   │   ├── CodeSnippet.tsx    # 组件主文件
│   │   │   ├── CodeSnippet.css    # 组件样式
│   │   │   └── index.ts           # 组件导出
│   │   └── index.ts               # 统一导出
│   ├── App.tsx                     # 演示页面
│   ├── App.css                     # 演示页面样式
│   ├── main.tsx                    # 入口文件
│   └── index.css                   # 全局样式
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## 技术栈

- React 18
- TypeScript
- Prism.js
- Vite
