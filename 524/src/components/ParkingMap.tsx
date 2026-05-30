import { useParkingStore } from '@/store'
import { ZONE_NAMES, ZONE_COLORS, EVENT_TYPES, type ZoneId } from '@/types'

export default function ParkingMap() {
  const { zones, selectedZone, setSelectedZone, eventImpacts, activeEvents } = useParkingStore()

  const getZoneColor = (zoneId: string, available: number, total: number) => {
    const rate = available / total
    if (eventImpacts[zoneId] && eventImpacts[zoneId] > 1.3) return '#EC4899'
    if (rate > 0.4) return '#06D6A0'
    if (rate > 0.15) return '#FBBF24'
    return '#FF6B35'
  }

  const getZoneGlow = (zoneId: string, available: number, total: number) => {
    const rate = available / total
    if (eventImpacts[zoneId] && eventImpacts[zoneId] > 1.3) return 'rgba(236, 72, 153, 0.4)'
    if (rate > 0.4) return 'rgba(6, 214, 160, 0.3)'
    if (rate > 0.15) return 'rgba(251, 191, 36, 0.3)'
    return 'rgba(255, 107, 53, 0.3)'
  }

  const zoneData = zones.reduce<Record<string, typeof zones[0]>>((acc, z) => {
    acc[z.zone_id] = z
    return acc
  }, {})

  const zonePositions: Record<string, { x: number; y: number; w: number; h: number; rx: number; labelY: number }> = {
    A: { x: 40, y: 30, w: 180, h: 90, rx: 12, labelY: 65 },
    B: { x: 260, y: 30, w: 180, h: 90, rx: 12, labelY: 65 },
    C: { x: 40, y: 160, w: 180, h: 90, rx: 12, labelY: 195 },
    D: { x: 260, y: 160, w: 180, h: 90, rx: 12, labelY: 195 },
    E: { x: 150, y: 290, w: 180, h: 90, rx: 12, labelY: 325 },
  }

  return (
    <div className="glass-card glow-cyan p-4 h-full">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">停车场实时地图</h3>
        <div className="flex items-center gap-3 text-[10px]">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#06D6A0]" /> 充足</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#FBBF24]" /> 紧张</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#FF6B35]" /> 已满</span>
          {Object.keys(eventImpacts).length > 0 && (
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#EC4899] animate-pulse" /> 活动</span>
          )}
        </div>
      </div>

      {activeEvents.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {activeEvents.map((event) => {
            const typeInfo = EVENT_TYPES[event.event_type] || { label: '活动', icon: '📅', color: '#EC4899' }
            return (
              <div
                key={event.id}
                className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-[10px]"
                style={{
                  background: `${typeInfo.color}15`,
                  border: `1px solid ${typeInfo.color}40`,
                  color: typeInfo.color,
                }}
              >
                <span>{typeInfo.icon}</span>
                <span className="font-medium">{event.title}</span>
                <span className="opacity-70">x{event.impact_factor}</span>
              </div>
            )
          })}
        </div>
      )}

      <svg viewBox="0 0 480 400" className="w-full h-auto" style={{ maxHeight: 'calc(100% - 32px)' }}>
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <linearGradient id="roadGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#1E293B" />
            <stop offset="50%" stopColor="#334155" />
            <stop offset="100%" stopColor="#1E293B" />
          </linearGradient>
          <pattern id="eventStripes" patternUnits="userSpaceOnUse" width="8" height="8">
            <rect width="8" height="8" fill="transparent" />
            <line x1="0" y1="0" x2="8" y2="8" stroke="#EC4899" strokeWidth="1" opacity="0.3" />
          </pattern>
        </defs>

        <rect x="0" y="0" width="480" height="400" fill="#0A0F1A" rx="8" />

        <rect x="220" y="120" width="40" height="40" fill="url(#roadGrad)" rx="4" />
        <rect x="220" y="250" width="40" height="40" fill="url(#roadGrad)" rx="4" />

        <line x1="130" y1="130" x2="220" y2="130" stroke="#334155" strokeWidth="2" strokeDasharray="4,4" />
        <line x1="260" y1="130" x2="350" y2="130" stroke="#334155" strokeWidth="2" strokeDasharray="4,4" />
        <line x1="130" y1="260" x2="220" y2="260" stroke="#334155" strokeWidth="2" strokeDasharray="4,4" />
        <line x1="260" y1="260" x2="350" y2="260" stroke="#334155" strokeWidth="2" strokeDasharray="4,4" />
        <line x1="240" y1="160" x2="240" y2="250" stroke="#334155" strokeWidth="2" strokeDasharray="4,4" />

        {Object.entries(zonePositions).map(([zoneId, pos]) => {
          const data = zoneData[zoneId]
          const avail = data?.available_spots ?? 0
          const total = data?.total_spots ?? 1
          const color = getZoneGlow(zoneId, avail, total)
          const isSelected = selectedZone === zoneId
          const hasEvent = eventImpacts[zoneId] && eventImpacts[zoneId] > 1.3

          return (
            <g
              key={zoneId}
              onClick={() => setSelectedZone(isSelected ? null : zoneId)}
              className="cursor-pointer transition-all duration-300"
            >
              {hasEvent && (
                <rect
                  x={pos.x}
                  y={pos.y}
                  width={pos.w}
                  height={pos.h}
                  rx={pos.rx}
                  fill="url(#eventStripes)"
                  opacity="0.8"
                />
              )}
              <rect
                x={pos.x}
                y={pos.y}
                width={pos.w}
                height={pos.h}
                rx={pos.rx}
                fill={color}
                fillOpacity={hasEvent ? 0.25 : 0.15}
                stroke={getZoneColor(zoneId, avail, total)}
                strokeWidth={isSelected ? 2.5 : hasEvent ? 2 : 1.5}
                strokeOpacity={isSelected ? 1 : hasEvent ? 0.9 : 0.6}
                filter={isSelected ? 'url(#glow)' : hasEvent ? 'url(#glow)' : undefined}
              />
              <text
                x={pos.x + pos.w / 2}
                y={pos.y + 28}
                textAnchor="middle"
                fill={hasEvent ? '#EC4899' : ZONE_COLORS[zoneId as ZoneId]}
                fontSize="16"
                fontWeight="700"
                fontFamily="Orbitron, monospace"
              >
                {zoneId}
              </text>
              <text
                x={pos.x + pos.w / 2}
                y={pos.y + 50}
                textAnchor="middle"
                fill="#E2E8F0"
                fontSize="22"
                fontWeight="800"
                fontFamily="Orbitron, monospace"
              >
                {avail}
              </text>
              <text
                x={pos.x + pos.w / 2}
                y={pos.y + 68}
                textAnchor="middle"
                fill="#94A3B8"
                fontSize="10"
                fontFamily="Noto Sans SC, sans-serif"
              >
                空位 / {total}
              </text>
              {hasEvent && (
                <text
                  x={pos.x + pos.w / 2}
                  y={pos.y + 85}
                  textAnchor="middle"
                  fill="#EC4899"
                  fontSize="9"
                  fontFamily="Noto Sans SC, sans-serif"
                >
                  ⚠ 活动影响 x{eventImpacts[zoneId].toFixed(1)}
                </text>
              )}
              {avail > 0 && (
                <circle
                  cx={pos.x + pos.w - 12}
                  cy={pos.y + 12}
                  r="4"
                  fill={getZoneColor(zoneId, avail, total)}
                  filter="url(#glow)"
                >
                  <animate
                    attributeName="opacity"
                    values="1;0.3;1"
                    dur="2s"
                    repeatCount="indefinite"
                  />
                </circle>
              )}
            </g>
          )
        })}

        <g>
          <rect x="40" y="380" width="60" height="16" rx="4" fill="#06D6A0" fillOpacity="0.2" stroke="#06D6A0" strokeWidth="0.5" />
          <text x="70" y="392" textAnchor="middle" fill="#06D6A0" fontSize="9" fontFamily="Noto Sans SC">入口A</text>
        </g>
        <g>
          <rect x="380" y="380" width="60" height="16" rx="4" fill="#3B82F6" fillOpacity="0.2" stroke="#3B82F6" strokeWidth="0.5" />
          <text x="410" y="392" textAnchor="middle" fill="#3B82F6" fontSize="9" fontFamily="Noto Sans SC">入口B</text>
        </g>

        {selectedZone && zoneData[selectedZone] && (
          <g>
            <rect
              x={zonePositions[selectedZone].x - 2}
              y={zonePositions[selectedZone].y - 2}
              width={zonePositions[selectedZone].w + 4}
              height={zonePositions[selectedZone].h + 4}
              rx={zonePositions[selectedZone].rx + 2}
              fill="none"
              stroke={ZONE_COLORS[selectedZone as ZoneId]}
              strokeWidth="1"
              strokeDasharray="6,3"
              opacity="0.8"
            >
              <animate
                attributeName="strokeDashoffset"
                from="0"
                to="18"
                dur="1.5s"
                repeatCount="indefinite"
              />
            </rect>
          </g>
        )}
      </svg>
    </div>
  )
}
