import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Layers,
  FolderTree,
  Upload,
  Users,
  LogOut,
  Search,
  Menu,
  X,
  Sparkles,
  BarChart3,
} from 'lucide-react'
import { useState } from 'react'
import { useAuthStore } from '@/store/authStore'
import { useIconStore } from '@/store/iconStore'

export default function Layout() {
  const { user, logout } = useAuthStore()
  const { setSearchQuery, fetchIcons } = useIconStore()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [searchInput, setSearchInput] = useState('')

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearchQuery(searchInput)
    fetchIcons()
  }

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: '仪表板' },
    { path: '/icons', icon: Layers, label: '图标库' },
    { path: '/ai-generate', icon: Sparkles, label: 'AI 生成' },
    { path: '/analytics', icon: BarChart3, label: '使用分析' },
    { path: '/categories', icon: FolderTree, label: '分类管理', roles: ['admin', 'editor'] },
    { path: '/upload', icon: Upload, label: '上传中心', roles: ['admin', 'editor'] },
    { path: '/team', icon: Users, label: '团队管理', roles: ['admin'] },
  ]

  const canAccess = (roles?: string[]) => {
    if (!roles) return true
    return user ? roles.includes(user.role) : false
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-20'
        } bg-white border-r border-gray-200 transition-all duration-300 flex flex-col`}
      >
        <div className="p-4 border-b border-gray-100 flex items-center justify-between">
          {sidebarOpen && (
            <h1 className="font-display font-bold text-xl text-primary-600">IconHub</h1>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          {navItems.map(
            (item) =>
              canAccess(item.roles) && (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/'}
                  className={({ isActive }) =>
                    `nav-item ${isActive ? 'nav-item-active' : ''}`
                  }
                >
                  <item.icon size={20} />
                  {sidebarOpen && <span>{item.label}</span>}
                </NavLink>
              )
          )}
        </nav>

        <div className="p-4 border-t border-gray-100">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
              <span className="text-primary-600 font-semibold">
                {user?.name.charAt(0).toUpperCase()}
              </span>
            </div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">{user?.name}</p>
                <p className="text-xs text-gray-500 capitalize">{user?.role}</p>
              </div>
            )}
          </div>
          <button
            onClick={handleLogout}
            className="nav-item w-full text-red-600 hover:bg-red-50 hover:text-red-600"
          >
            <LogOut size={20} />
            {sidebarOpen && <span>退出登录</span>}
          </button>
        </div>
      </aside>

      <main className="flex-1 flex flex-col min-w-0">
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <form onSubmit={handleSearch} className="max-w-xl">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="搜索图标名称或标签..."
                className="input pl-10"
              />
            </div>
          </form>
        </header>

        <div className="flex-1 p-6 overflow-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
