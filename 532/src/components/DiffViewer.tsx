import { useRef, useCallback, useEffect, useMemo, useState } from 'react'
import { DiffEditor, type DiffOnMount } from '@monaco-editor/react'
import { useDiffStore } from '@/store/diffStore'
import { useCommentStore } from '@/store/commentStore'
import { useConflictStore } from '@/store/conflictPlaybackStore'
import { Loader2, Zap } from 'lucide-react'
import {
  buildLineMappingFromHunks,
  calculateVisibleLineNumber,
  getClosestVisibleLine,
  alignDiffScroll,
  getDiffLineRanges,
  type LineMapping,
  type DiffLineChange,
} from '@/utils/lineMapping'

type DiffEditorInstance = Parameters<DiffOnMount>[0]

const LARGE_FILE_THRESHOLD = 5000
const CHUNK_SIZE = 1000

export default function DiffViewer() {
  const {
    oldCode,
    newCode,
    language,
    editorLayout,
    setDiffStats,
    setCurrentDiffIndex,
    setTotalDiffs,
  } = useDiffStore()

  const editorRef = useRef<DiffEditorInstance | null>(null)
  const decorationsRef = useRef<string[]>([])
  const lineMapRef = useRef<LineMapping | null>(null)
  const lineChangesRef = useRef<DiffLineChange[]>([])

  const [isLargeFile, setIsLargeFile] = useState(false)
  const [isChunking, setIsChunking] = useState(false)

  const oldLineCount = useMemo(() => oldCode.split('\n').length, [oldCode])
  const newLineCount = useMemo(() => newCode.split('\n').length, [newCode])

  useEffect(() => {
    const isLarge = oldLineCount > LARGE_FILE_THRESHOLD || newLineCount > LARGE_FILE_THRESHOLD
    setIsLargeFile(isLarge)
  }, [oldLineCount, newLineCount])

  const computeDiffWithBackend = useCallback(async () => {
    try {
      setIsChunking(true)
      const response = await fetch('/api/diff/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ oldText: oldCode, newText: newCode }),
      })
      const result = await response.json()
      if (result.success) {
        lineMapRef.current = buildLineMappingFromHunks(result.data.hunks)
        setDiffStats(result.data.stats)
        setTotalDiffs(result.data.stats.changes)
        setCurrentDiffIndex(result.data.stats.changes > 0 ? 0 : -1)
      }
    } catch (e) {
      console.warn('Backend diff failed, using frontend diff')
    } finally {
      setIsChunking(false)
    }
  }, [oldCode, newCode, setDiffStats, setTotalDiffs, setCurrentDiffIndex])

  const handleMount = useCallback(
    (editor: DiffEditorInstance) => {
      editorRef.current = editor

      const computeStats = () => {
        const modifications = editor.getLineChanges() as DiffLineChange[]
        lineChangesRef.current = modifications

        const additions = modifications.filter(
          (m) => m.modifiedEndLineNumber > 0 && m.originalEndLineNumber === 0
        ).length
        const deletions = modifications.filter(
          (m) => m.originalEndLineNumber > 0 && m.modifiedEndLineNumber === 0
        ).length
        const changes = modifications.length

        setDiffStats({ additions, deletions, changes })
        setTotalDiffs(changes)
        setCurrentDiffIndex(changes > 0 ? 0 : -1)
      }

      if (isLargeFile) {
        computeDiffWithBackend().then(() => computeStats())
      } else {
        computeStats()
      }

      editor.onDidUpdateDiff(() => {
        computeStats()
      })

      const originalEditor = editor.getOriginalEditor()
      const modifiedEditor = editor.getModifiedEditor()

      const updateCommentDecorations = () => {
        const comments = useCommentStore.getState().comments
        const selectedFile = useDiffStore.getState().selectedFile || ''

        const oldDecorations: any[] = []
        const newDecorations: any[] = []

        for (const comment of comments) {
          if (comment.filePath && comment.filePath !== selectedFile) continue

          const target = comment.side === 'old' ? oldDecorations : newDecorations
          target.push({
            range: {
              startLineNumber: comment.lineNumber,
              startColumn: 1,
              endLineNumber: comment.lineNumber,
              endColumn: 1,
            },
            options: {
              isWholeLine: true,
              glyphMarginClassName: comment.resolved
                ? 'comment-glyph-resolved'
                : 'comment-glyph-unresolved',
              glyphMarginHoverClassName: 'comment-glyph-hover',
              stickiness: 1,
              overviewRuler: {
                color: comment.resolved ? '#4ade80' : '#7c3aed',
                position: 2,
              },
            },
          })
        }

        originalEditor.deltaDecorations([], oldDecorations)
        modifiedEditor.deltaDecorations([], newDecorations)
      }

      const updateConflictDecorations = () => {
        const { conflictRegions, hasConflicts } = useConflictStore.getState()
        if (!hasConflicts) return

        const decorations: any[] = []

        for (const region of conflictRegions) {
          decorations.push({
            range: {
              startLineNumber: region.startLine,
              startColumn: 1,
              endLineNumber: region.endLine,
              endColumn: 1,
            },
            options: {
              isWholeLine: true,
              className: region.resolved ? 'conflict-region-resolved' : 'conflict-region',
              linesDecorationsClassName: 'conflict-line-marker',
              overviewRuler: {
                color: region.resolved ? '#4ade80' : '#f59e0b',
                position: 3,
              },
            },
          })
        }

        modifiedEditor.deltaDecorations([], decorations)
      }

      updateCommentDecorations()
      updateConflictDecorations()

      const unsubComments = useCommentStore.subscribe(() => {
        updateCommentDecorations()
      })
      const unsubConflicts = useConflictStore.subscribe(() => {
        updateConflictDecorations()
      })

      modifiedEditor.onMouseDown((e) => {
        if (e.target.type === 2 || e.target.type === 3) {
          const lineNumber = e.target.position?.lineNumber
          if (lineNumber) {
            const comments = useCommentStore.getState().comments
            const selectedFile = useDiffStore.getState().selectedFile || ''
            const lineComments = comments.filter(
              (c) => c.lineNumber === lineNumber && c.side === 'new' && (!c.filePath || c.filePath === selectedFile)
            )
            if (lineComments.length > 0) {
              useCommentStore.getState().setActiveCommentId(lineComments[0].id)
              useCommentStore.getState().setCommentPanelOpen(true)
            } else {
              const content = prompt(`添加评审评论 (行 ${lineNumber}, 新版本):`)
              if (content) {
                const reviewer = useCommentStore.getState().currentReviewer
                useCommentStore.getState().addComment({
                  filePath: selectedFile,
                  lineNumber,
                  side: 'new',
                  author: reviewer.name,
                  avatar: reviewer.avatar,
                  content,
                })
                useCommentStore.getState().setCommentPanelOpen(true)
              }
            }
          }
        }
      })

      originalEditor.onMouseDown((e) => {
        if (e.target.type === 2 || e.target.type === 3) {
          const lineNumber = e.target.position?.lineNumber
          if (lineNumber) {
            const comments = useCommentStore.getState().comments
            const selectedFile = useDiffStore.getState().selectedFile || ''
            const lineComments = comments.filter(
              (c) => c.lineNumber === lineNumber && c.side === 'old' && (!c.filePath || c.filePath === selectedFile)
            )
            if (lineComments.length > 0) {
              useCommentStore.getState().setActiveCommentId(lineComments[0].id)
              useCommentStore.getState().setCommentPanelOpen(true)
            } else {
              const content = prompt(`添加评审评论 (行 ${lineNumber}, 旧版本):`)
              if (content) {
                const reviewer = useCommentStore.getState().currentReviewer
                useCommentStore.getState().addComment({
                  filePath: selectedFile,
                  lineNumber,
                  side: 'old',
                  author: reviewer.name,
                  avatar: reviewer.avatar,
                  content,
                })
                useCommentStore.getState().setCommentPanelOpen(true)
              }
            }
          }
        }
      })

      editor.onDidDispose(() => {
        unsubComments()
        unsubConflicts()
      })

      const handleScroll = () => {
        if (editorLayout !== 'side-by-side') return

        const activeEditor = originalEditor.isFocused() ? originalEditor : modifiedEditor
        const viewRanges = activeEditor.getVisibleRanges()
        if (viewRanges.length === 0) return

        const visibleLine = viewRanges[0].startLineNumber
        const isOldEditor = activeEditor === originalEditor

        if (lineMapRef.current) {
          const { oldLine, newLine } = alignDiffScroll(visibleLine, isOldEditor, lineMapRef.current)

          const oldHidden = originalEditor.getHiddenAreas() || []
          const newHidden = modifiedEditor.getHiddenAreas() || []

          const adjustedOldLine = calculateVisibleLineNumber(oldLine, oldHidden)
          const adjustedNewLine = calculateVisibleLineNumber(newLine, newHidden)

          const targetOld = getClosestVisibleLine(adjustedOldLine, oldHidden)
          const targetNew = getClosestVisibleLine(adjustedNewLine, newHidden)

          if (isOldEditor) {
            modifiedEditor.revealLineNearTop(targetNew)
          } else {
            originalEditor.revealLineNearTop(targetOld)
          }
        }
      }

      originalEditor.onDidScrollChange(handleScroll)
      modifiedEditor.onDidScrollChange(handleScroll)
    },
    [setDiffStats, setTotalDiffs, setCurrentDiffIndex, isLargeFile, computeDiffWithBackend, editorLayout]
  )

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'F7' || (e.altKey && e.key === 'ArrowUp')) {
        e.preventDefault()
        useDiffStore.getState().navigateDiff('prev')
      }
      if (e.key === 'F8' || (e.altKey && e.key === 'ArrowDown')) {
        e.preventDefault()
        useDiffStore.getState().navigateDiff('next')
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const currentDiffIndex = useDiffStore((s) => s.currentDiffIndex)

  useEffect(() => {
    if (!editorRef.current) return

    const lineChanges = lineChangesRef.current.length > 0
      ? lineChangesRef.current
      : editorRef.current.getLineChanges() as DiffLineChange[]

    if (lineChanges.length === 0 || currentDiffIndex < 0) return

    const targetChange = lineChanges[currentDiffIndex]
    if (!targetChange) return

    const originalEditor = editorRef.current.getOriginalEditor()
    const modifiedEditor = editorRef.current.getModifiedEditor()

    const { oldStart, oldEnd, newStart, newEnd, centerOld, centerNew } = getDiffLineRanges(
      lineChanges,
      currentDiffIndex
    )

    const oldHidden = originalEditor.getHiddenAreas() || []
    const newHidden = modifiedEditor.getHiddenAreas() || []

    let adjustedOldLine = calculateVisibleLineNumber(centerOld, oldHidden)
    let adjustedNewLine = calculateVisibleLineNumber(centerNew, newHidden)

    adjustedOldLine = getClosestVisibleLine(adjustedOldLine, oldHidden)
    adjustedNewLine = getClosestVisibleLine(adjustedNewLine, newHidden)

    if (lineMapRef.current) {
      const mapped = alignDiffScroll(
        adjustedOldLine > 0 ? adjustedOldLine : adjustedNewLine,
        adjustedOldLine > 0,
        lineMapRef.current
      )
      adjustedOldLine = getClosestVisibleLine(mapped.oldLine, oldHidden)
      adjustedNewLine = getClosestVisibleLine(mapped.newLine, newHidden)
    }

    const hasOldChange = targetChange.originalStartLineNumber > 0
    const hasNewChange = targetChange.modifiedStartLineNumber > 0

    const revealOptions = { scrollType: 1 as any }

    if (hasNewChange && adjustedNewLine > 0) {
      modifiedEditor.revealLineInCenterIfOutsideViewport(adjustedNewLine, revealOptions)
    }
    if (hasOldChange && adjustedOldLine > 0) {
      originalEditor.revealLineInCenterIfOutsideViewport(adjustedOldLine, revealOptions)
    }

    if (decorationsRef.current.length > 0) {
      modifiedEditor.deltaDecorations(decorationsRef.current, [])
      originalEditor.deltaDecorations(decorationsRef.current, [])
    }

    const newDecorations: any[] = []

    if (hasNewChange) {
      newDecorations.push({
        range: {
          startLineNumber: newStart,
          startColumn: 1,
          endLineNumber: newEnd,
          endColumn: 1,
        },
        options: {
          isWholeLine: true,
          className: 'diff-highlight-active',
          overviewRuler: {
            color: '#7c3aed',
            position: 1,
          },
          linesDecorationsClassName: 'diff-highlight-active-marker',
        },
      })
    }

    if (hasOldChange) {
      newDecorations.push({
        range: {
          startLineNumber: oldStart,
          startColumn: 1,
          endLineNumber: oldEnd,
          endColumn: 1,
        },
        options: {
          isWholeLine: true,
          className: 'diff-highlight-active',
          overviewRuler: {
            color: '#7c3aed',
            position: 1,
          },
          linesDecorationsClassName: 'diff-highlight-active-marker',
        },
      })
    }

    const newIds = modifiedEditor.deltaDecorations([], newDecorations)
    const oldIds = originalEditor.deltaDecorations([], newDecorations)
    decorationsRef.current = [...newIds, ...oldIds]

    const timer = setTimeout(() => {
      modifiedEditor.deltaDecorations(decorationsRef.current, [])
      originalEditor.deltaDecorations(decorationsRef.current, [])
      decorationsRef.current = []
    }, 1500)

    return () => clearTimeout(timer)
  }, [currentDiffIndex])

  const editorOptions = useMemo(
    () => ({
      readOnly: true,
      renderSideBySide: editorLayout === 'side-by-side',
      enableSplitViewResizing: true,
      scrollBeyondLastLine: false,
      fontSize: 13,
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
      fontLigatures: true,
      minimap: { enabled: true, maxColumn: 80 },
      lineNumbers: 'on' as const,
      renderLineHighlight: 'all' as const,
      folding: true,
      foldingStrategy: 'indentation' as const,
      showFoldingControls: 'mouseover' as const,
      wordWrap: 'off' as const,
      automaticLayout: true,
      diffAlgorithm: 'advanced' as const,
      renderMarginRevertIcon: true,
      useInlineViewWhenSpaceIsLimited: true,
      glyphMargin: true,
      scrollbar: {
        useShadows: false,
        verticalHasArrows: false,
        horizontalHasArrows: false,
        vertical: 'auto' as const,
        horizontal: 'auto' as const,
        verticalScrollbarSize: 10,
        horizontalScrollbarSize: 10,
      },
      smoothScrolling: true,
      fastScrollSensitivity: 5,
    }),
    [editorLayout]
  )

  return (
    <div className="flex-1 overflow-hidden relative">
      {isLargeFile && (
        <div className="absolute top-2 right-2 z-50 flex items-center gap-1.5 px-2 py-1 bg-amber-500/20 border border-amber-500/40 rounded-lg">
          <Zap size={12} className="text-amber-400" />
          <span className="text-[10px] text-amber-300 font-medium">
            大文件模式 ({Math.max(oldLineCount, newLineCount)} 行)
          </span>
          {isChunking && <Loader2 size={12} className="text-amber-400 animate-spin" />}
        </div>
      )}

      <DiffEditor
        height="100%"
        language={language}
        original={oldCode}
        modified={newCode}
        options={editorOptions}
        onMount={handleMount}
        theme="vs-dark"
        loading={
          <div className="flex items-center justify-center h-full bg-[#1e1e2e]">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs text-zinc-500">加载编辑器...</span>
              {isLargeFile && (
                <span className="text-[10px] text-zinc-600">
                  大文件正在分块处理...
                </span>
              )}
            </div>
          </div>
        }
      />
    </div>
  )
}
