import { useMemo } from 'react'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { useAppStore } from '@/store/appStore'

const COLORS = ['#06b6d4', '#f97316', '#a855f7', '#22c55e', '#ef4444', '#eab308', '#3b82f6', '#ec4899']

export default function StatsDashboard() {
  const sampleStats = useAppStore((s) => s.sampleStats)
  const columnStats = useAppStore((s) => s.columnStats)
  const fileMeta = useAppStore((s) => s.fileMeta)

  const pieData = useMemo(() => {
    if (!sampleStats) return []
    const sampleSize = sampleStats.sampleSize
    const remaining = sampleStats.totalSize - sampleSize
    return [
      { name: 'Sample', value: sampleSize, fill: '#06b6d4' },
      { name: 'Remaining', value: remaining, fill: '#334155' },
    ]
  }, [sampleStats])

  const barData = useMemo(() => {
    if (!sampleStats?.distribution) return []
    return Object.entries(sampleStats.distribution).map(([name, value], idx) => ({
      name: name.length > 12 ? name.slice(0, 12) + '…' : name,
      count: value,
      fill: COLORS[idx % COLORS.length],
    }))
  }, [sampleStats])

  if (!sampleStats || !fileMeta) return null

  const ratioPercent = ((sampleStats.sampleSize / sampleStats.totalSize) * 100).toFixed(1)

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/50 p-5 backdrop-blur-sm">
      <div className="mb-4 text-sm font-medium text-slate-200">Sampling Statistics</div>

      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Original" value={sampleStats.totalSize.toLocaleString()} />
        <StatCard label="Sample" value={sampleStats.sampleSize.toLocaleString()} accent />
        <StatCard label="Ratio" value={`${ratioPercent}%`} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4">
        <div>
          <p className="mb-2 text-[11px] font-medium text-slate-400">Sample Proportion</p>
          <div className="flex items-center justify-center">
            <ResponsiveContainer width={140} height={140}>
              <PieChart>
                <Pie
                  data={pieData}
                  innerRadius={40}
                  outerRadius={60}
                  dataKey="value"
                  stroke="none"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={index} fill={entry.fill} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-1 flex items-center justify-center gap-4">
            <div className="flex items-center gap-1.5">
              <div className="h-2 w-2 rounded-full bg-cyan-500" />
              <span className="text-[10px] text-slate-400">Sample</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-2 w-2 rounded-full bg-slate-600" />
              <span className="text-[10px] text-slate-400">Remaining</span>
            </div>
          </div>
        </div>

        {barData.length > 0 && (
          <div>
            <p className="mb-2 text-[11px] font-medium text-slate-400">Stratum Distribution</p>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={barData} barSize={16}>
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 9, fill: '#94a3b8' }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 9, fill: '#94a3b8' }}
                  axisLine={false}
                  tickLine={false}
                  width={35}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    fontSize: '11px',
                    color: '#e2e8f0',
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {barData.map((entry, index) => (
                    <Cell key={index} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="rounded-lg bg-slate-900/50 p-3 text-center">
      <p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p>
      <p className={`mt-1 font-mono text-lg font-bold ${accent ? 'text-cyan-400' : 'text-slate-100'}`}>
        {value}
      </p>
    </div>
  )
}
