import { memo, useState, useEffect, useRef } from 'react'
import { Filter, X } from 'lucide-react'
import { cn } from '@/utils/cn'

interface FilterPopoverProps {
  columnId: string
  filterValue: string
  onFilterChange: (value: string) => void
  onClose: () => void
}

export const FilterPopover = memo(function FilterPopover({
  filterValue,
  onFilterChange,
  onClose,
}: FilterPopoverProps) {
  const [localValue, setLocalValue] = useState(filterValue)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleApply = () => {
    onFilterChange(localValue)
    onClose()
  }

  const handleClear = () => {
    setLocalValue('')
    onFilterChange('')
    onClose()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleApply()
    } else if (e.key === 'Escape') {
      onClose()
    }
  }

  return (
    <div className="absolute top-full left-0 mt-1 w-56 bg-dark-800 border border-dark-600 rounded-lg shadow-xl p-3 z-50">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-sm text-dark-200">
          <Filter className="w-4 h-4 text-accent-400" />
          筛选
        </div>
        <button
          onClick={onClose}
          className="text-dark-400 hover:text-dark-200 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <input
        ref={inputRef}
        type="text"
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="输入筛选值..."
        className="w-full px-3 py-2 bg-dark-900 border border-dark-600 rounded text-sm text-dark-100 placeholder-dark-500 focus:outline-none focus:border-accent-500"
      />

      <div className="flex items-center justify-end gap-2 mt-3">
        <button
          onClick={handleClear}
          className={cn(
            'px-3 py-1.5 text-xs rounded transition-colors',
            filterValue
              ? 'text-dark-300 hover:text-dark-100'
              : 'text-dark-500 cursor-not-allowed'
          )}
          disabled={!filterValue}
        >
          清除
        </button>
        <button
          onClick={handleApply}
          className="px-3 py-1.5 bg-accent-600 hover:bg-accent-500 text-white text-xs rounded transition-colors"
        >
          应用
        </button>
      </div>
    </div>
  )
})
