import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  ShieldCheck,
  Bell,
  GitBranch,
  Gauge,
  ChevronLeft,
  ChevronRight,
  Activity,
} from 'lucide-react'
import { useStore } from '@/store'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: '监控仪表盘' },
  { to: '/rules', icon: ShieldCheck, label: '监控规则' },
  { to: '/scores', icon: Gauge, label: '质量评分' },
  { to: '/alerts', icon: Bell, label: '告警中心' },
  { to: '/impact', icon: GitBranch, label: '影响分析' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const { sidebarCollapsed, toggleSidebar } = useStore()
  const location = useLocation()

  return (
    <div className="flex h-screen bg-[#0a0f1a] text-gray-100 overflow-hidden">
      <aside
        className={`${
          sidebarCollapsed ? 'w-16' : 'w-56'
        } flex-shrink-0 bg-[#0d1321] border-r border-cyan-900/30 transition-all duration-300 flex flex-col`}
      >
        <div className="h-14 flex items-center px-3 border-b border-cyan-900/30">
          <Activity className="w-6 h-6 text-cyan-400 flex-shrink-0" />
          {!sidebarCollapsed && (
            <span className="ml-2 text-sm font-mono font-bold tracking-wider text-cyan-300 whitespace-nowrap">
              DataQuality
            </span>
          )}
        </div>
        <nav className="flex-1 py-3 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center mx-2 px-3 py-2.5 rounded-lg transition-all duration-200 group ${
                  isActive
                    ? 'bg-cyan-500/15 text-cyan-300 shadow-lg shadow-cyan-500/10'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                }`
              }
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!sidebarCollapsed && (
                <span className="ml-3 text-sm font-medium">{label}</span>
              )}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={toggleSidebar}
          className="mx-2 mb-3 p-2 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-white/5 transition-colors"
        >
          {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </aside>

      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="h-14 flex items-center justify-between px-6 border-b border-cyan-900/30 bg-[#0d1321]/80 backdrop-blur-sm flex-shrink-0">
          <div className="flex items-center gap-3">
            <h1 className="text-base font-mono font-semibold text-gray-200">
              {navItems.find(n => {
                if (n.to === '/') return location.pathname === '/'
                return location.pathname.startsWith(n.to)
              })?.label || '数据质量监控平台'}
            </h1>
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-500 font-mono">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Spark 运行中
            </span>
            <span>Airflow 已连接</span>
          </div>
        </header>
        <div className="flex-1 overflow-auto p-6">
          {children}
        </div>
      </main>
    </div>
  )
}
