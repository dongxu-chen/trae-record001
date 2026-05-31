import { Download, FileJson, FileSpreadsheet } from 'lucide-react'
import { useState } from 'react'
import { useAppStore } from '@/store/appStore'
import { useDataApi } from '@/hooks/useDataApi'
import { cn } from '@/lib/utils'

export default function ExportPanel() {
  const [format, setFormat] = useState<'csv' | 'json'>('csv')
  const [isExporting, setIsExporting] = useState(false)
  const fileMeta = useAppStore((s) => s.fileMeta)
  const sampleIndices = useAppStore((s) => s.sampleIndices)
  const sampleResult = useAppStore((s) => s.sampleResult)
  const { exportSample } = useDataApi()

  const hasResults = sampleResult && sampleIndices.length > 0

  const handleExport = async () => {
    if (!fileMeta || !hasResults) return
    setIsExporting(true)
    try {
      await exportSample(fileMeta.fileId, sampleIndices, format)
    } catch (err) {
      console.error('Export error:', err)
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/50 p-5 backdrop-blur-sm">
      <div className="mb-3 text-sm font-medium text-slate-200">Export Results</div>

      <div className="flex gap-2">
        <button
          onClick={() => setFormat('csv')}
          className={cn(
            'flex flex-1 items-center justify-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition',
            format === 'csv'
              ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-400'
              : 'border-slate-600/30 bg-slate-900/30 text-slate-400 hover:border-slate-500/50',
          )}
        >
          <FileSpreadsheet className="h-4 w-4" />
          CSV
        </button>
        <button
          onClick={() => setFormat('json')}
          className={cn(
            'flex flex-1 items-center justify-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition',
            format === 'json'
              ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-400'
              : 'border-slate-600/30 bg-slate-900/30 text-slate-400 hover:border-slate-500/50',
          )}
        >
          <FileJson className="h-4 w-4" />
          JSON
        </button>
      </div>

      <button
        onClick={handleExport}
        disabled={!hasResults || isExporting}
        className={cn(
          'mt-3 flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all',
          hasResults && !isExporting
            ? 'bg-gradient-to-r from-orange-500 to-orange-400 text-white shadow-lg shadow-orange-500/20 hover:shadow-orange-500/30'
            : 'cursor-not-allowed bg-slate-700/50 text-slate-500',
        )}
      >
        <Download className="h-4 w-4" />
        {isExporting ? 'Exporting...' : 'Download Sample'}
      </button>

      {hasResults && (
        <p className="mt-2 text-center text-[10px] text-slate-500">
          {sampleIndices.length.toLocaleString()} records will be exported
        </p>
      )}
    </div>
  )
}
