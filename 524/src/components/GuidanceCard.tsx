import { useParkingStore } from '@/store'
import { ZONE_NAMES, ZONE_COLORS, type ZoneId } from '@/types'
import { Navigation, Clock, Footprints, ArrowRight, Shield } from 'lucide-react'

export default function GuidanceCard() {
  const { guidance } = useParkingStore()

  if (!guidance) {
    return (
      <div className="glass-card p-4 h-full flex items-center justify-center">
        <p className="text-sm text-slate-500">正在计算最优推荐...</p>
      </div>
    )
  }

  const recColor = ZONE_COLORS[guidance.recommended_zone as ZoneId]
  const confPct = Math.round(guidance.confidence * 100)

  return (
    <div className="glass-card p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Navigation className="w-4 h-4 text-brand-cyan" />
          智能引导
        </h3>
        <span className="text-[10px] text-slate-500">RL策略推荐</span>
      </div>

      <div className="flex-1 space-y-3 overflow-auto">
        <div
          className="rounded-xl p-4 relative overflow-hidden"
          style={{
            background: `linear-gradient(135deg, ${recColor}15, ${recColor}05)`,
            border: `1px solid ${recColor}40`,
          }}
        >
          <div className="absolute top-0 right-0 w-20 h-20 opacity-5">
            <Navigation className="w-full h-full" style={{ color: recColor }} />
          </div>

          <div className="flex items-start justify-between mb-2">
            <div>
              <div className="text-[10px] text-slate-400 mb-1">推荐前往</div>
              <div className="flex items-center gap-2">
                <span
                  className="zone-tag text-sm"
                  style={{ background: `${recColor}20`, color: recColor, border: `1px solid ${recColor}60` }}
                >
                  {guidance.recommended_zone}
                </span>
                <span className="text-sm font-medium text-white">
                  {ZONE_NAMES[guidance.recommended_zone as ZoneId]}
                </span>
              </div>
            </div>
            <ArrowRight className="w-5 h-5 mt-4" style={{ color: recColor }} />
          </div>

          <div className="flex items-center gap-4 mt-3">
            <div className="flex items-center gap-1 text-xs text-slate-400">
              <Clock className="w-3 h-3" />
              {guidance.estimated_wait_minutes > 0
                ? `预计等待${guidance.estimated_wait_minutes}分钟`
                : '无需等待'}
            </div>
            <div className="flex items-center gap-1 text-xs text-slate-400">
              <Footprints className="w-3 h-3" />
              步行{Math.round(guidance.walking_distance)}米
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Shield className="w-3 h-3 text-brand-cyan" />
          <span className="text-[10px] text-slate-400">推荐置信度</span>
          <div className="flex-1 h-1.5 bg-brand-dark rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${confPct}%`,
                background: confPct > 70 ? '#06D6A0' : confPct > 40 ? '#FBBF24' : '#FF6B35',
              }}
            />
          </div>
          <span className="data-value text-xs text-brand-cyan">{confPct}%</span>
        </div>

        <div className="text-xs text-slate-400 bg-brand-dark/50 rounded-lg p-3">
          {guidance.reason}
        </div>

        {guidance.alternatives.length > 0 && (
          <div>
            <div className="text-[10px] text-slate-500 mb-2">备选区域</div>
            <div className="space-y-1.5">
              {guidance.alternatives.slice(0, 3).map((alt) => {
                const altColor = ZONE_COLORS[alt.zone_id as ZoneId]
                return (
                  <div key={alt.zone_id} className="flex items-center gap-2 text-xs">
                    <span
                      className="zone-tag w-6 h-6 text-[10px]"
                      style={{ background: `${altColor}15`, color: altColor, border: `1px solid ${altColor}30` }}
                    >
                      {alt.zone_id}
                    </span>
                    <div className="flex-1 h-1 bg-brand-dark rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${alt.score * 100}%`, background: altColor }}
                      />
                    </div>
                    <span className="text-slate-400 w-8 text-right">{Math.round(alt.score * 100)}%</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
