import { useEffect, useCallback } from 'react'
import type { CellPosition, EditState } from '@/types/table'

interface UseKeyboardShortcutsProps {
  selectedCell: CellPosition | null
  editingCell: EditState | null
  columnIds: string[]
  rowCount: number
  onSelectCell: (pos: CellPosition) => void
  onStartEdit: (pos: CellPosition) => void
  onSaveEdit: () => void
  onCancelEdit: () => void
  onCopy: () => void
  onPaste: () => void
  onSelectAll: () => void
  onDelete: () => void
}

export function useKeyboardShortcuts({
  selectedCell,
  editingCell,
  columnIds,
  rowCount,
  onSelectCell,
  onStartEdit,
  onSaveEdit,
  onCancelEdit,
  onCopy,
  onPaste,
  onSelectAll,
  onDelete,
}: UseKeyboardShortcutsProps): void {
  const getNextCell = useCallback((pos: CellPosition, direction: 'up' | 'down' | 'left' | 'right'): CellPosition => {
    const currentColIndex = columnIds.indexOf(pos.columnId)
    let newRowIndex = pos.rowIndex
    let newColIndex = currentColIndex

    switch (direction) {
      case 'up':
        newRowIndex = Math.max(0, pos.rowIndex - 1)
        break
      case 'down':
        newRowIndex = Math.min(rowCount - 1, pos.rowIndex + 1)
        break
      case 'left':
        newColIndex = Math.max(0, currentColIndex - 1)
        break
      case 'right':
        newColIndex = Math.min(columnIds.length - 1, currentColIndex + 1)
        break
    }

    return {
      rowIndex: newRowIndex,
      columnId: columnIds[newColIndex],
    }
  }, [columnIds, rowCount])

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (editingCell) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        onSaveEdit()
        if (selectedCell) {
          const nextCell = getNextCell(selectedCell, 'down')
          onSelectCell(nextCell)
        }
      } else if (e.key === 'Escape') {
        e.preventDefault()
        onCancelEdit()
      } else if (e.key === 'Tab') {
        e.preventDefault()
        onSaveEdit()
        if (selectedCell) {
          const direction = e.shiftKey ? 'left' : 'right'
          const nextCell = getNextCell(selectedCell, direction)
          onSelectCell(nextCell)
        }
      }
      return
    }

    if (e.ctrlKey || e.metaKey) {
      switch (e.key.toLowerCase()) {
        case 'c':
          e.preventDefault()
          onCopy()
          break
        case 'v':
          e.preventDefault()
          onPaste()
          break
        case 'a':
          e.preventDefault()
          onSelectAll()
          break
      }
      return
    }

    if (selectedCell) {
      switch (e.key) {
        case 'ArrowUp':
          e.preventDefault()
          onSelectCell(getNextCell(selectedCell, 'up'))
          break
        case 'ArrowDown':
          e.preventDefault()
          onSelectCell(getNextCell(selectedCell, 'down'))
          break
        case 'ArrowLeft':
          e.preventDefault()
          onSelectCell(getNextCell(selectedCell, 'left'))
          break
        case 'ArrowRight':
          e.preventDefault()
          onSelectCell(getNextCell(selectedCell, 'right'))
          break
        case 'Enter':
        case 'F2':
          e.preventDefault()
          onStartEdit(selectedCell)
          break
        case 'Delete':
        case 'Backspace':
          e.preventDefault()
          onDelete()
          break
      }
    }
  }, [editingCell, selectedCell, getNextCell, onSaveEdit, onCancelEdit, onSelectCell, onCopy, onPaste, onSelectAll, onStartEdit, onDelete])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}
