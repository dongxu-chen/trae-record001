import { useEffect, useState } from 'react'
import { fetchGuidance, fetchSimulation, fetchZones, fetchActiveEvents } from '@/api'
import { ZONE_NAMES, ZONE_COLORS, EVENT_TYPES, type ZoneId, type GuidanceResult, type SimulationResult, type ZoneReading, type EventInfo } from '@/types'
import {
  Navigation, MapPin, Clock, Footprints, Car,
  ChevronRight, Play, BarChart3, CheckCircle2, AlertTriangle,
} from 'lucide-react'

export default function Guide() {
  const [entrance, setEntrance] = useState<'A' | 'B'>('A')
  const [guidance, setGuidance] = useState<GuidanceResult | null>(null)
  const [zones, setZones] = useState<ZoneReading[]>([])
  const [simulations, setSimulations] = useState<Record<string, SimulationResult>>({})
  const [activeEvents, setActiveEvents] = useState<EventInfo[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [entrance])

  async function loadData() {
    setLoading(true)
    try {
      const [g, z, evts] = await Promise.all([
        fetchGuidance(entrance),
        fetchZones(),
        fetchActiveEvents(),
      ])
      setGuidance(g)
      if (Array.isArray(z)) {
        setZones(z)
      } else if (z.data) {
        setZones(z.data)
      }
      setActiveEvents(evts)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  async function runSimulation(zoneId: string) {
    try {
      const result = await fetchSimulation(entrance, zoneId)
      setSimulations((prev) => ({ ...prev, [zoneId]: result }))
    } catch (err) {
      console.error(err)
    }
  }

  async function runAllSimulations() {
    const results: Record<string, SimulationResult> = {}
    await Promise.all(
      ['A', 'B', 'C', 'D', 'E'].map(async (zid) => {
        results[zid] = await fetchSimulation(entrance, zid)
      })
    )
    setSimulations(results)
  }

  const zoneMap = zones.reduce<Record<string, ZoneReading>>((acc, z) => {
    acc[z.zone_id] = z
    return acc
  }, {})

  return (
    <div className="p-4 h-full overflow-auto animate-fade-in">
      {activeEvents.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {activeEvents.map((event) => {
        const typeInfo = EVENT_TYPES[event.event_type] || { label: '活动', color: '#EC4899', icon: '📅' }
            return (
              <div
                key={event.id}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs"
                style={{
                  background: `${typeInfo.color}15`,
                  border: `1px solid ${typeInfo.color}40`,
                  color: typeInfo.color,
                }}
              >
                <AlertTriangle className="w-4 h-4" />
                <span>{typeInfo.icon} {event.title}</span>
                <span className="opacity-70">x{event.impact_factor}</span>
                <span className="opacity-70">影响 {event.impact_zone_ids}</span>
              </div>
            )
          })}
        </div>
      )}

      <header className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-white font-body">引导推荐</h2>
          <p className="text-xs text-slate-500">基于强化学习的最优停车区域推荐</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">当前入口</span>
          {(['A', 'B'] as const).map((e) => (
            <button
              key={e}
              onClick={() => setEntrance(e)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                entrance === e
                  ? 'bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/40'
                  : 'glass-card text-slate-400 hover:text-white'
              }`}
            >
              入口{e}
            </button>
          ))}
        </div>
      </header>

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-5">
          {guidance && (
            <div className="glass-card glow-cyan p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-brand-cyan/20 flex items-center justify-center">
                  <Navigation className="w-4 h-4 text-brand-cyan" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">最优推荐</h3>
                  <p className="text-[10px] text-slate-500">Q-Learning策略选择</p>
                </div>
              </div>

              <div
                className="rounded-xl p-5 mb-4"
                style={{
                  background: `linear-gradient(135deg, ${ZONE_COLORS[guidance.recommended_zone as ZoneId]}15, ${ZONE_COLORS[guidance.recommended_zone as ZoneId]}05)`,
                  border: `1px solid ${ZONE_COLORS[guidance.recommended_zone as ZoneId]}40`,
                }}
              >
                <div className="flex items-center gap-3 mb-4">
                  <span
                    className="w-12 h-12 rounded-xl flex items-center justify-center text-xl font-bold font-orbitron"
                    style={{
                      background: `${ZONE_COLORS[guidance.recommended_zone as ZoneId]}20`,
                      color: ZONE_COLORS[guidance.recommended_zone as ZoneId],
                      border: `1px solid ${ZONE_COLORS[guidance.recommended_zone as ZoneId]}60`,
                    }}
                  >
                    {guidance.recommended_zone}
                  </span>
                  <div>
                    <div className="text-base font-bold text-white">
                      {ZONE_NAMES[guidance.recommended_zone as ZoneId]}
                    </div>
                    <div className="text-xs text-slate-400">{guidance.reason}</div>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-3">
                  <div className="bg-brand-dark/50 rounded-lg p-2 text-center">
                    <Clock className="w-3 h-3 mx-auto text-brand-cyan mb-1" />
                    <div className="data-value text-sm text-white">
                      {guidance.estimated_wait_minutes > 0 ? `${guidance.estimated_wait_minutes}min` : '无需等待'}
                    </div>
                    <div className="text-[10px] text-slate-500">预计等待</div>
                  </div>
                  <div className="bg-brand-dark/50 rounded-lg p-2 text-center">
                    <Footprints className="w-3 h-3 mx-auto text-brand-blue mb-1" />
                    <div className="data-value text-sm text-white">{Math.round(guidance.walking_distance)}m</div>
                    <div className="text-[10px] text-slate-500">步行距离</div>
                  </div>
                  <div className="bg-brand-dark/50 rounded-lg p-2 text-center">
                    <BarChart3 className="w-3 h-3 mx-auto text-brand-purple mb-1" />
                    <div className="data-value text-sm text-brand-cyan">
                      {Math.round(guidance.confidence * 100)}%
                    </div>
                    <div className="text-[10px] text-slate-500">置信度</div>
                  </div>
                  <div className="bg-brand-dark/50 rounded-lg p-2 text-center">
                    <CheckCircle2 className="w-3 h-3 mx-auto text-brand-green mb-1" />
                    <div className="data-value text-sm text-brand-green">
                      {Math.round(guidance.utility_score * 100)}%
                    </div>
                    <div className="text-[10px] text-slate-500">效用评分</div>
                  </div>
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-400 mb-2">备选方案</div>
                <div className="space-y-2">
                  {guidance.alternatives.map((alt) => {
                    const color = ZONE_COLORS[alt.zone_id as ZoneId]
                    return (
                      <div
                        key={alt.zone_id}
                        className="flex items-center gap-3 p-2 rounded-lg bg-brand-dark/30 hover:bg-brand-dark/60 transition-all cursor-pointer"
                        onClick={() => runSimulation(alt.zone_id)}
                      >
                        <span
                          className="zone-tag"
                          style={{ background: `${color}20`, color, border: `1px solid ${color}40` }}
                        >
                          {alt.zone_id}
                        </span>
                        <div className="flex-1">
                          <div className="text-xs font-medium text-white">{ZONE_NAMES[alt.zone_id as ZoneId]}</div>
                          <div className="text-[10px] text-slate-500">{alt.reason}</div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="text-right">
                            <div className="text-[10px] text-slate-500">效用</div>
                            <div className="text-[10px] font-medium text-brand-cyan">{Math.round(alt.utility_score * 100)}%</div>
                          </div>
                          <div className="w-12 h-1.5 bg-brand-dark rounded-full overflow-hidden">
                            <div className="h-full rounded-full" style={{ width: `${alt.score * 100}%`, background: color }} />
                          </div>
                          <ChevronRight className="w-3 h-3 text-slate-500" />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="col-span-7">
          <div className="glass-card p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <MapPin className="w-4 h-4 text-brand-orange" />
                区域模拟
              </h3>
              <button
                onClick={runAllSimulations}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-brand-cyan/10 text-brand-cyan border border-brand-cyan/30 hover:bg-brand-cyan/20 transition-all"
              >
                <Play className="w-3 h-3" />
                全部模拟
              </button>
            </div>

            <div className="space-y-3">
              {['A', 'B', 'C', 'D', 'E'].map((zid) => {
                const zone = zoneMap[zid]
                const sim = simulations[zid]
                const color = ZONE_COLORS[zid as ZoneId]
                const hasEvent = zone?.event_impact?.active_events?.length > 0

                return (
                  <div
                    key={zid}
                    className="flex items-center gap-4 p-3 rounded-xl bg-brand-dark/30 hover:bg-brand-dark/50 transition-all"
                    style={hasEvent ? { borderColor: 'rgba(236, 72, 153, 0.3)' } : {}}
                  >
                    <div className="flex items-center gap-3 w-36">
                      <span
                        className="zone-tag"
                        style={{ background: `${color}20`, color, border: `1px solid ${color}40` }}
                      >
                        {zid}
                      </span>
                      <div>
                        <div className="text-xs font-medium text-white flex items-center gap-1">
                          {ZONE_NAMES[zid as ZoneId]}
                          {hasEvent && (
                            <span className="text-[9px] text-pink-500">
                              <AlertTriangle className="w-2.5 h-2.5" />
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] text-slate-500">
                          {zone ? `${zone.available_spots}空位 / ${zone.total_spots}总位` : '--'}
                        </div>
                      </div>
                    </div>

                    {sim ? (
                      <div className="flex-1 grid grid-cols-5 gap-2">
                        <div className="text-center">
                          <Car className="w-3 h-3 mx-auto text-brand-blue mb-0.5" />
                          <div className="data-value text-xs text-white">{sim.driving_time_minutes}min</div>
                          <div className="text-[10px] text-slate-500">驾车</div>
                        </div>
                        <div className="text-center">
                          <Footprints className="w-3 h-3 mx-auto text-brand-purple mb-0.5" />
                          <div className="data-value text-xs text-white">{sim.walking_time_minutes}min</div>
                          <div className="text-[10px] text-slate-500">步行</div>
                        </div>
                        <div className="text-center">
                          <CheckCircle2 className="w-3 h-3 mx-auto text-brand-cyan mb-0.5" />
                          <div className="data-value text-xs text-brand-cyan">
                            {Math.round(sim.arrival_probability * 100)}%
                          </div>
                          <div className="text-[10px] text-slate-500">到达有位</div>
                        </div>
                        <div className="text-center">
                          <BarChart3 className="w-3 h-3 mx-auto text-brand-green mb-0.5" />
                          <div className="data-value text-xs text-brand-green">
                            {Math.round(sim.utility_score * 100)}%
                          </div>
                          <div className="text-[10px] text-slate-500">综合效用</div>
                        </div>
                        <div className="flex items-center justify-center">
                          <div className="w-full h-1.5 bg-brand-dark rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${sim.arrival_probability * 100}%`,
                                background: sim.arrival_probability > 0.6 ? '#06D6A0' : sim.arrival_probability > 0.3 ? '#FBBF24' : '#FF6B35',
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="flex-1 flex items-center justify-center">
                        <button
                          onClick={() => runSimulation(zid)}
                          className="text-[10px] text-slate-500 hover:text-brand-cyan transition-all flex items-center gap-1"
                        >
                          <Play className="w-2.5 h-2.5" />
                          点击模拟
                        </button>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
