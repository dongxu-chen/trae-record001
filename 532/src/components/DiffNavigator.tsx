import { useDiffStore } from '@/store/diffStore'
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react'

export default function DiffNavigator() {
  const { currentDiffIndex, totalDiffs, navigateDiff, diffStats } = useDiffStore()

  if (!diffStats || totalDiffs === 0) return null

  return (
    <div className="absolute bottom-4 right-4 flex items-center gap-2 bg-[#1a1a2e]/95 backdrop-blur-md border border-[#2a2a4a] rounded-xl px-3 py-2 shadow-2xl shadow-black/40 z-50">
      <span className="text-xs text-zinc-400 font-medium min-w-[80px] text-center font-['JetBrains_Mono']">
        {currentDiffIndex + 1}/{totalDiffs} 差异
      </span>

      <div className="h-4 w-px bg-[#2a2a4a]" />

      <button
        onClick={() => navigateDiff('prev')}
        disabled={currentDiffIndex <= 0}
        className="p-1 rounded-md text-zinc-400 hover:text-white hover:bg-[#2a2a4a] transition-all disabled:opacity-30 disabled:cursor-not-allowed"
        title="上一个差异 (F7)"
      >
        <ChevronUp size={14} />
      </button>

      <button
        onClick={() => navigateDiff('next')}
        disabled={currentDiffIndex >= totalDiffs - 1}
        className="p-1 rounded-md text-zinc-400 hover:text-white hover:bg-[#2a2a4a] transition-all disabled:opacity-30 disabled:cursor-not-allowed"
        title="下一个差异 (F8)"
      >
        <ChevronDown size={14} />
      </button>

      <div className="h-4 w-px bg-[#2a2a4a]" />

      <button
        onClick={() => {
          useDiffStore.getState().setCurrentDiffIndex(0)
        }}
        className="p-1 rounded-md text-zinc-400 hover:text-white hover:bg-[#2a2a4a] transition-all"
        title="回到第一个差异"
      >
        <ChevronsUpDown size={14} />
      </button>

      <div className="flex items-center gap-1.5 ml-1">
        <span className="text-[10px] text-emerald-400/70 font-['JetBrains_Mono']">+{diffStats.additions}</span>
        <span className="text-[10px] text-red-400/70 font-['JetBrains_Mono']">-{diffStats.deletions}</span>
      </div>
    </div>
  )
}
