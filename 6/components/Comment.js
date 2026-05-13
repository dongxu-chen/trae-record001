import { useState, useCallback, useEffect, useRef } from 'react'
import { createComment, subscribeToPost, publishComment } from '../lib/api'

const MAX_AUTHOR_LENGTH = 50
const MAX_CONTENT_LENGTH = 1000

function sanitizeText(text) {
  if (typeof text !== 'string') {
    return ''
  }
  return text
    .replace(/[<>]/g, '')
    .replace(/javascript:/gi, '')
    .replace(/on\w+="[^"]*"/gi, '')
    .replace(/on\w+='[^']*'/gi, '')
    .trim()
}

function validateAuthor(value) {
  const sanitized = sanitizeText(value)
  if (!sanitized) {
    return { valid: false, message: '请填写昵称' }
  }
  if (sanitized.length > MAX_AUTHOR_LENGTH) {
    return { valid: false, message: `昵称不能超过 ${MAX_AUTHOR_LENGTH} 个字符` }
  }
  return { valid: true, value: sanitized }
}

function validateContent(value) {
  const sanitized = sanitizeText(value)
  if (!sanitized) {
    return { valid: false, message: '请填写评论内容' }
  }
  if (sanitized.length > MAX_CONTENT_LENGTH) {
    return { valid: false, message: `评论内容不能超过 ${MAX_CONTENT_LENGTH} 个字符` }
  }
  return { valid: true, value: sanitized }
}

function CommentItem({ comment, highlight }) {
  const author = sanitizeText(comment.author || '')
  const content = sanitizeText(comment.content || '')
  const dateText = comment.createdAt
    ? new Date(comment.createdAt).toLocaleDateString()
    : ''

  const style = {
    padding: '12px',
    borderBottom: '1px solid #e5e7eb',
    marginBottom: '8px',
    backgroundColor: highlight ? '#eff6ff' : 'transparent',
    transition: 'background-color 0.3s ease'
  }

  return (
    <div style={style}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
        <strong>{author}</strong>
        <span style={{ color: '#6b7280', fontSize: '14px' }}>
          {dateText}
        </span>
      </div>
      <p style={{ margin: '4px 0', color: '#374151', whiteSpace: 'pre-wrap' }}>{content}</p>
    </div>
  )
}

function CommentForm({ postId, onCommentAdded }) {
  const [author, setAuthor] = useState('')
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault()

    if (loading) {
      return
    }

    const authorResult = validateAuthor(author)
    if (!authorResult.valid) {
      setError(authorResult.message)
      return
    }

    const contentResult = validateContent(content)
    if (!contentResult.valid) {
      setError(contentResult.message)
      return
    }

    setLoading(true)
    setError('')

    try {
      const newComment = await createComment(postId, {
        author: authorResult.value,
        content: contentResult.value
      })

      setAuthor('')
      setContent('')
      onCommentAdded(newComment)

      publishComment(postId, newComment)
    } catch (err) {
      setError(err.message || '提交失败，请重试')
    } finally {
      setLoading(false)
    }
  }, [author, content, loading, postId, onCommentAdded])

  return (
    <form onSubmit={handleSubmit} style={{ marginTop: '20px' }}>
      <h3 style={{ marginBottom: '12px' }}>发表评论</h3>

      {error && (
        <div style={{ color: '#dc2626', marginBottom: '12px' }}>{error}</div>
      )}

      <div style={{ marginBottom: '12px' }}>
        <input
          type="text"
          placeholder="您的昵称"
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          maxLength={MAX_AUTHOR_LENGTH}
          disabled={loading}
          autoComplete="off"
          style={{
            width: '100%',
            padding: '8px 12px',
            border: '1px solid #d1d5db',
            borderRadius: '4px'
          }}
        />
      </div>

      <div style={{ marginBottom: '12px' }}>
        <textarea
          placeholder="评论内容"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={4}
          maxLength={MAX_CONTENT_LENGTH}
          disabled={loading}
          style={{
            width: '100%',
            padding: '8px 12px',
            border: '1px solid #d1d5db',
            borderRadius: '4px',
            resize: 'vertical'
          }}
        />
        <div style={{ textAlign: 'right', fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>
          {content.length} / {MAX_CONTENT_LENGTH}
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        style={{
          padding: '8px 16px',
          backgroundColor: loading ? '#9ca3af' : '#2563eb',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: loading ? 'not-allowed' : 'pointer'
        }}
      >
        {loading ? '提交中...' : '发表评论'}
      </button>
    </form>
  )
}

export default function Comments({ postId, initialComments }) {
  const [comments, setComments] = useState(initialComments || [])
  const highlightIdRef = useRef(null)
  const [, forceUpdate] = useState(0)

  useEffect(() => {
    setComments(initialComments || [])
  }, [initialComments, postId])

  const handleCommentAdded = useCallback((newComment) => {
    setComments((prev) => {
      const exists = prev.some((c) => c.id === newComment.id)
      if (exists) {
        return prev
      }
      highlightIdRef.current = newComment.id
      forceUpdate((n) => n + 1)
      setTimeout(() => {
        highlightIdRef.current = null
        forceUpdate((n) => n + 1)
      }, 2000)
      return [...prev, newComment]
    })
  }, [])

  useEffect(() => {
    const unsubscribe = subscribeToPost(postId, handleCommentAdded)
    return () => {
      if (typeof unsubscribe === 'function') {
        unsubscribe()
      }
    }
  }, [postId, handleCommentAdded])

  return (
    <div style={{ marginTop: '40px' }}>
      <h2 style={{ marginBottom: '16px' }}>评论 ({comments.length})</h2>

      {comments.length === 0 ? (
        <p style={{ color: '#6b7280' }}>暂无评论，快来抢沙发！</p>
      ) : (
        <div style={{ marginBottom: '20px' }}>
          {comments.map((comment) => (
            <CommentItem
              key={comment.id || `comment-${Date.now()}-${Math.random()}`}
              comment={comment}
              highlight={comment.id === highlightIdRef.current}
            />
          ))}
        </div>
      )}

      <CommentForm postId={postId} onCommentAdded={handleCommentAdded} />
    </div>
  )
}
