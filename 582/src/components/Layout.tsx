import { Outlet, NavLink } from 'react-router-dom';
import { Home, Edit, LayoutTemplate, Package, Download, Sparkles, Scale, Swords } from 'lucide-react';

const NAV_ITEMS = [
  { to: '/', icon: Home, label: '首页' },
  { to: '/editor', icon: Edit, label: '编辑器' },
  { to: '/templates', icon: LayoutTemplate, label: '模板' },
  { to: '/batch', icon: Package, label: '批量' },
  { to: '/export', icon: Download, label: '导出' },
  { to: '/ai-design', icon: Sparkles, label: 'AI设计' },
  { to: '/balance', icon: Scale, label: '平衡分析' },
  { to: '/battle', icon: Swords, label: '对战模拟' },
];

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden bg-dark-900">
      <aside className="w-16 lg:w-52 flex-shrink-0 bg-dark-800 border-r border-dark-600 flex flex-col">
        <div className="h-14 flex items-center justify-center lg:justify-start lg:px-4 border-b border-dark-600">
          <span className="font-cinzel text-gold-500 text-lg font-bold hidden lg:block">
            Card Forge
          </span>
          <span className="font-cinzel text-gold-500 text-lg font-bold lg:hidden">CF</span>
        </div>

        <nav className="flex-1 py-4 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 mx-2 rounded transition-all text-sm ${
                  isActive
                    ? 'bg-dark-700 text-gold-500 border border-gold-500/30 shadow-[0_0_8px_rgba(212,168,83,0.2)]'
                    : 'text-parchment-200/60 hover:text-parchment-200 hover:bg-dark-700/50'
                }`
              }
            >
              <item.icon size={18} />
              <span className="font-cinzel hidden lg:inline">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-dark-600">
          <div className="hidden lg:block text-[10px] text-dark-600 font-cinzel text-center">
            v1.0.0
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <div className="min-h-full">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
