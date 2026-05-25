import { memo, useState } from 'react'
import {
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  Filter,
} from 'lucide-react'
import { cn } from '@/utils/cn'
import { FilterPopover } from './FilterPopover'
import { ColumnDragHandle } from './ColumnDragHandle'
import type { Column } from '@tanstack/react-table'
import type { DataRow, ColumnMeta } from '@/types/table'

interface TableHeaderProps {
  column: Column<DataRow>
}

export const TableHeader = memo(function TableHeader({ column }: TableHeaderProps) {
  const [showFilter, setShowFilter] = useState(false)
  const meta = column.columnDef.meta as ColumnMeta | undefined

  const canSort = column.getCanSort()
  const canFilter = column.getCanFilter()
  const sortDirection = column.getIsSorted()

  const handleSort = () => {
    if (canSort) {
      column.toggleSorting(sortDirection === 'asc')
    }
  }

  const handleFilterChange = (value: string) => {
    column.setFilterValue(value || undefined)
  }

  return (
    <div
      className={cn(
        'flex items-center justify-between px-3 py-3 bg-dark-800 border-r border-b border-dark-600 text-left font-medium',
        canSort && 'cursor-pointer hover:bg-dark-700'
      )}
      style={{ width: meta?.width || 150, minWidth: meta?.minWidth || 100 }}
    >
      <ColumnDragHandle id={column.id}>
        <div
          className="flex items-center gap-2 flex-1"
          onClick={canSort ? handleSort : undefined}
        >
          <span className="text-sm text-dark-200 truncate">
            {column.columnDef.header as string}
          </span>
          {canSort && (
            <span className="text-dark-400">
              {sortDirection === 'asc' ? (
                <ChevronUp className="w-4 h-4 text-accent-400" />
              ) : sortDirection === 'desc' ? (
                <ChevronDown className="w-4 h-4 text-accent-400" />
              ) : (
                <ChevronsUpDown className="w-4 h-4 opacity-50" />
              )}
            </span>
          )}
        </div>
      </ColumnDragHandle>

      {canFilter && (
        <div className="relative">
          <button
            onClick={() => setShowFilter(!showFilter)}
            className={cn(
              'p-1 rounded transition-colors',
              column.getFilterValue()
                ? 'text-accent-400 bg-accent-500/20'
                : 'text-dark-400 hover:text-dark-200 hover:bg-dark-700'
            )}
          >
            <Filter className="w-3.5 h-3.5" />
          </button>

          {showFilter && (
            <FilterPopover
              columnId={column.id}
              filterValue={String(column.getFilterValue() ?? '')}
              onFilterChange={handleFilterChange}
              onClose={() => setShowFilter(false)}
            />
          )}
        </div>
      )}
    </div>
  )
})
