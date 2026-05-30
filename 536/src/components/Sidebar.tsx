import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  ArrowLeftRight,
  Network,
  Bell,
  Stethoscope,
  Activity,
  Gauge,
} from 'lucide-react';
import { useMonitorStore } from '@/store';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: '仪表盘' },
  { to: '/transactions', icon: ArrowLeftRight, label: '事务列表' },
  { to: '/trace', icon: Network, label: '链路追踪' },
  { to: '/alerts', icon: Bell, label: '告警管理' },
  { to: '/diagnosis', icon: Stethoscope, label: '异常诊断' },
  { to: '/pressure-test', icon: Gauge, label: '压测中心' },
];

export default function Sidebar() {
  const location = useLocation();
  const alertCount = useMonitorStore((s) => s.unacknowledgedAlertCount);

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-60 bg-monitor-surface border-r border-monitor-border flex flex-col z-50">
      <div className="h-16 flex items-center gap-3 px-5 border-b border-monitor-border">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-monitor-accent to-emerald-600 flex items-center justify-center">
          <Activity className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-monitor-text font-sans font-bold text-base leading-tight">DTMonitor</h1>
          <p className="text-monitor-text-muted text-[10px] font-mono">分布式事务监控</p>
        </div>
      </div>

      <nav className="flex-1 py-4 px-3 space-y-1">
        {navItems.map((item) => {
          const isActive =
            item.to === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.to);

          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={() =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-sans font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-monitor-accent/10 text-monitor-accent'
                    : 'text-monitor-text-dim hover:bg-monitor-hover hover:text-monitor-text'
                }`
              }
            >
              <item.icon className="w-4.5 h-4.5 flex-shrink-0" />
              <span>{item.label}</span>
              {item.label === '告警管理' && alertCount > 0 && (
                <span className="ml-auto bg-monitor-danger text-white text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-full leading-none">
                  {alertCount}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      <div className="p-4 border-t border-monitor-border">
        <div className="flex items-center gap-2 text-monitor-text-muted text-xs font-mono">
          <div className="w-2 h-2 rounded-full bg-monitor-accent animate-pulse" />
          <span>监控中</span>
        </div>
      </div>
    </aside>
  );
}
