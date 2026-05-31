import { ZoomIn } from 'lucide-react'

interface CoordinateInfoProps {
  x: number | null
  y: number | null
  zoomLevel: number
}

export default function CoordinateInfo({ x, y, zoomLevel }: CoordinateInfoProps) {
  if (x === null || y === null) {
    return null
  }

  return (
    <div className="absolute bottom-4 left-4 z-10 rounded-lg bg-gray-900/80 px-4 py-3 text-white shadow-lg backdrop-blur-sm">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-blue-400">x:</span>
            <span className="font-mono text-sm">{x.toFixed(4)}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-red-400">y:</span>
            <span className="font-mono text-sm">{y.toFixed(4)}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 border-t border-gray-700 pt-2">
          <ZoomIn className="h-3 w-3 text-gray-400" />
          <span className="text-xs text-gray-400">
            缩放比例: {(zoomLevel * 100).toFixed(0)}%
          </span>
        </div>
      </div>
    </div>
  )
}
