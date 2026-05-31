import { useMemo } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import { cn } from '@/lib/utils'

export default function DataTable({
  data,
  title,
  highlightIndices,
}: {
  data: Record<string, unknown>[]
  title: string
  highlightIndices?: Set<number>
}) {
  const rawPage = useAppStore((s) => s.rawPage)
  const rawPageSize = useAppStore((s) => s.rawPageSize)
  const setRawPage = useAppStore((s) => s.setRawPage)

  const columns = useMemo(() => {
    if (data.length === 0) return []
    return Object.keys(data[0])
  }, [data])

  const totalPages = Math.ceil(data.length / rawPageSize)
  const pageData = useMemo(() => {
    const start = (rawPage - 1) * rawPageSize
    return data.slice(start, start + rawPageSize)
  }, [data, rawPage, rawPageSize])

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-slate-700/50 bg-slate-800/30">
        <p className="text-sm text-slate-500">No data to display</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/50 backdrop-blur-sm">
      <div className="flex items-center justify-between border-b border-slate-700/50 px-4 py-3">
        <span className="text-sm font-medium text-slate-200">{title}</span>
        <span className="rounded bg-slate-700/50 px-2 py-0.5 text-[11px] text-slate-400">
          {data.length.toLocaleString()} rows · {columns.length} cols
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-700/30">
              <th className="sticky left-0 z-10 bg-slate-800 px-3 py-2 font-mono text-[10px] font-semibold text-slate-500">
                #
              </th>
              {columns.map((col) => (
                <th
                  key={col}
                  className="whitespace-nowrap px-3 py-2 font-mono text-[10px] font-semibold text-slate-500"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageData.map((row, idx) => {
              const globalIdx = (rawPage - 1) * rawPageSize + idx
              const isHighlighted = highlightIndices?.has(globalIdx)
              return (
                <tr
                  key={idx}
                  className={cn(
                    'border-b border-slate-700/20 transition-colors',
                    isHighlighted
                      ? 'bg-cyan-500/10'
                      : 'hover:bg-slate-700/20',
                  )}
                >
                  <td
                    className={cn(
                      'sticky left-0 z-10 bg-slate-800 px-3 py-1.5 font-mono text-[10px]',
                      isHighlighted ? 'text-cyan-400' : 'text-slate-600',
                    )}
                  >
                    {globalIdx}
                  </td>
                  {columns.map((col) => (
                    <td
                      key={col}
                      className={cn(
                        'max-w-[200px] truncate px-3 py-1.5 font-mono',
                        isHighlighted ? 'text-cyan-200' : 'text-slate-300',
                      )}
                      title={String(row[col] ?? '')}
                    >
                      {String(row[col] ?? '')}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between border-t border-slate-700/50 px-4 py-2">
        <button
          onClick={() => setRawPage(Math.max(1, rawPage - 1))}
          disabled={rawPage <= 1}
          className="rounded p-1 text-slate-400 transition hover:bg-slate-700/50 hover:text-slate-200 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-[11px] text-slate-500">
          Page {rawPage} / {totalPages || 1}
        </span>
        <button
          onClick={() => setRawPage(Math.min(totalPages, rawPage + 1))}
          disabled={rawPage >= totalPages}
          className="rounded p-1 text-slate-400 transition hover:bg-slate-700/50 hover:text-slate-200 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
