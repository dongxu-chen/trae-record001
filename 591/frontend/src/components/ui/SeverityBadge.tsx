import { cn, severityColor, severityBg } from '@/utils/helpers'
import type { SeverityLevel } from '@/types'

interface SeverityBadgeProps {
  severity: SeverityLevel
  className?: string
}

const severityLabels: Record<SeverityLevel, string> = {
  CRITICAL: '严重',
  HIGH: '高危',
  MEDIUM: '中危',
  LOW: '低危',
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold',
        severityBg(severity),
        severityColor(severity),
        className,
      )}
    >
      {severityLabels[severity]}
    </span>
  )
}
