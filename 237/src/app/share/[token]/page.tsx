'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Note } from '@/types'
import { ArrowLeft, FileText } from 'lucide-react'
import Link from 'next/link'

export default function SharePage() {
  const params = useParams()
  const [note, setNote] = useState<Note | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (params.token) {
      fetchSharedNote()
    }
  }, [params.token])

  const fetchSharedNote = async () => {
    try {
      const res = await fetch(`/api/share/${params.token}`)
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.error || '无法加载分享的笔记')
      }
      const data = await res.json()
      setNote(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">加载中...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <FileText size={64} className="mx-auto mb-4 text-gray-300" />
          <p className="text-gray-500 text-lg">{error}</p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 mt-4 text-blue-600 hover:underline"
          >
            <ArrowLeft size={16} />
            返回首页
          </Link>
        </div>
      </div>
    )
  }

  if (!note) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-800">{note.title}</h1>
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm text-blue-600 hover:underline"
          >
            <ArrowLeft size={16} />
            我的笔记
          </Link>
        </div>
      </div>

      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-white rounded-lg shadow-sm p-8">
          <div className="text-sm text-gray-500 mb-6">
            创建于 {new Date(note.createdAt).toLocaleDateString('zh-CN', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </div>
          <div className="markdown-preview">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{note.content}</ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  )
}
