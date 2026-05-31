import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, ShieldAlert, ArrowUpCircle, GitBranch, Heart, ChevronLeft, ChevronRight } from 'lucide-react';

const navItems = [
  { icon: LayoutDashboard, label: '仪表盘', path: '/' },
  { icon: ShieldAlert, label: '漏洞报告', path: '/vulnerabilities' },
  { icon: ArrowUpCircle, label: '升级建议', path: '/upgrades' },
  { icon: Heart, label: '健康管理', path: '/health' },
  { icon: GitBranch, label: '仓库管理', path: '/repositories' },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <aside
      className={`h-screen flex flex-col bg-dep-secondary border-r border-dep-border transition-all duration-300 ${
        collapsed ? 'w-16' : 'w-60'
      }`}
    >
      <div className="h-16 flex items-center justify-center border-b border-dep-border px-4">
        {collapsed ? (
          <span className="font-mono font-bold text-xl text-dep-accent">DG</span>
        ) : (
          <span className="font-mono font-bold text-xl text-dep-accent tracking-wider">DepGuard</span>
        )}
      </div>

      <nav className="flex-1 py-4 flex flex-col gap-1 px-2">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`relative flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group ${
                isActive
                  ? 'bg-dep-hover text-dep-accent'
                  : 'text-dep-muted hover:bg-dep-hover hover:text-dep-text'
              }`}
            >
              <div
                className={`absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r transition-all duration-200 ${
                  isActive ? 'bg-dep-accent' : 'bg-transparent group-hover:bg-dep-accent/50'
                }`}
              />
              <item.icon className="w-5 h-5 shrink-0" />
              {!collapsed && <span className="text-sm font-medium truncate">{item.label}</span>}
            </button>
          );
        })}
      </nav>

      <div className="border-t border-dep-border p-2">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-dep-muted hover:bg-dep-hover hover:text-dep-text transition-all duration-200"
        >
          {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
          {!collapsed && <span className="text-sm">收起</span>}
        </button>
      </div>
    </aside>
  );
}
