import { Outlet } from 'react-router-dom';
import { Bell, Search } from 'lucide-react';
import Sidebar from './Sidebar';

export default function AppLayout() {
  return (
    <div className="flex min-h-screen bg-dep-bg">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 items-center justify-between border-b border-dep-border bg-dep-secondary/50 px-6">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-dep-muted" />
              <input
                type="text"
                placeholder="搜索依赖、CVE、仓库..."
                className="h-9 w-80 rounded-lg border border-dep-border bg-dep-card pl-9 pr-4 text-sm text-dep-text placeholder:text-dep-muted focus:border-dep-accent/50 focus:outline-none"
              />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button className="relative flex h-9 w-9 items-center justify-center rounded-lg text-dep-muted transition-colors hover:bg-dep-hover hover:text-dep-text">
              <Bell className="h-5 w-5" />
              <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-dep-critical" />
            </button>
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-dep-accent to-dep-safe" />
              <span className="text-sm font-medium text-dep-text">DevOps</span>
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
