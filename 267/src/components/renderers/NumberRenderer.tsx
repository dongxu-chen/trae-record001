import { memo } from 'react'
import { cn } from '@/utils/cn'
import { formatNumber, formatCurrency } from '@/utils/dataGenerator'

interface NumberRendererProps {
  value: number
  format?: 'number' | 'currency'
  className?: string
}

export const NumberRenderer = memo(function NumberRenderer({
  value,
  format = 'number',
  className,
}: NumberRendererProps) {
  const displayValue = format === 'currency' ? formatCurrency(value) : formatNumber(value)

  return (
    <span className={cn('text-sm text-dark-100 font-mono', className)}>
      {displayValue}
    </span>
  )
})
