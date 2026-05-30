import { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area } from 'recharts'
import { useParkingStore } from '@/store'
import { ZONE_COLORS, type ZoneId } from '@/types'

export default function PredictionChart() {
  const { predictions, selectedZone } = useParkingStore()

  const chartData = useMemo(() => {
    const displayZones = selectedZone ? [selectedZone] : ['A', 'B', 'C', 'D', 'E']

    const allPreds = displayZones.map((zid) => predictions[zid]?.predictions ?? [])
    const maxLen = Math.max(...allPreds.map((p) => p.length), 0)

    return Array.from({ length: maxLen }, (_, i) => {
      const point: Record<string, string | number> = {}
      const firstPred = allPreds[0]?.[i]
      if (firstPred) {
        const date = new Date(firstPred.timestamp)
        point.time = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
      }
      displayZones.forEach((zid, idx) => {
        const pred = allPreds[idx]?.[i]
        if (pred) {
          point[zid] = Math.max(0, Math.round(pred.available_spots))
          point[`${zid}_conf`] = pred.confidence
        }
      })
      return point
    })
  }, [predictions, selectedZone])

  const displayZones = selectedZone ? [selectedZone] : ['A', 'B', 'C', 'D', 'E']

  return (
    <div className="glass-card glow-cyan p-4 h-full">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">空位预测趋势</h3>
        <span className="text-[10px] text-slate-500">未来30分钟</span>
      </div>
      <div className="h-[calc(100%-28px)]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 10, fill: '#64748B' }}
              axisLine={{ stroke: '#1E293B' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: '#64748B' }}
              axisLine={{ stroke: '#1E293B' }}
              tickLine={false}
              width={30}
            />
            <Tooltip
              contentStyle={{
                background: '#0F172A',
                border: '1px solid #334155',
                borderRadius: 8,
                fontSize: 11,
                color: '#E2E8F0',
              }}
              labelStyle={{ color: '#94A3B8' }}
            />
            {displayZones.map((zid) => (
              <Line
                key={zid}
                type="monotone"
                dataKey={zid}
                stroke={ZONE_COLORS[zid as ZoneId]}
                strokeWidth={2}
                dot={{ r: 2, fill: ZONE_COLORS[zid as ZoneId] }}
                activeDot={{ r: 4, fill: ZONE_COLORS[zid as ZoneId], stroke: '#0F172A', strokeWidth: 2 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
