import React from 'react'
import { NavLink } from 'react-router-dom'

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

const Sidebar: React.FC<SidebarProps> = ({ collapsed, onToggle }) => {
  const navItems = [
    { path: '/', icon: '📋', label: '剪贴板历史' },
    { path: '/devices', icon: '💻', label: '设备管理' },
    { path: '/dashboard', icon: '📊', label: '速度仪表盘' },
    { path: '/settings', icon: '⚙️', label: '设置' }
  ]

  return (
    <aside
      className={`${
        collapsed ? 'w-16' : 'w-56'
      } bg-white border-r border-gray-200 flex flex-col transition-all duration-300`}
    >
      <div className="h-14 flex items-center px-4 border-b border-gray-100">
        <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center text-white font-bold">
          C
        </div>
        {!collapsed && (
          <span className="ml-3 font-semibold text-gray-800">ClipSync</span>
        )}
        <button
          onClick={onToggle}
          className="ml-auto text-gray-400 hover:text-gray-600"
        >
          {collapsed ? '→' : '←'}
        </button>
      </div>

      <nav className="flex-1 py-4">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `flex items-center px-4 py-3 mx-2 rounded-lg transition-all duration-200 ${
                isActive
                  ? 'bg-primary-50 text-primary-600 font-medium'
                  : 'text-gray-600 hover:bg-gray-50'
              }`
            }
          >
            <span className="text-xl">{item.icon}</span>
            {!collapsed && <span className="ml-3">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-gray-100">
        {!collapsed && (
          <div className="text-xs text-gray-400 text-center">
            版本 1.0.0
          </div>
        )}
      </div>
    </aside>
  )
}

export default Sidebar
