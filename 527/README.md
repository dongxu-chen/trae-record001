# 信息抽取标注工具

一个功能完整的Web端信息抽取标注工具，支持实体、关系、事件标注，采用Prodigy风格的深色UI设计。

## ✨ 功能特性

### 核心标注功能
- **实体标注**: 拖拽选择文本进行实体高亮标注
- **关系标注**: 实体间关系连线标注
- **事件标注**: 支持事件触发词和论元标注

### 高级功能
- **自动预标注**: 基于规则和关键词的自动预标注（模拟预训练模型效果）
- **一致性检查**: 标签不一致检测、实体重叠检测
- **数据导出**: 支持JSON和CoNLL格式导出

### 数据管理
- **任务管理**: 创建、编辑、删除标注任务
- **文档管理**: 批量导入文档，标注进度追踪
- **统计面板**: 实时标注进度和数据统计

## 🛠️ 技术栈

### 前端
- React 18 + React Router
- Styled Components (Prodigy风格深色UI)
- Axios (HTTP客户端)

### 后端
- Node.js + Express
- MongoDB + Mongoose
- RESTful API设计

## 📁 项目结构

```
annotation-tool/
├── backend/                 # 后端服务
│   ├── src/
│   │   ├── models/         # 数据模型
│   │   ├── controllers/    # 业务逻辑
│   │   ├── routes/         # API路由
│   │   └── middleware/     # 中间件
│   ├── server.js           # 服务入口
│   └── package.json
│
└── frontend/               # 前端应用
    ├── src/
    │   ├── components/     # UI组件
    │   ├── pages/          # 页面组件
    │   ├── services/       # API服务
    │   ├── styles/         # 样式文件
    │   └── utils/          # 工具函数
    └── package.json
```

## 🚀 快速开始

### 环境要求
- Node.js >= 14.x
- MongoDB >= 4.x

### 安装依赖

```bash
# 安装后端依赖
cd backend
npm install

# 安装前端依赖
cd ../frontend
npm install
```

### 启动服务

1. 确保MongoDB服务已启动
   - Windows: 以管理员身份运行 `net start MongoDB`
   - 或确保MongoDB Compass已连接

2. 启动后端服务
```bash
cd backend
npm start
# 或开发模式: npm run dev
```

3. 启动前端服务 (新开终端)
```bash
cd frontend
npm start
```

4. 访问应用: http://localhost:3000

## 📖 使用指南

### 1. 创建标注任务

1. 点击左侧菜单的「任务管理」
2. 点击「创建任务」按钮
3. 填写任务名称和描述
4. 配置实体类型（可自定义标签和颜色）
5. 点击「创建任务」

### 2. 添加示例数据

在任务列表中点击「添加示例数据」按钮，系统会自动添加5条中文示例文档。

### 3. 开始标注

1. 点击「开始标注」进入标注界面
2. **实体标注模式**:
   - 在左侧标签面板选择实体类型
   - 在文本中拖拽选择要标注的文字
   - 点击已标注实体可删除
3. **关系标注模式**:
   - 点击「关系」切换到关系模式
   - 依次点击两个实体创建关系
   - 输入关系类型名称
4. 点击「自动预标注」可自动识别常见实体
5. 点击「下一篇」保存并跳转

### 4. 导出数据

1. 在任务列表中点击「导出数据」
2. 查看标注统计信息
3. 选择导出格式:
   - **JSON格式**: 包含完整的标注详情
   - **CoNLL格式**: BIO标注体系的NER训练数据

### 5. 一致性检查

1. 在任务列表中点击「一致性检查」
2. 系统自动检测:
   - 标签不一致（同一文本被标为不同类型）
   - 实体重叠（同一位置被多个实体标注）
3. 根据检查结果优化标注质量

## 📊 数据格式

### JSON导出格式

```json
{
  "id": "annotation-id",
  "documentId": "doc-id",
  "text": "原始文本内容",
  "entities": [
    {
      "id": "entity-id",
      "start": 0,
      "end": 4,
      "text": "实体文本",
      "label": "PERSON",
      "isPreAnnotated": false
    }
  ],
  "relations": [
    {
      "id": "relation-id",
      "sourceId": "entity-1",
      "targetId": "entity-2",
      "label": "WORK_FOR"
    }
  ],
  "events": []
}
```

### CoNLL导出格式

```
-DOCSTART- -X- -X- O

张三 -X- -X- B-PERSON
在 -X- -X- O
百度 -X- -X- B-ORGANIZATION
工作 -X- -X- O
```

## 🎨 UI设计特点

- **深色主题**: 护眼的Prodigy风格深色界面
- **三栏布局**: 标签选择 + 文本标注 + 标注列表
- **实时高亮**: 不同实体类型用不同颜色区分
- **进度追踪**: 直观的标注进度条显示
- **响应式设计**: 适配不同屏幕尺寸

## 🔧 API接口

### 任务管理
- `GET /api/tasks` - 获取所有任务
- `POST /api/tasks` - 创建任务
- `GET /api/tasks/:id` - 获取任务详情
- `PUT /api/tasks/:id` - 更新任务
- `DELETE /api/tasks/:id` - 删除任务

### 文档管理
- `GET /api/documents/task/:taskId` - 获取任务文档
- `GET /api/documents/next/:taskId/:currentId` - 获取下一个文档
- `POST /api/documents/bulk` - 批量创建文档

### 标注管理
- `GET /api/annotations/document/:documentId` - 获取文档标注
- `POST /api/annotations/document/:documentId` - 保存标注

### 导出与分析
- `GET /api/export/json/:taskId?format=flat|nested` - 导出JSON（支持扁平化/嵌套格式）
- `GET /api/export/conll/:taskId` - 导出CoNLL
- `GET /api/export/stats/:taskId` - 获取统计数据

### 主动学习与预标注
- `POST /api/preannotate/document/:documentId` - 预标注文档（支持主动学习参数）
- `POST /api/preannotate/finetune/:taskId` - 模型微调（数据回流）
- `GET /api/preannotate/next-uncertain/:taskId?strategy=uncertainty` - 获取不确定性文档
- `GET /api/preannotate/model-info/:taskId` - 获取模型信息
- `GET /api/preannotate/consistency/:taskId?sampleSize=50&sampleStrategy=random` - 抽样一致性检查

## 📝 标注规范建议

1. **实体边界**: 尽量标注完整的语义单元
2. **一致性**: 相同类型的实体使用相同标签
3. **不重叠**: 避免实体重叠标注
4. **预标注**: 自动预标注结果需要人工校验

## 🔄 扩展开发

### 添加新的标注类型
1. 在后端 `Annotation.js` 模型中添加字段
2. 在前端 `AnnotationPage.js` 添加对应UI
3. 在导出控制器添加格式支持

### 集成真实预训练模型
1. 修改 `preAnnotateController.js`
2. 接入BERT/ERNIE等NLP模型的API
3. 调整置信度阈值和后处理逻辑

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！
