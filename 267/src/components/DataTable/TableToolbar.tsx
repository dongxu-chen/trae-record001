import { memo, useState } from 'react'
import {
  Download,
  Search,
  Columns,
  RefreshCw,
  Copy,
  FileSpreadsheet,
  FileText,
  X,
} from 'lucide-react'
import { cn } from '@/utils/cn'
import type { DataRow } from '@/types/table'
import { exportToExcel, exportToCSV } from '@/utils/excelExport'

interface TableToolbarProps {
  globalFilter: string
  onGlobalFilterChange: (value: string) => void
  data: DataRow[]
  columns: { id: string; header: string }[]
  selectedCount: number
  onRefresh: () => void
}

export const TableToolbar = memo(function TableToolbar({
  globalFilter,
  onGlobalFilterChange,
  data,
  columns,
  selectedCount,
  onRefresh,
}: TableToolbarProps) {
  const [showExportMenu, setShowExportMenu] = useState(false)

  const handleExportExcel = () => {
    exportToExcel(data, columns, { filename: 'employee_data' })
    setShowExportMenu(false)
  }

  const handleExportCSV = () => {
    exportToCSV(data, columns, { filename: 'employee_data' })
    setShowExportMenu(false)
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-dark-800/50 border-b border-dark-700">
      <div className="flex items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-400" />
          <input
            type="text"
            placeholder="搜索..."
            value={globalFilter}
            onChange={(e) => onGlobalFilterChange(e.target.value)}
            className="pl-10 pr-4 py-2 bg-dark-900 border border-dark-600 rounded-lg text-sm text-dark-100 placeholder-dark-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/50 transition-colors w-64"
          />
          {globalFilter && (
            <button
              onClick={() => onGlobalFilterChange('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-dark-400 hover:text-dark-200"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>

        <button
          onClick={onRefresh}
          className="flex items-center gap-2 px-3 py-2 bg-dark-700 hover:bg-dark-600 text-dark-200 rounded-lg text-sm transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          刷新
        </button>
      </div>

      <div className="flex items-center gap-3">
        {selectedCount > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-primary-500/20 border border-primary-500/30 rounded-lg">
            <span className="text-sm text-primary-300">
              已选择 {selectedCount} 行
            </span>
          </div>
        )}

        <div className="flex items-center gap-1 px-2 py-1 bg-dark-700/50 rounded-lg">
          <Copy className="w-4 h-4 text-dark-400" />
          <kbd className="px-1.5 py-0.5 bg-dark-800 rounded text-xs text-dark-400 font-mono">
            Ctrl+C
          </kbd>
          <span className="text-xs text-dark-500 mx-1">/</span>
          <kbd className="px-1.5 py-0.5 bg-dark-800 rounded text-xs text-dark-400 font-mono">
            Ctrl+V
          </kbd>
        </div>

        <button
          className="flex items-center gap-2 px-3 py-2 bg-dark-700 hover:bg-dark-600 text-dark-200 rounded-lg text-sm transition-colors"
        >
          <Columns className="w-4 h-4" />
          列设置
        </button>

        <div className="relative">
          <button
            onClick={() => setShowExportMenu(!showExportMenu)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Download className="w-4 h-4" />
            导出
          </button>

          {showExportMenu && (
            <div className="absolute right-0 top-full mt-2 w-48 bg-dark-800 border border-dark-600 rounded-lg shadow-xl overflow-hidden z-50">
              <button
                onClick={handleExportExcel}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm text-dark-200 hover:bg-dark-700 transition-colors"
              >
                <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
                导出 Excel
              </button>
              <button
                onClick={handleExportCSV}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm text-dark-200 hover:bg-dark-700 transition-colors"
              >
                <FileText className="w-4 h-4 text-blue-400" />
                导出 CSV
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
})
