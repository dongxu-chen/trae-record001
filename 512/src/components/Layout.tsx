import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { Activity, Settings, Clock, Bell, Wifi, WifiOff } from 'lucide-react';
import { cn } from '@/utils/helpers';
import { useAlertStore } from '@/stores/alert-store';
import { useWebSocket } from '@/hooks/useWebSocket';

const NAV_ITEMS = [
  { to: '/', icon: Activity, label: '仪表盘' },
  { to: '/config', icon: Settings, label: '规则配置' },
  { to: '/history', icon: Clock, label: '告警历史' },
];

export default function Layout() {
  const [sidebarExpanded, setSidebarExpanded] = useState(false);
  const { connected } = useWebSocket();
  const alertPanelOpen = useAlertStore(s => s.alertPanelOpen);
  const setAlertPanelOpen = useAlertStore(s => s.setAlertPanelOpen);
  const realtimeAlerts = useAlertStore(s => s.realtimeAlerts);

  const unacknowledgedCount = realtimeAlerts.filter(a => !a.acknowledged).length;

  return (
    <div className="flex h-screen overflow-hidden bg-brand-dark">
      <aside
        onMouseEnter={() => setSidebarExpanded(true)}
        onMouseLeave={() => setSidebarExpanded(false)}
        className={cn(
          'flex flex-col border-r border-brand-border bg-brand-surface transition-all duration-300 ease-in-out z-20',
          sidebarExpanded ? 'w-48' : 'w-16'
        )}
      >
        <div className="flex h-14 items-center justify-center border-b border-brand-border px-3">
          <div className="flex items-center gap-2">
            <Activity className="h-6 w-6 text-brand-cyan shrink-0" />
            {sidebarExpanded && (
              <span className="font-semibold text-brand-cyan whitespace-nowrap animate-fade-in-up">
                DataGuard
              </span>
            )}
          </div>
        </div>

        <nav className="flex-1 py-4 space-y-1 px-2">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
                  isActive
                    ? 'bg-brand-cyan/10 text-brand-cyan'
                    : 'text-brand-text-secondary hover:bg-brand-card hover:text-brand-text-primary'
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className={cn('h-5 w-5 shrink-0', isActive && 'text-brand-cyan')} />
                  {sidebarExpanded && (
                    <span className="whitespace-nowrap animate-fade-in-up">{label}</span>
                  )}
                  {isActive && (
                    <div className="absolute left-0 h-6 w-0.5 bg-brand-cyan rounded-r" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center justify-between border-b border-brand-border bg-brand-surface px-4">
          <div className="flex items-center gap-2">
            <h1 className="text-base font-semibold text-brand-text-primary">数据预警监控</h1>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              {connected ? (
                <>
                  <Wifi className="h-4 w-4 text-brand-green" />
                  <span className="text-xs text-brand-green">已连接</span>
                </>
              ) : (
                <>
                  <WifiOff className="h-4 w-4 text-brand-red" />
                  <span className="text-xs text-brand-red">未连接</span>
                </>
              )}
            </div>

            <button
              onClick={() => setAlertPanelOpen(!alertPanelOpen)}
              className="relative flex items-center justify-center rounded-lg p-2 text-brand-text-secondary hover:bg-brand-card hover:text-brand-text-primary transition-colors"
            >
              <Bell className="h-5 w-5" />
              {unacknowledgedCount > 0 && (
                <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-brand-red px-1 text-[10px] font-bold text-white animate-alert-pulse">
                  {unacknowledgedCount > 99 ? '99+' : unacknowledgedCount}
                </span>
              )}
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-auto bg-brand-dark p-4">
          <Outlet />
        </main>
      </div>

      {alertPanelOpen && (
        <aside className="w-80 border-l border-brand-border bg-brand-surface animate-slide-in-right overflow-auto">
          <div className="flex items-center justify-between border-b border-brand-border p-4">
            <h2 className="text-sm font-semibold text-brand-text-primary">实时告警</h2>
            <button
              onClick={() => setAlertPanelOpen(false)}
              className="text-brand-text-secondary hover:text-brand-text-primary text-xs"
            >
              关闭
            </button>
          </div>
          <div className="p-2 space-y-2">
            {realtimeAlerts.length === 0 ? (
              <div className="py-8 text-center text-sm text-brand-text-secondary">
                暂无实时告警
              </div>
            ) : (
              realtimeAlerts.map(alert => (
                <div
                  key={alert.id}
                  className={cn(
                    'rounded-lg border p-3',
                    alert.acknowledged
                      ? 'border-brand-border bg-brand-card/50 opacity-60'
                      : 'border-brand-border bg-brand-card'
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={cn(
                        'text-xs font-medium px-1.5 py-0.5 rounded',
                        alert.level === 'warning' && 'bg-brand-amber/20 text-brand-amber',
                        alert.level === 'danger' && 'bg-brand-red/20 text-brand-red',
                        alert.level === 'critical' && 'bg-brand-red/30 text-brand-red'
                      )}
                    >
                      {alert.level === 'warning' ? '警告' : alert.level === 'danger' ? '危险' : '严重'}
                    </span>
                    <span className="font-mono-num text-[10px] text-brand-text-secondary">
                      {new Date(alert.createdAt).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="mt-1.5 text-xs text-brand-text-primary line-clamp-2">
                    {alert.message}
                  </p>
                  <p className="mt-1 text-[10px] text-brand-text-secondary">{alert.metric}</p>
                </div>
              ))
            )}
          </div>
        </aside>
      )}
    </div>
  );
}
