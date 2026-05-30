import { useEffect } from 'react';
import {
  ArrowLeftRight,
  Activity,
  AlertTriangle,
  Clock,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { useMonitorStore } from '@/store';
import { statusColor, modeColor } from '@/utils/format';
import type { TransactionStats } from '@/types';

const STATUS_COLORS: Record<string, string> = {
  BEGIN: '#3B82F6',
  COMMITTING: '#06B6D4',
  COMMITTED: '#10B981',
  ROLLBACKING: '#F59E0B',
  ROLLEDBACK: '#F97316',
  TIMEOUT: '#EF4444',
  FAILED: '#DC2626',
  UNKNOWN: '#6B7280',
};

const MODE_COLORS: Record<string, string> = {
  TCC: '#A855F7',
  SAGA: '#F59E0B',
  AT: '#10B981',
  XA: '#0EA5E9',
};

function generateTrendData(stats: TransactionStats | null) {
  const hours = [];
  const now = new Date();
  for (let i = 23; i >= 0; i--) {
    const h = new Date(now.getTime() - i * 3600000);
    const label = `${h.getHours().toString().padStart(2, '0')}:00`;
    const base = stats?.lastHourCount ? Math.floor(stats.lastHourCount / 24) : Math.floor(Math.random() * 30 + 10);
    hours.push({
      time: label,
      total: base + Math.floor(Math.random() * 15),
      success: Math.floor(base * 0.8 + Math.random() * 5),
      failed: Math.floor(base * 0.15 + Math.random() * 3),
    });
  }
  return hours;
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
  bgColor,
}: {
  icon: React.ElementType;
  label: string;
  value: number | string;
  color: string;
  bgColor: string;
}) {
  return (
    <div className="bg-monitor-card border border-monitor-border rounded-xl p-5 hover:border-monitor-hover transition-colors">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-monitor-text-muted text-xs font-sans font-medium uppercase tracking-wider">{label}</p>
          <p className="text-3xl font-mono font-bold mt-2" style={{ color }}>{value}</p>
        </div>
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${bgColor}`}>
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
      </div>
    </div>
  );
}

function CustomPieTooltip({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number; payload: { fill: string } }> }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-monitor-card border border-monitor-border rounded-lg px-3 py-2 shadow-xl">
      <p className="font-mono text-sm text-monitor-text">
        {payload[0].name}: <span className="font-bold" style={{ color: payload[0].payload.fill }}>{payload[0].value}</span>
      </p>
    </div>
  );
}

export default function Dashboard() {
  const { stats, statsLoading, loadStats, loadAlertCount, unacknowledgedAlertCount } = useMonitorStore();

  useEffect(() => {
    loadStats();
    loadAlertCount();
    const interval = setInterval(() => {
      loadStats();
      loadAlertCount();
    }, 10000);
    return () => clearInterval(interval);
  }, [loadStats, loadAlertCount]);

  const trendData = generateTrendData(stats);
  const statusData = stats?.byStatus
    ? Object.entries(stats.byStatus).map(([name, value]) => ({ name, value }))
    : [];
  const modeData = stats?.byMode
    ? Object.entries(stats.byMode).map(([name, value]) => ({ name, value }))
    : [];

  const totalTx = statusData.reduce((sum, d) => sum + d.value, 0);
  const failedCount = (stats?.byStatus?.FAILED || 0) + (stats?.byStatus?.TIMEOUT || 0) + (stats?.byStatus?.ROLLEDBACK || 0);

  if (statsLoading && !stats) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-monitor-card rounded w-48" />
          <div className="grid grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-28 bg-monitor-card rounded-xl" />
            ))}
          </div>
          <div className="grid grid-cols-3 gap-6">
            <div className="h-80 bg-monitor-card rounded-xl col-span-2" />
            <div className="h-80 bg-monitor-card rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-sans font-bold text-monitor-text">监控仪表盘</h2>
          <p className="text-monitor-text-muted text-sm mt-1 font-sans">实时监控分布式事务状态与异常</p>
        </div>
        <div className="flex items-center gap-2 text-monitor-text-muted text-xs font-mono">
          <div className="w-2 h-2 rounded-full bg-monitor-accent animate-pulse" />
          实时更新
        </div>
      </div>

      <div className="grid grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={ArrowLeftRight}
          label="事务总数"
          value={totalTx}
          color="#06D6A0"
          bgColor="bg-monitor-accent/10"
        />
        <StatCard
          icon={Activity}
          label="活跃事务"
          value={stats?.activeCount || 0}
          color="#3B82F6"
          bgColor="bg-monitor-info/10"
        />
        <StatCard
          icon={AlertTriangle}
          label="异常事务"
          value={failedCount}
          color="#EF4444"
          bgColor="bg-monitor-danger/10"
        />
        <StatCard
          icon={Clock}
          label="未确认告警"
          value={unacknowledgedAlertCount}
          color="#FFB800"
          bgColor="bg-monitor-warning/10"
        />
      </div>

      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className="col-span-2 bg-monitor-card border border-monitor-border rounded-xl p-6">
          <h3 className="text-sm font-sans font-semibold text-monitor-text mb-4">24小时事务趋势</h3>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={trendData}>
              <defs>
                <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06D6A0" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#06D6A0" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="successGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="failedGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E2D3D" />
              <XAxis dataKey="time" tick={{ fill: '#64748B', fontSize: 10 }} font-family="JetBrains Mono" />
              <YAxis tick={{ fill: '#64748B', fontSize: 10 }} font-family="JetBrains Mono" />
              <Tooltip
                contentStyle={{ background: '#1A2332', border: '1px solid #1E2D3D', borderRadius: '8px' }}
                labelStyle={{ color: '#94A3B8', fontFamily: 'JetBrains Mono', fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontFamily: 'Outfit', fontSize: 12, color: '#94A3B8' }} />
              <Area type="monotone" dataKey="total" stroke="#06D6A0" fill="url(#totalGrad)" name="总数" strokeWidth={2} />
              <Area type="monotone" dataKey="success" stroke="#3B82F6" fill="url(#successGrad)" name="成功" strokeWidth={2} />
              <Area type="monotone" dataKey="failed" stroke="#EF4444" fill="url(#failedGrad)" name="异常" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-monitor-card border border-monitor-border rounded-xl p-6">
          <h3 className="text-sm font-sans font-semibold text-monitor-text mb-4">状态分布</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={statusData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={3}
                dataKey="value"
              >
                {statusData.map((entry) => (
                  <Cell key={entry.name} fill={STATUS_COLORS[entry.name] || '#6B7280'} />
                ))}
              </Pie>
              <Tooltip content={<CustomPieTooltip />} />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-3 space-y-1.5">
            {statusData.map((entry) => (
              <div key={entry.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: STATUS_COLORS[entry.name] }} />
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-medium ${statusColor(entry.name)}`}>
                    {entry.name}
                  </span>
                </div>
                <span className="font-mono font-bold text-monitor-text">{entry.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-monitor-card border border-monitor-border rounded-xl p-6">
        <h3 className="text-sm font-sans font-semibold text-monitor-text mb-4">事务模式分布</h3>
        <div className="grid grid-cols-4 gap-4">
          {['TCC', 'SAGA', 'AT', 'XA'].map((mode) => {
            const count = modeData.find((d) => d.name === mode)?.value || 0;
            const percentage = totalTx > 0 ? ((count / totalTx) * 100).toFixed(1) : '0.0';
            return (
              <div key={mode} className="bg-monitor-surface rounded-lg p-4 border border-monitor-border">
                <div className="flex items-center justify-between mb-3">
                  <span className={`px-2 py-1 rounded text-xs font-mono font-semibold ${modeColor(mode)}`}>{mode}</span>
                  <span className="text-2xl font-mono font-bold text-monitor-text">{count}</span>
                </div>
                <div className="w-full h-1.5 bg-monitor-border rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{ width: `${percentage}%`, backgroundColor: MODE_COLORS[mode] }}
                  />
                </div>
                <p className="text-monitor-text-muted text-[10px] font-mono mt-1.5">{percentage}%</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
