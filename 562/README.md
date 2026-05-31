# 🖼️ 图片文字擦除工具

一个基于 Web 的智能图片文字擦除工具，使用 React + Canvas + 图像修复算法实现。

## ✨ 功能特性

- **🎨 智能涂抹擦除**: 使用画笔涂抹需要擦除的文字区域
- **🔧 多种修复算法**:
  - Telea 算法 (快速)
  - Navier-Stokes 算法 (高质量)
  - 混合算法 (推荐)
  - 快速行进算法
- **📦 批量处理**: 支持多张图片批量处理
- **📱 响应式设计**: 适配不同屏幕尺寸
- **💾 一键下载**: 处理完成后一键下载结果
- **🖱️ 拖拽上传**: 支持拖拽方式上传图片

## 🏗️ 技术栈

### 前端
- React 18
- Canvas API
- Axios
- CSS3 (响应式设计)

### 后端
- Node.js
- Express.js
- Jimp (图像处理)
- 自定义图像修复算法实现

## 🚀 快速开始

### 安装依赖

```bash
# 安装根目录依赖
npm install

# 安装前后端依赖
npm run install-all
```

### 启动开发服务器

```bash
# 同时启动前后端
npm run dev

# 或者分别启动
# 启动后端 (端口 5000)
npm run server

# 启动前端 (端口 3000)
npm run client
```

### 构建生产版本

```bash
npm run build
```

## 📖 使用说明

### 单图处理

1. 点击或拖拽上传图片
2. 使用画笔涂抹需要擦除的文字区域
3. 选择合适的修复算法
4. 点击「开始擦除」按钮
5. 查看处理结果并下载

### 批量处理

1. 切换到「批量处理」标签
2. 上传多张图片
3. 配置处理参数
4. 点击「开始批量处理」
5. 下载全部或单个结果

### 画笔设置

- **画笔大小**: 根据文字粗细调整，范围 5-100px
- **修复算法**:
  - Telea: 速度快，适合简单背景
  - Navier-Stokes: 质量高，适合复杂背景
  - 混合算法: 结合两者优点，推荐使用
- **修复半径**: 控制修复范围，范围 1-10px

## 📁 项目结构

```
.
├── client/                 # 前端代码
│   ├── public/            # 静态资源
│   ├── src/
│   │   ├── components/    # React 组件
│   │   │   ├── ImageEditor.js       # 单图编辑器组件
│   │   │   ├── ImageEditor.css      # 编辑器样式
│   │   │   ├── BatchProcessor.js    # 批量处理组件
│   │   │   └── BatchProcessor.css   # 批量处理样式
│   │   ├── App.js         # 主应用组件
│   │   ├── App.css        # 主应用样式
│   │   ├── index.js       # 入口文件
│   │   └── index.css      # 全局样式
│   └── package.json
├── server/                # 后端代码
│   ├── server.js          # Express 服务器
│   ├── inpainting.js      # 图像修复算法
│   └── package.json
├── package.json           # 项目配置
└── README.md
```

## 🔌 API 接口

### POST /api/inpaint

单图修复接口

**请求体:**
```json
{
  "image": "base64编码的图片数据",
  "mask": "base64编码的掩码图片",
  "algorithm": "telea | ns | hybrid | fm",
  "radius": 3
}
```

**响应:**
```json
{
  "success": true,
  "result": "base64编码的处理结果图片",
  "width": 800,
  "height": 600
}
```

### POST /api/batch-inpaint

批量修复接口

**请求体:**
```json
{
  "images": [
    {
      "image": "base64编码的图片数据",
      "mask": "base64编码的掩码图片",
      "name": "图片名称"
    }
  ],
  "algorithm": "telea",
  "radius": 3
}
```

### GET /api/health

健康检查接口

## 🎯 算法说明

### Telea 算法

基于快速行进方法，使用加权平均的方式填充修复区域。速度快，适合简单背景的文字擦除。

### Navier-Stokes 算法

基于流体力学的 Navier-Stokes 方程，能够更好地保持图像的纹理和边缘。质量高，但速度较慢。

### 混合算法

先使用 Telea 算法快速填充，再使用 NS 算法进行细化，兼顾速度和质量。

### 快速行进算法

基于水平集方法的快速行进算法，适合处理较大的修复区域。

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
