import { useCallback, useState } from 'react'
import { Upload, FileText, Database, Loader2 } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import { useDataApi } from '@/hooks/useDataApi'
import { cn } from '@/lib/utils'

const FORMAT_ICONS: Record<string, string> = {
  csv: 'CSV',
  json: 'JSON',
  parquet: 'PARQ',
}

const FORMAT_COLORS: Record<string, string> = {
  csv: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  json: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  parquet: 'bg-violet-500/20 text-violet-400 border-violet-500/30',
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
}

export default function FileUploader() {
  const [isDragging, setIsDragging] = useState(false)
  const fileMeta = useAppStore((s) => s.fileMeta)
  const isUploading = useAppStore((s) => s.isUploading)
  const uploadProgress = useAppStore((s) => s.uploadProgress)
  const reset = useAppStore((s) => s.reset)
  const { uploadFile } = useDataApi()

  const handleFile = useCallback(
    async (file: File) => {
      const ext = file.name.split('.').pop()?.toLowerCase()
      if (!['csv', 'json', 'jsonl', 'parquet'].includes(ext ?? '')) {
        alert('Only CSV, JSON, and Parquet files are supported')
        return
      }
      await uploadFile(file)
    },
    [uploadFile],
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile],
  )

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const onDragLeave = useCallback(() => setIsDragging(false), [])

  const onFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) handleFile(file)
    },
    [handleFile],
  )

  if (fileMeta) {
    return (
      <div className="rounded-xl border border-slate-700/50 bg-slate-800/50 p-5 backdrop-blur-sm">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-cyan-500/10">
              <FileText className="h-5 w-5 text-cyan-400" />
            </div>
            <div>
              <p className="font-mono text-sm font-medium text-slate-100">{fileMeta.fileName}</p>
              <p className="mt-0.5 text-xs text-slate-400">
                {formatFileSize(fileMeta.fileSize)} · {fileMeta.totalRows.toLocaleString()} rows · {fileMeta.columns.length} columns
              </p>
            </div>
          </div>
          <span
            className={cn(
              'rounded-md border px-2 py-0.5 text-[10px] font-bold tracking-wider',
              FORMAT_COLORS[fileMeta.format],
            )}
          >
            {FORMAT_ICONS[fileMeta.format]}
          </span>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {fileMeta.columns.slice(0, 8).map((col) => (
            <span
              key={col.name}
              className="rounded-md bg-slate-700/50 px-2 py-0.5 text-[11px] text-slate-300"
            >
              {col.name}
              <span className="ml-1 text-slate-500">{col.type}</span>
            </span>
          ))}
          {fileMeta.columns.length > 8 && (
            <span className="rounded-md bg-slate-700/50 px-2 py-0.5 text-[11px] text-slate-500">
              +{fileMeta.columns.length - 8} more
            </span>
          )}
        </div>

        <button
          onClick={reset}
          className="mt-4 w-full rounded-lg border border-slate-600/50 bg-slate-700/30 px-3 py-2 text-xs text-slate-300 transition hover:bg-slate-700/60 hover:text-slate-100"
        >
          Upload Another File
        </button>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/50 p-5 backdrop-blur-sm">
      <div className="mb-3 flex items-center gap-2">
        <Database className="h-4 w-4 text-cyan-400" />
        <span className="text-sm font-medium text-slate-200">Data Source</span>
      </div>

      <label
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-all duration-200',
          isDragging
            ? 'border-cyan-400 bg-cyan-500/10'
            : 'border-slate-600/50 bg-slate-900/30 hover:border-cyan-500/50 hover:bg-cyan-500/5',
          isUploading && 'pointer-events-none',
        )}
      >
        {isUploading ? (
          <>
            <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
            <p className="mt-3 text-sm text-slate-300">Uploading... {uploadProgress}%</p>
            <div className="mt-2 h-1.5 w-48 overflow-hidden rounded-full bg-slate-700">
              <div
                className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-cyan-300 transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </>
        ) : (
          <>
            <Upload className="h-8 w-8 text-slate-500 transition-colors group-hover:text-cyan-400" />
            <p className="mt-3 text-sm text-slate-300">
              Drop file here or <span className="text-cyan-400">browse</span>
            </p>
            <p className="mt-1 text-xs text-slate-500">CSV, JSON, JSONL, Parquet supported</p>
          </>
        )}
        <input
          type="file"
          accept=".csv,.json,.jsonl,.parquet"
          onChange={onFileInput}
          className="hidden"
          disabled={isUploading}
        />
      </label>
    </div>
  )
}
