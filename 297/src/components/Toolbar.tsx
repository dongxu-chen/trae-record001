import { MousePointer2, Box, PenTool, Trash2, Undo, ZoomIn } from 'lucide-react'
import { useAnnotationStore } from '@/store/annotationStore'
import { ToolType } from '@/types'
import { cn } from '@/utils/cn'

const tools: { type: ToolType; icon: typeof MousePointer2; label: string; shortcut: string }[] = [
  { type: 'select', icon: MousePointer2, label: '选择', shortcut: 'V' },
  { type: 'box', icon: Box, label: '框选', shortcut: 'B' },
  { type: 'polygon', icon: PenTool, label: '多边形', shortcut: 'P' },
]

interface ToolbarProps {
  onDelete: () => void
  onUndo: () => void
  onResetView: () => void
  canUndo: boolean
}

export default function Toolbar({ onDelete, onUndo, onResetView, canUndo }: ToolbarProps) {
  const { currentTool, setCurrentTool, selectedAnnotationId } = useAnnotationStore()

  return (
    <div className="glass-panel rounded-xl p-2 space-y-1">
      {tools.map((tool) => {
        const Icon = tool.icon
        const isActive = currentTool === tool.type
        return (
          <button
            key={tool.type}
            onClick={() => setCurrentTool(tool.type)}
            className={cn(
              'w-12 h-12 rounded-lg flex flex-col items-center justify-center gap-0.5 transition-all',
              isActive
                ? 'bg-primary-500 text-white'
                : 'text-zinc-400 hover:bg-zinc-700 hover:text-white',
            )}
            title={`${tool.label} (${tool.shortcut})`}
          >
            <Icon className="w-5 h-5" />
            <span className="text-[10px]">{tool.shortcut}</span>
          </button>
        )
      })}

      <div className="h-px bg-zinc-700 my-2" />

      <button
        onClick={onDelete}
        disabled={!selectedAnnotationId}
        className={cn(
          'w-12 h-12 rounded-lg flex flex-col items-center justify-center gap-0.5 transition-all',
          selectedAnnotationId
            ? 'text-red-400 hover:bg-red-500/20 hover:text-red-300'
            : 'text-zinc-600 cursor-not-allowed',
        )}
        title="删除标注 (Del)"
      >
        <Trash2 className="w-5 h-5" />
        <span className="text-[10px]">Del</span>
      </button>

      <button
        onClick={onUndo}
        disabled={!canUndo}
        className={cn(
          'w-12 h-12 rounded-lg flex flex-col items-center justify-center gap-0.5 transition-all',
          canUndo
            ? 'text-zinc-400 hover:bg-zinc-700 hover:text-white'
            : 'text-zinc-600 cursor-not-allowed',
        )}
        title="撤销 (Ctrl+Z)"
      >
        <Undo className="w-5 h-5" />
        <span className="text-[10px]">Ctrl+Z</span>
      </button>

      <button
        onClick={onResetView}
        className="w-12 h-12 rounded-lg flex flex-col items-center justify-center gap-0.5 transition-all text-zinc-400 hover:bg-zinc-700 hover:text-white"
        title="重置视角"
      >
        <ZoomIn className="w-5 h-5" />
        <span className="text-[10px]">重置</span>
      </button>
    </div>
  )
}
