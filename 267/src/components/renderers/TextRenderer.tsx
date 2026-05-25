import { memo } from 'react'
import { cn } from '@/utils/cn'

interface TextRendererProps {
  value: string
  className?: string
}

export const TextRenderer = memo(function TextRenderer({ value, className }: TextRendererProps) {
  return (
    <span className={cn('text-sm text-dark-100 truncate', className)}>
      {value}
    </span>
  )
})
