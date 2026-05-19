import prisma from '@/lib/prisma'
import { cache, CACHE_KEYS } from '@/lib/redis'

// 获取热门片段（带缓存）
export async function getHotSnippets() {
  const cacheKey = CACHE_KEYS.HOT_SNIPPETS
  
  // 尝试从缓存获取
  const cached = await cache.get(cacheKey)
  if (cached) {
    return cached
  }

  // 从数据库获取热门片段（按点赞数排序，取前20个）
  const hotSnippets = await prisma.snippet.findMany({
    where: {
      isPublic: true
    },
    include: {
      author: {
        select: {
          id: true,
          name: true,
          email: true
        }
      },
      _count: {
        select: {
          likes: true
        }
      }
    },
    orderBy: [
      { likes: { _count: 'desc' } },
      { createdAt: 'desc' }
    ],
    take: 20
  })

  // 写入缓存，TTL 5分钟
  await cache.set(cacheKey, hotSnippets, 300)
  
  return hotSnippets
}

// 获取所有公开片段（无缓存，实时查询）
export async function getPublicSnippets(search?: string, language?: string) {
  const where: any = { isPublic: true }

  if (search) {
    where.OR = [
      { title: { contains: search, mode: 'insensitive' } },
      { description: { contains: search, mode: 'insensitive' } },
      { code: { contains: search, mode: 'insensitive' } }
    ]
  }

  if (language) {
    where.language = language
  }

  const snippets = await prisma.snippet.findMany({
    where,
    include: {
      author: {
        select: {
          id: true,
          name: true,
          email: true
        }
      }
    },
    orderBy: {
      createdAt: 'desc'
    }
  })

  return snippets
}

// 获取所有可用语言（带缓存）
export async function getAvailableLanguages() {
  const cacheKey = CACHE_KEYS.LANGUAGES
  
  const cached = await cache.get<string[]>(cacheKey)
  if (cached) {
    return cached
  }

  const languages = await prisma.snippet.findMany({
    where: { isPublic: true },
    select: { language: true },
    distinct: ['language']
  })

  const languageList = languages
    .map((s) => s.language)
    .filter(Boolean)
    .sort() as string[]

  await cache.set(cacheKey, languageList, 600) // 10分钟缓存
  
  return languageList
}

// 获取热门片段ID（用于静态生成）
export async function getHotSnippetIds() {
  const hotSnippets = await getHotSnippets()
  return hotSnippets.map((s: any) => ({ id: s.id }))
}

// 获取单个片段详情（带缓存）
export async function getSnippetById(id: string) {
  const cacheKey = CACHE_KEYS.SNIPPET_DETAIL(id)
  
  const cached = await cache.get(cacheKey)
  if (cached) {
    return cached
  }

  const snippet = await prisma.snippet.findUnique({
    where: { id },
    include: {
      author: {
        select: {
          id: true,
          name: true,
          email: true
        }
      }
    }
  })

  if (snippet) {
    await cache.set(cacheKey, snippet, 300) // 5分钟缓存
  }

  return snippet
}

// 缓存失效：当片段更新或删除时调用
export async function invalidateSnippetCache(snippetId?: string) {
  // 失效热门列表缓存
  await cache.del(CACHE_KEYS.HOT_SNIPPETS)
  await cache.del(CACHE_KEYS.LANGUAGES)
  
  // 失效特定片段缓存
  if (snippetId) {
    await cache.del(CACHE_KEYS.SNIPPET_DETAIL(snippetId))
  }
}

// 获取用户个人片段（带缓存）
export async function getUserSnippets(userId: string) {
  const cacheKey = CACHE_KEYS.USER_SNIPPETS(userId)
  
  const cached = await cache.get(cacheKey)
  if (cached) {
    return cached
  }

  const snippets = await prisma.snippet.findMany({
    where: { authorId: userId },
    include: {
      author: {
        select: {
          id: true,
          name: true,
          email: true
        }
      }
    },
    orderBy: { createdAt: 'desc' }
  })

  await cache.set(cacheKey, snippets, 120) // 2分钟缓存

  return snippets
}
