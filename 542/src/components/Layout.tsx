import { Link, useLocation } from 'react-router-dom';
import { Eye, FileText, Palette, Globe, Users } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  const navItems = [
    { path: '/', label: '检测工作台', icon: Eye },
    { path: '/report', label: 'WCAG报告', icon: FileText },
    { path: '/batch-scan', label: '批量扫描', icon: Globe },
    { path: '/user-testing', label: '用户测试', icon: Users },
  ];

  return (
    <div className="min-h-screen bg-[#1a1d23] text-zinc-200">
      <header className="border-b border-zinc-800 bg-[#1a1d23]/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-[1600px] mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#00d4aa] to-[#00d4aa]/60 flex items-center justify-center">
              <Palette className="w-4 h-4 text-zinc-900" />
            </div>
            <span className="font-bold text-lg tracking-tight">
              Color<span className="text-[#00d4aa]">A11y</span>
            </span>
            <span className="text-xs text-zinc-600 font-mono ml-2 hidden sm:block">
              色盲无障碍检测
            </span>
          </div>

          <nav className="flex items-center gap-1">
            {navItems.map(({ path, label, icon: Icon }) => (
              <Link
                key={path}
                to={path}
                className={cn(
                  'px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors',
                  location.pathname === path
                    ? 'bg-[#00d4aa]/10 text-[#00d4aa]'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
                )}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto px-6 py-6">{children}</main>
    </div>
  );
}
