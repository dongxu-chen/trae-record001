import { Suspense } from 'react'
import { getPublicSnippets, getHotSnippets, getAvailableLanguages } from '@/lib/services/snippetService'
import SnippetCard from '@/components/SnippetCard'
import SearchFilter from '@/components/SearchFilter'
import Link from 'next/link'

interface HomePageProps {
  searchParams: {
    search?: string
    language?: string
  }
}

// 热门片段组件 - 服务端渲染，带缓存
async function HotSnippets() {
  const hotSnippets = await getHotSnippets()

  if (hotSnippets.length === 0) return null

  return (
    <section className="mb-12">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <span>🔥</span> 热门片段
          <span className="text-xs bg-blue-100 text-blue-600 px-2 py-1 rounded-full ml-2">
            已缓存
          </span>
        </h2>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {hotSnippets.slice(0, 8).map((snippet: any) => (
          <Link key={snippet.id} href={`/snippets/${snippet.id}`}>
            <div className="bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow border-l-4 border-orange-400 h-full">
              <h3 className="font-semibold text-gray-800 mb-2 truncate">
                {snippet.title}
              </h3>
              <div className="flex items-center justify-between text-sm">
                <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded text-xs">
                  {snippet.language}
                </span>
                <span className="text-gray-500 flex items-center gap-1">
                  ❤️ {snippet._count?.likes || 0}
                </span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </section>
  )
}

export default async function HomePage({ searchParams }: HomePageProps) {
  const { search = '', language = '' } = searchParams

  // 并行获取数据 - 服务端直接查询
  const [snippets, languageList] = await Promise.all([
    getPublicSnippets(search, language),
    getAvailableLanguages()
  ])

  const hasFilter = search || language

  return (
    <div>
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-800 mb-4">
          Discover & Share Code Snippets
        </h1>
        <p className="text-gray-600 text-lg">
          Find useful code snippets from the community or share your own
        </p>
      </div>

      {/* 热门片段区域 - Redis 缓存 */}
      {!hasFilter && (
        <Suspense fallback={<div>Loading hot snippets...</div>}>
          <HotSnippets />
        </Suspense>
      )}

      {/* 搜索和筛选 */}
      <Suspense fallback={<div>Loading filter...</div>}>
        <SearchFilter languages={languageList} />
      </Suspense>

      {/* 最新片段列表 */}
      {hasFilter ? (
        <h2 className="text-2xl font-bold text-gray-800 mb-6">
          搜索结果
        </h2>
      ) : (
        <h2 className="text-2xl font-bold text-gray-800 mb-6">
          最新片段
        </h2>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {snippets.map((snippet: any) => (
          <SnippetCard key={snippet.id} snippet={snippet} />
        ))}
      </div>

      {snippets.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500 text-lg">No snippets found</p>
        </div>
      )}
    </div>
  )
}

// 强制动态渲染以确保搜索功能正常工作
export const dynamic = 'force-dynamic'

