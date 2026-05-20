# 低代码数据ETL平台

基于Python + Prefect + React的低代码数据ETL平台，支持可视化数据管道设计、任务调度监控、数据质量检查和断点续跑。

## 功能特性

### 1. 可视化数据管道设计
- 拖拽式节点设计界面
- 支持数据提取、转换、加载、数据质量检查等多种任务类型
- 可视化连接数据流

### 2. 任务调度和监控
- 实时监控管道执行状态
- 查看执行历史和统计信息
- 任务执行详情追踪

### 3. 数据质量检查
- 空值检查
- 重复数据检查
- 数值范围检查
- 正则表达式校验
- 唯一性检查

### 4. 断点续跑
- 自动保存执行检查点
- 失败任务支持断点续跑
- 跳过已完成任务

## 技术栈

### 后端
- **Python 3.8+**
- **FastAPI**: Web API框架
- **Prefect 2.x**: 工作流编排引擎
- **SQLAlchemy**: ORM框架
- **Pandas**: 数据处理
- **SQLite**: 数据库

### 前端
- **React 18+**
- **React Flow**: 可视化流程设计
- **Ant Design**: UI组件库
- **Axios**: HTTP客户端
- **React Router**: 路由管理

## 项目结构

```
etl-platform/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/           # API路由
│   │   │   ├── pipelines.py
│   │   │   └── data_quality.py
│   │   ├── core/          # 核心配置
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── models/        # 数据模型
│   │   │   ├── pipeline.py
│   │   │   └── schemas.py
│   │   ├── pipelines/     # 管道执行逻辑
│   │   │   ├── tasks.py
│   │   │   ├── data_quality.py
│   │   │   └── executor.py
│   │   └── main.py
│   ├── main.py
│   └── requirements.txt
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── pages/         # 页面组件
│   │   │   ├── PipelineList.jsx
│   │   │   ├── PipelineDesigner.jsx
│   │   │   └── ExecutionMonitor.jsx
│   │   ├── services/      # API服务
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## 快速开始

### 后端启动

1. 进入后端目录并创建虚拟环境
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 启动Prefect服务（可选）
```bash
prefect server start
```

4. 启动后端服务
```bash
python main.py
```

后端服务将运行在 http://localhost:8000
API文档: http://localhost:8000/docs

### 前端启动

1. 进入前端目录
```bash
cd frontend
```

2. 安装依赖
```bash
npm install
```

3. 启动开发服务器
```bash
npm run dev
```

前端服务将运行在 http://localhost:5173

## 使用说明

### 1. 创建管道
- 进入"管道管理"页面
- 点击"新建管道"创建新的数据管道
- 点击"设计"进入可视化设计界面

### 2. 设计管道
- 从左侧任务面板拖拽任务节点到画布
- 连接节点形成数据流
- 点击节点配置参数
- 保存管道配置

### 3. 运行管道
- 在设计界面点击"运行"
- 或在管道列表点击运行按钮

### 4. 监控执行
- 进入"执行监控"页面
- 选择管道查看执行历史
- 点击执行记录查看任务详情
- 失败任务支持"断点续跑"

## 支持的任务类型

### 数据提取
- `extract_csv`: CSV文件提取
- `extract_database`: 数据库提取

### 数据转换
- `transform_filter`: 数据过滤
- `transform_rename`: 字段重命名
- `transform_select`: 字段选择
- `transform_join`: 数据合并

### 数据加载
- `load_csv`: CSV文件导出
- `load_database`: 数据库导出

### 数据质量检查
- `check_null_values`: 空值检查
- `check_duplicates`: 重复数据检查
- `check_range`: 数值范围检查
- `check_regex`: 正则表达式检查
- `check_unique`: 唯一性检查

## API接口

### 管道管理
- `GET /api/pipelines` - 获取管道列表
- `POST /api/pipelines` - 创建管道
- `GET /api/pipelines/{id}` - 获取管道详情
- `PUT /api/pipelines/{id}` - 更新管道
- `DELETE /api/pipelines/{id}` - 删除管道
- `POST /api/pipelines/{id}/run` - 运行管道

### 执行监控
- `GET /api/pipelines/{id}/executions` - 获取执行记录
- `GET /api/pipelines/executions/{id}/tasks` - 获取任务详情
- `GET /api/pipelines/executions/{id}/resume-checkpoint` - 获取检查点

## 开发说明

### 添加新任务类型
1. 在 `backend/app/pipelines/tasks.py` 添加任务函数
2. 在前端 `PipelineDesigner.jsx` 的 `taskTypes` 数组添加配置
3. 添加节点配置表单

### 扩展数据质量检查
1. 在 `backend/app/pipelines/data_quality.py` 添加检查函数
2. 注册到 `DATA_QUALITY_REGISTRY`
3. 前端添加对应节点配置

## 许可证

MIT License
