import { useEffect, useMemo } from 'react';
import { Activity, RefreshCw, Clock } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { useLifecycleStore } from '@/store';
import StatusBadge from '@/components/StatusBadge';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

function getBarColor(percent: number): string {
  if (percent > 90) return 'bg-red-400';
  if (percent > 70) return 'bg-amber-400';
  return 'bg-sky-400';
}

const DISK_COLORS = ['#38bdf8', '#fbbf24', '#34d399', '#f87171', '#a78bfa'];

const JOB_LABELS: Record<string, string> = {
  ttl_check: 'TTL 检查',
  tiering: '分层存储',
  cleanup: '数据清理',
  optimize: '优化合并',
};

export default function Monitor() {
  const {
    currentSnapshot,
    snapshots,
    schedulerStatus,
    fetchCurrentSnapshot,
    fetchSnapshots,
    fetchSchedulerStatus,
    snapshotsLoading,
  } = useLifecycleStore();

  useEffect(() => {
    fetchCurrentSnapshot();
    fetchSnapshots();
    fetchSchedulerStatus();
  }, [fetchCurrentSnapshot, fetchSnapshots, fetchSchedulerStatus]);

  const diskNames = useMemo(() => {
    const names = new Set<string>();
    snapshots.forEach((s) => s.disks.forEach((d) => names.add(d.name)));
    return Array.from(names);
  }, [snapshots]);

  const chartData = useMemo(() => {
    return snapshots.map((s) => {
      const entry: Record<string, unknown> = {
        timestamp: new Date(s.timestamp).toLocaleString(),
      };
      s.disks.forEach((d) => {
        entry[d.name] = d.used_pct;
      });
      return entry;
    });
  }, [snapshots]);

  const handleRefresh = () => {
    fetchCurrentSnapshot();
    fetchSnapshots();
    fetchSchedulerStatus();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">监控</h1>
          <p className="mt-1 text-sm text-slate-400">ClickHouse 集群状态监控与趋势分析</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={snapshotsLoading}
          className="flex items-center gap-2 rounded-lg bg-sky-400/10 px-4 py-2 text-sm font-medium text-sky-400 transition-colors hover:bg-sky-400/20 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${snapshotsLoading ? 'animate-spin' : ''}`} />
          刷新
        </button>
      </div>

      <div className="bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-5">
        <div className="mb-4 flex items-center gap-2">
          <Activity className="h-5 w-5 text-sky-400" />
          <h2 className="text-lg font-semibold text-slate-100">当前快照</h2>
          {currentSnapshot && (
            <span className="ml-auto text-xs text-slate-500">
              {new Date(currentSnapshot.timestamp).toLocaleString()}
            </span>
          )}
        </div>
        {currentSnapshot ? (
          <div className="space-y-6">
            <div>
              <h3 className="mb-3 text-sm font-medium text-slate-300">磁盘使用</h3>
              <div className="grid grid-cols-2 gap-4">
                {currentSnapshot.disks.map((disk) => {
                  const used = disk.total_space - disk.free_space;
                  return (
                    <div
                      key={disk.name}
                      className="rounded-lg bg-slate-900/50 border border-slate-700/30 px-4 py-3"
                    >
                      <div className="mb-1 flex items-center justify-between text-sm">
                        <span className="text-slate-300">{disk.name}</span>
                        <span className="text-slate-400">
                          {formatBytes(used)} / {formatBytes(disk.total_space)}
                        </span>
                      </div>
                      <div className="h-2 w-full rounded-full bg-slate-700">
                        <div
                          className={`h-2 rounded-full transition-all ${getBarColor(disk.used_pct)}`}
                          style={{ width: `${Math.min(disk.used_pct, 100)}%` }}
                        />
                      </div>
                      <p className="mt-0.5 text-xs text-slate-500">{disk.used_pct.toFixed(1)}% 已使用</p>
                    </div>
                  );
                })}
              </div>
            </div>
            <div>
              <h3 className="mb-3 text-sm font-medium text-slate-300">表信息汇总</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700/50 text-left text-slate-400">
                      <th className="pb-2 pr-4 font-medium">数据库</th>
                      <th className="pb-2 pr-4 font-medium">表</th>
                      <th className="pb-2 pr-4 font-medium">行数</th>
                      <th className="pb-2 pr-4 font-medium">大小</th>
                      <th className="pb-2 font-medium">分区数</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentSnapshot.tables.map((t, idx) => (
                      <tr key={idx} className="border-b border-slate-700/30">
                        <td className="py-2 pr-4 text-slate-300">{t.database}</td>
                        <td className="py-2 pr-4 text-slate-300">{t.table}</td>
                        <td className="py-2 pr-4 text-slate-400">{t.total_rows.toLocaleString()}</td>
                        <td className="py-2 pr-4 text-slate-400">{formatBytes(t.total_bytes)}</td>
                        <td className="py-2 text-slate-400">{t.partition_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {currentSnapshot.tables.length === 0 && (
                <p className="text-sm text-slate-500">暂无表数据</p>
              )}
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">暂无快照数据</p>
        )}
      </div>

      <div className="bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-5">
        <h2 className="mb-4 text-lg font-semibold text-slate-100">磁盘趋势</h2>
        {chartData.length > 1 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis
                dataKey="timestamp"
                tick={{ fill: '#64748b', fontSize: 12 }}
                axisLine={{ stroke: '#334155' }}
                tickLine={{ stroke: '#334155' }}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: '#64748b', fontSize: 12 }}
                axisLine={{ stroke: '#334155' }}
                tickLine={{ stroke: '#334155' }}
                tickFormatter={(v: number) => `${v}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                  color: '#e2e8f0',
                  fontSize: 13,
                }}
                formatter={(value: number, name: string) => [`${value.toFixed(1)}%`, name]}
              />
              {diskNames.map((name, idx) => (
                <Line
                  key={name}
                  type="monotone"
                  dataKey={name}
                  stroke={DISK_COLORS[idx % DISK_COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-slate-500">需要至少 2 个快照才能显示趋势</p>
        )}
      </div>

      <div className="bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-100">快照历史</h2>
          <button
            onClick={() => fetchSnapshots()}
            className="flex items-center gap-1.5 rounded-lg bg-sky-400/10 px-3 py-1.5 text-xs font-medium text-sky-400 transition-colors hover:bg-sky-400/20"
          >
            <RefreshCw className="h-3 w-3" />
            刷新
          </button>
        </div>
        {snapshots.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/50 text-left text-slate-400">
                  <th className="pb-2 pr-4 font-medium">时间</th>
                  <th className="pb-2 pr-4 font-medium">磁盘数</th>
                  <th className="pb-2 font-medium">表数</th>
                </tr>
              </thead>
              <tbody>
                {snapshots.map((s, idx) => (
                  <tr key={idx} className="border-b border-slate-700/30">
                    <td className="py-2 pr-4 text-slate-300">
                      {new Date(s.timestamp).toLocaleString()}
                    </td>
                    <td className="py-2 pr-4 text-slate-400">{s.disks.length}</td>
                    <td className="py-2 text-slate-400">{s.tables.length}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-slate-500">暂无快照历史</p>
        )}
      </div>

      <div className="bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-5">
        <h2 className="mb-4 text-lg font-semibold text-slate-100">调度日志</h2>
        <div className="space-y-3">
          {Object.entries(schedulerStatus).map(([jobType, job]) => (
            <div
              key={jobType}
              className="flex items-center justify-between rounded-lg bg-slate-900/50 border border-slate-700/30 px-4 py-3"
            >
              <div className="flex items-center gap-3">
                <Clock className="h-4 w-4 text-slate-400" />
                <div>
                  <p className="text-sm font-medium text-slate-200">
                    {JOB_LABELS[jobType] ?? jobType}
                  </p>
                  <div className="mt-0.5 flex items-center gap-3 text-xs text-slate-500">
                    <StatusBadge status={job.status} size="sm" />
                    {job.last_run && (
                      <span>上次: {new Date(job.last_run).toLocaleString()}</span>
                    )}
                    {job.duration != null && (
                      <span>{(job.duration / 1000).toFixed(1)}s</span>
                    )}
                  </div>
                  {job.error && (
                    <p className="mt-1 text-xs text-red-400">{job.error}</p>
                  )}
                </div>
              </div>
            </div>
          ))}
          {Object.keys(schedulerStatus).length === 0 && (
            <p className="text-sm text-slate-500">暂无调度日志</p>
          )}
        </div>
      </div>
    </div>
  );
}
