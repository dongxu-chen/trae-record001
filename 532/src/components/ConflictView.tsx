import { useCallback, useMemo } from 'react'
import { useConflictStore } from '@/store/conflictPlaybackStore'
import { useDiffStore } from '@/store/diffStore'
import { AlertTriangle, Check, ArrowLeftRight, Layers, RotateCcw } from 'lucide-react'

export default function ConflictView() {
  const {
    conflictRegions,
    hasConflicts,
    resolveConflict,
    resolveAll,
    resetConflicts,
  } = useConflictStore()

  const { newCode, setNewCode } = useDiffStore()

  const resolvedCount = conflictRegions.filter((r) => r.resolved).length
  const allResolved = hasConflicts && resolvedCount === conflictRegions.length

  const handleResolve = useCallback(
    (index: number, resolution: 'current' | 'incoming' | 'both') => {
      resolveConflict(index, resolution)
    },
    [resolveConflict]
  )

  const handleResolveAll = useCallback(
    (resolution: 'current' | 'incoming' | 'both') => {
      resolveAll(resolution)
    },
    [resolveAll]
  )

  const handleApplyResolution = useCallback(() => {
    const resolved = useConflictStore.getState().getResolvedCode(newCode)
    setNewCode(resolved)
    resetConflicts()
  }, [newCode, setNewCode, resetConflicts])

  if (!hasConflicts) return null

  return (
    <div className="border-b border-[#2a2a4a] bg-[#1a1a2e]">
      <div className="px-4 py-2 flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <AlertTriangle size={14} className="text-amber-400" />
          <span className="text-xs font-semibold text-amber-300">
            合并冲突
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300">
            {conflictRegions.length - resolvedCount} 未解决
          </span>
        </div>

        <div className="h-4 w-px bg-[#2a2a4a]" />

        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-zinc-500">全部:</span>
          <button
            onClick={() => handleResolveAll('current')}
            className="px-2 py-0.5 rounded text-[10px] font-medium bg-sky-500/10 text-sky-400 hover:bg-sky-500/20 border border-sky-500/30 transition-colors"
          >
            采用当前
          </button>
          <button
            onClick={() => handleResolveAll('incoming')}
            className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/30 transition-colors"
          >
            采用传入
          </button>
          <button
            onClick={() => handleResolveAll('both')}
            className="px-2 py-0.5 rounded text-[10px] font-medium bg-violet-500/10 text-violet-400 hover:bg-violet-500/20 border border-violet-500/30 transition-colors"
          >
            保留双方
          </button>
        </div>

        <div className="flex-1" />

        {allResolved && (
          <button
            onClick={handleApplyResolution}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-500 shadow-md shadow-emerald-600/30 transition-all"
          >
            <Check size={12} />
            应用解决结果
          </button>
        )}

        <button
          onClick={resetConflicts}
          className="p-1 rounded text-zinc-500 hover:text-zinc-300 hover:bg-[#2a2a4a] transition-colors"
          title="重置冲突"
        >
          <RotateCcw size={12} />
        </button>
      </div>

      <div className="px-4 pb-2 max-h-48 overflow-y-auto custom-scrollbar space-y-1.5">
        {conflictRegions.map((region, index) => (
          <div
            key={index}
            className={`rounded-lg border transition-all ${
              region.resolved
                ? 'border-emerald-500/20 bg-emerald-500/5'
                : 'border-amber-500/20 bg-amber-500/5'
            }`}
          >
            <div className="px-3 py-1.5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-['JetBrains_Mono'] ${region.resolved ? 'text-emerald-400' : 'text-amber-400'}`}>
                  冲突 #{index + 1}
                </span>
                <span className="text-[10px] text-zinc-500">
                  行 {region.startLine}-{region.endLine}
                </span>
                {region.resolved && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                    ✓ {region.resolution === 'current' ? '当前' : region.resolution === 'incoming' ? '传入' : '双方'}
                  </span>
                )}
              </div>

              {!region.resolved && (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleResolve(index, 'current')}
                    className="px-1.5 py-0.5 rounded text-[10px] text-sky-400 hover:bg-sky-500/20 transition-colors"
                    title="采用当前更改"
                  >
                    当前
                  </button>
                  <button
                    onClick={() => handleResolve(index, 'incoming')}
                    className="px-1.5 py-0.5 rounded text-[10px] text-emerald-400 hover:bg-emerald-500/20 transition-colors"
                    title="采用传入更改"
                  >
                    传入
                  </button>
                  <button
                    onClick={() => handleResolve(index, 'both')}
                    className="px-1.5 py-0.5 rounded text-[10px] text-violet-400 hover:bg-violet-500/20 transition-colors"
                    title="保留双方更改"
                  >
                    双方
                  </button>
                </div>
              )}
            </div>

            <div className="px-3 pb-2 grid grid-cols-2 gap-2">
              <div className="rounded bg-sky-500/5 border border-sky-500/10 p-1.5">
                <div className="text-[9px] text-sky-400 font-medium mb-1 flex items-center gap-1">
                  <ArrowLeftRight size={8} />
                  {region.currentLabel}
                </div>
                <pre className="text-[10px] text-zinc-400 font-['JetBrains_Mono'] leading-tight whitespace-pre-wrap max-h-16 overflow-hidden">
                  {region.currentContent.slice(0, 200)}
                  {region.currentContent.length > 200 ? '...' : ''}
                </pre>
              </div>
              <div className="rounded bg-emerald-500/5 border border-emerald-500/10 p-1.5">
                <div className="text-[9px] text-emerald-400 font-medium mb-1 flex items-center gap-1">
                  <ArrowLeftRight size={8} />
                  {region.incomingLabel}
                </div>
                <pre className="text-[10px] text-zinc-400 font-['JetBrains_Mono'] leading-tight whitespace-pre-wrap max-h-16 overflow-hidden">
                  {region.incomingContent.slice(0, 200)}
                  {region.incomingContent.length > 200 ? '...' : ''}
                </pre>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
