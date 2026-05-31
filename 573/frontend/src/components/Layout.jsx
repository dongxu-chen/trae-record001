import React from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Play, 
  ListChecks, 
  FileText, 
  Shield 
} from 'lucide-react';
import classNames from 'classnames';

const navigation = [
  { name: '仪表盘', href: '/', icon: LayoutDashboard },
  { name: '新建扫描', href: '/scan', icon: Play },
  { name: '任务列表', href: '/jobs', icon: ListChecks },
  { name: '报告', href: '/reports', icon: FileText },
  { name: '规则', href: '/rules', icon: Shield },
];

export default function Layout() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0">
        <div className="flex-1 flex flex-col min-h-0 bg-gray-800">
          <div className="flex items-center h-16 flex-shrink-0 px-4 bg-gray-900">
            <Shield className="h-8 w-8 text-indigo-500" />
            <span className="ml-2 text-white font-bold text-lg">安全扫描</span>
          </div>
          <nav className="flex-1 px-2 py-4 space-y-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={classNames(
                    isActive
                      ? 'bg-gray-900 text-white'
                      : 'text-gray-300 hover:bg-gray-700 hover:text-white',
                    'group flex items-center px-2 py-2 text-sm font-medium rounded-md'
                  )}
                >
                  <Icon
                    className={classNames(
                      isActive ? 'text-indigo-400' : 'text-gray-400',
                      'mr-3 flex-shrink-0 h-6 w-6'
                    )}
                  />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      <div className="md:pl-64 flex flex-col flex-1">
        <main className="flex-1">
          <div className="py-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
              <Outlet />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
