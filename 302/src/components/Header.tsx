import React from 'react'
import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/', label: '文本翻译', icon: '📝' },
  { to: '/document', label: '文档翻译', icon: '📄' },
  { to: '/terms', label: '术语库', icon: '📚' },
  { to: '/memory', label: '翻译记忆', icon: '💾' },
  { to: '/plugin', label: '网页翻译', icon: '🌐' },
  { to: '/settings', label: '设置', icon: '⚙️' },
]

export const Header: React.FC = () => {
  return (
    <header className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-3xl">🌍</span>
            <h1 className="text-2xl font-bold">多语言翻译工具</h1>
          </div>
          <nav className="flex gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `px-4 py-2 rounded-lg transition-all duration-200 flex items-center gap-2 ${
                    isActive
                      ? 'bg-white/20 text-white font-medium'
                      : 'text-white/80 hover:bg-white/10 hover:text-white'
                  }`
                }
              >
                <span>{item.icon}</span>
                <span className="hidden sm:inline">{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </div>
      </div>
    </header>
  )
}
