# 3D模型编辑器 - 全栈应用

基于 Babylon.js + Express + MongoDB 的在线3D模型编辑器。

## 功能特性

### 1. 模型导入
- 支持 glTF/GLB 格式
- 支持 OBJ 格式
- 模型上传与管理

### 2. PBR材质编辑
- 基础颜色 (Albedo)
- 金属度 (Metallic)
- 粗糙度 (Roughness)
- 自发光颜色与强度

### 3. 动画预览
- 动画播放/暂停/停止
- 播放速度调节
- 多动画切换

### 4. 云端渲染农场
- 多种分辨率选择 (1080p, 2K, 4K)
- 采样质量设置 (64-512)
- 渲染引擎选择 (Cycles/Eevee)
- 任务状态跟踪

## 技术栈

- **前端**: Babylon.js, HTML5, CSS3, JavaScript
- **后端**: Node.js, Express.js
- **数据库**: MongoDB
- **文件存储**: 本地文件系统

## 安装与运行

### 前置要求

- Node.js (v14+)
- MongoDB (本地或远程)

### 安装依赖

```bash
npm install
```

### 配置环境变量

创建 `.env` 文件 (已包含):

```
PORT=3000
MONGODB_URI=mongodb://localhost:27017/3d-model-editor
UPLOAD_PATH=./uploads
```

### 启动应用

```bash
npm start
```

开发模式 (nodemon):

```bash
npm run dev
```

### 访问应用

打开浏览器访问: `http://localhost:3000`

## 项目结构

```
3d-model-editor/
├── server/
│   ├── index.js              # 服务入口
│   ├── models/
│   │   ├── Model.js          # 模型数据模型
│   │   └── RenderJob.js      # 渲染任务数据模型
│   └── routes/
│       ├── models.js         # 模型API路由
│       └── render.js         # 渲染API路由
├── public/
│   ├── index.html            # 主页面
│   ├── css/
│   │   └── style.css         # 样式文件
│   └── js/
│       └── app.js            # 前端应用逻辑
├── uploads/                  # 上传文件存储目录
├── package.json
└── .env
```

## API 接口

### 模型管理
- `GET /api/models` - 获取所有模型
- `GET /api/models/:id` - 获取单个模型
- `POST /api/models/upload` - 上传模型
- `PUT /api/models/:id` - 更新模型信息
- `DELETE /api/models/:id` - 删除模型

### 渲染农场
- `GET /api/render` - 获取所有渲染任务
- `GET /api/render/:id` - 获取单个渲染任务
- `POST /api/render/submit` - 提交渲染任务
- `PUT /api/render/:id/status` - 更新任务状态

## 使用说明

1. **上传模型**: 点击"上传模型"按钮，选择模型文件并填写信息
2. **编辑材质**: 在侧边栏选择材质，调节PBR参数
3. **播放动画**: 在动画控制面板选择动画，点击播放
4. **提交渲染**: 调整好视角后，点击"提交渲染"，设置渲染参数

## 注意事项

- 确保 MongoDB 服务正在运行
- 上传的模型文件大小受服务器配置限制
- glTF 格式支持最佳，推荐使用

## 许可证

MIT
