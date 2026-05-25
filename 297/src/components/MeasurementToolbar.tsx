import { Ruler, Square, Triangle, Trash2, X } from 'lucide-react'
import { useToolsStore } from '@/store/toolsStore'
import { MeasurementType } from '@/utils/MeasurementTool'
import { cn } from '@/utils/cn'

const tools: { type: MeasurementType; icon: typeof Ruler; label: string; shortcut: string }[] = [
  { type: 'distance', icon: Ruler, label: '距离', shortcut: 'D' },
  { type: 'area', icon: Square, label: '面积', shortcut: 'A' },
  { type: 'angle', icon: Triangle, label: '角度', shortcut: 'G' },
]

export default function MeasurementToolbar() {
  const {
    measurementType,
    setMeasurementType,
    measurements,
    clearMeasurements,
    isMeasuring,
    measurementPoints,
    clearMeasurementPoints,
  } = useToolsStore()

  return (
    <div className="space-y-4">
      <div className="glass-panel rounded-xl p-2">
        <div className="flex items-center justify-between px-2 mb-2">
          <span className="text-sm font-semibold text-white">测量工具</span>
          {measurements.length > 0 && (
            <button
              onClick={clearMeasurements}
              className="text-xs text-zinc-400 hover:text-red-400 transition-colors"
            >
              清除全部
            </button>
          )}
        </div>
        <div className="flex gap-1">
          {tools.map((tool) => {
            const Icon = tool.icon
            const isActive = measurementType === tool.type
            return (
              <button
                key={tool.type}
                onClick={() => setMeasurementType(tool.type)}
                className={cn(
                  'flex-1 py-2 px-1 rounded-lg flex flex-col items-center gap-1 transition-all',
                  isActive
                    ? 'bg-yellow-500/20 text-yellow-400'
                    : 'text-zinc-400 hover:bg-zinc-700 hover:text-white',
                )}
                title={`${tool.label} (${tool.shortcut})`}
              >
                <Icon className="w-4 h-4" />
                <span className="text-[10px]">{tool.shortcut}</span>
              </button>
            )
          })}
        </div>
      </div>

      {isMeasuring && (
        <div className="glass-panel rounded-xl p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-yellow-400">
              {measurementType === 'distance' && '测量距离'}
              {measurementType === 'area' && '测量面积'}
              {measurementType === 'angle' && '测量角度'}
            </span>
            <button
              onClick={clearMeasurementPoints}
              className="p-1 hover:bg-zinc-700 rounded transition-colors"
            >
              <X className="w-4 h-4 text-zinc-400" />
            </button>
          </div>
          <p className="text-xs text-zinc-400">
            点击场景放置测量点
            {measurementType === 'distance' && ' (需要2个点)'}
            {measurementType === 'area' && ' (3个点以上，按Enter完成)'}
            {measurementType === 'angle' && ' (需要3个点)'}
          </p>
          <div className="mt-2 text-xs text-zinc-500">
            已放置: {measurementPoints.length} 个点
          </div>
        </div>
      )}

      {measurements.length > 0 && (
        <div className="glass-panel rounded-xl p-3">
          <div className="text-sm font-medium text-white mb-2">测量结果</div>
          <div className="space-y-2 max-h-48 overflow-y-auto scrollbar-thin">
            {measurements.map((m, idx) => (
              <div
                key={m.id}
                className="flex items-center justify-between p-2 rounded-lg bg-zinc-800/50"
              >
                <div className="flex items-center gap-2">
                  {m.type === 'distance' && <Ruler className="w-4 h-4 text-yellow-400" />}
                  {m.type === 'area' && <Square className="w-4 h-4 text-yellow-400" />}
                  {m.type === 'angle' && <Triangle className="w-4 h-4 text-yellow-400" />}
                  <span className="text-sm text-white">
                    #{idx + 1}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-yellow-400 font-mono">
                    {m.value.toFixed(2)} {m.unit}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
