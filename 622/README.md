# AI 风格迁移工具 (AI Style Transfer)

一个基于 Web 的 AI 绘画风格迁移工具，支持多种艺术风格转换。

## 技术栈

- **前端**: React 18 + Vite + Tailwind CSS
- **后端 API**: FastAPI (Python)
- **图像处理服务**: Node.js + Express + Sharp
- **风格迁移**: 基于 OpenCV + PIL 的图像处理算法（支持 GAN/Diffusion 模式模拟）

## 功能特性

- 🖼️ 上传内容图片（支持拖拽）
- 🎨 8种预设艺术风格（梵高、毕加索、莫奈等）
- 🖌️ 支持自定义风格图片上传
- ⚙️ GAN 和 Diffusion 两种模型选择
- 🎚️ 风格强度调节（0-100%）
- 👁️ 实时预览功能
- 🔄 并排/滑动对比效果
- 💾 下载生成结果

## 项目结构

```
622/
├── frontend/              # React 前端应用
│   ├── src/
│   │   ├── components/    # React 组件
│   │   ├── services/      # API 服务
│   │   ├── App.jsx        # 主应用组件
│   │   ├── main.jsx       # 入口文件
│   │   └── index.css      # 全局样式
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── backend/               # FastAPI 后端
│   ├── main.py            # API 主程序
│   ├── style_transfer.py  # 风格迁移算法
│   ├── image_utils.py     # 图像处理工具
│   ├── styles/            # 风格参考图片目录
│   └── requirements.txt
├── node-service/          # Node.js 图像处理服务
│   ├── server.js
│   └── package.json
├── uploads/               # 上传文件存储
├── outputs/               # 生成结果存储
└── processed/             # 处理中文件存储
```

## 快速开始

### 1. 启动 FastAPI 后端

```bash
cd backend
pip install -r requirements.txt
python main.py
```

后端服务将运行在: http://localhost:8000

API 文档: http://localhost:8000/docs

### 2. 启动 Node.js 服务（可选）

```bash
cd node-service
npm install
npm start
```

Node 服务将运行在: http://localhost:3001

### 3. 启动 React 前端

```bash
cd frontend
npm install
npm run dev
```

前端应用将运行在: http://localhost:3000

## 使用说明

1. **上传内容图片**: 在左侧区域点击或拖拽上传需要处理的图片
2. **选择模型**: 选择 GAN（快速）或 Diffusion（高质量）
3. **调节强度**: 拖动滑块控制风格化程度
4. **选择风格**: 从预设风格中选择或上传自定义风格图片
5. **开始转换**: 点击"开始风格迁移"按钮
6. **查看结果**: 在右侧预览区查看对比效果，可切换并排/滑动模式
7. **下载**: 点击下载按钮保存生成的图片

## API 接口

### FastAPI 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/styles | 获取风格列表 |
| GET | /api/models | 获取模型列表 |
| POST | /api/upload | 上传图片 |
| POST | /api/transfer | 执行风格迁移 |
| POST | /api/preview | 生成预览图 |

### Node.js 服务接口

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/process-image | 图像处理 |
| POST | /api/batch-process | 批量处理 |
| POST | /api/generate-thumbnail | 生成缩略图 |

## 风格说明

### 经典风格
- **梵高星空**: 印象派后印象主义风格
- **毕加索立体主义**: 立体主义抽象风格
- **莫奈睡莲**: 印象派光影风格
- **神奈川冲浪**: 日本浮世绘风格

### 现代风格
- **赛博朋克**: 未来科技霓虹风格
- **水彩画**: 清新水彩风格
- **油画**: 厚重油画质感
- **素描**: 铅笔素描风格

## 扩展开发

### 添加新的风格预设

在 `backend/style_transfer.py` 中的 `StyleTransfer` 类添加新的风格处理方法，然后在 `STYLE_PRESETS` 中注册。

### 接入真实的深度学习模型

可以替换 `style_transfer.py` 中的模拟实现，接入真实的预训练模型（如 PyTorch 的 Neural Style Transfer、Stable Diffusion 等）。

## 许可证

MIT License
