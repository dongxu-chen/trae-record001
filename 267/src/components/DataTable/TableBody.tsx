import { memo, useRef, useMemo } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { cn } from '@/utils/cn'
import { TableCell } from './TableCell'
import type { DataRow, CellPosition, EditState, ColumnMeta, ValidationRule } from '@/types/table'
import type { Row, Column } from '@tanstack/react-table'

interface TableBodyProps {
  rows: Row<DataRow>[]
  columns: Column<DataRow>[]
  selectedCell: CellPosition | null
  editingCell: EditState | null
  onCellClick: (rowIndex: number, columnId: string) => void
  onStartEdit: (pos: CellPosition) => void
  onUpdateEditValue: (value: unknown) => void
  onSaveEdit: () => void
  onCancelEdit: () => void
  onValidateError?: (error: string) => void
  onRestoreOriginal?: () => void
  rowHeight?: number
  bufferSize?: number
}

export const TableBody = memo(function TableBody({
  rows,
  columns,
  selectedCell,
  editingCell,
  onCellClick,
  onStartEdit,
  onUpdateEditValue,
  onSaveEdit,
  onCancelEdit,
  onValidateError,
  onRestoreOriginal,
  rowHeight = 40,
  bufferSize = 30,
}: TableBodyProps) {
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowHeight,
    overscan: bufferSize,
    paddingStart: 0,
    paddingEnd: 0,
    scrollPaddingStart: 0,
    scrollPaddingEnd: 0,
  })

  const virtualItems = virtualizer.getVirtualItems()
  const totalSize = virtualizer.getTotalSize()

  const totalWidth = useMemo(() => {
    return columns.reduce((acc, col) => {
      const meta = col.columnDef.meta as ColumnMeta | undefined
      return acc + (meta?.width || 150)
    }, 0)
  }, [columns])

  const rowIndices = useMemo(() => {
    return new Set(virtualItems.map(item => item.index))
  }, [virtualItems])

  const paddingBefore = virtualItems.length > 0 ? virtualItems[0].start : 0
  const paddingAfter = virtualItems.length > 0
    ? totalSize - virtualItems[virtualItems.length - 1].end
    : totalSize

  return (
    <div
      ref={parentRef}
      className="flex-1 overflow-auto bg-dark-900"
      style={{
        contain: 'strict',
        willChange: 'scroll-position',
        overscrollBehavior: 'contain',
      }}
    >
      <div
        style={{
          height: totalSize,
          width: totalWidth,
          position: 'relative',
        }}
      >
        {paddingBefore > 0 && (
          <div style={{ height: paddingBefore, width: '100%' }} />
        )}

        {virtualItems.map((virtualRow) => {
          const row = rows[virtualRow.index]
          if (!row) return null

          const rowIndex = virtualRow.index
          const isInBuffer =
            virtualRow.index < virtualizer.options.overscan ||
            virtualRow.index >= rows.length - virtualizer.options.overscan

          return (
            <div
              key={row.id}
              data-index={rowIndex}
              className={cn(
                'flex w-full',
                rowIndex % 2 === 0 ? 'bg-dark-900' : 'bg-dark-850',
                isInBuffer && 'opacity-90'
              )}
              style={{
                height: rowHeight,
                transform: 'translateZ(0)',
                willChange: 'transform',
              }}
            >
              {columns.map((column) => {
                const meta = column.columnDef.meta as ColumnMeta | undefined
                const columnId = column.id

                const cell = row.getValue(columnId)
                const isSelected =
                  selectedCell?.rowIndex === rowIndex &&
                  selectedCell?.columnId === columnId
                const isEditing =
                  editingCell?.rowIndex === rowIndex &&
                  editingCell?.columnId === columnId

                return (
                  <div
                    key={columnId}
                    style={{
                      width: meta?.width || 150,
                      minWidth: meta?.minWidth || 100,
                    }}
                  >
                    <TableCell
                          value={cell}
                          rowIndex={rowIndex}
                          columnId={columnId}
                          renderer={meta?.renderer}
                          validation={meta?.validation}
                          isSelected={isSelected}
                          isEditing={isEditing}
                          editValue={isEditing ? editingCell.value : cell}
                          editError={isEditing ? editingCell.error : undefined}
                          onClick={() => onCellClick(rowIndex, columnId)}
                          onDoubleClick={() => onStartEdit({ rowIndex, columnId })}
                          onEditChange={onUpdateEditValue}
                          onEditSave={onSaveEdit}
                          onEditCancel={onCancelEdit}
                          onValidateError={onValidateError}
                          onRestoreOriginal={onRestoreOriginal}
                        />
                  </div>
                )
              })}
            </div>
          )
        })}

        {paddingAfter > 0 && (
          <div style={{ height: paddingAfter, width: '100%' }} />
        )}
      </div>
    </div>
  )
})
