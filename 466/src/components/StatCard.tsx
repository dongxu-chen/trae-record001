import { cn } from '@/lib/utils'
import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  label: string
  value: string | number
  icon: LucideIcon
  trend?: string
  color: 'cyan' | 'amber' | 'red' | 'emerald' | 'violet'
  pulse?: boolean
}

const colorMap = {
  cyan: 'from-cyan-500/20 to-cyan-600/5 border-cyan-500/30 text-cyan-400',
  amber: 'from-amber-500/20 to-amber-600/5 border-amber-500/30 text-amber-400',
  red: 'from-red-500/20 to-red-600/5 border-red-500/30 text-red-400',
  emerald: 'from-emerald-500/20 to-emerald-600/5 border-emerald-500/30 text-emerald-400',
  violet: 'from-violet-500/20 to-violet-600/5 border-violet-500/30 text-violet-400',
}

const iconBgMap = {
  cyan: 'bg-cyan-500/15',
  amber: 'bg-amber-500/15',
  red: 'bg-red-500/15',
  emerald: 'bg-emerald-500/15',
  violet: 'bg-violet-500/15',
}

export default function StatCard({ label, value, icon: Icon, trend, color, pulse }: StatCardProps) {
  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-xl border bg-gradient-to-br p-5 transition-all duration-300 hover:scale-[1.02] hover:shadow-lg',
        colorMap[color],
      )}
    >
      {pulse && (
        <span className="absolute top-3 right-3 w-2 h-2 rounded-full bg-red-400 animate-ping" />
      )}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-400 font-medium tracking-wide uppercase">{label}</p>
          <p className="mt-2 text-3xl font-mono font-bold tracking-tight">{value}</p>
          {trend && <p className="mt-1 text-xs text-gray-500">{trend}</p>}
        </div>
        <div className={cn('p-2.5 rounded-lg', iconBgMap[color])}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  )
}
