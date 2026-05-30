import { useState, useCallback } from 'react'
import { useDiffStore } from '@/store/diffStore'
import { useConflictStore } from '@/store/conflictPlaybackStore'
import { useCommentStore } from '@/store/commentStore'
import { LANGUAGE_OPTIONS, SAMPLE_OLD_CODE, SAMPLE_NEW_CODE } from '@/utils/languages'
import {
  Code2,
  FolderTree,
  Play,
  RotateCcw,
  MessageSquare,
  AlertTriangle,
  GitCommitHorizontal,
} from 'lucide-react'

export default function Toolbar() {
  const {
    mode,
    setMode,
    language,
    setLanguage,
    oldCode,
    newCode,
    diffStats,
    isComparing,
    setIsComparing,
    editorLayout,
    setEditorLayout,
    setNewCode,
  } = useDiffStore()

  const { commentPanelOpen, toggleCommentPanel, comments } = useCommentStore()
  const { parseConflicts, hasConflicts } = useConflictStore()

  const [showReview, setShowReview] = useState(false)
  const [showConflict, setShowConflict] = useState(false)
  const [showPlayback, setShowPlayback] = useState(false)

  const unresolvedCount = comments.filter((c) => !c.resolved).length

  const handleCompare = useCallback(() => {
    if (!oldCode && !newCode) return
    setIsComparing(!isComparing)
    if (!isComparing && newCode) {
      parseConflicts(newCode)
    }
  }, [oldCode, newCode, isComparing, setIsComparing, parseConflicts])

  const handleReset = useCallback(() => {
    useDiffStore.getState().reset()
    useCommentStore.getState().clearComments()
    useConflictStore.getState().resetConflicts()
    useConflictStore.getState().reset && useConflictStore.getState().resetConflicts()
  }, [])

  const handleToggleReview = useCallback(() => {
    const next = !showReview
    setShowReview(next)
    if (next) {
      useCommentStore.getState().setCommentPanelOpen(true)
    } else {
      useCommentStore.getState().setCommentPanelOpen(false)
    }
  }, [showReview])

  const handleToggleConflict = useCallback(() => {
    const next = !showConflict
    setShowConflict(next)
    if (next && newCode) {
      parseConflicts(newCode)
    }
  }, [showConflict, newCode, parseConflicts])

  return (
    <div className="h-12 bg-[#1a1a2e] border-b border-[#2a2a4a] flex items-center px-4 gap-3 shrink-0">
      <div className="flex items-center gap-1 mr-2">
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
          <Code2 size={14} className="text-white" />
        </div>
        <span className="text-sm font-semibold text-white tracking-wide font-['IBM_Plex_Sans']">
          CodeDiff
        </span>
      </div>

      <div className="h-5 w-px bg-[#2a2a4a]" />

      <div className="flex items-center bg-[#0d0d1a] rounded-lg p-0.5">
        <button
          onClick={() => setMode('code')}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all duration-200 ${
            mode === 'code'
              ? 'bg-violet-600 text-white shadow-md shadow-violet-600/30'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Code2 size={12} />
          代码对比
        </button>
        <button
          onClick={() => setMode('directory')}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all duration-200 ${
            mode === 'directory'
              ? 'bg-violet-600 text-white shadow-md shadow-violet-600/30'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <FolderTree size={12} />
          目录树对比
        </button>
      </div>

      <div className="h-5 w-px bg-[#2a2a4a]" />

      <select
        value={language}
        onChange={(e) => setLanguage(e.target.value)}
        className="bg-[#0d0d1a] text-zinc-300 text-xs rounded-lg px-2.5 py-1.5 border border-[#2a2a4a] focus:border-violet-500 focus:outline-none cursor-pointer hover:border-zinc-500 transition-colors"
      >
        {LANGUAGE_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      <div className="h-5 w-px bg-[#2a2a4a]" />

      <div className="flex items-center bg-[#0d0d1a] rounded-lg p-0.5">
        <button
          onClick={() => setEditorLayout('side-by-side')}
          className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all duration-200 ${
            editorLayout === 'side-by-side'
              ? 'bg-violet-600 text-white shadow-md shadow-violet-600/30'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          并排
        </button>
        <button
          onClick={() => setEditorLayout('inline')}
          className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all duration-200 ${
            editorLayout === 'inline'
              ? 'bg-violet-600 text-white shadow-md shadow-violet-600/30'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          内联
        </button>
      </div>

      <div className="h-5 w-px bg-[#2a2a4a]" />

      <div className="flex items-center gap-1">
        <button
          onClick={handleToggleReview}
          className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-all duration-200 ${
            showReview
              ? 'bg-violet-600/20 text-violet-300 border border-violet-500/30'
              : 'text-zinc-400 hover:text-zinc-200 border border-transparent'
          }`}
          title="代码评审"
        >
          <MessageSquare size={12} />
          评审
          {unresolvedCount > 0 && (
            <span className="px-1 rounded-full bg-amber-500/20 text-amber-300 text-[9px]">
              {unresolvedCount}
            </span>
          )}
        </button>

        <button
          onClick={handleToggleConflict}
          className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-all duration-200 ${
            showConflict
              ? 'bg-amber-600/20 text-amber-300 border border-amber-500/30'
              : 'text-zinc-400 hover:text-zinc-200 border border-transparent'
          }`}
          title="合并冲突"
        >
          <AlertTriangle size={12} />
          冲突
          {hasConflicts && (
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
          )}
        </button>

        <button
          onClick={() => setShowPlayback(!showPlayback)}
          className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-all duration-200 ${
            showPlayback
              ? 'bg-cyan-600/20 text-cyan-300 border border-cyan-500/30'
              : 'text-zinc-400 hover:text-zinc-200 border border-transparent'
          }`}
          title="代码演变回放"
        >
          <GitCommitHorizontal size={12} />
          回放
        </button>
      </div>

      <div className="flex-1" />

      {diffStats && isComparing && (
        <div className="flex items-center gap-3 text-xs">
          <span className="text-emerald-400 font-medium">+{diffStats.additions}</span>
          <span className="text-red-400 font-medium">-{diffStats.deletions}</span>
          <span className="text-zinc-400">{diffStats.changes} 处变更</span>
        </div>
      )}

      <button
        onClick={handleCompare}
        disabled={!oldCode && !newCode}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
          isComparing
            ? 'bg-amber-600 text-white hover:bg-amber-500 shadow-md shadow-amber-600/30'
            : 'bg-violet-600 text-white hover:bg-violet-500 shadow-md shadow-violet-600/30 disabled:opacity-40 disabled:cursor-not-allowed'
        }`}
      >
        <Play size={12} />
        {isComparing ? '编辑' : '对比'}
      </button>

      <button
        onClick={handleReset}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-white hover:bg-[#2a2a4a] transition-all duration-200"
      >
        <RotateCcw size={12} />
      </button>
    </div>
  )
}
