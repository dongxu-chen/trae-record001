import { NavLink, Outlet } from 'react-router-dom'
import { LayoutDashboard, BarChart3, Navigation, Car, CalendarPlus } from 'lucide-react'

const navItems = [
  { to: '/', label: '监控大屏', icon: LayoutDashboard },
  { to: '/analytics', label: '数据分析', icon: BarChart3 },
  { to: '/guide', label: '引导推荐', icon: Navigation },
  { to: '/reserve', label: '预约导航', icon: CalendarPlus },
]

export default function Layout() {
  return (
    <div className="flex h-screen bg-brand-deeper">
      <aside className="w-56 flex-shrink-0 border-r border-brand-border bg-brand-dark/80 backdrop-blur-xl flex flex-col">
        <div className="px-5 py-5 flex items-center gap-3 border-b border-brand-border">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-cyan to-brand-blue flex items-center justify-center">
            <Car className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white font-body">智能停车引导</h1>
            <p className="text-[10px] text-slate-500 font-orbitron tracking-wider">SMART PARKING</p>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `nav-item flex items-center gap-3 ${isActive ? 'active' : ''}`
              }
            >
              <Icon className="w-4 h-4" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="px-4 py-4 border-t border-brand-border">
          <div className="glass-card p-3 text-center">
            <div className="text-[10px] text-slate-500 mb-1">系统状态</div>
            <div className="flex items-center justify-center gap-2">
              <span className="status-dot available" />
              <span className="text-xs text-brand-cyan font-medium">运行中</span>
            </div>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
