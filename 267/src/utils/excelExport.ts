import * as XLSX from 'xlsx'
import type { ExportOptions } from '@/types/table'

export function exportToExcel<T extends Record<string, unknown>>(
  data: T[],
  columns: { id: string; header: string }[],
  options: ExportOptions = {}
): void {
  const { filename = 'data_export', includeHeaders = true } = options

  const exportData = data.map(row => {
    const exportRow: Record<string, unknown> = {}
    columns.forEach(col => {
      exportRow[col.header] = row[col.id]
    })
    return exportRow
  })

  const ws = XLSX.utils.json_to_sheet(exportData, {
    header: includeHeaders ? columns.map(c => c.header) : undefined,
  })

  ws['!cols'] = columns.map(() => ({ wch: 15 }))

  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Data')

  XLSX.writeFile(wb, `${filename}.xlsx`)
}

export function exportToCSV<T extends Record<string, unknown>>(
  data: T[],
  columns: { id: string; header: string }[],
  options: ExportOptions = {}
): void {
  const { filename = 'data_export', includeHeaders = true } = options

  let csv = ''

  if (includeHeaders) {
    csv += columns.map(c => `"${c.header}"`).join(',') + '\n'
  }

  data.forEach(row => {
    const values = columns.map(col => {
      const value = row[col.id]
      return `"${String(value ?? '').replace(/"/g, '""')}"`
    })
    csv += values.join(',') + '\n'
  })

  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `${filename}.csv`
  link.click()
  URL.revokeObjectURL(link.href)
}

export function copyToClipboard(text: string): Promise<void> {
  return navigator.clipboard.writeText(text)
}

export function readFromClipboard(): Promise<string> {
  return navigator.clipboard.readText()
}

export function parseTSV(tsv: string): string[][] {
  return tsv.split('\n').map(row =>
    row.split('\t').map(cell => cell.trim())
  ).filter(row => row.some(cell => cell !== ''))
}

export function toTSV(data: string[][]): string {
  return data.map(row => row.join('\t')).join('\n')
}
