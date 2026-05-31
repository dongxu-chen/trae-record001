import { ZoomIn, ZoomOut, RefreshCw, Download, Grid, Crosshair } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ControlPanelProps {
  onResetView: () => void
  showGrid: boolean
  onToggleGrid: () => void
  showAxes: boolean
  onToggleAxes: () => void
  onExportPNG: () => void
  zoomLevel: number
}

export default function ControlPanel({
  onResetView,
  showGrid,
  onToggleGrid,
  showAxes,
  onToggleAxes,
  onExportPNG,
  zoomLevel,
}: ControlPanelProps) {
  return (
    <div className="absolute top-4 right-4 z-10 flex flex-col gap-2 rounded-lg bg-slate-800/90 p-3 shadow-lg backdrop-blur-sm">
      <div className="flex items-center gap-2 border-b border-slate-700 pb-2">
        <ZoomIn className="h-4 w-4 text-slate-300" />
        <span className="text-sm font-medium text-slate-200">
          缩放: {(zoomLevel * 100).toFixed(0)}%
        </span>
      </div>

      <div className="flex flex-col gap-1">
        <button
          onClick={onResetView}
          className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-300 transition-colors hover:bg-slate-700"
        >
          <RefreshCw className="h-4 w-4" />
          重置视图
        </button>

        <button
          onClick={onToggleGrid}
          className={cn(
            'flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors',
            showGrid
              ? 'bg-cyan-500/20 text-cyan-400'
              : 'text-slate-300 hover:bg-slate-700'
          )}
        >
          <Grid className="h-4 w-4" />
          {showGrid ? '隐藏网格' : '显示网格'}
        </button>

        <button
          onClick={onToggleAxes}
          className={cn(
            'flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors',
            showAxes
              ? 'bg-cyan-500/20 text-cyan-400'
              : 'text-slate-300 hover:bg-slate-700'
          )}
        >
          <Crosshair className="h-4 w-4" />
          {showAxes ? '隐藏坐标轴' : '显示坐标轴'}
        </button>

        <button
          onClick={onExportPNG}
          className="flex items-center gap-2 rounded-md bg-cyan-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-cyan-500"
        >
          <Download className="h-4 w-4" />
          导出 PNG
        </button>
      </div>

      <div className="flex items-center justify-between border-t border-slate-700 pt-2 text-xs text-slate-500">
        <div className="flex items-center gap-1">
          <ZoomOut className="h-3 w-3" />
          <span>滚轮缩放</span>
        </div>
        <div className="flex items-center gap-1">
          <ZoomIn className="h-3 w-3" />
          <span>拖拽平移</span>
        </div>
      </div>
    </div>
  )
}
