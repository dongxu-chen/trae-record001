'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import ReactMarkdown from 'react-markdown'

interface Author {
  id: string
  name: string | null
  email: string
}

interface Reply {
  id: string
  content: string
  author: Author
  createdAt: string
}

interface Comment {
  id: string
  content: string
  author: Author
  createdAt: string
  replies: Reply[]
}

interface CommentSectionProps {
  snippetId: string
  isOwner: boolean
}

export default function CommentSection({ snippetId, isOwner }: CommentSectionProps) {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [comments, setComments] = useState<Comment[]>([])
  const [newComment, setNewComment] = useState('')
  const [replyTo, setReplyTo] = useState<string | null>(null)
  const [replyContent, setReplyContent] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    const fetchComments = async () => {
      try {
        const response = await fetch(`/api/snippets/${snippetId}/comments`)
        if (response.ok) {
          const data = await response.json()
          setComments(data)
        }
      } catch (error) {
        console.error('Failed to fetch comments:', error)
      }
    }

    fetchComments()
  }, [snippetId])

  const handleSubmitComment = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newComment.trim()) return

    if (status === 'unauthenticated') {
      router.push('/login')
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch(`/api/snippets/${snippetId}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newComment })
      })

      if (response.ok) {
        const comment = await response.json()
        setComments(prev => [comment, ...prev])
        setNewComment('')
      }
    } catch (error) {
      console.error('Failed to post comment:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleReply = async (parentId: string) => {
    if (!replyContent.trim()) return

    if (status === 'unauthenticated') {
      router.push('/login')
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch(`/api/snippets/${snippetId}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: replyContent, parentId })
      })

      if (response.ok) {
        const newReply = await response.json()
        setComments(prev =>
          prev.map(comment =>
            comment.id === parentId
              ? { ...comment, replies: [...comment.replies, newReply] }
              : comment
          )
        )
        setReplyTo(null)
        setReplyContent('')
      }
    } catch (error) {
      console.error('Failed to post reply:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteComment = async (commentId: string) => {
    if (!confirm('确定删除这条评论吗？')) return

    try {
      const response = await fetch(`/api/snippets/${snippetId}/comments?commentId=${commentId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        setComments(prev =>
          prev
            .filter(comment => comment.id !== commentId)
            .map(comment => ({
              ...comment,
              replies: comment.replies.filter(reply => reply.id !== commentId)
            }))
        )
      }
    } catch (error) {
      console.error('Failed to delete comment:', error)
    }
  }

  return (
    <div className="mt-8">
      <h2 className="text-2xl font-bold mb-6">评论 ({comments.length})</h2>

      {status === 'authenticated' ? (
        <form onSubmit={handleSubmitComment} className="mb-8">
          <textarea
            value={newComment}
            onChange={e => setNewComment(e.target.value)}
            placeholder="写下你的评论...（支持 Markdown）"
            rows={4}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <p className="text-sm text-gray-500 mt-1">支持 Markdown 格式</p>
          <button
            type="submit"
            disabled={isLoading || !newComment.trim()}
            className="mt-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
          >
            发表评论
          </button>
        </form>
      ) : (
        <p className="mb-8 text-gray-600">
          请 <a href="/login" className="text-blue-600 hover:underline">登录</a> 后发表评论
        </p>
      )}

      <div className="space-y-6">
        {comments.map(comment => (
          <div key={comment.id} className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center text-white font-bold">
                  {(comment.author.name || comment.author.email).charAt(0).toUpperCase()}
                </div>
                <div>
                  <p className="font-semibold">{comment.author.name || comment.author.email}</p>
                  <p className="text-sm text-gray-500">
                    {new Date(comment.createdAt).toLocaleString()}
                  </p>
                </div>
              </div>
              {(session?.user?.email && (
                comment.author.email === session.user.email || isOwner
              )) && (
                <button
                  onClick={() => handleDeleteComment(comment.id)}
                  className="text-red-500 hover:text-red-700 text-sm"
                >
                  删除
                </button>
              )}
            </div>

            <div className="prose prose-sm max-w-none">
              <ReactMarkdown>{comment.content}</ReactMarkdown>
            </div>

            {status === 'authenticated' && (
              <button
                onClick={() => setReplyTo(replyTo === comment.id ? null : comment.id)}
                className="mt-4 text-blue-600 hover:text-blue-800 text-sm"
              >
                回复
              </button>
            )}

            {replyTo === comment.id && (
              <div className="mt-4 ml-8">
                <textarea
                  value={replyContent}
                  onChange={e => setReplyContent(e.target.value)}
                  placeholder="写下你的回复..."
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => handleReply(comment.id)}
                    disabled={isLoading || !replyContent.trim()}
                    className="px-4 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 text-sm"
                  >
                    回复
                  </button>
                  <button
                    onClick={() => {
                      setReplyTo(null)
                      setReplyContent('')
                    }}
                    className="px-4 py-1 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition text-sm"
                  >
                    取消
                  </button>
                </div>
              </div>
            )}

            {comment.replies.length > 0 && (
              <div className="mt-4 ml-8 space-y-4">
                {comment.replies.map(reply => (
                  <div key={reply.id} className="bg-gray-50 rounded-lg p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white text-sm font-bold">
                          {(reply.author.name || reply.author.email).charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-semibold text-sm">{reply.author.name || reply.author.email}</p>
                          <p className="text-xs text-gray-500">
                            {new Date(reply.createdAt).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      {(session?.user?.email && (
                        reply.author.email === session.user.email || isOwner
                      )) && (
                        <button
                          onClick={() => handleDeleteComment(reply.id)}
                          className="text-red-500 hover:text-red-700 text-xs"
                        >
                          删除
                        </button>
                      )}
                    </div>
                    <div className="prose prose-xs max-w-none">
                      <ReactMarkdown>{reply.content}</ReactMarkdown>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {comments.length === 0 && (
          <p className="text-center text-gray-500 py-8">暂无评论，来发表第一条评论吧！</p>
        )}
      </div>
    </div>
  )
}
