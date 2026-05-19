# 电子书在线阅读系统

基于 Nuxt 3 + EPUB.js + MySQL 构建的电子书在线阅读系统。

## 功能特性

- 📚 **EPUB 文件上传和解析** - 支持上传 EPUB 格式电子书
- 📖 **在线阅读器** - 流畅的阅读体验，支持翻页导航
- 🔤 **字体调整** - 可调节字体大小和行高
- 🎨 **多种主题** - 明亮、护眼、夜间三种阅读主题
- ✨ **笔记标注** - 选中文本添加高亮和批注
- 📍 **阅读进度同步** - 自动保存阅读位置，下次打开继续阅读

## 技术栈

- **前端框架**: Nuxt 3 (Vue 3)
- **电子书解析**: EPUB.js
- **数据库**: MySQL
- **ORM**: Prisma
- **文件上传**: Multer

## 前置要求

- Node.js >= 18
- MySQL >= 5.7
- npm 或 yarn

## 安装步骤

### 1. 安装依赖

```bash
npm install
```

### 2. 配置数据库

编辑 `.env` 文件，配置数据库连接：

```env
DATABASE_URL="mysql://用户名:密码@localhost:3306/ebook_reader"
```

### 3. 初始化数据库

```bash
# 创建数据库
npx prisma db push

# 生成 Prisma Client
npx prisma generate
```

### 4. 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000 即可使用。

## 项目结构

```
ebook-reader/
├── pages/
│   ├── index.vue          # 首页 - 书籍列表
│   └── reader/
│       └── [id].vue       # 阅读器页面
├── server/
│   ├── api/
│   │   ├── books/         # 书籍相关 API
│   │   ├── progress/      # 阅读进度 API
│   │   ├── annotations/   # 笔记标注 API
│   │   └── upload.post.ts # 文件上传 API
│   ├── plugins/
│   │   └── multer.ts      # 文件上传配置
│   └── utils/
│       └── prisma.ts      # Prisma 实例
├── prisma/
│   └── schema.prisma      # 数据库模型
├── uploads/
│   └── books/             # 上传的 EPUB 文件
├── package.json
├── nuxt.config.ts
└── .env
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/books | 获取所有书籍 |
| GET | /api/books/:id | 获取单本书籍信息 |
| GET | /api/books/file/:filename | 获取 EPUB 文件 |
| POST | /api/upload | 上传 EPUB 文件 |
| GET | /api/progress/:bookId | 获取阅读进度 |
| POST | /api/progress | 保存阅读进度 |
| GET | /api/annotations/:bookId | 获取书籍笔记 |
| POST | /api/annotations | 添加笔记 |
| DELETE | /api/annotations/:id | 删除笔记 |

## 数据库模型

### Book (书籍)
- id: 主键
- title: 书名
- author: 作者
- description: 描述
- cover: 封面
- filePath: 文件路径
- createdAt: 创建时间
- updatedAt: 更新时间

### Progress (阅读进度)
- id: 主键
- bookId: 书籍 ID
- location: EPUB CFI 位置
- percentage: 阅读百分比
- createdAt: 创建时间
- updatedAt: 更新时间

### Annotation (笔记标注)
- id: 主键
- bookId: 书籍 ID
- cfi: EPUB CFI 位置
- text: 选中的文本
- note: 批注内容
- color: 高亮颜色
- createdAt: 创建时间
- updatedAt: 更新时间

## 生产构建

```bash
npm run build
npm run preview
```

## 注意事项

1. 确保 MySQL 服务已启动
2. 确保 `uploads/books` 目录有写入权限
3. 支持的文件格式仅限 EPUB
4. 单个文件大小限制为 50MB

## 许可证

MIT
