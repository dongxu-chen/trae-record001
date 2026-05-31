import { cn } from '@/utils/helpers'

interface StatusBadgeProps {
  status: string
  className?: string
}

const statusConfig: Record<string, { label: string; className: string }> = {
  COMPLETED: { label: '已完成', className: 'bg-dep-safe/15 text-dep-safe border-dep-safe/30' },
  SCANNING: { label: '扫描中', className: 'bg-dep-accent/15 text-dep-accent border-dep-accent/30' },
  FAILED: { label: '失败', className: 'bg-dep-critical/15 text-dep-critical border-dep-critical/30' },
  IDLE: { label: '空闲', className: 'bg-dep-muted/15 text-dep-muted border-dep-muted/30' },
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status] || { label: status, className: 'bg-dep-muted/15 text-dep-muted border-dep-muted/30' }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium',
        config.className,
        status === 'SCANNING' && 'animate-pulse',
        className,
      )}
    >
      {status === 'SCANNING' && (
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-dep-accent opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-dep-accent" />
        </span>
      )}
      {config.label}
    </span>
  )
}
