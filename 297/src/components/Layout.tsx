import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { LogOut, FolderOpen, BarChart3, Layers } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/utils/cn'

const navItems = [
  { path: '/projects', label: '项目列表', icon: FolderOpen },
]

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const isAnnotatePage = location.pathname.startsWith('/annotate')
  const isStatisticsPage = location.pathname.startsWith('/statistics')

  if (isAnnotatePage) {
    return (
      <div className="h-screen w-screen flex flex-col bg-zinc-950">
        <header className="h-14 border-b border-zinc-800 flex items-center justify-between px-4 glass-panel">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Layers className="w-6 h-6 text-primary-400" />
              <span className="font-bold text-white">点云标注工具</span>
            </div>
            <div className="h-6 w-px bg-zinc-700" />
            <button
              onClick={() => navigate('/projects')}
              className="text-sm text-zinc-400 hover:text-white transition-colors"
            >
              ← 返回项目列表
            </button>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-zinc-400">
              {user?.username}
            </span>
            <button
              onClick={handleLogout}
              className="p-2 hover:bg-zinc-800 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4 text-zinc-400" />
            </button>
          </div>
        </header>
        <div className="flex-1 overflow-hidden">
          <Outlet />
        </div>
      </div>
    )
  }

  if (isStatisticsPage) {
    return (
      <div className="h-screen w-screen flex flex-col bg-zinc-950">
        <header className="h-14 border-b border-zinc-800 flex items-center justify-between px-4 glass-panel">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-6 h-6 text-primary-400" />
              <span className="font-bold text-white">统计分析</span>
            </div>
            <div className="h-6 w-px bg-zinc-700" />
            <button
              onClick={() => navigate('/projects')}
              className="text-sm text-zinc-400 hover:text-white transition-colors"
            >
              ← 返回项目列表
            </button>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-zinc-400">
              {user?.username}
            </span>
            <button
              onClick={handleLogout}
              className="p-2 hover:bg-zinc-800 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4 text-zinc-400" />
            </button>
          </div>
        </header>
        <div className="flex-1 overflow-hidden">
          <Outlet />
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen w-screen flex bg-zinc-950">
      <aside className="w-64 border-r border-zinc-800 glass-panel flex flex-col">
        <div className="p-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <Layers className="w-8 h-8 text-primary-400" />
            <span className="font-bold text-lg text-white">点云标注</span>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={cn(
                  'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors text-left',
                  isActive
                    ? 'bg-primary-500/20 text-primary-400'
                    : 'text-zinc-400 hover:bg-zinc-800 hover:text-white',
                )}
              >
                <Icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </button>
            )
          })}
        </nav>

        <div className="p-3 border-t border-zinc-800">
          <div className="flex items-center justify-between p-2">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-primary-500/20 flex items-center justify-center">
                <span className="text-primary-400 text-sm font-medium">
                  {user?.username?.charAt(0).toUpperCase()}
                </span>
              </div>
              <div>
                <p className="text-sm font-medium text-white">
                  {user?.username}
                </p>
                <p className="text-xs text-zinc-500">
                  {user?.role === 'admin' ? '管理员' : '标注员'}
                </p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 hover:bg-zinc-800 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4 text-zinc-400" />
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}
