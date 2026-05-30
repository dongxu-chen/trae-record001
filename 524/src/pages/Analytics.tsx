import { useEffect, useState } from 'react'
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { fetchOccupancy, fetchAllPredictions, fetchStrategyStats } from '@/api'
import { ZONE_COLORS, ZONE_NAMES, type ZoneId, type OccupancyRecord, type PredictionResult, type StrategyStats } from '@/types'
import { TrendingUp, Brain, Target, BarChart3 } from 'lucide-react'

type TimeRange = '6' | '24' | '72' | '168'

export default function Analytics() {
  const [timeRange, setTimeRange] = useState<TimeRange>('24')
  const [occupancyData, setOccupancyData] = useState<Record<string, OccupancyRecord[]>>({})
  const [predictions, setPredictions] = useState<Record<string, PredictionResult>>({})
  const [strategyStats, setStrategyStats] = useState<StrategyStats | null>(null)
  const [selectedZones, setSelectedZones] = useState<string[]>(['A', 'B', 'C', 'D', 'E'])

  useEffect(() => {
    async function load() {
      const [occ, preds, stats] = await Promise.all([
        fetchOccupancy(parseInt(timeRange)),
        fetchAllPredictions(30),
        fetchStrategyStats(),
      ])
      setOccupancyData(occ)
      setPredictions(preds)
      setStrategyStats(stats)
    }
    load()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [timeRange])

  const chartData = (() => {
    const allTimestamps = new Set<string>()
    Object.entries(occupancyData).forEach(([zid, records]) => {
      if (!selectedZones.includes(zid)) return
      records.forEach((r) => allTimestamps.add(r.timestamp))
    })

    const sorted = Array.from(allTimestamps).sort()
    const step = Math.max(1, Math.floor(sorted.length / 60))

    return sorted
      .filter((_, i) => i % step === 0)
      .map((ts) => {
        const point: Record<string, string | number> = {}
        const date = new Date(ts)
        point.time = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
        selectedZones.forEach((zid) => {
          const records = occupancyData[zid] || []
          const match = records.find((r) => r.timestamp === ts)
          if (match) {
            point[zid] = match.occupied
          }
        })
        return point
      })
  })()

  const predictionAccuracy = Object.entries(predictions).map(([zid, pred]) => ({
    zone: `${zid}区`,
    mae: pred.accuracy_metrics.mae,
    rmse: pred.accuracy_metrics.rmse,
    color: ZONE_COLORS[zid as ZoneId],
  }))

  const strategyData = strategyStats
    ? Object.entries(strategyStats.zone_distribution).map(([zid, count]) => ({
        zone: `${zid}区`,
        count,
        fill: ZONE_COLORS[zid as ZoneId],
      }))
    : []

  const toggleZone = (zid: string) => {
    setSelectedZones((prev) =>
      prev.includes(zid) ? prev.filter((z) => z !== zid) : [...prev, zid]
    )
  }

  const timeRangeOptions: { value: TimeRange; label: string }[] = [
    { value: '6', label: '6小时' },
    { value: '24', label: '24小时' },
    { value: '72', label: '3天' },
    { value: '168', label: '7天' },
  ]

  return (
    <div className="p-4 h-full overflow-auto animate-fade-in">
      <header className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-white font-body">数据分析</h2>
          <p className="text-xs text-slate-500">历史占用率、预测准确率、策略效果分析</p>
        </div>
      </header>

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-8">
          <div className="glass-card glow-cyan p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-brand-cyan" />
                历史占用率
              </h3>
              <div className="flex items-center gap-2">
                {timeRangeOptions.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setTimeRange(opt.value)}
                    className={`px-2 py-1 rounded text-[10px] transition-all ${
                      timeRange === opt.value
                        ? 'bg-brand-cyan/20 text-brand-cyan'
                        : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2 mb-3">
              {['A', 'B', 'C', 'D', 'E'].map((zid) => (
                <button
                  key={zid}
                  onClick={() => toggleZone(zid)}
                  className={`px-2 py-0.5 rounded text-[10px] border transition-all ${
                    selectedZones.includes(zid)
                      ? 'border-transparent'
                      : 'border-brand-border opacity-40'
                  }`}
                  style={{
                    background: selectedZones.includes(zid) ? `${ZONE_COLORS[zid as ZoneId]}20` : 'transparent',
                    color: selectedZones.includes(zid) ? ZONE_COLORS[zid as ZoneId] : '#64748B',
                  }}
                >
                  {zid}区
                </button>
              ))}
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                  <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#64748B' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#64748B' }} tickLine={false} width={30} />
                  <Tooltip
                    contentStyle={{ background: '#0F172A', border: '1px solid #334155', borderRadius: 8, fontSize: 11, color: '#E2E8F0' }}
                  />
                  {selectedZones.map((zid) => (
                    <Area
                      key={zid}
                      type="monotone"
                      dataKey={zid}
                      stroke={ZONE_COLORS[zid as ZoneId]}
                      fill={ZONE_COLORS[zid as ZoneId]}
                      fillOpacity={0.1}
                      strokeWidth={1.5}
                    />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="col-span-4 space-y-4">
          <div className="glass-card p-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-3">
              <Brain className="w-4 h-4 text-brand-purple" />
              预测准确率
            </h3>
            <div className="space-y-2">
              {predictionAccuracy.map((item) => (
                <div key={item.zone} className="flex items-center gap-2">
                  <span className="text-[10px] w-8" style={{ color: item.color }}>{item.zone}</span>
                  <div className="flex-1">
                    <div className="flex items-center gap-1 text-[10px] text-slate-400">
                      <span>MAE</span>
                      <span className="data-value" style={{ color: item.color }}>{item.mae}</span>
                    </div>
                    <div className="h-1 bg-brand-dark rounded-full mt-0.5">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${Math.min(100, item.mae * 5)}%`, background: item.color }}
                      />
                    </div>
                  </div>
                  <div className="w-16">
                    <div className="flex items-center gap-1 text-[10px] text-slate-400">
                      <span>RMSE</span>
                      <span className="data-value" style={{ color: item.color }}>{item.rmse}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card p-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-3">
              <Target className="w-4 h-4 text-brand-orange" />
              策略统计
            </h3>
            {strategyStats && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-brand-dark/50 rounded-lg p-2 text-center">
                    <div className="data-value text-lg text-brand-cyan">{strategyStats.total_guidance}</div>
                    <div className="text-[10px] text-slate-500">总引导次数</div>
                  </div>
                  <div className="bg-brand-dark/50 rounded-lg p-2 text-center">
                    <div className="data-value text-lg text-brand-cyan">
                      {Math.round(strategyStats.success_rate * 100)}%
                    </div>
                    <div className="text-[10px] text-slate-500">成功率</div>
                  </div>
                </div>
                {strategyData.length > 0 && (
                  <div className="h-32">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={strategyData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                        <XAxis dataKey="zone" tick={{ fontSize: 10, fill: '#64748B' }} tickLine={false} />
                        <YAxis tick={{ fontSize: 10, fill: '#64748B' }} tickLine={false} width={25} />
                        <Tooltip
                          contentStyle={{ background: '#0F172A', border: '1px solid #334155', borderRadius: 8, fontSize: 11, color: '#E2E8F0' }}
                        />
                        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                          {strategyData.map((entry, index) => (
                            <rect key={index} fill={entry.fill} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
