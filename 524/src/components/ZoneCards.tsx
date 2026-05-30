import { ZONE_NAMES, ZONE_COLORS, EVENT_TYPES, type ZoneId } from '@/types'
import { useParkingStore } from '@/store'
import { Car, Users, AlertTriangle } from 'lucide-react'

export default function ZoneCards() {
  const { zones, selectedZone, setSelectedZone, eventImpacts } = useParkingStore()

  const getStatusInfo = (available: number, total: number, hasEvent: boolean) => {
    if (hasEvent) return { label: '活动', color: 'text-[#EC4899]', bg: 'bg-[#EC4899]/10', dot: 'full' }
    const rate = available / total
    if (rate > 0.4) return { label: '充足', color: 'text-[#06D6A0]', bg: 'bg-[#06D6A0]/10', dot: 'available' }
    if (rate > 0.15) return { label: '紧张', color: 'text-[#FBBF24]', bg: 'bg-[#FBBF24]/10', dot: 'busy' }
    return { label: '已满', color: 'text-[#FF6B35]', bg: 'bg-[#FF6B35]/10', dot: 'full' }
  }

  return (
    <div className="space-y-2">
      {zones.map((zone) => {
        const hasEvent = eventImpacts[zone.zone_id] && eventImpacts[zone.zone_id] > 1.3
        const status = getStatusInfo(zone.available_spots, zone.total_spots, hasEvent)
        const isSelected = selectedZone === zone.zone_id
        const pct = Math.round(zone.occupancy_rate * 100)
        const color = hasEvent ? '#EC4899' : ZONE_COLORS[zone.zone_id as ZoneId]
        const eventFactor = eventImpacts[zone.zone_id]

        return (
          <div
            key={zone.zone_id}
            onClick={() => setSelectedZone(isSelected ? null : zone.zone_id)}
            className={`glass-card p-3 cursor-pointer transition-all duration-300 ${
              isSelected ? 'glow-border-cyan' : hasEvent ? 'border-pink-500/40' : 'hover:border-slate-600'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div
                  className="zone-tag"
                  style={{ background: `${color}20`, color, border: `1px solid ${color}40` }}
                >
                  {zone.zone_id}
                </div>
                <div>
                  <div className="text-xs font-medium text-white flex items-center gap-1.5">
                    {ZONE_NAMES[zone.zone_id as ZoneId]}
                    {hasEvent && (
                      <span
                        className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-medium"
                        style={{ background: `${color}20`, color }}
                      >
                        <AlertTriangle className="w-2.5 h-2.5" />
                        x{eventFactor?.toFixed(1)}
                      </span>
                    )}
                  </div>
                  <div className={`text-[10px] ${status.color} font-medium`}>{status.label}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="data-value text-xl" style={{ color }}>
                  {zone.available_spots}
                </div>
                <div className="text-[10px] text-slate-500">/ {zone.total_spots} 位</div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-brand-dark rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${pct}%`,
                    background: `linear-gradient(90deg, ${color}, ${color}80)`,
                  }}
                />
              </div>
              <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
                <Users className="w-3 h-3" />
                {pct}%
              </div>
            </div>

            {zone.event_impact && zone.event_impact.active_events.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {zone.event_impact.active_events.map((evt, i) => {
                  const typeInfo = EVENT_TYPES[evt.type] || { label: '活动', color: '#EC4899', icon: '📅' }
                  return (
                    <span
                      key={i}
                      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px]"
                      style={{ background: `${typeInfo.color}15`, color: typeInfo.color }}
                    >
                      {typeInfo.icon} {evt.title}
                    </span>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
