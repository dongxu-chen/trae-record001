import type { ClipboardCell, CellPosition } from '@/types/table'

export interface ParsedClipboardData {
  cells: ClipboardCell[][]
  rowCount: number
  colCount: number
}

export function parseClipboardTSV(tsv: string): ParsedClipboardData {
  const lines = tsv.split('\n').filter(line => line.trim() !== '')
  if (lines.length === 0) {
    return { cells: [], rowCount: 0, colCount: 0 }
  }

  const grid: ClipboardCell[][] = []
  let maxCols = 0

  lines.forEach(line => {
    const cells = line.split('\t')
    const row: ClipboardCell[] = []

    cells.forEach(cellValue => {
      const trimmedValue = cellValue.trim()
      row.push({
        value: trimmedValue,
        rowSpan: 1,
        colSpan: 1,
        isEmpty: trimmedValue === '',
      })
    })

    grid.push(row)
    maxCols = Math.max(maxCols, row.length)
  })

  detectMergedCells(grid)

  return {
    cells: grid,
    rowCount: grid.length,
    colCount: maxCols,
  }
}

function detectMergedCells(grid: ClipboardCell[][]): void {
  const rowCount = grid.length
  const colCount = Math.max(...grid.map(row => row.length))

  for (let row = 0; row < rowCount; row++) {
    for (let col = 0; col < colCount; col++) {
      const cell = grid[row]?.[col]
      if (!cell || cell.isEmpty) continue

      let colSpan = 1
      while (col + colSpan < colCount) {
        const nextCell = grid[row]?.[col + colSpan]
        if (nextCell?.isEmpty) {
          colSpan++
        } else {
          break
        }
      }

      let rowSpan = 1
      let canMergeRows = true
      while (row + rowSpan < rowCount && canMergeRows) {
        for (let c = 0; c < colSpan; c++) {
          const belowCell = grid[row + rowSpan]?.[col + c]
          if (!belowCell?.isEmpty) {
            canMergeRows = false
            break
          }
        }
        if (canMergeRows) {
          rowSpan++
        }
      }

      if (colSpan > 1 || rowSpan > 1) {
        cell.colSpan = colSpan
        cell.rowSpan = rowSpan

        for (let r = 0; r < rowSpan; r++) {
          for (let c = 0; c < colSpan; c++) {
            if (r === 0 && c === 0) continue
            const mergedCell = grid[row + r]?.[col + c]
            if (mergedCell) {
              mergedCell.isEmpty = true
              mergedCell.value = ''
            }
          }
        }
      }
    }
  }
}

export function toClipboardTSV(
  data: string[][],
  mergedCells?: Map<string, { rowSpan: number; colSpan: number }>
): string {
  const result: string[] = []

  data.forEach((row, rowIndex) => {
    const rowValues: string[] = []

    row.forEach((cellValue, colIndex) => {
      const key = `${rowIndex}-${colIndex}`
      const mergeInfo = mergedCells?.get(key)

      if (mergeInfo) {
        rowValues.push(cellValue)
        for (let c = 1; c < mergeInfo.colSpan; c++) {
          rowValues.push('')
        }
      } else {
        let isMergedPart = false
        mergedCells?.forEach((info, k) => {
          const [startRow, startCol] = k.split('-').map(Number)
          if (
            rowIndex >= startRow &&
            rowIndex < startRow + info.rowSpan &&
            colIndex >= startCol &&
            colIndex < startCol + info.colSpan &&
            !(rowIndex === startRow && colIndex === startCol)
          ) {
            isMergedPart = true
          }
        })

        if (!isMergedPart) {
          rowValues.push(cellValue)
        }
      }
    })

    result.push(rowValues.join('\t'))
  })

  return result.join('\n')
}

export function applyClipboardDataToGrid(
  clipboardData: ParsedClipboardData,
  startPosition: CellPosition,
  targetData: Record<string, unknown>[],
  columnIds: string[],
  updateCell: (rowIndex: number, columnId: string, value: unknown) => void
): void {
  const startColIndex = columnIds.indexOf(startPosition.columnId)

  clipboardData.cells.forEach((row, rowOffset) => {
    row.forEach((cell, colOffset) => {
      if (cell.isEmpty) return

      const targetRowIndex = startPosition.rowIndex + rowOffset
      const targetColIndex = startColIndex + colOffset

      if (targetRowIndex >= targetData.length || targetColIndex >= columnIds.length) {
        return
      }

      const columnId = columnIds[targetColIndex]
      let parsedValue: unknown = cell.value

      if (columnId === 'salary' || columnId === 'performance' || columnId === 'projects') {
        parsedValue = Number(cell.value) || 0
      }

      updateCell(targetRowIndex, columnId, parsedValue)
    })
  })
}

export function detectExcelMergeFormat(html: string): { hasMergedCells: boolean; mergedRanges: string[] } {
  const mergedRanges: string[] = []

  const colspanMatches = html.match(/colspan=["'](\d+)["']/gi)
  const rowspanMatches = html.match(/rowspan=["'](\d+)["']/gi)

  const hasMergedCells = !!(colspanMatches || rowspanMatches)

  return { hasMergedCells, mergedRanges }
}

export function parseClipboardHTML(html: string): ParsedClipboardData | null {
  try {
    const parser = new DOMParser()
    const doc = parser.parseFromString(html, 'text/html')
    const table = doc.querySelector('table')

    if (!table) return null

    const rows = table.querySelectorAll('tr')
    const grid: ClipboardCell[][] = []

    rows.forEach(row => {
      const cells = row.querySelectorAll('td, th')
      const rowData: ClipboardCell[] = []

      cells.forEach(cell => {
        const colSpan = parseInt(cell.getAttribute('colspan') || '1', 10)
        const rowSpan = parseInt(cell.getAttribute('rowspan') || '1', 10)
        const text = cell.textContent?.trim() || ''

        rowData.push({
          value: text,
          rowSpan,
          colSpan,
          isEmpty: text === '',
        })
      })

      grid.push(rowData)
    })

    return {
      cells: grid,
      rowCount: grid.length,
      colCount: Math.max(...grid.map(row => row.length), 0),
    }
  } catch {
    return null
  }
}
