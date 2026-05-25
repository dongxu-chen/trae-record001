import { useCallback } from 'react'
import { copyToClipboard, readFromClipboard } from '@/utils/excelExport'
import {
  parseClipboardTSV,
  parseClipboardHTML,
  applyClipboardDataToGrid,
  toClipboardTSV,
} from '@/utils/clipboardParser'
import type { CellPosition, DataRow } from '@/types/table'

interface UseClipboardProps {
  data: DataRow[]
  columnIds: string[]
  selectedCell: CellPosition | null
  onUpdateCell: (rowIndex: number, columnId: string, value: unknown) => void
}

export function useClipboard({
  data,
  columnIds,
  selectedCell,
  onUpdateCell,
}: UseClipboardProps) {
  const handleCopy = useCallback(() => {
    if (!selectedCell) return

    const cellValue = data[selectedCell.rowIndex]?.[selectedCell.columnId as keyof DataRow]
    const text = String(cellValue ?? '')
    copyToClipboard(text).catch(console.error)
  }, [data, selectedCell])

  const handlePaste = useCallback(async () => {
    if (!selectedCell) return

    try {
      const text = await readFromClipboard()

      let parsedData = parseClipboardHTML(text)

      if (!parsedData || parsedData.rowCount === 0) {
        parsedData = parseClipboardTSV(text)
      }

      if (parsedData.rowCount === 0) return

      applyClipboardDataToGrid(
        parsedData,
        selectedCell,
        data as Record<string, unknown>[],
        columnIds,
        onUpdateCell
      )
    } catch (error) {
      console.error('Paste failed:', error)
    }
  }, [data, columnIds, selectedCell, onUpdateCell])

  const copySelectionToTSV = useCallback((
    selection: { rows: number[], columns: string[] },
    mergedCells?: Map<string, { rowSpan: number; colSpan: number }>
  ) => {
    const values: string[][] = []

    selection.rows.forEach(rowIndex => {
      const row: string[] = []
      selection.columns.forEach(columnId => {
        const value = data[rowIndex]?.[columnId as keyof DataRow]
        row.push(String(value ?? ''))
      })
      values.push(row)
    })

    return toClipboardTSV(values, mergedCells)
  }, [data])

  return {
    handleCopy,
    handlePaste,
    copySelectionToTSV,
  }
}
