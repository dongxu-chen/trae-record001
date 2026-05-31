import { Outlet, NavLink } from 'react-router-dom';
import {
  Database,
  LayoutDashboard,
  Shield,
  HardDrive,
  ArrowRightLeft,
  Lightbulb,
  Activity,
  Archive,
  Route,
  TrendingUp,
} from 'lucide-react';

const navItems = [
  { to: '/', label: '仪表盘', icon: LayoutDashboard },
  { to: '/policies', label: '策略管理', icon: Shield },
  { to: '/partitions', label: '分区管理', icon: HardDrive },
  { to: '/tiering', label: '存储分层', icon: ArrowRightLeft },
  { to: '/advisor', label: '优化建议', icon: Lightbulb },
  { to: '/archive', label: '数据归档', icon: Archive },
  { to: '/router', label: '查询路由', icon: Route },
  { to: '/simulator', label: '生命周期模拟', icon: TrendingUp },
  { to: '/monitor', label: '监控', icon: Activity },
];

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-slate-900">
      <aside className="w-60 bg-slate-950 flex flex-col border-r border-slate-800">
        <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-800">
          <Database className="h-6 w-6 text-sky-400" />
          <span className="text-lg font-semibold text-white">CH Lifecycle</span>
        </div>

        <nav className="flex-1 py-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-5 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-sky-500/10 text-sky-400 border-l-2 border-sky-400'
                    : 'text-slate-400 hover:text-slate-200 border-l-2 border-transparent'
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="flex-1 min-h-screen bg-slate-900 p-6">
        <Outlet />
      </main>
    </div>
  );
}
