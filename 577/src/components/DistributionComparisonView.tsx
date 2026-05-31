import { useEffect, useMemo, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { GitCompare, TrendingUp } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import { compareDistribution, findBestComparisonColumn } from '@/utils/distributionAnalysis'
import { cn } from '@/lib/utils'

export default function DistributionComparisonView() {
  const fileMeta = useAppStore((s) => s.fileMeta)
  const allDataCache = useAppStore((s) => s.allDataCache)
  const sampleResult = useAppStore((s) => s.sampleResult)
  const sampleStats = useAppStore((s) => s.sampleStats)
  const distributionComparison = useAppStore((s) => s.distributionComparison)
  const setDistributionComparison = useAppStore((s) => s.setDistributionComparison)

  const [selectedColumn, setSelectedColumn] = useState<string>('')

  useEffect(() => {
    if (!fileMeta) return
    const bestCol = findBestComparisonColumn(allDataCache, fileMeta.columns)
    if (bestCol) setSelectedColumn(bestCol.name)
  }, [fileMeta?.fileId])

  useEffect(() => {
    if (!sampleResult || !allDataCache.length || !selectedColumn) return
    const colMeta = fileMeta?.columns.find(c => c.name === selectedColumn)
    if (!colMeta) return

    const comparison = compareDistribution(allDataCache, sampleResult, selectedColumn, colMeta.type)
    setDistributionComparison(comparison)
  }, [sampleResult, selectedColumn, allDataCache, fileMeta?.columns, setDistributionComparison])

  const chartData = useMemo(() => {
    if (!distributionComparison) return []
    return distributionComparison.overall.map((o, idx) => ({
      bin: o.bin,
      总体: o.ratio * 100,
      样本: distributionComparison.sample[idx]?.ratio * 100 || 0,
    }))
  }, [distributionComparison])

  if (!sampleStats || !fileMeta || !sampleResult) return null

  const colMeta = fileMeta.columns.find(c => c.name === selectedColumn)
  const selectedColType = colMeta?.type || 'string'

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/50 p-5 backdrop-blur-sm">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitCompare className="h-4 w-4 text-violet-400" />
          <span className="text-sm font-medium text-slate-200">分布对比</span>
        </div>
        <select
          value={selectedColumn}
          onChange={(e) => setSelectedColumn(e.target.value)}
          className="rounded-md border border-slate-600/50 bg-slate-900/50 px-2 py-1 text-[11px] text-slate-300 outline-none focus:border-violet-500/50"
        >
          {fileMeta.columns.map(col => (
            <option key={col.name} value={col.name}>
              {col.name} ({col.type})
            </option>
          ))}
        </select>
      </div>

      {distributionComparison && (
        <>
          {selectedColType === 'number' && (
            <div className="mb-4 grid grid-cols-2 gap-3">
              <StatBadge
                label="KS 统计量"
                value={distributionComparison.ksStatistic.toFixed(4)}
                status={distributionComparison.ksStatistic < 0.1 ? 'good' : distributionComparison.ksStatistic < 0.2 ? 'warn' : 'bad'}
              />
              <StatBadge
                label="Wasserstein 距离"
                value={distributionComparison.wassersteinDistance.toFixed(2)}
              />
            </div>
          )}

          <div className="mb-2 flex items-center gap-4 text-[10px]">
            <div className="flex items-center gap-1.5">
              <div className="h-2 w-2 rounded-full bg-slate-500" />
              <span className="text-slate-400">总体分布</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-2 w-2 rounded-full bg-cyan-500" />
              <span className="text-slate-400">样本分布</span>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} barGap={2}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey="bin"
                tick={{ fontSize: 9, fill: '#64748b' }}
                axisLine={false}
                tickLine={false}
                angle={-20}
                textAnchor="end"
                height={50}
              />
              <YAxis
                tick={{ fontSize: 9, fill: '#64748b' }}
                axisLine={false}
                tickLine={false}
                width={35}
                tickFormatter={(v) => `${v.toFixed(0)}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                  fontSize: '11px',
                  color: '#e2e8f0',
                }}
                formatter={(value: number) => [`${value.toFixed(2)}%`]}
              />
              <Bar dataKey="总体" fill="#475569" radius={[3, 3, 0, 0]} />
              <Bar dataKey="样本" fill="#06b6d4" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>

          <div className="mt-2 flex items-start gap-2 rounded-md bg-slate-900/40 px-2.5 py-2">
            <TrendingUp className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-violet-400" />
            <p className="text-[10px] leading-relaxed text-slate-400">
              {selectedColType === 'number' ? (
                distributionComparison.ksStatistic < 0.05
                  ? '样本与总体分布无显著差异，代表性良好 (KS < 0.05)'
                  : distributionComparison.ksStatistic < 0.1
                    ? '样本分布与总体基本一致，可接受 (KS < 0.1)'
                    : '样本分布与总体存在一定偏差，建议检查抽样方法'
              ) : (
                '分类字段分布对比，检查各类别占比是否一致'
              )}
            </p>
          </div>
        </>
      )}
    </div>
  )
}

function StatBadge({ label, value, status }: { label: string; value: string; status?: 'good' | 'warn' | 'bad' }) {
  return (
    <div className="rounded-md bg-slate-900/50 px-3 py-2">
      <p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p>
      <p className={cn(
        'mt-0.5 font-mono text-base font-bold',
        status === 'good' && 'text-emerald-400',
        status === 'warn' && 'text-amber-400',
        status === 'bad' && 'text-orange-400',
        !status && 'text-slate-200',
      )}>
        {value}
      </p>
    </div>
  )
}
