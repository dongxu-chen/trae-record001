import { memo } from 'react'
import { cn } from '@/utils/cn'
import { formatDate } from '@/utils/dataGenerator'

interface DateRendererProps {
  value: string
  className?: string
}

export const DateRenderer = memo(function DateRenderer({ value, className }: DateRendererProps) {
  return (
    <span className={cn('text-sm text-dark-100 font-mono', className)}>
      {formatDate(value)}
    </span>
  )
})
