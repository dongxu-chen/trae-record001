import { useState, useEffect } from 'react'
import { fetchPricing, fetchZones } from '@/api'
import { ZONE_NAMES, ZONE_COLORS, type ZoneId, type ZonePricing, type ZoneReading } from '@/types'
import { DollarSign, TrendingUp, TrendingDown, Minus, BarChart3 } from 'lucide-react'

export default function PricingPanel() {
  const [pricing, setPricing] = useState<ZonePricing[]>([])
  const [zones, setZones] = useState<ZoneReading[]>([])

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 10000)
    return () => clearInterval(interval)
  }, [])

  async function loadData() {
    try {
      const [prices, zoneResp] = await Promise.all([fetchPricing(), fetchZones()])
      setPricing(prices)
      setZones(zoneResp.data || [])
    } catch (e) {
      console.error(e)
    }
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

  function getTrend(p: ZonePricing) {
    if (p.surge_factor > 1.5) return 'up'
    if (p.surge_factor < 1.0) return 'down'
    return 'stable'
  }

  const zoneMap = zones.reduce<Record<string, ZoneReading>>((acc, z) => {
    acc[z.zone_id] = z
    return acc
  }, {})

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <DollarSign className="w-4 h-4 text-brand-orange" />
          动态定价
        </h3>
        <span className="text-[10px] text-slate-500">实时调价 · 每10秒更新</span>
      </div>

      <div className="glass-card p-3">
        <div className="grid grid-cols-2 gap-2 mb-3">
          <div className="bg-brand-dark/50 rounded-lg p-2 text-center">
            <div className="text-[10px] text-slate-500">均价</div>
            <div className="data-value text-lg text-brand-cyan">
              ¥{pricing.length > 0 ? (pricing.reduce((s, p) => s + p.current_price, 0) / pricing.length).toFixed(1) : '--'}
            </div>
          </div>
          <div className="bg-brand-dark/50 rounded-lg p-2 text-center">
            <div className="text-[10px] text-slate-500">最高溢价</div>
            <div className="data-value text-lg text-brand-orange">
              x{pricing.length > 0 ? Math.max(...pricing.map((p) => p.surge_factor)).toFixed(1) : '--'}
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {pricing.map((p) => {
          const color = ZONE_COLORS[p.zone_id as ZoneId] || '#64748B'
          const demandColor = DEMAND_COLORS[p.demand_level] || '#06D6A0'
          const trend = getTrend(p)
          const zone = zoneMap[p.zone_id]
          const occupancy = zone ? Math.round(zone.occupancy_rate * 100) : 0

          return (
            <div key={p.zone_id} className="glass-card p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="zone-tag" style={{ background: `${color}20`, color, border: `1px solid ${color}40` }}>
                    {p.zone_id}
                  </span>
                  <span className="text-xs text-slate-400">{ZONE_NAMES[p.zone_id as ZoneId]}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className="px-1.5 py-0.5 rounded text-[9px] font-medium"
                    style={{ background: `${demandColor}15`, color: demandColor }}
                  >
                    {DEMAND_LABELS[p.demand_level] || '正常'}
                  </span>
                  {trend === 'up' && <TrendingUp className="w-3 h-3 text-brand-orange" />}
                  {trend === 'down' && <TrendingDown className="w-3 h-3 text-brand-cyan" />}
                  {trend === 'stable' && <Minus className="w-3 h-3 text-slate-500" />}
                </div>
              </div>

              <div className="grid grid-cols-4 gap-2 text-center">
                <div>
                  <div className="data-value text-sm text-white">¥{p.current_price}</div>
                  <div className="text-[9px] text-slate-500">现价/h</div>
                </div>
                <div>
                  <div className="text-xs text-slate-400">¥{p.base_hourly}</div>
                  <div className="text-[9px] text-slate-500">基准/h</div>
                </div>
                <div>
                  <div className="text-xs" style={{ color: demandColor }}>x{p.surge_factor}</div>
                  <div className="text-[9px] text-slate-500">溢价</div>
                </div>
                <div>
                  <div className="text-xs text-slate-400">{occupancy}%</div>
                  <div className="text-[9px] text-slate-500">占用率</div>
                </div>
              </div>

              <div className="mt-2 h-1 bg-brand-dark rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${occupancy}%`,
                    background: `linear-gradient(90deg, ${color}, ${demandColor})`,
                  }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
