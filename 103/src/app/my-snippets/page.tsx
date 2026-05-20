'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import SnippetCard from '@/components/SnippetCard'

interface Snippet {
  id: string
  title: string
  description: string | null
  code: string
  language: string
  isPublic: boolean
  createdAt: string
  author: {
    id: string
    name: string | null
    email: string
  }
}

export default function MySnippetsPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [snippets, setSnippets] = useState<Snippet[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  // 获取用户片段
  const fetchSnippets = useCallback(async () => {
    if (status !== 'authenticated') return

    setIsLoading(true)
    try {
      const response = await fetch('/api/user/snippets')
      if (response.ok) {
        const data = await response.json()
        setSnippets(data)
      }
    } catch (error) {
      console.error('Failed to fetch snippets:', error)
    } finally {
      setIsLoading(false)
    }
  }, [status])

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login')
    }
  }, [status, router])

  useEffect(() => {
    fetchSnippets()
  }, [fetchSnippets])

  // 删除片段（带实时更新）
  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除这个代码片段吗？')) return

    setDeletingId(id)
    try {
      const response = await fetch(`/api/snippets/${id}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        // 乐观更新 UI
        setSnippets(prev => prev.filter(s => s.id !== id))
      }
    } catch (error) {
      console.error('Failed to delete snippet:', error)
    } finally {
      setDeletingId(null)
    }
  }

  if (status === 'loading' || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-500">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">My Snippets</h1>
          <p className="text-gray-600">Manage your code snippets</p>
        </div>
        <button
          onClick={fetchSnippets}
          className="px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition"
          title="刷新列表"
        >
          🔄 刷新
        </button>
      </div>

      {snippets.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow-md">
          <p className="text-gray-500 text-lg mb-4">
            You haven't created any snippets yet
          </p>
          <a
            href="/snippets/new"
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition inline-block"
          >
            Create Your First Snippet
          </a>
        </div>
      ) : (
        <>
          <p className="text-gray-500 mb-4">共 {snippets.length} 个代码片段</p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {snippets.map((snippet) => (
              <div key={snippet.id} className="relative">
                <SnippetCard snippet={snippet as any} />
                {/* 删除按钮覆盖层 */}
                <button
                  onClick={() => handleDelete(snippet.id)}
                  disabled={deletingId === snippet.id}
                  className="absolute top-4 right-4 p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition disabled:opacity-50"
                  title="删除片段"
                >
                  {deletingId === snippet.id ? (
                    <span className="animate-spin">⏳</span>
                  ) : (
                    <span>🗑️</span>
                  )}
                </button>
                {/* 公开/私有标识 */}
                <div className="absolute bottom-4 right-4">
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    snippet.isPublic
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {snippet.isPublic ? '公开' : '私有'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

