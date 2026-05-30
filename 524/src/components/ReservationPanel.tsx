import { useState, useEffect } from 'react'
import { createReservation, fetchReservations, cancelReservation, fetchPricing } from '@/api'
import { ZONE_NAMES, ZONE_COLORS, type ZoneId, type ReservationInfo, type ZonePricing } from '@/types'
import { CalendarPlus, Car, X, Clock, DollarSign, CheckCircle2 } from 'lucide-react'

export default function ReservationPanel() {
  const [reservations, setReservations] = useState<ReservationInfo[]>([])
  const [pricing, setPricing] = useState<ZonePricing[]>([])
  const [showForm, setShowForm] = useState(false)
  const [successMsg, setSuccessMsg] = useState('')
  const [formData, setFormData] = useState({
    zone_id: 'E',
    vehicle_plate: '',
    arrival_time: '',
    duration_hours: 2.0,
  })

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 10000)
    return () => clearInterval(interval)
  }, [])

  async function loadData() {
    try {
      const [resvs, prices] = await Promise.all([
        fetchReservations(undefined, 'active'),
        fetchPricing(),
      ])
      setReservations(resvs)
      setPricing(prices)
    } catch (e) {
      console.error(e)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      const result = await createReservation(formData)
      setSuccessMsg(result.message)
      setShowForm(false)
      setFormData({ zone_id: 'E', vehicle_plate: '', arrival_time: '', duration_hours: 2.0 })
      loadData()
      setTimeout(() => setSuccessMsg(''), 4000)
    } catch (err) {
      console.error(err)
    }
  }

  async function handleCancel(id: number) {
    try {
      await cancelReservation(id)
      loadData()
    } catch (err) {
      console.error(err)
    }
  }

  const zonePrice = (zoneId: string) => {
    const p = pricing.find((x) => x.zone_id === zoneId)
    return p ? p.current_price : 8
  }

  const DEMAND_COLORS: Record<string, string> = {
    very_high: '#FF6B35',
    high: '#F59E0B',
    elevated: '#FBBF24',
    normal: '#06D6A0',
    low: '#3B82F6',
  }

  const DEMAND_LABELS: Record<string, string> = {
    very_high: '极高',
    high: '高',
    elevated: '偏高',
    normal: '正常',
    low: '低',
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <CalendarPlus className="w-4 h-4 text-brand-cyan" />
          预约停车
        </h3>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs bg-brand-cyan/10 text-brand-cyan border border-brand-cyan/30 hover:bg-brand-cyan/20 transition-all"
        >
          <CalendarPlus className="w-3 h-3" />
          预约车位
        </button>
      </div>

      {successMsg && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs bg-[#06D6A0]/10 text-[#06D6A0] border border-[#06D6A0]/30">
          <CheckCircle2 className="w-4 h-4" />
          {successMsg}
        </div>
      )}

      {pricing.length > 0 && (
        <div className="grid grid-cols-5 gap-1.5">
          {pricing.map((p) => {
            const color = ZONE_COLORS[p.zone_id as ZoneId] || '#64748B'
            const demandColor = DEMAND_COLORS[p.demand_level] || '#06D6A0'
            return (
              <div key={p.zone_id} className="glass-card p-2 text-center">
                <div className="text-[10px] font-medium" style={{ color }}>{p.zone_id}</div>
                <div className="data-value text-sm text-white">¥{p.current_price}</div>
                <div className="text-[9px]" style={{ color: demandColor }}>
                  {DEMAND_LABELS[p.demand_level] || '正常'}
                  {p.surge_factor > 1.0 && ` x${p.surge_factor}`}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {showForm && (
        <div className="glass-card p-4 animate-slide-up">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">停车区域</label>
                <select
                  value={formData.zone_id}
                  onChange={(e) => setFormData({ ...formData, zone_id: e.target.value })}
                  className="w-full px-2 py-1.5 rounded-lg text-xs bg-brand-dark border border-brand-border text-white focus:outline-none focus:border-brand-cyan"
                >
                  {Object.entries(ZONE_NAMES).map(([id, name]) => (
                    <option key={id} value={id}>{id} - {name} (¥{zonePrice(id)}/h)</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">车牌号</label>
                <input
                  type="text"
                  value={formData.vehicle_plate}
                  onChange={(e) => setFormData({ ...formData, vehicle_plate: e.target.value.toUpperCase() })}
                  placeholder="京A12345"
                  className="w-full px-2 py-1.5 rounded-lg text-xs bg-brand-dark border border-brand-border text-white focus:outline-none focus:border-brand-cyan"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">预计到达</label>
                <input
                  type="datetime-local"
                  value={formData.arrival_time}
                  onChange={(e) => setFormData({ ...formData, arrival_time: e.target.value })}
                  className="w-full px-2 py-1.5 rounded-lg text-xs bg-brand-dark border border-brand-border text-white focus:outline-none focus:border-brand-cyan"
                  required
                />
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">停放时长(小时)</label>
                <select
                  value={formData.duration_hours}
                  onChange={(e) => setFormData({ ...formData, duration_hours: parseFloat(e.target.value) })}
                  className="w-full px-2 py-1.5 rounded-lg text-xs bg-brand-dark border border-brand-border text-white focus:outline-none focus:border-brand-cyan"
                >
                  {[1, 1.5, 2, 3, 4, 6, 8, 12].map((h) => (
                    <option key={h} value={h}>{h}小时 - ¥{(zonePrice(formData.zone_id) * h).toFixed(0)}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="glass-card p-2 flex items-center justify-between">
              <span className="text-[10px] text-slate-400">预估费用</span>
              <span className="data-value text-sm text-brand-cyan">
                ¥{(zonePrice(formData.zone_id) * formData.duration_hours).toFixed(0)}
              </span>
            </div>

            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)} className="px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white transition-all">取消</button>
              <button type="submit" className="px-3 py-1.5 rounded-lg text-xs bg-brand-cyan text-brand-dark font-medium hover:bg-brand-cyan/90 transition-all">确认预约</button>
            </div>
          </form>
        </div>
      )}

      <div className="space-y-2 max-h-60 overflow-auto">
        {reservations.length === 0 ? (
          <div className="text-center py-6 text-slate-500 text-xs">暂无预约</div>
        ) : (
          reservations.map((r) => {
            const color = ZONE_COLORS[r.zone_id as ZoneId] || '#64748B'
            return (
              <div key={r.id} className="glass-card p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="zone-tag" style={{ background: `${color}20`, color, border: `1px solid ${color}40` }}>
                      {r.zone_id}
                    </span>
                    <div>
                      <div className="flex items-center gap-1.5 text-xs text-white">
                        <Car className="w-3 h-3 text-slate-400" />
                        {r.vehicle_plate}
                      </div>
                      <div className="text-[10px] text-slate-500">
                        车位 #{r.reserved_spot} · {r.duration_hours}h
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-brand-cyan">¥{r.price}</span>
                    <button
                      onClick={() => handleCancel(r.id)}
                      className="p-1 rounded text-slate-500 hover:text-brand-orange hover:bg-brand-orange/10 transition-all"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
