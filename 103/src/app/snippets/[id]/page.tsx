import { getServerSession } from 'next-auth/next'
import CodeBlock from '@/components/CodeBlock'
import Link from 'next/link'
import DeleteButton from '@/components/DeleteButton'
import LikeButton from '@/components/LikeButton'
import CommentSection from '@/components/CommentSection'
import VersionHistory from '@/components/VersionHistory'
import { getSnippetById, getHotSnippetIds } from '@/lib/services/snippetService'

interface SnippetPageProps {
  params: {
    id: string
  }
}

// 静态生成热门片段页面
export async function generateStaticParams() {
  try {
    const hotIds = await getHotSnippetIds()
    return hotIds
  } catch (error) {
    console.error('generateStaticParams error:', error)
    return []
  }
}

// 配置增量静态再生 - 非热门片段1小时后重新验证
export const revalidate = 3600

// 允许动态渲染未预生成的片段
export const dynamicParams = true

export default async function SnippetPage({ params }: SnippetPageProps) {
  const session = await getServerSession()

  // 使用带缓存的查询
  const snippet = await getSnippetById(params.id)

  if (!snippet) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 text-lg">Snippet not found</p>
      </div>
    )
  }

  const isOwner = session?.user?.email && snippet.author.email === session.user.email

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-md p-8">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-800 mb-2">
              {snippet.title}
            </h1>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span>By {snippet.author.name || snippet.author.email}</span>
              <span>•</span>
              <span>{new Date(snippet.createdAt).toLocaleDateString()}</span>
              <span>•</span>
              <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                {snippet.language}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <LikeButton snippetId={snippet.id} />
            {isOwner && (
              <>
                <Link
                  href={`/snippets/${snippet.id}/edit`}
                  className="bg-yellow-500 text-white px-4 py-2 rounded-lg hover:bg-yellow-600 transition"
                >
                  Edit
                </Link>
                <DeleteButton snippetId={snippet.id} />
              </>
            )}
          </div>
        </div>

        {snippet.description && (
          <p className="text-gray-600 mb-6 text-lg">{snippet.description}</p>
        )}

        <div className="mt-6">
          <CodeBlock code={snippet.code} language={snippet.language} />
        </div>

        {isOwner && <VersionHistory snippetId={snippet.id} isOwner={isOwner} />}
      </div>

      <CommentSection snippetId={snippet.id} isOwner={isOwner || false} />
    </div>
  )
}

