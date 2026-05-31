import { useCallback, useEffect, useRef } from 'react'
import { Shuffle, Layers, ArrowDownUp, Loader2 } from 'lucide-react'
import { useAppStore, type SampleMethod } from '@/store/appStore'
import { useDataApi } from '@/hooks/useDataApi'
import { useSampling } from '@/hooks/useSampling'
import { cn } from '@/lib/utils'

const METHODS: Array<{ key: SampleMethod; label: string; icon: typeof Shuffle; desc: string }> = [
  { key: 'random', label: 'Random', icon: Shuffle, desc: 'Fisher-Yates partial shuffle' },
  { key: 'stratified', label: 'Stratified', icon: Layers, desc: 'Proportional by group' },
  { key: 'systematic', label: 'Systematic', icon: ArrowDownUp, desc: 'Fixed interval sampling' },
]

export default function SamplingPanel() {
  const fileMeta = useAppStore((s) => s.fileMeta)
  const sampleConfig = useAppStore((s) => s.sampleConfig)
  const isSampling = useAppStore((s) => s.isSampling)
  const sampleResult = useAppStore((s) => s.sampleResult)
  const allDataCache = useAppStore((s) => s.allDataCache)
  const stratifyIndex = useAppStore((s) => s.stratifyIndex)
  const sampleStats = useAppStore((s) => s.sampleStats)
  const recommendation = useAppStore((s) => s.recommendation)
  const distributionComparison = useAppStore((s) => s.distributionComparison)
  const analysisGoal = useAppStore((s) => s.analysisGoal)
  const setSampleConfig = useAppStore((s) => s.setSampleConfig)
  const setAllDataCache = useAppStore((s) => s.setAllDataCache)
  const addAuditRecord = useAppStore((s) => s.addAuditRecord)
  const { fetchChunk, fetchColumnStats, fetchStratifyIndex } = useDataApi()
  const { sample } = useSampling()

  const isLoadingData = useRef(false)
  const hasPendingAudit = useRef(false)

  useEffect(() => {
    if (!isSampling && sampleStats && hasPendingAudit.current && fileMeta) {
      hasPendingAudit.current = false
      addAuditRecord({
        fileId: fileMeta.fileId,
        fileName: fileMeta.fileName,
        config: { ...sampleConfig },
        stats: { ...sampleStats },
        recommendation: recommendation ? { ...recommendation } : undefined,
        comparison: distributionComparison ? { ...distributionComparison } : undefined,
        totalRows: fileMeta.totalRows,
        columnNames: fileMeta.columns.map(c => c.name),
      })
    }
  }, [isSampling, sampleStats, fileMeta, sampleConfig, recommendation, distributionComparison, addAuditRecord])

  const ensureAllData = useCallback(async (): Promise<Record<string, unknown>[] | null> => {
    if (!fileMeta) return null
    if (allDataCache.length > 0) return allDataCache

    if (isLoadingData.current) return null
    isLoadingData.current = true

    try {
      const allData: Record<string, unknown>[] = []
      const chunkSize = 5000
      let offset = 0
      let hasMore = true

      while (hasMore) {
        const chunk = await fetchChunk(fileMeta.fileId, offset, chunkSize)
        allData.push(...chunk.data)
        offset += chunkSize
        hasMore = offset < chunk.totalRows
      }

      setAllDataCache(allData)
      return allData
    } catch (err) {
      console.error('Data fetch error:', err)
      return null
    } finally {
      isLoadingData.current = false
    }
  }, [fileMeta, allDataCache, fetchChunk, setAllDataCache])

  const executeSampling = useCallback(async () => {
    if (!fileMeta) return
    hasPendingAudit.current = true

    const data = await ensureAllData()
    if (!data) {
      hasPendingAudit.current = false
      return
    }

    const currentConfig = useAppStore.getState().sampleConfig
    const currentIndex = useAppStore.getState().stratifyIndex

    if (currentConfig.method === 'stratified' && currentConfig.stratifyColumn) {
      if (!currentIndex || currentIndex.column !== currentConfig.stratifyColumn) {
        try {
          const index = await fetchStratifyIndex(fileMeta.fileId, currentConfig.stratifyColumn)
          sample(data, currentConfig, index)
          return
        } catch (err) {
          console.error('Stratify index error:', err)
        }
      }
      sample(data, currentConfig, currentIndex)
      return
    }

    sample(data, currentConfig, null)
  }, [fileMeta, ensureAllData, fetchStratifyIndex, sample])

  const handleMethodChange = useCallback((method: SampleMethod) => {
    setSampleConfig({ method })
    if (fileMeta && allDataCache.length > 0) {
      setTimeout(() => executeSampling(), 0)
    }
  }, [setSampleConfig, fileMeta, allDataCache, executeSampling])

  const handleSliderRelease = useCallback(() => {
    if (fileMeta && allDataCache.length > 0 && !isSampling) {
      executeSampling()
    }
  }, [fileMeta, allDataCache, isSampling, executeSampling])

  const handleStratifyColumnChange = async (column: string) => {
    setSampleConfig({ stratifyColumn: column })
    if (fileMeta && column) {
      try {
        await Promise.all([
          fetchColumnStats(fileMeta.fileId, column),
          fetchStratifyIndex(fileMeta.fileId, column),
        ])
        if (allDataCache.length > 0) {
          setTimeout(() => executeSampling(), 0)
        }
      } catch {
        // silently fail
      }
    }
  }

  const isDisabled = !fileMeta || isSampling
  const canExecute = fileMeta && sampleConfig.ratio > 0 && sampleConfig.ratio <= 1

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/50 p-5 backdrop-blur-sm">
      <div className="mb-4 text-sm font-medium text-slate-200">Sampling Method</div>

      <div className="grid grid-cols-3 gap-2">
        {METHODS.map(({ key, label, icon: Icon, desc }) => (
          <button
            key={key}
            onClick={() => handleMethodChange(key)}
            disabled={isDisabled}
            className={cn(
              'flex flex-col items-center gap-1.5 rounded-lg border p-3 transition-all duration-200',
              sampleConfig.method === key
                ? 'border-cyan-500/60 bg-cyan-500/10 text-cyan-400 shadow-lg shadow-cyan-500/5'
                : 'border-slate-600/30 bg-slate-900/30 text-slate-400 hover:border-slate-500/50 hover:text-slate-300',
              isDisabled && 'cursor-not-allowed opacity-50',
            )}
          >
            <Icon className="h-5 w-5" />
            <span className="text-xs font-semibold">{label}</span>
            <span className="text-[10px] leading-tight opacity-60">{desc}</span>
          </button>
        ))}
      </div>

      <div className="mt-5">
        <div className="flex items-center justify-between">
          <label className="text-xs font-medium text-slate-300">Sample Ratio</label>
          <span className="rounded bg-cyan-500/15 px-2 py-0.5 font-mono text-xs font-bold text-cyan-400">
            {(sampleConfig.ratio * 100).toFixed(0)}%
          </span>
        </div>
        <input
          type="range"
          min={1}
          max={100}
          value={Math.round(sampleConfig.ratio * 100)}
          onChange={(e) => setSampleConfig({ ratio: parseInt(e.target.value) / 100 })}
          onPointerUp={handleSliderRelease}
          onKeyUp={handleSliderRelease}
          disabled={isDisabled}
          className="mt-2 h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-700 accent-cyan-500 disabled:cursor-not-allowed disabled:opacity-50"
        />
        <div className="mt-1 flex justify-between text-[10px] text-slate-500">
          <span>1%</span>
          <span>50%</span>
          <span>100%</span>
        </div>
        {fileMeta && allDataCache.length > 0 && (
          <p className="mt-1 text-[10px] text-slate-500">Release slider to auto-update preview</p>
        )}
      </div>

      {sampleConfig.method === 'stratified' && (
        <div className="mt-4">
          <label className="text-xs font-medium text-slate-300">Stratify Column</label>
          <select
            value={sampleConfig.stratifyColumn}
            onChange={(e) => handleStratifyColumnChange(e.target.value)}
            disabled={isDisabled}
            className="mt-1.5 w-full rounded-lg border border-slate-600/50 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 outline-none transition focus:border-cyan-500/50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <option value="">Select column...</option>
            {fileMeta?.columns.map((col) => (
              <option key={col.name} value={col.name}>
                {col.name} ({col.type})
              </option>
            ))}
          </select>
          {stratifyIndex && stratifyIndex.column === sampleConfig.stratifyColumn && (
            <p className="mt-1.5 text-[10px] text-emerald-400/80">
              Pre-computed: {Object.keys(stratifyIndex.groups).length} groups indexed
            </p>
          )}
        </div>
      )}

      {sampleConfig.method === 'systematic' && (
        <div className="mt-4">
          <label className="text-xs font-medium text-slate-300">Step Size</label>
          <input
            type="number"
            min={1}
            value={sampleConfig.stepSize}
            onChange={(e) => setSampleConfig({ stepSize: Math.max(1, parseInt(e.target.value) || 1) })}
            onBlur={() => {
              if (fileMeta && allDataCache.length > 0 && !isSampling) {
                executeSampling()
              }
            }}
            disabled={isDisabled}
            className="mt-1.5 w-full rounded-lg border border-slate-600/50 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 outline-none transition focus:border-cyan-500/50 disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>
      )}

      {fileMeta && (
        <div className="mt-4 rounded-lg bg-slate-900/50 p-3">
          <p className="text-[11px] text-slate-400">
            Expected sample size:{' '}
            <span className="font-mono font-bold text-cyan-400">
              {Math.max(1, Math.round(fileMeta.totalRows * sampleConfig.ratio)).toLocaleString()}
            </span>
            {' / '}
            <span className="font-mono text-slate-300">
              {fileMeta.totalRows.toLocaleString()}
            </span>
          </p>
        </div>
      )}

      <button
        onClick={executeSampling}
        disabled={!canExecute || isSampling}
        className={cn(
          'mt-5 flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all duration-200',
          canExecute && !isSampling
            ? 'bg-gradient-to-r from-cyan-500 to-cyan-400 text-slate-900 shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30'
            : 'cursor-not-allowed bg-slate-700/50 text-slate-500',
        )}
      >
        {isSampling ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Sampling...
          </>
        ) : (
          <>
            <Shuffle className="h-4 w-4" />
            Execute Sampling
          </>
        )}
      </button>
    </div>
  )
}
