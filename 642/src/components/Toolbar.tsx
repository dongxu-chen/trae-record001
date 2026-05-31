import { MousePointer2, Box, Lightbulb, SprayCan, Palette, Wind } from 'lucide-react'
import { useSimulationStore } from '@/store/useSimulationStore'
import type { ToolType } from '@/types'

const tools: { type: ToolType; icon: typeof MousePointer2; label: string }[] = [
  { type: 'select', icon: MousePointer2, label: '选择' },
  { type: 'force', icon: Wind, label: '力场' },
  { type: 'obstacle', icon: Box, label: '障碍物' },
  { type: 'light', icon: Lightbulb, label: '光源' },
  { type: 'emitter', icon: SprayCan, label: '发射器' },
  { type: 'material', icon: Palette, label: '材质' },
]

export function Toolbar() {
  const { currentTool, setCurrentTool } = useSimulationStore((state) => ({
    currentTool: state.currentTool,
    setCurrentTool: state.setCurrentTool,
  }))

  return (
    <div className="absolute left-4 top-1/2 -translate-y-1/2 z-10">
      <div className="glass-panel p-2 flex flex-col gap-2">
        {tools.map(({ type, icon: Icon, label }) => (
          <button
            key={type}
            className={`tool-button group relative ${currentTool === type ? 'active' : ''}`}
            onClick={() => setCurrentTool(type)}
            title={label}
          >
            <Icon className="w-5 h-5 text-current" />
            <span className="absolute left-full ml-3 px-2 py-1 bg-space-blue border border-cyber-cyan/30 rounded text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
              {label}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
