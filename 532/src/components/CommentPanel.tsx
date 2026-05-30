import { useState, useCallback } from 'react'
import { useCommentStore, REVIEWERS } from '@/store/commentStore'
import type { ReviewComment } from '@/types'
import {
  MessageSquare,
  X,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronUp,
  Send,
  Trash2,
  RotateCcw,
  Users,
} from 'lucide-react'

function CommentItem({
  comment,
  isActive,
  onClick,
}: {
  comment: ReviewComment
  isActive: boolean
  onClick: () => void
}) {
  const { resolveComment, unresolveComment, deleteComment, addReply, currentReviewer } =
    useCommentStore()
  const [showReplies, setShowReplies] = useState(false)
  const [replyText, setReplyText] = useState('')

  const handleReply = useCallback(() => {
    if (!replyText.trim()) return
    addReply(comment.id, {
      author: currentReviewer.name,
      avatar: currentReviewer.avatar,
      content: replyText.trim(),
    })
    setReplyText('')
  }, [comment.id, replyText, addReply, currentReviewer])

  const timeStr = new Date(comment.timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <div
      onClick={onClick}
      className={`border rounded-lg transition-all duration-200 cursor-pointer ${
        isActive
          ? 'border-violet-500/50 bg-violet-500/5'
          : comment.resolved
            ? 'border-[#2a2a4a] bg-[#0d0d1a]/50'
            : 'border-[#2a2a4a] bg-[#0d0d1a]'
      }`}
    >
      <div className="px-3 py-2">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-sm">{comment.avatar}</span>
          <span className="text-xs font-semibold text-zinc-300">{comment.author}</span>
          <span className="text-[10px] text-zinc-600 font-['JetBrains_Mono']">
            L{comment.lineNumber} · {comment.side === 'old' ? '旧' : '新'}
          </span>
          <span className="text-[10px] text-zinc-600 ml-auto">{timeStr}</span>
        </div>

        <p className={`text-xs leading-relaxed ${comment.resolved ? 'text-zinc-500 line-through' : 'text-zinc-300'}`}>
          {comment.content}
        </p>

        <div className="flex items-center gap-1.5 mt-2">
          {comment.resolved ? (
            <button
              onClick={(e) => { e.stopPropagation(); unresolveComment(comment.id) }}
              className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] text-emerald-400 hover:bg-emerald-500/10 transition-colors"
            >
              <RotateCcw size={10} />
              重新打开
            </button>
          ) : (
            <button
              onClick={(e) => { e.stopPropagation(); resolveComment(comment.id) }}
              className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] text-zinc-400 hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors"
            >
              <Check size={10} />
              已解决
            </button>
          )}
          <button
            onClick={(e) => { e.stopPropagation(); deleteComment(comment.id) }}
            className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] text-zinc-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <Trash2 size={10} />
          </button>
          {comment.replies.length > 0 && (
            <button
              onClick={(e) => { e.stopPropagation(); setShowReplies(!showReplies) }}
              className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] text-zinc-400 hover:text-zinc-200 transition-colors ml-auto"
            >
              <MessageSquare size={10} />
              {comment.replies.length}
              {showReplies ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
            </button>
          )}
        </div>
      </div>

      {showReplies && comment.replies.length > 0 && (
        <div className="border-t border-[#2a2a4a] px-3 py-2 space-y-2">
          {comment.replies.map((reply) => (
            <div key={reply.id} className="flex gap-2">
              <span className="text-xs shrink-0">{reply.avatar}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-semibold text-zinc-400">{reply.author}</span>
                  <span className="text-[10px] text-zinc-600">
                    {new Date(reply.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <p className="text-[11px] text-zinc-300 leading-relaxed">{reply.content}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {!comment.resolved && (
        <div className="border-t border-[#2a2a4a] px-3 py-2 flex gap-2">
          <input
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleReply() }}
            placeholder="回复..."
            className="flex-1 bg-[#1a1a2e] text-xs text-zinc-300 px-2 py-1 rounded border border-[#2a2a4a] focus:border-violet-500 focus:outline-none placeholder:text-zinc-600"
            onClick={(e) => e.stopPropagation()}
          />
          <button
            onClick={(e) => { e.stopPropagation(); handleReply() }}
            disabled={!replyText.trim()}
            className="p-1 rounded text-zinc-400 hover:text-violet-400 hover:bg-violet-500/10 disabled:opacity-30 transition-colors"
          >
            <Send size={12} />
          </button>
        </div>
      )}
    </div>
  )
}

export default function CommentPanel() {
  const {
    comments,
    activeCommentId,
    commentPanelOpen,
    toggleCommentPanel,
    setActiveCommentId,
    currentReviewer,
    setReviewer,
  } = useCommentStore()

  const unresolved = comments.filter((c) => !c.resolved)
  const resolved = comments.filter((c) => c.resolved)

  if (!commentPanelOpen) return null

  return (
    <div className="w-80 border-l border-[#2a2a4a] bg-[#0d0d1a] flex flex-col shrink-0 animate-fade-in">
      <div className="px-3 py-2 border-b border-[#2a2a4a] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare size={14} className="text-violet-400" />
          <span className="text-xs font-semibold text-zinc-300">代码评审</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-violet-500/20 text-violet-300">
            {unresolved.length}
          </span>
        </div>
        <button
          onClick={toggleCommentPanel}
          className="p-1 rounded text-zinc-500 hover:text-zinc-300 hover:bg-[#2a2a4a] transition-colors"
        >
          <X size={14} />
        </button>
      </div>

      <div className="px-3 py-2 border-b border-[#2a2a4a]">
        <div className="flex items-center gap-1.5 mb-1">
          <Users size={10} className="text-zinc-500" />
          <span className="text-[10px] text-zinc-500">当前评审者</span>
        </div>
        <div className="flex gap-1">
          {REVIEWERS.map((r) => (
            <button
              key={r.name}
              onClick={() => setReviewer(r.name, r.avatar)}
              className={`flex items-center gap-1 px-2 py-1 rounded-md text-[10px] transition-all ${
                currentReviewer.name === r.name
                  ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30'
                  : 'bg-[#1a1a2e] text-zinc-400 hover:text-zinc-300 border border-transparent'
              }`}
            >
              <span className="text-xs">{r.avatar}</span>
              {r.name}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2">
        {comments.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <MessageSquare size={24} className="text-zinc-700 mb-2" />
            <p className="text-xs text-zinc-500">暂无评论</p>
            <p className="text-[10px] text-zinc-600 mt-1">点击代码行号旁的 + 添加评论</p>
          </div>
        ) : (
          <>
            {unresolved.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-[10px] text-zinc-500">
                  <span>未解决</span>
                  <span className="px-1 rounded bg-amber-500/20 text-amber-300">{unresolved.length}</span>
                </div>
                {unresolved.map((c) => (
                  <CommentItem
                    key={c.id}
                    comment={c}
                    isActive={c.id === activeCommentId}
                    onClick={() => setActiveCommentId(c.id === activeCommentId ? null : c.id)}
                  />
                ))}
              </div>
            )}
            {resolved.length > 0 && (
              <div className="space-y-2 mt-3">
                <div className="flex items-center gap-1.5 text-[10px] text-zinc-500">
                  <CheckCheck size={10} />
                  <span>已解决</span>
                  <span className="px-1 rounded bg-emerald-500/20 text-emerald-300">{resolved.length}</span>
                </div>
                {resolved.map((c) => (
                  <CommentItem
                    key={c.id}
                    comment={c}
                    isActive={c.id === activeCommentId}
                    onClick={() => setActiveCommentId(c.id === activeCommentId ? null : c.id)}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
