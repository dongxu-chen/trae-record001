# 图像分割标注工具

一个专业的Web端图像分割标注工具，支持多种标注模式和SAM模型辅助的半自动分割。

## 功能特性

- ✅ **多边形标注** - 点击添加顶点，闭合完成多边形区域标注
- ✅ **点标注** - 单点击标记关键点
- ✅ **矩形标注** - 拖拽绘制矩形框
- ✅ **画笔标注** - 自由绘制语义分割区域
- ✅ **SAM点击分割** - 基于Segment Anything模型的一键半自动分割
- ✅ **像素计算** - 自动计算标注区域的像素面积和占比
- ✅ **撤销/重做** - 完整的历史记录管理
- ✅ **数据导出** - 支持JSON格式和掩码图像导出
- ✅ **标签管理** - 自定义分类标签和颜色
- ✅ **画布操作** - 滚轮缩放、空格键平移
- ✅ **快捷键支持** - 高效的键盘操作

## 技术栈

### 前端
- React 18 + TypeScript
- Vite 6
- Tailwind CSS 3
- Zustand (状态管理)
- Canvas 2D API
- WebSocket

### 后端
- FastAPI 0.109
- WebSocket
- Segment Anything (SAM) - 可选
- OpenCV + NumPy + Pillow

## 快速开始

### 1. 安装前端依赖

```bash
cd client
npm install
```

### 2. 安装后端依赖

```bash
cd server
pip install -r requirements.txt
```

### 3. (可选) 安装SAM模型依赖

如需使用SAM点击分割功能，需要额外安装：

```bash
pip install torch torchvision segment-anything
```

然后下载SAM模型权重文件，放入 `server/models/` 目录：

- **ViT-B** (推荐): https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth
- **ViT-L**: https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth
- **ViT-H**: https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth

### 4. 启动后端服务

```bash
cd server
python main.py
```

后端服务将在 `http://localhost:8000` 启动

### 5. 启动前端开发服务器

```bash
cd client
npm run dev
```

前端服务将在 `http://localhost:5173` 启动

## 使用说明

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| `V` | 选择工具 |
| `P` | 多边形工具 |
| `O` | 点工具 |
| `R` | 矩形工具 |
| `B` | 画笔工具 |
| `S` | SAM点击工具 |
| `Ctrl+Z` | 撤销 |
| `Ctrl+Y` / `Ctrl+Shift+Z` | 重做 |
| `Space` | 按住平移画布 |
| `滚轮` | 缩放画布 |
| `Esc` | 取消当前操作 |
| `右键` | 取消多边形绘制 |

### 标注流程

1. 点击「上传图像」按钮选择要标注的图片
2. 从左侧工具栏选择标注工具
3. 在画布上进行标注
4. 从右侧面板可以编辑标注标签、调整颜色
5. 完成后点击「导出JSON」或「导出掩码图」保存结果

### SAM半自动分割

1. 确保后端已安装SAM依赖并下载了模型权重
2. 选择SAM点击工具（快捷键S）
3. 在目标物体上点击一下
4. 等待SAM模型生成分割掩码
5. 确认后掩码自动保存为标注

## 项目结构

```
372/
├── client/                    # React前端
│   ├── src/
│   │   ├── components/        # UI组件
│   │   │   ├── Canvas/        # Canvas标注组件
│   │   │   ├── Toolbar/       # 工具栏
│   │   │   ├── Sidebar/       # 右侧面板
│   │   │   ├── Header/        # 顶部导航
│   │   │   └── StatusBar/     # 状态栏
│   │   ├── store/             # 状态管理
│   │   ├── tools/             # 标注工具实现
│   │   ├── services/          # API和WebSocket服务
│   │   ├── utils/             # 工具函数
│   │   └── types/             # TypeScript类型定义
│   └── package.json
└── server/                    # FastAPI后端
    ├── main.py                # 应用入口
    ├── sam_model.py           # SAM模型封装
    ├── websocket_handler.py   # WebSocket处理器
    ├── image_service.py       # 图像处理服务
    ├── schemas.py             # Pydantic数据模型
    ├── requirements.txt
    └── models/                # SAM模型权重目录
```

## 标注数据格式

### JSON导出格式

```json
{
  "version": "1.0",
  "image": {
    "id": "xxx",
    "filename": "image.jpg",
    "width": 800,
    "height": 600
  },
  "annotations": [
    {
      "id": "xxx",
      "type": "polygon",
      "label": "前景",
      "color": "#ef4444",
      "points": [{"x": 10, "y": 20}, ...],
      "pixelArea": 15000,
      "pixelPercentage": 3.125
    }
  ],
  "exportedAt": 1234567890
}
```

## 注意事项

- SAM模型较大，首次加载需要几秒时间
- 如果没有安装SAM，工具会正常运行，只是SAM功能不可用
- 标注数据存储在内存中，刷新页面会丢失，请及时导出
- 支持的图像格式：JPG、PNG、BMP、WebP、TIFF

## License

MIT
