import { useEffect } from 'react'
import { useParkingData } from '@/hooks/useParkingData'
import { useParkingStore } from '@/store'
import ParkingMap from '@/components/ParkingMap'
import ZoneCards from '@/components/ZoneCards'
import PredictionChart from '@/components/PredictionChart'
import GuidanceCard from '@/components/GuidanceCard'
import EventManager from '@/components/EventManager'
import { Activity, RefreshCw, AlertTriangle, Cpu, Clock } from 'lucide-react'
import { EVENT_TYPES } from '@/types'

export default function Dashboard() {
  useParkingData()
  const { zones, lastUpdate, activeEvents, edgeSummary, eventImpacts } = useParkingStore()

  const totalAvailable = zones.reduce((sum, z) => sum + z.available_spots, 0)
  const totalSpots = zones.reduce((sum, z) => sum + z.total_spots, 0)
  const overallRate = totalSpots > 0 ? Math.round((1 - totalAvailable / totalSpots) * 100) : 0

  const formattedTime = lastUpdate
    ? new Date(lastUpdate).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '--:--:--'

  return (
    <div className="p-4 h-full flex flex-col animate-fade-in">
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
                <span className="text-sm">{typeInfo.icon}</span>
                <span className="font-bold">{event.title}</span>
                <span className="opacity-70">
                  <Clock className="w-3 h-3 inline mr-1" />
                  {event.start_hour.toString().padStart(2, '0')}:00 - {event.end_hour.toString().padStart(2, '0')}:00
                </span>
                <span className="opacity-70">
                  影响区域: {event.impact_zone_ids}
                </span>
                <span className="font-bold">x{event.impact_factor}</span>
              </div>
            )
          })}
        </div>
      )}

      <header className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-white font-body">监控大屏</h2>
          <p className="text-xs text-slate-500">实时停车场状态监控与智能引导</p>
        </div>
        <div className="flex items-center gap-4">
          {edgeSummary && (
            <div className="glass-card px-3 py-1.5 flex items-center gap-2" style={{ borderColor: 'rgba(139, 92, 246, 0.3)' }}>
              <Cpu className="w-3 h-3 text-brand-purple" />
              <span className="text-[10px] text-slate-400">边缘节点</span>
              <span className="data-value text-[10px] text-brand-purple">{edgeSummary.processing_latency_ms}ms</span>
            </div>
          )}
          <div className="glass-card px-3 py-1.5 flex items-center gap-2">
            <Activity className="w-3 h-3 text-brand-cyan" />
            <span className="text-[10px] text-slate-400">总占用率</span>
            <span className="data-value text-sm text-brand-cyan">{overallRate}%</span>
          </div>
          <div className="glass-card px-3 py-1.5 flex items-center gap-2">
            <RefreshCw className="w-3 h-3 text-brand-orange animate-spin" style={{ animationDuration: '3s' }} />
            <span className="text-[10px] text-slate-400">更新</span>
            <span className="data-value text-[10px] text-brand-orange">{formattedTime}</span>
          </div>
        </div>
      </header>

      <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
        <div className="col-span-5 flex flex-col gap-4">
          <div className="flex-1 min-h-0">
            <ParkingMap />
          </div>
        </div>

        <div className="col-span-3 flex flex-col gap-4 min-h-0 overflow-auto">
          <ZoneCards />
          <div className="glass-card p-3">
            <EventManager />
          </div>
        </div>

        <div className="col-span-4 flex flex-col gap-4 min-h-0">
          <div className="flex-1 min-h-0">
            <PredictionChart />
          </div>
          <div className="flex-1 min-h-0">
            <GuidanceCard />
          </div>
        </div>
      </div>
    </div>
  )
}
