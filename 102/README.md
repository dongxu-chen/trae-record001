# Vue 3 个人博客主题

一个基于 Vue 3 + TypeScript + Vite + TailwindCSS 的响应式个人博客主题。

## 功能特性

- ✅ 响应式设计，完美适配移动端和桌面端
- ✅ 深色/浅色主题切换
- ✅ 文章列表页，支持分页
- ✅ 按分类和标签筛选文章
- ✅ 文章详情页，支持 Markdown 渲染和代码高亮
- ✅ 关于页面
- ✅ 友链页面
- ✅ 所有数据从前端 Mock 获取

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **TypeScript** - 类型安全的 JavaScript 超集
- **Vite** - 下一代前端构建工具
- **Vue Router** - Vue.js 官方路由管理器
- **TailwindCSS** - 原子化 CSS 框架
- **Marked** - Markdown 解析器
- **Highlight.js** - 代码语法高亮

## 快速开始

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

### 预览生产版本

```bash
npm run preview
```

## 项目结构

```
src/
├── components/          # 组件目录
│   ├── ArticleCard.vue # 文章卡片组件
│   ├── Footer.vue      # 页脚组件
│   ├── NavBar.vue      # 导航栏组件
│   ├── Pagination.vue  # 分页组件
│   └── Sidebar.vue     # 侧边栏组件
├── composables/         # 组合式函数
│   └── useTheme.ts     # 主题切换逻辑
├── mock/               # Mock 数据
│   └── index.ts        # 模拟文章、分类、标签和友链数据
├── router/             # 路由配置
│   └── index.ts
├── types/              # TypeScript 类型定义
│   └── index.ts
├── views/              # 页面组件
│   ├── AboutView.vue   # 关于页面
│   ├── ArticleView.vue # 文章详情页
│   ├── FriendsView.vue # 友链页面
│   └── HomeView.vue    # 首页/文章列表页
├── App.vue             # 根组件
├── main.ts             # 入口文件
└── style.css           # 全局样式
```

## 使用说明

### 主题切换

点击导航栏右上角的图标即可在深色和浅色主题之间切换。主题偏好会保存在本地存储中。

### 文章筛选

- **按分类筛选**: 在侧边栏点击分类名称即可筛选该分类下的文章
- **按标签筛选**: 在侧边栏点击标签即可筛选包含该标签的文章
- **清除筛选**: 再次点击已选中的分类或标签即可清除筛选

### 分页

每页显示 4 篇文章，通过分页导航切换页面。

## 自定义数据

所有数据都在 `src/mock/index.ts` 文件中定义，你可以根据自己的需求修改：

- `mockArticles` - 文章数据
- `mockCategories` - 分类数据
- `mockTags` - 标签数据
- `mockFriendLinks` - 友链数据

## 浏览器支持

- Chrome (推荐)
- Firefox
- Safari
- Edge

## 许可证

MIT
