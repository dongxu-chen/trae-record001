import { useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FileCheck,
  Clock,
  BarChart3,
  AlertTriangle,
  TrendingUp,
  Menu,
  X,
  Database,
  ChevronDown,
  Activity,
  Wrench,
  Monitor,
} from 'lucide-react';
import { getCurrentUser, setCurrentUser } from '@/lib/api';

const navItems = [
  { path: '/dashboard', label: '仪表盘', icon: LayoutDashboard },
  { path: '/health-score', label: '健康评分', icon: Activity },
  { path: '/rules', label: '规则管理', icon: FileCheck },
  { path: '/tasks', label: '任务调度', icon: Clock },
  { path: '/reports', label: '质量报告', icon: BarChart3 },
  { path: '/issues', label: '问题跟踪', icon: AlertTriangle },
  { path: '/auto-fix', label: '自动修复', icon: Wrench },
  { path: '/trends', label: '趋势分析', icon: TrendingUp },
  { path: '/board', label: '质量看板', icon: Monitor },
];

const roleOptions = [
  { id: 'user_admin', name: '管理员', role: 'admin' as const, initials: 'AD', color: 'bg-primary-100 text-primary-700' },
  { id: 'user_engineer', name: '张工', role: 'engineer' as const, initials: 'ZG', color: 'bg-blue-100 text-blue-700' },
  { id: 'user_analyst', name: '李分析', role: 'analyst' as const, initials: 'LF', color: 'bg-purple-100 text-purple-700' },
];

const roleLabels: Record<string, string> = {
  admin: '管理员',
  engineer: '工程师',
  analyst: '分析师',
};

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [roleMenuOpen, setRoleMenuOpen] = useState(false);
  const [activeUser, setActiveUser] = useState(() => {
    const u = getCurrentUser();
    return roleOptions.find(r => r.id === u.id) || roleOptions[0];
  });
  const location = useLocation();

  const handleRoleSwitch = (option: typeof roleOptions[number]) => {
    setActiveUser(option);
    setCurrentUser({ id: option.id, name: option.name, role: option.role });
    setRoleMenuOpen(false);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-20'
        } bg-gradient-to-b from-primary-800 to-primary-900 text-white transition-all duration-300 flex flex-col`}
      >
        <div className="p-4 flex items-center justify-between border-b border-primary-700">
          {sidebarOpen && (
            <div className="flex items-center gap-2">
              <Database className="w-8 h-8" />
              <span className="font-display text-xl font-bold">DataQuality</span>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-primary-700 rounded-lg transition-colors"
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                  isActive
                    ? 'bg-primary-600 text-white shadow-lg'
                    : 'text-primary-100 hover:bg-primary-700 hover:text-white'
                }`}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {sidebarOpen && <span className="font-medium">{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {sidebarOpen && (
          <div className="p-4 border-t border-primary-700">
            <p className="text-xs text-primary-300">数据质量管理平台 v1.0</p>
          </div>
        )}
      </aside>

      <main className="flex-1 flex flex-col">
        <header className="bg-white shadow-sm px-8 py-4 flex items-center justify-between">
          <div>
            <h1 className="font-display text-2xl font-bold text-gray-800">
              {navItems.find((item) => location.pathname.startsWith(item.path))?.label || '数据质量管理平台'}
            </h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative">
              <button
                onClick={() => setRoleMenuOpen(!roleMenuOpen)}
                className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className={`w-9 h-9 rounded-full ${activeUser.color} flex items-center justify-center`}>
                  <span className="font-semibold text-sm">{activeUser.initials}</span>
                </div>
                <div className="text-left">
                  <p className="text-sm font-medium text-gray-800">{activeUser.name}</p>
                  <p className="text-xs text-gray-500">{roleLabels[activeUser.role]}</p>
                </div>
                <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${roleMenuOpen ? 'rotate-180' : ''}`} />
              </button>

              {roleMenuOpen && (
                <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-xl shadow-lg border border-gray-100 py-2 z-50">
                  <p className="px-4 py-2 text-xs font-medium text-gray-400 uppercase">切换角色</p>
                  {roleOptions.map((option) => (
                    <button
                      key={option.id}
                      onClick={() => handleRoleSwitch(option)}
                      className={`w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors ${
                        activeUser.id === option.id ? 'bg-primary-50' : ''
                      }`}
                    >
                      <div className={`w-8 h-8 rounded-full ${option.color} flex items-center justify-center`}>
                        <span className="font-semibold text-xs">{option.initials}</span>
                      </div>
                      <div className="text-left">
                        <p className="text-sm font-medium text-gray-800">{option.name}</p>
                        <p className="text-xs text-gray-500">{roleLabels[option.role]}</p>
                      </div>
                      {activeUser.id === option.id && (
                        <div className="ml-auto w-2 h-2 rounded-full bg-primary-500" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </header>

        <div className="flex-1 p-8 overflow-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
