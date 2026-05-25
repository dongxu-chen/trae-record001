import { memo } from 'react'
import { cn } from '@/utils/cn'

type StatusType = 'active' | 'inactive' | 'pending'

interface StatusRendererProps {
  value: StatusType
  className?: string
}

const statusConfig: Record<StatusType, { label: string; color: string }> = {
  active: { label: '在职', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' },
  inactive: { label: '离职', color: 'bg-red-500/20 text-red-400 border-red-500/30' },
  pending: { label: '待入职', color: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
}

export const StatusRenderer = memo(function StatusRenderer({ value, className }: StatusRendererProps) {
  const config = statusConfig[value] || statusConfig.pending

  return (
    <span className={cn(
      'inline-flex items-center px-2 py-1 text-xs font-medium rounded-full border',
      config.color,
      className
    )}>
      <span className={cn(
        'w-1.5 h-1.5 rounded-full mr-1.5',
        value === 'active' ? 'bg-emerald-400' :
        value === 'inactive' ? 'bg-red-400' : 'bg-amber-400'
      )} />
      {config.label}
    </span>
  )
})
