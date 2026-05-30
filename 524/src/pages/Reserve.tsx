import { useParkingData } from '@/hooks/useParkingData'
import { useParkingStore } from '@/store'
import ReservationPanel from '@/components/ReservationPanel'
import PricingPanel from '@/components/PricingPanel'
import NavigationPanel from '@/components/NavigationPanel'
import ParkingMap from '@/components/ParkingMap'
import { Car, DollarSign, Navigation } from 'lucide-react'

export default function Reserve() {
  useParkingData()
  const { zones } = useParkingStore()

  const totalAvailable = zones.reduce((sum, z) => sum + z.available_spots, 0)
  const totalSpots = zones.reduce((sum, z) => sum + z.total_spots, 0)

  return (
    <div className="p-4 h-full flex flex-col animate-fade-in">
      <header className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-white font-body">预约与导航</h2>
          <p className="text-xs text-slate-500">预约停车位 · 动态定价 · 车机导航推送</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="glass-card px-3 py-1.5 flex items-center gap-2">
            <Car className="w-3 h-3 text-brand-cyan" />
            <span className="text-[10px] text-slate-400">可用车位</span>
            <span className="data-value text-sm text-brand-cyan">{totalAvailable}/{totalSpots}</span>
          </div>
          <div className="glass-card px-3 py-1.5 flex items-center gap-2" style={{ borderColor: 'rgba(245, 158, 11, 0.3)' }}>
            <DollarSign className="w-3 h-3 text-brand-orange" />
            <span className="text-[10px] text-slate-400">动态定价</span>
            <span className="text-[10px] text-brand-orange">实时</span>
          </div>
        </div>
      </header>

      <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
        <div className="col-span-4 flex flex-col gap-4 min-h-0 overflow-auto">
          <ReservationPanel />
        </div>

        <div className="col-span-4 flex flex-col gap-4 min-h-0 overflow-auto">
          <PricingPanel />
        </div>

        <div className="col-span-4 flex flex-col gap-4 min-h-0 overflow-auto">
          <NavigationPanel />
        </div>
      </div>
    </div>
  )
}
