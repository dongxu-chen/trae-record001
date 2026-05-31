# 词云生成工具

一个功能强大的Web端词云生成工具，支持中英文分词、多种形状和配色方案。

## 功能特性

- ✅ **中英文分词**：支持中文和英文混合文本的智能分词
- ✅ **词频统计**：自动统计词频并按重要性排序
- ✅ **多种形状**：圆形、椭圆、方形、菱形、三角形、星形、心形
- ✅ **配色方案**：鲜艳、暖色、冷色、柔和、单色等5种配色
- ✅ **字体配置**：支持多种中文字体和英文字体
- ✅ **字号调整**：可自定义最大和最小字号
- ✅ **停用词**：支持自定义停用词过滤
- ✅ **实时预览**：输入文本实时生成词云
- ✅ **图片下载**：一键下载PNG格式词云图片
- ✅ **统计信息**：显示词汇数量、总词频、高频词汇等

## 技术栈

- **前端**：React 18 + Vite + Canvas
- **后端**：Node.js + Express + segmentit（中文分词）
- **词云算法**：自研螺旋布局算法 + 碰撞检测

## 快速开始

### 安装依赖

```bash
# 安装根目录依赖
npm install

# 安装后端依赖
cd server
npm install

# 安装前端依赖
cd ../client
npm install
```

或者一键安装所有依赖：

```bash
npm run install-all
```

### 启动开发服务

#### 方式一：仅启动前端（推荐快速体验）

```bash
cd client
npm run dev
```

前端内置了本地分词降级方案，即使不启动后端也可以使用。

#### 方式二：同时启动前后端（推荐，分词效果更好）

```bash
npm run dev
```

或者分别启动：

```bash
# 启动后端服务（端口3001）
cd server
npm run dev

# 启动前端服务（端口3000）
cd client
npm run dev
```

### 访问应用

打开浏览器访问：`http://localhost:3000`

## 使用说明

1. **输入文本**：在左侧文本框输入要生成词云的内容
2. **配置形状**：选择词云的外形（圆形、心形等）
3. **选择配色**：点击配色方案选择喜欢的颜色组合
4. **调整字体**：选择字体和字号范围
5. **添加停用词**：输入不想显示的词汇
6. **实时预览**：右侧会实时显示词云效果
7. **下载图片**：点击"下载图片"按钮保存词云

## 项目结构

```
wordcloud-generator/
├── client/                 # 前端React应用
│   ├── src/
│   │   ├── App.jsx        # 主应用组件
│   │   ├── main.jsx       # 入口文件
│   │   ├── styles.css     # 样式文件
│   │   └── utils/
│   │       └── wordcloud.js  # 词云算法核心
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── server/                 # 后端Node.js服务
│   ├── index.js           # 服务入口（分词API）
│   └── package.json
├── package.json
└── README.md
```

## API接口

### 分词分析接口

**POST** `/api/analyze`

请求体：
```json
{
  "text": "要分析的文本内容",
  "stopWords": ["停用词1", "停用词2"]
}
```

响应：
```json
{
  "words": [
    { "word": "词汇1", "count": 10 },
    { "word": "词汇2", "count": 8 }
  ]
}
```

## 构建生产版本

```bash
cd client
npm run build
```

构建产物将输出到 `client/dist` 目录。

## License

MIT
