import { useState } from 'react'
import { createNavigationRoute, pushNavigationToVehicle } from '@/api'
import { ZONE_NAMES, ZONE_COLORS, type ZoneId, type NavigationRoute, type NavigationPushResult } from '@/types'
import { Navigation, Send, MapPin, Car, Clock, Footprints, ChevronRight, CheckCircle2, XCircle } from 'lucide-react'

const STEP_ICONS: Record<string, string> = {
  right: '→',
  left: '←',
  straight: '↑',
  arrive: '🏁',
  walk: '🚶',
  reservation: '✅',
}

export default function NavigationPanel() {
  const [zoneId, setZoneId] = useState('E')
  const [entrance, setEntrance] = useState<'A' | 'B'>('A')
  const [vehiclePlate, setVehiclePlate] = useState('')
  const [route, setRoute] = useState<NavigationRoute | null>(null)
  const [pushResult, setPushResult] = useState<NavigationPushResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleGenerateRoute() {
    setLoading(true)
    try {
      const result = await createNavigationRoute(zoneId, entrance, vehiclePlate || undefined)
      setRoute(result)
      setPushResult(null)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  async function handlePushToVehicle() {
    setLoading(true)
    try {
      const result = await pushNavigationToVehicle(zoneId, entrance, vehiclePlate || undefined)
      setPushResult(result)
      if (result.route_data) {
        setRoute(result.route_data)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const color = ZONE_COLORS[zoneId as ZoneId] || '#64748B'

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Navigation className="w-4 h-4 text-brand-purple" />
          导航集成
        </h3>
        <span className="text-[10px] text-slate-500">CarPlay / AndroidAuto</span>
      </div>

      <div className="glass-card p-3">
        <div className="grid grid-cols-3 gap-2 mb-3">
          <div>
            <label className="block text-[10px] text-slate-400 mb-1">目标区域</label>
            <select
              value={zoneId}
              onChange={(e) => setZoneId(e.target.value)}
              className="w-full px-2 py-1.5 rounded-lg text-xs bg-brand-dark border border-brand-border text-white focus:outline-none focus:border-brand-cyan"
            >
              {Object.entries(ZONE_NAMES).map(([id, name]) => (
                <option key={id} value={id}>{id} - {name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[10px] text-slate-400 mb-1">入口</label>
            <div className="flex gap-1">
              {(['A', 'B'] as const).map((e) => (
                <button
                  key={e}
                  onClick={() => setEntrance(e)}
                  className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    entrance === e ? 'bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/40' : 'bg-brand-dark text-slate-400 border border-brand-border'
                  }`}
                >
                  入口{e}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-[10px] text-slate-400 mb-1">车牌(选填)</label>
            <input
              type="text"
              value={vehiclePlate}
              onChange={(e) => setVehiclePlate(e.target.value.toUpperCase())}
              placeholder="京A12345"
              className="w-full px-2 py-1.5 rounded-lg text-xs bg-brand-dark border border-brand-border text-white focus:outline-none focus:border-brand-cyan"
            />
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleGenerateRoute}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs bg-brand-purple/10 text-brand-purple border border-brand-purple/30 hover:bg-brand-purple/20 transition-all disabled:opacity-50"
          >
            <MapPin className="w-3 h-3" />
            生成路线
          </button>
          <button
            onClick={handlePushToVehicle}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs bg-brand-cyan/10 text-brand-cyan border border-brand-cyan/30 hover:bg-brand-cyan/20 transition-all disabled:opacity-50"
          >
            <Send className="w-3 h-3" />
            推送车机
          </button>
        </div>
      </div>

      {pushResult && (
        <div
          className={`glass-card p-3 flex items-center gap-2 ${
            pushResult.success ? 'border-[#06D6A0]/40' : 'border-[#FF6B35]/40'
          }`}
        >
          {pushResult.success ? (
            <CheckCircle2 className="w-4 h-4 text-[#06D6A0] flex-shrink-0" />
          ) : (
            <XCircle className="w-4 h-4 text-[#FF6B35] flex-shrink-0" />
          )}
          <div>
            <div className={`text-xs font-medium ${pushResult.success ? 'text-[#06D6A0]' : 'text-[#FF6B35]'}`}>
              {pushResult.message}
            </div>
            <div className="text-[10px] text-slate-500">
              {pushResult.protocol} · {pushResult.push_time?.split('T')[1]?.split('.')[0]}
            </div>
          </div>
        </div>
      )}

      {route && (
        <div className="glass-card p-3">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="zone-tag" style={{ background: `${color}20`, color, border: `1px solid ${color}40` }}>
                {route.zone_id}
              </span>
              <span className="text-xs text-white">{ZONE_NAMES[route.zone_id as ZoneId]}</span>
              {route.has_reservation && (
                <span className="px-1.5 py-0.5 rounded text-[9px] bg-[#06D6A0]/10 text-[#06D6A0]">
                  已预约
                </span>
              )}
            </div>
            <span className="text-[10px] text-slate-500">预计 {route.estimated_arrival} 到达</span>
          </div>

          <div className="grid grid-cols-4 gap-2 mb-3">
            <div className="bg-brand-dark/50 rounded-lg p-1.5 text-center">
              <Car className="w-3 h-3 mx-auto text-brand-blue mb-0.5" />
              <div className="data-value text-[11px] text-white">{route.driving_time_minutes}min</div>
              <div className="text-[9px] text-slate-500">驾车</div>
            </div>
            <div className="bg-brand-dark/50 rounded-lg p-1.5 text-center">
              <Footprints className="w-3 h-3 mx-auto text-brand-purple mb-0.5" />
              <div className="data-value text-[11px] text-white">{route.walking_time_minutes}min</div>
              <div className="text-[9px] text-slate-500">步行</div>
            </div>
            <div className="bg-brand-dark/50 rounded-lg p-1.5 text-center">
              <MapPin className="w-3 h-3 mx-auto text-brand-orange mb-0.5" />
              <div className="data-value text-[11px] text-white">{route.driving_distance}m</div>
              <div className="text-[9px] text-slate-500">里程</div>
            </div>
            <div className="bg-brand-dark/50 rounded-lg p-1.5 text-center">
              <Clock className="w-3 h-3 mx-auto text-brand-cyan mb-0.5" />
              <div className="data-value text-[11px] text-brand-cyan">{route.estimated_arrival}</div>
              <div className="text-[9px] text-slate-500">到达</div>
            </div>
          </div>

          <div className="text-[10px] text-slate-400 mb-2">逐步导航</div>
          <div className="space-y-1.5">
            {route.turn_by_turn.map((step, i) => (
              <div key={i} className="flex items-center gap-2 p-1.5 rounded-lg bg-brand-dark/30">
                <span className="text-sm w-6 text-center flex-shrink-0">{STEP_ICONS[step.icon] || '·'}</span>
                <div className="flex-1">
                  <div className="text-[11px] text-white">{step.instruction}</div>
                  {step.distance > 0 && (
                    <div className="text-[9px] text-slate-500">{step.distance}m</div>
                  )}
                </div>
                {i < route.turn_by_turn.length - 1 && (
                  <ChevronRight className="w-3 h-3 text-slate-600 flex-shrink-0" />
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
