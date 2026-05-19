import type { Article, Category, Tag, FriendLink } from '../types'

export const mockArticles: Article[] = [
  {
    id: 1,
    title: 'Vue 3 组合式 API 完全指南',
    excerpt: '深入了解 Vue 3 的组合式 API，包括 setup 函数、响应式系统、生命周期钩子等核心概念。',
    content: `# Vue 3 组合式 API 完全指南

Vue 3 引入了组合式 API（Composition API），这是一种新的编写组件逻辑的方式。

## 什么是组合式 API

组合式 API 是一组基于函数的 API，允许我们灵活地组合组件逻辑。与选项式 API 相比，它提供了更好的代码组织和逻辑复用。

### setup 函数

\`setup\` 函数是组合式 API 的入口点：

\`\`\`javascript
import { ref, onMounted } from 'vue'

export default {
  setup() {
    const count = ref(0)
    
    function increment() {
      count.value++
    }
    
    onMounted(() => {
      console.log('Component mounted!')
    })
    
    return { count, increment }
  }
}
\`\`\`

## 响应式系统

Vue 3 提供了两种创建响应式数据的方式：

1. **ref** - 用于基本类型
2. **reactive** - 用于对象

### 使用 ref

\`\`\`typescript
const count = ref(0)
console.log(count.value) // 0

count.value++
console.log(count.value) // 1
\`\`\`

## 生命周期钩子

组合式 API 中的生命周期钩子以 \`on\` 开头：

- onMounted
- onUpdated
- onUnmounted
- onBeforeMount
- onBeforeUpdate
- onBeforeUnmount

> 组合式 API 让我们能够更好地组织代码，特别是在处理复杂组件时。

## 总结

组合式 API 是 Vue 3 的一大亮点，它提供了：

- 更好的代码组织
- 更灵活的逻辑复用
- 更好的 TypeScript 支持
`,
    category: 'Vue',
    tags: ['Vue3', 'Composition API', 'JavaScript'],
    coverImage: 'https://picsum.photos/seed/vue3/800/400',
    createdAt: '2024-01-15',
    readTime: 8,
    author: '博主'
  },
  {
    id: 2,
    title: 'TypeScript 高级类型技巧',
    excerpt: '探索 TypeScript 中的高级类型特性，包括泛型、条件类型、映射类型等。',
    content: `# TypeScript 高级类型技巧

TypeScript 的类型系统非常强大，让我们来探索一些高级特性。

## 泛型

泛型允许我们创建可重用的组件：

\`\`\`typescript
function identity<T>(arg: T): T {
  return arg
}

const num = identity<number>(42)
const str = identity<string>('hello')
\`\`\`

## 条件类型

条件类型允许我们根据条件选择类型：

\`\`\`typescript
type IsString<T> = T extends string ? true : false

type A = IsString<'hello'> // true
type B = IsString<42>      // false
\`\`\`

## 映射类型

映射类型可以将一个类型的所有属性转换为另一种形式：

\`\`\`typescript
type Readonly<T> = {
  readonly [P in keyof T]: T[P]
}

interface Person {
  name: string
  age: number
}

type ReadonlyPerson = Readonly<Person>
\`\`\`
`,
    category: 'TypeScript',
    tags: ['TypeScript', '类型系统', '前端'],
    coverImage: 'https://picsum.photos/seed/typescript/800/400',
    createdAt: '2024-01-12',
    readTime: 6,
    author: '博主'
  },
  {
    id: 3,
    title: 'TailwindCSS 最佳实践',
    excerpt: '学习如何高效使用 TailwindCSS，包括组件提取、自定义配置和性能优化。',
    content: `# TailwindCSS 最佳实践

TailwindCSS 是一个功能类优先的 CSS 框架，以下是一些最佳实践。

## 组件提取

当功能类组合重复出现时，考虑提取为组件：

\`\`\`vue
<template>
  <button class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
    Click me
  </button>
</template>
\`\`\`

## 自定义配置

在 \`tailwind.config.js\` 中自定义主题：

\`\`\`javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: '#3b82f6'
      }
    }
  }
}
\`\`\`

## 性能优化

1. 使用 PurgeCSS 移除未使用的样式
2. 合理使用 @apply
3. 避免深层嵌套
`,
    category: 'CSS',
    tags: ['TailwindCSS', 'CSS', '样式'],
    coverImage: 'https://picsum.photos/seed/tailwind/800/400',
    createdAt: '2024-01-10',
    readTime: 5,
    author: '博主'
  },
  {
    id: 4,
    title: 'Vite 构建工具深度解析',
    excerpt: '了解 Vite 的工作原理，以及如何利用其特性提升开发体验。',
    content: `# Vite 构建工具深度解析

Vite 是新一代前端构建工具，提供了极快的开发体验。

## 为什么选择 Vite

- 快速的冷启动
- 即时的模块热更新
- 真正的按需编译

## 工作原理

Vite 利用浏览器原生 ES 模块支持，避免了打包步骤。

## 配置示例

\`\`\`javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000
  }
})
\`\`\`
`,
    category: '工具',
    tags: ['Vite', '构建工具', '前端'],
    coverImage: 'https://picsum.photos/seed/vite/800/400',
    createdAt: '2024-01-08',
    readTime: 7,
    author: '博主'
  },
  {
    id: 5,
    title: 'React Hooks 入门教程',
    excerpt: '从零开始学习 React Hooks，掌握 useState、useEffect、useContext 等核心概念。',
    content: `# React Hooks 入门教程

React Hooks 让我们可以在函数组件中使用状态和其他 React 特性。

## useState

\`\`\`jsx
import { useState } from 'react'

function Counter() {
  const [count, setCount] = useState(0)
  
  return (
    <button onClick={() => setCount(count + 1)}>
      Count: {count}
    </button>
  )
}
\`\`\`

## useEffect

\`\`\`jsx
import { useEffect } from 'react'

function Example() {
  useEffect(() => {
    document.title = \`Clicked \${count} times\`
    
    return () => {
      // 清理函数
    }
  }, [count])
}
\`\`\`
`,
    category: 'React',
    tags: ['React', 'Hooks', 'JavaScript'],
    coverImage: 'https://picsum.photos/seed/react/800/400',
    createdAt: '2024-01-05',
    readTime: 9,
    author: '博主'
  },
  {
    id: 6,
    title: 'Node.js 性能优化指南',
    excerpt: '深入探讨 Node.js 应用的性能优化策略，包括异步处理、内存管理和集群模式。',
    content: `# Node.js 性能优化指南

优化 Node.js 应用性能是每个后端开发者必备的技能。

## 异步处理

确保正确使用 async/await：

\`\`\`javascript
async function fetchData() {
  try {
    const data = await fetch('api/data')
    return data.json()
  } catch (error) {
    console.error(error)
  }
}
\`\`\`

## 内存管理

- 避免内存泄漏
- 合理使用缓存
- 监控内存使用

## 集群模式

利用多核 CPU：

\`\`\`javascript
const cluster = require('cluster')
const numCPUs = require('os').cpus().length

if (cluster.isMaster) {
  for (let i = 0; i < numCPUs; i++) {
    cluster.fork()
  }
} else {
  // Worker 代码
}
\`\`\`
`,
    category: 'Node.js',
    tags: ['Node.js', '性能优化', '后端'],
    coverImage: 'https://picsum.photos/seed/nodejs/800/400',
    createdAt: '2024-01-03',
    readTime: 10,
    author: '博主'
  }
]

export const mockCategories: Category[] = [
  { name: 'Vue', count: 1 },
  { name: 'TypeScript', count: 1 },
  { name: 'CSS', count: 1 },
  { name: '工具', count: 1 },
  { name: 'React', count: 1 },
  { name: 'Node.js', count: 1 }
]

export const mockTags: Tag[] = [
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
  { name: '后端', count: 1 }
]

export const mockFriendLinks: FriendLink[] = [
  {
    id: 1,
    name: '张三的博客',
    url: 'https://example.com',
    avatar: 'https://picsum.photos/seed/friend1/100/100',
    description: '一个热爱技术的前端开发者'
  },
  {
    id: 2,
    name: '李四技术栈',
    url: 'https://example.com',
    avatar: 'https://picsum.photos/seed/friend2/100/100',
    description: '分享后端开发经验'
  },
  {
    id: 3,
    name: '王五的全栈之路',
    url: 'https://example.com',
    avatar: 'https://picsum.photos/seed/friend3/100/100',
    description: '全栈开发学习笔记'
  },
  {
    id: 4,
    name: '设计灵感',
    url: 'https://example.com',
    avatar: 'https://picsum.photos/seed/friend4/100/100',
    description: 'UI/UX 设计分享'
  }
]
