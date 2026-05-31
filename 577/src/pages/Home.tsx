import { useEffect, useMemo } from 'react'
import { Beaker } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import { useDataApi } from '@/hooks/useDataApi'
import FileUploader from '@/components/FileUploader'
import SamplingPanel from '@/components/SamplingPanel'
import DataTable from '@/components/DataTable'
import StatsDashboard from '@/components/StatsDashboard'
import ExportPanel from '@/components/ExportPanel'
import SmartRecommendation from '@/components/SmartRecommendation'
import DistributionComparisonView from '@/components/DistributionComparisonView'
import AuditHistory from '@/components/AuditHistory'

export default function Home() {
  const fileMeta = useAppStore((s) => s.fileMeta)
  const rawData = useAppStore((s) => s.rawData)
  const sampleResult = useAppStore((s) => s.sampleResult)
  const sampleIndices = useAppStore((s) => s.sampleIndices)
  const rawPage = useAppStore((s) => s.rawPage)
  const { fetchChunk } = useDataApi()

  useEffect(() => {
    if (!fileMeta) return
    fetchChunk(fileMeta.fileId, 0, 200).catch(console.error)
  }, [fileMeta?.fileId])

  useEffect(() => {
    if (!fileMeta) return
    const offset = (rawPage - 1) * 50
    fetchChunk(fileMeta.fileId, offset, 50).catch(console.error)
  }, [rawPage])

  const highlightSet = useMemo(() => new Set(sampleIndices), [sampleIndices])

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-slate-950/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500/15">
              <Beaker className="h-4 w-4 text-cyan-400" />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-slate-100">DataSampler</h1>
              <p className="text-[10px] text-slate-500">Multi-strategy data sampling tool</p>
            </div>
          </div>
          {fileMeta && (
            <div className="flex items-center gap-2 rounded-lg bg-slate-800/60 px-3 py-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[11px] text-slate-300">{fileMeta.fileName}</span>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-6">
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-12 lg:col-span-4 space-y-4">
            <FileUploader />
            {fileMeta && (
              <>
                <SmartRecommendation />
                <SamplingPanel />
                <AuditHistory />
              </>
            )}
            {sampleResult && <ExportPanel />}
          </div>

          <div className="col-span-12 lg:col-span-8 space-y-4">
            {fileMeta && (
              <DataTable
                data={rawData}
                title="Original Data Preview"
                highlightIndices={highlightSet}
              />
            )}

            {sampleResult && (
              <>
                <DataTable
                  data={sampleResult}
                  title="Sample Data"
                />
                <StatsDashboard />
                <DistributionComparisonView />
              </>
            )}

            {!fileMeta && (
              <div className="flex h-[60vh] items-center justify-center rounded-xl border border-slate-800/50 bg-slate-900/20">
                <div className="text-center">
                  <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-800/60">
                    <Beaker className="h-8 w-8 text-slate-600" />
                  </div>
                  <p className="text-sm font-medium text-slate-400">Upload a file to begin sampling</p>
                  <p className="mt-1 text-xs text-slate-600">Supports CSV, JSON, and Parquet formats</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
