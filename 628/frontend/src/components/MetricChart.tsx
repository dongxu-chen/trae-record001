import { useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceDot, Legend,
} from 'recharts'
import type { TimeSeries, Anomaly } from '../types'

interface Props {
  series: TimeSeries[]
  anomalies: Anomaly[]
  selectedMetrics: string[]
  allMetrics: string[]
  onMetricToggle: (name: string) => void
}

const COLORS = ['#f97316', '#3b82f6', '#10b981', '#a78bfa', '#ef4444', '#f59e0b', '#06b6d4', '#ec4899']

const containerStyle: React.CSSProperties = {
  width: '100%',
}

const chipsStyle: React.CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '8px',
  marginBottom: '16px',
}

const chipStyle = (active: boolean, color: string): React.CSSProperties => ({
  padding: '4px 12px',
  borderRadius: '20px',
  fontSize: '12px',
  fontWeight: 600,
  cursor: 'pointer',
  border: `1px solid ${active ? color : '#30363d'}`,
  background: active ? `${color}20` : '#21262d',
  color: active ? color : '#8b949e',
  transition: 'all 0.15s',
})

export default function MetricChart({ series, anomalies, selectedMetrics, allMetrics, onMetricToggle }: Props) {
  const chartData = useMemo(() => {
    if (series.length === 0) return []

    const timeMap = new Map<number, Record<string, number>>()

    for (const s of series) {
      for (const p of s.points) {
        const ts = new Date(p.timestamp).getTime()
        if (!timeMap.has(ts)) {
          timeMap.set(ts, { timestamp: ts })
        }
        const entry = timeMap.get(ts)!
        entry[s.name] = p.value
      }
    }

    const sorted = Array.from(timeMap.entries()).sort((a, b) => a[0] - b[0])
    return sorted.map(([, entry]) => entry)
  }, [series])

  const anomalyDots = useMemo(() => {
    const dots: Record<string, Array<{ timestamp: number; value: number; direction: string }>> = {}
    for (const a of anomalies) {
      if (!dots[a.metric]) dots[a.metric] = []
      dots[a.metric].push({
        timestamp: new Date(a.timestamp).getTime(),
        value: a.value,
        direction: a.direction,
      })
    }
    return dots
  }, [anomalies])

  if (series.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: '#8b949e' }}>
        暂无指标数据，点击"运行检测"获取Demo数据
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      <div style={chipsStyle}>
        {allMetrics.map((name, i) => (
          <span
            key={name}
            style={chipStyle(selectedMetrics.includes(name), COLORS[i % COLORS.length])}
            onClick={() => onMetricToggle(name)}
          >
            {name.replace(/_/g, ' ')}
          </span>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
          <XAxis
            dataKey="timestamp"
            type="number"
            domain={['dataMin', 'dataMax']}
            tickFormatter={(v: number) => {
              const d = new Date(v)
              return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
            }}
            stroke="#8b949e"
            fontSize={11}
          />
          <YAxis stroke="#8b949e" fontSize={11} />
          <Tooltip
            contentStyle={{
              background: '#161b22',
              border: '1px solid #30363d',
              borderRadius: '8px',
              color: '#e1e4e8',
              fontSize: '12px',
            }}
            labelFormatter={(v: number) => new Date(v).toLocaleTimeString()}
          />
          <Legend />
          {series.map((s, i) => (
            <Line
              key={s.name}
              type="monotone"
              dataKey={s.name}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
          {series.map((s, i) => {
            const dots = anomalyDots[s.name] || []
            return dots.map((d, j) => (
              <ReferenceDot
                key={`${s.name}-${j}`}
                x={d.timestamp}
                y={d.value}
                r={6}
                fill={d.direction === 'up' ? '#ef4444' : '#3b82f6'}
                stroke={d.direction === 'up' ? '#ef444480' : '#3b82f680'}
                strokeWidth={3}
              />
            ))
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
