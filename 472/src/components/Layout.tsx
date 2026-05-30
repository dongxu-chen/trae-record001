import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { Home, BarChart3, Users, Settings, ChevronLeft } from 'lucide-react';
import { useStore } from '../stores/useStore';

export const Layout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { currentProject, currentUser } = useStore();

  const navItems = [
    { path: '/', label: '工作区', icon: Home },
    { path: '/collaborators', label: '协作者', icon: Users },
    { path: '/settings', label: '设置', icon: Settings },
  ];

  const isInProject = location.pathname.startsWith('/project/');

  return (
    <div className="min-h-screen bg-slate-900 flex">
      <aside className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col">
        <div className="p-6 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-400 rounded-xl flex items-center justify-center">
              <BarChart3 className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">ChartAnnotate</h1>
              <p className="text-xs text-slate-400">数据标注平台</p>
            </div>
          </div>
        </div>

        {isInProject && currentProject && (
          <div className="p-4 border-b border-slate-700">
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-3"
            >
              <ChevronLeft className="w-4 h-4" />
              <span className="text-sm">返回工作区</span>
            </button>
            <div className="bg-slate-700/50 rounded-lg p-3">
              <p className="text-sm text-slate-400">当前项目</p>
              <p className="text-white font-medium truncate">{currentProject.name}</p>
            </div>
          </div>
        )}

        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                      isActive
                        ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                        : 'text-slate-400 hover:bg-slate-700 hover:text-white'
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="text-sm font-medium">{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="p-4 border-t border-slate-700">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold"
              style={{ backgroundColor: currentUser.color }}
            >
              {currentUser.name.charAt(0)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{currentUser.name}</p>
              <p className="text-xs text-slate-400">在线</p>
            </div>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
};
