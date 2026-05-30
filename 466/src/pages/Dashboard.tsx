import { useEffect, useState, useMemo } from 'react'
import {
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Area, AreaChart, Legend,
} from 'recharts'
import { Activity, AlertTriangle, Database, Shield, TrendingUp, TrendingDown, Minus, Sparkles, Loader2 } from 'lucide-react'
import StatCard from '@/components/StatCard'
import { useStore } from '@/store'
import { api } from '@/utils/api'
import { cn } from '@/lib/utils'
import type { MetricsTrendPoint, AnomalyHeatmapPoint, MetricType, ForecastPoint } from '@/types'

const METRIC_OPTIONS: { value: string; label: string }[] = [
  { value: 'all', label: 'All Metrics' },
  { value: 'row_count', label: 'Row Count' },
  { value: 'null_rate', label: 'Null Rate' },
  { value: 'duplicate_rate', label: 'Duplicate Rate' },
]

const METRIC_COLORS: Record<string, string> = {
  row_count: '#06B6D4',
  null_rate: '#F59E0B',
  duplicate_rate: '#EF4444',
}

const SEVERITY_BADGE: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  warning: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  info: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
}

function statusDot(status: string) {
  if (status === 'active') return 'bg-red-400 animate-pulse'
  if (status === 'acknowledged') return 'bg-amber-400'
  return 'bg-gray-500'
}

function heatmapColor(severity: number) {
  if (severity >= 0.8) return 'bg-red-500/70'
  if (severity >= 0.5) return 'bg-amber-500/60'
  if (severity >= 0.2) return 'bg-yellow-500/40'
  return 'bg-emerald-500/40'
}

const trendIcon: Record<string, typeof TrendingUp> = {
  increasing: TrendingUp,
  decreasing: TrendingDown,
  stable: Minus,
}

const trendColor: Record<string, string> = {
  increasing: 'text-red-400',
  decreasing: 'text-emerald-400',
  stable: 'text-gray-400',
}

export default function Dashboard() {
  const {
    dashboardOverview, fetchDashboardOverview, recentAlerts, fetchRecentAlerts,
    forecastOverview, forecastTimeseries, forecastLoading,
    fetchForecastOverview, fetchForecastTimeseries, generateForecast,
  } = useStore()

  const [metricType, setMetricType] = useState('all')
  const [tableId, setTableId] = useState('')
  const [trendData, setTrendData] = useState<Record<string, MetricsTrendPoint[]>>({})
  const [heatmapData, setHeatmapData] = useState<AnomalyHeatmapPoint[]>([])
  const [forecastHorizon, setForecastHorizon] = useState(30)
  const [generatingForecast, setGeneratingForecast] = useState(false)

  useEffect(() => {
    fetchDashboardOverview()
    fetchRecentAlerts(8)
    fetchForecastOverview()
    fetchForecastTimeseries(30)
  }, [])

  useEffect(() => {
    fetchForecastTimeseries(forecastHorizon)
  }, [forecastHorizon])

  const handleGenerateForecast = async () => {
    setGeneratingForecast(true)
    try {
      await generateForecast(forecastHorizon)
    } finally {
      setGeneratingForecast(false)
    }
  }

  useEffect(() => {
    const types = metricType === 'all' ? ['row_count', 'null_rate', 'duplicate_rate'] as MetricType[] : [metricType as MetricType]
    Promise.all(
      types.map(t => api.dashboard.metricsTrend({ tableId: tableId || undefined, metricType: t, days: 30 }))
    ).then(results => {
      const map: Record<string, MetricsTrendPoint[]> = {}
      types.forEach((t, i) => { map[t] = results[i] })
      setTrendData(map)
    })
  }, [metricType, tableId])

  useEffect(() => {
    api.dashboard.anomalyHeatmap().then(setHeatmapData)
  }, [])

  const chartData = useMemo(() => {
    const dateMap = new Map<string, Record<string, number>>()
    Object.entries(trendData).forEach(([metric, points]) => {
      points.forEach(p => {
        if (!dateMap.has(p.date)) dateMap.set(p.date, { date: p.date })
        dateMap.get(p.date)![metric] = p.value
      })
    })
    return Array.from(dateMap.values()).sort((a, b) => a.date.localeCompare(b.date))
  }, [trendData])

  const { tableNames, metricNames, heatmapGrid } = useMemo(() => {
    const tables = [...new Set(heatmapData.map(h => h.table_name))]
    const metrics = [...new Set(heatmapData.map(h => h.metric))]
    const grid = new Map<string, AnomalyHeatmapPoint>()
    heatmapData.forEach(h => grid.set(`${h.table_name}::${h.metric}`, h))
    return { tableNames: tables, metricNames: metrics, heatmapGrid: grid }
  }, [heatmapData])

  const forecastChartData = useMemo(() => {
    const dateMap = new Map<string, {
      date: string;
      historical?: number;
      predicted?: number;
      upper_bound?: number;
      lower_bound?: number;
    }>()

    const now = new Date()
    for (let i = 29; i >= 0; i--) {
      const d = new Date(now)
      d.setDate(d.getDate() - i)
      const dateStr = d.toISOString().split('T')[0]
      dateMap.set(dateStr, { date: dateStr })
    }

    for (let i = 1; i <= forecastHorizon; i++) {
      const d = new Date(now)
      d.setDate(d.getDate() + i)
      const dateStr = d.toISOString().split('T')[0]
      dateMap.set(dateStr, { date: dateStr })
    }

    forecastTimeseries.forEach((p: ForecastPoint) => {
      const entry = dateMap.get(p.date)
      if (entry) {
        const pointDate = new Date(p.date)
        if (pointDate <= now) {
          entry.historical = p.predicted_alerts
        } else {
          entry.predicted = p.predicted_alerts
          entry.upper_bound = p.upper_bound
          entry.lower_bound = p.lower_bound
        }
      }
    })

    return Array.from(dateMap.values()).sort((a, b) => a.date.localeCompare(b.date))
  }, [forecastTimeseries, forecastHorizon])

  const overview = dashboardOverview
  const forecast = forecastOverview

  const forecastTrendIcon = forecast?.trend_direction ? trendIcon[forecast.trend_direction] : Minus
  const forecastTrendColor = forecast?.trend_direction ? trendColor[forecast.trend_direction] : 'text-gray-400'

  return (
    <div className="space-y-6 p-6 min-h-screen bg-[#0a0f1a]">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard label="Quality Score" value={overview?.overallScore ?? '—'} icon={Activity} color="cyan" trend={overview ? `${overview.statusBreakdown.healthy} healthy` : undefined} />
        <StatCard label="Active Alerts" value={overview?.activeAlerts ?? 0} icon={AlertTriangle} color="red" pulse={(overview?.activeAlerts ?? 0) > 0} />
        <StatCard label="Monitored Tables" value={overview?.monitoredTables ?? '—'} icon={Database} color="emerald" />
        <StatCard label="Total Rules" value={overview?.totalRules ?? '—'} icon={Shield} color="violet" />
        <div
          className={cn(
            'relative overflow-hidden rounded-xl border bg-gradient-to-br p-5 transition-all duration-300 hover:scale-[1.02] hover:shadow-lg',
            'from-violet-500/20 to-violet-600/5 border-violet-500/30 text-violet-400',
          )}
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs text-gray-400 font-medium tracking-wide uppercase">未来7天预测告警</p>
              <p className="mt-2 text-3xl font-mono font-bold tracking-tight">
                {forecastLoading ? '—' : (forecast?.next_7_days ?? '—')}
              </p>
              {forecast && (
                <div className="mt-1 flex items-center gap-1.5">
                  <forecastTrendIcon className={cn('w-3.5 h-3.5', forecastTrendColor)} />
                  <span className="text-xs text-gray-500">
                    置信度 <span className="text-gray-300">{forecast.confidence}%</span>
                  </span>
                </div>
              )}
            </div>
            <div className="p-2.5 rounded-lg bg-violet-500/15">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 rounded-xl border border-gray-700/50 bg-[#0d1424] p-5">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
            <h2 className="text-lg font-semibold text-gray-200">Metrics Trend</h2>
            <div className="flex gap-2">
              <select
                value={metricType}
                onChange={e => setMetricType(e.target.value)}
                className="bg-[#0a0f1a] border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300 focus:outline-none focus:border-cyan-500"
              >
                {METRIC_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <select
                value={tableId}
                onChange={e => setTableId(e.target.value)}
                className="bg-[#0a0f1a] border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300 focus:outline-none focus:border-cyan-500"
              >
                <option value="">All Tables</option>
              </select>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <defs>
                {Object.entries(METRIC_COLORS).map(([key, color]) => (
                  <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={color} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ background: '#0d1424', border: '1px solid #1e293b', borderRadius: 8 }}
                labelStyle={{ color: '#94a3b8' }}
              />
              {Object.entries(METRIC_COLORS)
                .filter(([key]) => metricType === 'all' || key === metricType)
                .map(([key, color]) => (
                  <Area key={key} type="monotone" dataKey={key} stroke={color} fill={`url(#grad-${key})`} strokeWidth={2} dot={false} />
                ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl border border-gray-700/50 bg-[#0d1424] p-5">
          <h2 className="text-lg font-semibold text-gray-200 mb-4">Recent Alerts</h2>
          <div className="space-y-3 max-h-[340px] overflow-y-auto pr-1">
            {recentAlerts.map(alert => (
              <div key={alert.id} className="flex items-start gap-3 p-3 rounded-lg bg-[#0a0f1a]/60 border border-gray-800/50">
                <span className={cn('mt-1 w-2 h-2 rounded-full shrink-0', statusDot(alert.status))} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={cn('text-[10px] px-1.5 py-0.5 rounded border font-medium', SEVERITY_BADGE[alert.severity])}>
                      {alert.severity}
                    </span>
                    <span className="text-xs text-gray-400 truncate">{alert.table_name}</span>
                  </div>
                  <p className="text-xs text-gray-300 leading-relaxed">{alert.message}</p>
                  <p className="text-[10px] text-gray-600 mt-1">{new Date(alert.triggered_at).toLocaleString()}</p>
                </div>
              </div>
            ))}
            {recentAlerts.length === 0 && (
              <p className="text-sm text-gray-600 text-center py-8">No recent alerts</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 rounded-xl border border-gray-700/50 bg-[#0d1424] p-5">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
            <h2 className="text-lg font-semibold text-gray-200">质量趋势预测</h2>
            <div className="flex gap-2">
              <select
                value={forecastHorizon}
                onChange={e => setForecastHorizon(Number(e.target.value))}
                className="bg-[#0a0f1a] border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300 focus:outline-none focus:border-violet-500"
              >
                <option value={7}>未来 7 天</option>
                <option value={14}>未来 14 天</option>
                <option value={30}>未来 30 天</option>
              </select>
              <button
                onClick={handleGenerateForecast}
                disabled={generatingForecast}
                className="px-3 py-1.5 rounded-lg border border-violet-500/50 bg-violet-500/10 text-violet-400 text-sm font-medium hover:bg-violet-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
              >
                {generatingForecast ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                {generatingForecast ? '生成中...' : '生成预测'}
              </button>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={forecastChartData}>
              <defs>
                <linearGradient id="grad-historical" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#06B6D4" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="grad-predicted" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="grad-confidence" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ background: '#0d1424', border: '1px solid #1e293b', borderRadius: 8 }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="upper_bound"
                stroke="transparent"
                fill="url(#grad-confidence)"
                strokeWidth={0}
                name="置信区间上界"
              />
              <Area
                type="monotone"
                dataKey="lower_bound"
                stroke="transparent"
                fill="#0d1424"
                strokeWidth={0}
                name="置信区间下界"
              />
              <Area
                type="monotone"
                dataKey="historical"
                stroke="#06B6D4"
                fill="url(#grad-historical)"
                strokeWidth={2}
                dot={false}
                name="历史告警"
              />
              <Area
                type="monotone"
                dataKey="predicted"
                stroke="#8B5CF6"
                fill="url(#grad-predicted)"
                strokeWidth={2}
                dot={false}
                strokeDasharray="5 5"
                name="预测告警"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl border border-gray-700/50 bg-[#0d1424] p-5">
          <h2 className="text-lg font-semibold text-gray-200 mb-4">预测概览</h2>
          {forecastLoading ? (
            <div className="flex items-center justify-center h-[300px] text-gray-500">
              <Loader2 className="w-6 h-6 animate-spin text-violet-400" />
            </div>
          ) : forecast ? (
            <div className="space-y-4">
              <div className="rounded-lg border border-gray-700/50 bg-[#0a0f1a] p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-400">未来 7 天</span>
                  <span className="text-2xl font-mono font-bold text-violet-400">{forecast.next_7_days}</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <forecastTrendIcon className={cn('w-4 h-4', forecastTrendColor)} />
                  <span className="text-gray-500">趋势: <span className={forecastTrendColor}>{forecast.trend_direction === 'increasing' ? '上升' : forecast.trend_direction === 'decreasing' ? '下降' : '稳定'}</span></span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-gray-700/50 bg-[#0a0f1a] p-3">
                  <p className="text-xs text-gray-500 mb-1">14天预测</p>
                  <p className="text-lg font-mono font-bold text-cyan-400">{forecast.next_14_days ?? '—'}</p>
                </div>
                <div className="rounded-lg border border-gray-700/50 bg-[#0a0f1a] p-3">
                  <p className="text-xs text-gray-500 mb-1">30天预测</p>
                  <p className="text-lg font-mono font-bold text-emerald-400">{forecast.next_30_days ?? '—'}</p>
                </div>
              </div>

              <div className="rounded-lg border border-gray-700/50 bg-[#0a0f1a] p-4">
                <p className="text-xs text-gray-500 mb-2">置信度</p>
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-2 rounded-full bg-gray-800">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-violet-600 to-violet-400"
                      style={{ width: `${forecast.confidence}%` }}
                    />
                  </div>
                  <span className="text-sm font-mono text-violet-400">{forecast.confidence}%</span>
                </div>
              </div>

              <div className="rounded-lg border border-gray-700/50 bg-[#0a0f1a] p-4">
                <p className="text-xs text-gray-500 mb-2">预测明细</p>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">严重告警</span>
                    <span className="font-mono text-red-400">{forecast.predicted_critical ?? 0}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">警告告警</span>
                    <span className="font-mono text-amber-400">{forecast.predicted_warning ?? 0}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">模型版本</span>
                    <span className="font-mono text-cyan-400">{forecast.model_version ?? '—'}</span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-[300px] text-gray-500">
              <TrendingUp className="w-12 h-12 mb-3 opacity-30" />
              <p className="text-sm mb-4">暂无预测数据</p>
              <button
                onClick={handleGenerateForecast}
                disabled={generatingForecast}
                className="px-4 py-2 text-sm rounded-lg border border-violet-500/50 bg-violet-500/10 text-violet-400 hover:bg-violet-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {generatingForecast ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                {generatingForecast ? '生成中...' : '生成预测'}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-gray-700/50 bg-[#0d1424] p-5">
        <h2 className="text-lg font-semibold text-gray-200 mb-4">Anomaly Heatmap</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr>
                <th className="text-left text-gray-500 font-medium pb-3 pr-4">Table</th>
                {metricNames.map(m => (
                  <th key={m} className="text-center text-gray-500 font-medium pb-3 px-2">{m}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tableNames.map(table => (
                <tr key={table}>
                  <td className="text-gray-300 py-1.5 pr-4 font-mono">{table}</td>
                  {metricNames.map(metric => {
                    const point = heatmapGrid.get(`${table}::${metric}`)
                    const sev = point?.severity ?? 0
                    return (
                      <td key={metric} className="px-2 py-1.5 text-center">
                        <div className={cn('rounded h-8 flex items-center justify-center font-mono', heatmapColor(sev))}>
                          <span className="text-[10px] text-gray-200">{sev > 0 ? sev.toFixed(1) : '—'}</span>
                        </div>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center gap-4 mt-4 text-[10px] text-gray-500">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-emerald-500/40" /> Healthy</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-yellow-500/40" /> Low</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-amber-500/60" /> Warning</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-500/70" /> Critical</span>
        </div>
      </div>
    </div>
  )
}
