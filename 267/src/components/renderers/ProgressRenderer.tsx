import { memo } from 'react'
import { cn } from '@/utils/cn'

interface ProgressRendererProps {
  value: number
  className?: string
}

export const ProgressRenderer = memo(function ProgressRenderer({ value, className }: ProgressRendererProps) {
  const getColor = (val: number) => {
    if (val >= 80) return 'bg-emerald-500'
    if (val >= 60) return 'bg-accent-500'
    if (val >= 40) return 'bg-amber-500'
    return 'bg-red-500'
  }

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex-1 h-2 bg-dark-700 rounded-full overflow-hidden min-w-[60px]">
        <div
          className={cn('h-full rounded-full transition-all duration-300', getColor(value))}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
      <span className="text-xs text-dark-300 font-mono w-10 text-right">
        {value}%
      </span>
    </div>
  )
})
