import type { Article, Category, Tag } from '../types'

const mockArticles: Article[] = [
  {
    id: 1,
    title: 'Vue 3 组合式 API 完全指南',
    excerpt: '深入了解 Vue 3 的组合式 API，包括 setup 函数、响应式系统、生命周期钩子等核心概念。',
    content: `# Vue 3 组合式 API 完全指南\n\nVue 3 引入了组合式 API（Composition API），这是一种新的编写组件逻辑的方式。\n\n## 什么是组合式 API\n\n组合式 API 是一组基于函数的 API，允许我们灵活地组合组件逻辑。与选项式 API 相比，它提供了更好的代码组织和逻辑复用。\n\n### setup 函数\n\n\`setup\` 函数是组合式 API 的入口点：\n\n\`\`\`javascript\nimport { ref, onMounted } from 'vue'\n\nexport default {\n  setup() {\n    const count = ref(0)\n    \n    function increment() {\n      count.value++\n    }\n    \n    onMounted(() => {\n      console.log('Component mounted!')\n    })\n    \n    return { count, increment }\n  }\n}\n\`\`\`\n\n## 响应式系统\n\nVue 3 提供了两种创建响应式数据的方式：\n\n1. **ref** - 用于基本类型\n2. **reactive** - 用于对象\n\n### 使用 ref\n\n\`\`\`typescript\nconst count = ref(0)\nconsole.log(count.value) // 0\n\ncount.value++\nconsole.log(count.value) // 1\n\`\`\`\n\n## 生命周期钩子\n\n组合式 API 中的生命周期钩子以 \`on\` 开头：\n\n- onMounted\n- onUpdated\n- onUnmounted\n- onBeforeMount\n- onBeforeUpdate\n- onBeforeUnmount\n\n> 组合式 API 让我们能够更好地组织代码，特别是在处理复杂组件时。\n\n## 总结\n\n组合式 API 是 Vue 3 的一大亮点，它提供了：\n\n- 更好的代码组织\n- 更灵活的逻辑复用\n- 更好的 TypeScript 支持\n`,
    category: 'Vue',
    tags: ['Vue3', 'Composition API', 'JavaScript'],
    coverImage: 'https://picsum.photos/seed/vue3/800/400',
    createdAt: '2024-01-15',
    readTime: 8,
    author: '博主',
  },
  {
    id: 2,
    title: 'TypeScript 高级类型技巧',
    excerpt: '探索 TypeScript 中的高级类型特性，包括泛型、条件类型、映射类型等。',
    content: `# TypeScript 高级类型技巧\n\nTypeScript 的类型系统非常强大，让我们来探索一些高级特性。\n\n## 泛型\n\n泛型允许我们创建可重用的组件：\n\n\`\`\`typescript\nfunction identity<T>(arg: T): T {\n  return arg\n}\n\nconst num = identity<number>(42)\nconst str = identity<string>('hello')\n\`\`\`\n\n## 条件类型\n\n条件类型允许我们根据条件选择类型：\n\n\`\`\`typescript\ntype IsString<T> = T extends string ? true : false\n\ntype A = IsString<'hello'> // true\ntype B = IsString<42>      // false\n\`\`\`\n\n## 映射类型\n\n映射类型可以将一个类型的所有属性转换为另一种形式：\n\n\`\`\`typescript\ntype Readonly<T> = {\n  readonly [P in keyof T]: T[P]\n}\n\ninterface Person {\n  name: string\n  age: number\n}\n\ntype ReadonlyPerson = Readonly<Person>\n\`\`\`\n`,
    category: 'TypeScript',
    tags: ['TypeScript', '类型系统', '前端'],
    coverImage: 'https://picsum.photos/seed/typescript/800/400',
    createdAt: '2024-01-12',
    readTime: 6,
    author: '博主',
  },
  {
    id: 3,
    title: 'TailwindCSS 最佳实践',
    excerpt: '学习如何高效使用 TailwindCSS，包括组件提取、自定义配置和性能优化。',
    content: `# TailwindCSS 最佳实践\n\nTailwindCSS 是一个功能类优先的 CSS 框架，以下是一些最佳实践。\n\n## 组件提取\n\n当功能类组合重复出现时，考虑提取为组件：\n\n\`\`\`vue\n<template>\n  <button class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">\n    Click me\n  </button>\n</template>\n\`\`\`\n\n## 自定义配置\n\n在 \`tailwind.config.js\` 中自定义主题：\n\n\`\`\`javascript\nmodule.exports = {\n  theme: {\n    extend: {\n      colors: {\n        primary: '#3b82f6'\n      }\n    }\n  }\n}\n\`\`\`\n\n## 性能优化\n\n1. 使用 PurgeCSS 移除未使用的样式\n2. 合理使用 @apply\n3. 避免深层嵌套\n`,
    category: 'CSS',
    tags: ['TailwindCSS', 'CSS', '样式'],
    coverImage: 'https://picsum.photos/seed/tailwind/800/400',
    createdAt: '2024-01-10',
    readTime: 5,
    author: '博主',
  },
  {
    id: 4,
    title: 'Vite 构建工具深度解析',
    excerpt: '了解 Vite 的工作原理，以及如何利用其特性提升开发体验。',
    content: `# Vite 构建工具深度解析\n\nVite 是新一代前端构建工具，提供了极快的开发体验。\n\n## 为什么选择 Vite\n\n- 快速的冷启动\n- 即时的模块热更新\n- 真正的按需编译\n\n## 工作原理\n\nVite 利用浏览器原生 ES 模块支持，避免了打包步骤。\n\n## 配置示例\n\n\`\`\`javascript\nimport { defineConfig } from 'vite'\nimport vue from '@vitejs/plugin-vue'\n\nexport default defineConfig({\n  plugins: [vue()],\n  server: {\n    port: 3000\n  }\n})\n\`\`\`\n`,
    category: '工具',
    tags: ['Vite', '构建工具', '前端'],
    coverImage: 'https://picsum.photos/seed/vite/800/400',
    createdAt: '2024-01-08',
    readTime: 7,
    author: '博主',
  },
]

const mockCategories: Category[] = [
  { name: 'Vue', count: 1 },
  { name: 'TypeScript', count: 1 },
  { name: 'CSS', count: 1 },
  { name: '工具', count: 1 },
  { name: 'React', count: 1 },
  { name: 'Node.js', count: 1 },
]

const mockTags: Tag[] = [
  { name: 'Vue3', count: 1 },
  { name: 'Composition API', count: 1 },
  { name: 'JavaScript', count: 2 },
  { name: 'TypeScript', count: 1 },
  { name: '类型系统', count: 1 },
  { name: '前端', count: 3 },
  { name: 'TailwindCSS', count: 1 },
  { name: 'CSS', count: 1 },
  { name: '样式', count: 1 },
  { name: 'Vite', count: 1 },
  { name: '构建工具', count: 1 },
  { name: 'React', count: 1 },
  { name: 'Hooks', count: 1 },
  { name: 'Node.js', count: 1 },
  { name: '性能优化', count: 1 },
  { name: '后端', count: 1 },
]

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export interface ArticleListParams {
  category?: string | null
  tag?: string | null
  page?: number
  pageSize?: number
}

export interface ArticleListResponse {
  articles: Article[]
  total: number
  page: number
  pageSize: number
}

export const fetchArticles = async (
  params: ArticleListParams = {}
): Promise<ArticleListResponse> => {
  await delay(300)
  console.log('[API] Fetching articles with params:', params)

  let filtered = [...mockArticles]

  if (params.category) {
    filtered = filtered.filter((a) => a.category === params.category)
  }

  if (params.tag) {
    filtered = filtered.filter((a) => a.tags.includes(params.tag!))
  }

  const page = params.page || 1
  const pageSize = params.pageSize || 4
  const start = (page - 1) * pageSize
  const end = start + pageSize

  return {
    articles: filtered.slice(start, end),
    total: filtered.length,
    page,
    pageSize,
  }
}

export const fetchArticleById = async (id: number): Promise<Article | null> => {
  await delay(400)
  console.log(`[API] Fetching article ${id}`)
  return mockArticles.find((a) => a.id === id) || null
}

export const fetchCategories = async (): Promise<Category[]> => {
  await delay(200)
  console.log('[API] Fetching categories')
  return mockCategories
}

export const fetchTags = async (): Promise<Tag[]> => {
  await delay(200)
  console.log('[API] Fetching tags')
  return mockTags
}
