import { create } from 'zustand'
import type { ReviewComment, ReviewReply } from '@/types'

const REVIEWERS = [
  { name: '张伟', avatar: '🧑‍💻' },
  { name: '李明', avatar: '👩‍💻' },
  { name: '王芳', avatar: '👨‍💻' },
  { name: '赵静', avatar: '👩‍🔬' },
]

interface CommentStore {
  comments: ReviewComment[]
  activeCommentId: string | null
  commentPanelOpen: boolean
  currentReviewer: { name: string; avatar: string }

  addComment: (comment: Omit<ReviewComment, 'id' | 'timestamp' | 'replies' | 'resolved'>) => void
  deleteComment: (id: string) => void
  resolveComment: (id: string) => void
  unresolveComment: (id: string) => void
  addReply: (commentId: string, reply: Omit<ReviewReply, 'id' | 'timestamp'>) => void
  setActiveCommentId: (id: string | null) => void
  toggleCommentPanel: () => void
  setCommentPanelOpen: (open: boolean) => void
  setReviewer: (name: string, avatar: string) => void
  getCommentsForLine: (filePath: string, lineNumber: number, side: 'old' | 'new') => ReviewComment[]
  getCommentsForFile: (filePath: string) => ReviewComment[]
  clearComments: () => void
}

export const useCommentStore = create<CommentStore>((set, get) => ({
  comments: [],
  activeCommentId: null,
  commentPanelOpen: false,
  currentReviewer: REVIEWERS[0],

  addComment: (comment) => {
    const id = `cmt_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    const newComment: ReviewComment = {
      ...comment,
      id,
      timestamp: Date.now(),
      replies: [],
      resolved: false,
    }
    set((s) => ({ comments: [...s.comments, newComment] }))
  },

  deleteComment: (id) => {
    set((s) => ({ comments: s.comments.filter((c) => c.id !== id) }))
  },

  resolveComment: (id) => {
    set((s) => ({
      comments: s.comments.map((c) => (c.id === id ? { ...c, resolved: true } : c)),
    }))
  },

  unresolveComment: (id) => {
    set((s) => ({
      comments: s.comments.map((c) => (c.id === id ? { ...c, resolved: false } : c)),
    }))
  },

  addReply: (commentId, reply) => {
    const replyId = `rpl_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    const newReply: ReviewReply = { ...reply, id: replyId, timestamp: Date.now() }
    set((s) => ({
      comments: s.comments.map((c) =>
        c.id === commentId ? { ...c, replies: [...c.replies, newReply] } : c
      ),
    }))
  },

  setActiveCommentId: (activeCommentId) => set({ activeCommentId }),
  toggleCommentPanel: () => set((s) => ({ commentPanelOpen: !s.commentPanelOpen })),
  setCommentPanelOpen: (commentPanelOpen) => set({ commentPanelOpen }),
  setReviewer: (name, avatar) => set({ currentReviewer: { name, avatar } }),

  getCommentsForLine: (filePath, lineNumber, side) => {
    return get().comments.filter(
      (c) => c.filePath === filePath && c.lineNumber === lineNumber && c.side === side
    )
  },

  getCommentsForFile: (filePath) => {
    return get().comments.filter((c) => c.filePath === filePath)
  },

  clearComments: () => set({ comments: [], activeCommentId: null }),
}))

export { REVIEWERS }
