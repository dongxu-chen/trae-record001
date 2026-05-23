# Markdown 笔记应用

一个功能完整的在线Markdown笔记应用，使用 Next.js + MongoDB + Elasticsearch 构建。

## 功能特性

- ✅ **Markdown实时预览** - 支持实时编辑和预览Markdown内容
- ✅ **多文档管理** - 支持文件夹和标签分类管理笔记
- ✅ **全文搜索** - 基于Elasticsearch的中文分词搜索
- ✅ **笔记导出** - 支持导出为MD、HTML、PDF格式
- ✅ **自动保存** - 防抖自动保存，防止内容丢失
- ✅ **历史版本** - 自动保存笔记历史版本，支持恢复
- ✅ **笔记分享** - 生成公开链接，方便分享笔记

## 技术栈

- **前端**: Next.js 14, React 18, Tailwind CSS
- **后端**: Next.js API Routes
- **数据库**: MongoDB (Mongoose ODM)
- **搜索引擎**: Elasticsearch (IK中文分词器)
- **Markdown编辑器**: SimpleMDE + React Markdown

## 环境要求

- Node.js >= 18
- MongoDB >= 4.4
- Elasticsearch >= 8.0 (需安装IK分词器插件)

## 安装步骤

### 1. 安装依赖

```bash
npm install
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

配置内容：

```env
MONGODB_URI=mongodb://localhost:27017/markdown-notes
ELASTICSEARCH_NODE=http://localhost:9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=changeme
NEXT_PUBLIC_BASE_URL=http://localhost:3000
```

### 3. 安装Elasticsearch IK分词器

下载对应版本的IK分词器插件：

```bash
# 进入Elasticsearch插件目录
cd elasticsearch/plugins

# 下载IK分词器（请对应你的Elasticsearch版本）
elasticsearch-plugin install https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v8.12.0/elasticsearch-analysis-ik-8.12.0.zip
```

### 4. 启动服务

确保MongoDB和Elasticsearch服务已启动，然后运行：

```bash
npm run dev
```

访问 http://localhost:3000 即可使用应用。

## 项目结构

```
src/
├── app/
│   ├── api/                    # API路由
│   │   ├── notes/             # 笔记相关API
│   │   ├── folders/           # 文件夹相关API
│   │   ├── tags/              # 标签相关API
│   │   ├── search/            # 搜索API
│   │   └── share/             # 分享API
│   ├── share/[token]/         # 分享页面
│   ├── globals.css            # 全局样式
│   ├── layout.tsx             # 根布局
│   └── page.tsx               # 主页面
├── components/                 # React组件
│   ├── Sidebar.tsx            # 侧边栏
│   ├── Toolbar.tsx            # 工具栏
│   ├── NoteEditor.tsx         # 笔记编辑器
│   ├── MarkdownEditor.tsx     # Markdown编辑器
│   └── SearchResults.tsx      # 搜索结果
├── hooks/                      # 自定义Hooks
│   └── useDebounce.ts         # 防抖Hook
├── lib/                        # 工具库
│   ├── mongodb.ts             # MongoDB连接
│   └── elasticsearch.ts       # Elasticsearch连接
├── models/                     # 数据模型
│   ├── Note.ts                # 笔记模型
│   ├── Folder.ts              # 文件夹模型
│   ├── Tag.ts                 # 标签模型
│   ├── Version.ts             # 版本模型
│   └── Share.ts               # 分享模型
└── types/                      # TypeScript类型定义
    └── index.ts
```

## 📚 API文档

### 笔记管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/notes` | 获取所有笔记 |
| POST | `/api/notes` | 创建笔记 |
| GET | `/api/notes/:id` | 获取笔记详情 |
| PUT | `/api/notes/:id` | 更新笔记 |
| DELETE | `/api/notes/:id` | 删除笔记 |

### 文件夹/标签管理

- `GET/POST /api/folders` - 文件夹列表/创建
- `PUT/DELETE /api/folders/:id` - 文件夹更新/删除
- `GET/POST /api/tags` - 标签列表/创建
- `PUT/DELETE /api/tags/:id` - 标签更新/删除

### 搜索

- `GET /api/search?q=关键词` - 全文搜索（Jieba中文分词 + TF-IDF排序）

### 导出

- `GET /api/notes/:id/export?format=md` - 导出为Markdown
- `GET /api/notes/:id/export?format=html` - 导出为HTML
- `GET /api/notes/:id/export?format=pdf` - 导出为PDF

### 版本管理

- `GET /api/notes/:id/versions` - 获取历史版本列表（自动重建完整内容）
- `GET /api/notes/:id/versions?compare=v1,v2` - 对比两个版本差异

### 分享管理

- `GET/POST /api/notes/:id/share` - 获取/切换分享状态
- `DELETE /api/notes/:id/share` - 取消分享
- `GET /api/share/:token` - 获取分享的笔记内容

## 📖 使用说明

1. **创建笔记**: 点击左侧"新建笔记"按钮创建新笔记
2. **编辑笔记**: 在编辑器中编写Markdown内容，支持实时预览
3. **分类管理**: 使用文件夹和标签对笔记进行分类
4. **搜索笔记**: 在顶部搜索框输入关键词进行全文搜索
5. **导出笔记**: 点击工具栏"导出"按钮选择导出格式
6. **分享笔记**: 点击"分享"按钮生成公开链接
7. **历史版本**: 点击"历史版本"查看和恢复之前的版本
8. **版本对比**: 在历史版本列表中点击"对比"按钮，选择两个版本查看差异

## ⚠️ 注意事项

### 自动保存机制
- 防抖时间: **5秒**（标题和内容统一）
- 本地缓存: 实时写入localStorage
- 同步策略: 防抖触发后写入数据库，同步成功清除本地缓存
- 冲突处理: 优先使用时间戳较新的版本

### 版本存储策略
- 每 **10个版本** 保存一次完整版本
- 其余版本保存与上一版本的差异补丁（Diff）
- 读取时自动从最近的完整版本开始重建
- 支持任意两个版本的差异对比

### 搜索实现
- 使用 **@node-rs/jieba** (Rust实现) 进行中文分词
- MongoDB原生倒排索引存储
- TF-IDF算法计算相关性得分
- 支持搜索结果高亮显示

## 📄 License

MIT
