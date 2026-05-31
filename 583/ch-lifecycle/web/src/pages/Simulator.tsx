import { useState, useMemo } from 'react';
import { TrendingUp, Play, AlertTriangle, Loader2, HardDrive, Archive, ArrowRightLeft, Trash2, DollarSign } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { useLifecycleStore } from '@/store';
import type { DailyStat, PartitionProjection, SavingsMetric } from '@/types';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

const ACTION_STYLES: Record<string, string> = {
  move_to_disk: 'bg-sky-400/10 text-sky-400',
  drop: 'bg-red-400/10 text-red-400',
  freeze: 'bg-amber-400/10 text-amber-400',
  archive: 'bg-violet-400/10 text-violet-400',
  keep: 'bg-green-400/10 text-green-400',
};

function calculateSavings(stats: DailyStat[]): SavingsMetric {
  const lastDay = stats[stats.length - 1];
  if (!lastDay) {
    return {
      total_savings_bytes: 0,
      drop_savings: 0,
      archive_savings: 0,
      tier_savings: 0,
      savings_percent: 0,
      projected_without_policies: 0,
      projected_with_policies: 0,
    };
  }

  const totalDropped = stats.reduce((sum, s) => sum + s.dropped_size, 0);
  const totalArchived = stats.reduce((sum, s) => sum + s.archived_size, 0);
  const totalMoved = stats.reduce((sum, s) => sum + Math.max(0, s.hot_size - (stats[0]?.hot_size || 0)), 0);
  const totalSavings = totalDropped + totalArchived + totalMoved;

  const finalHot = lastDay.hot_size;
  const finalCold = lastDay.cold_size;
  const finalArchived = lastDay.archived_size;
  const projectedWithPolicies = finalHot + finalCold + finalArchived;

  const totalGrowth = stats.reduce((sum, s) => sum + (s.new_partitions * 1024 * 1024 * 100), 0);
  const projectedWithoutPolicies = projectedWithPolicies + totalDropped + (totalArchived * 0.8);

  const savingsPercent = projectedWithoutPolicies > 0
    ? ((projectedWithoutPolicies - projectedWithPolicies) / projectedWithoutPolicies) * 100
    : 0;

  return {
    total_savings_bytes: totalSavings,
    drop_savings: totalDropped,
    archive_savings: totalArchived * 0.8,
    tier_savings: totalMoved * 0.5,
    savings_percent: savingsPercent,
    projected_without_policies: projectedWithoutPolicies,
    projected_with_policies: projectedWithPolicies,
  };
}

export default function Simulator() {
  const [database, setDatabase] = useState('default');
  const [table, setTable] = useState('events');
  const [daysToSimulate, setDaysToSimulate] = useState('365');
  const [dailyGrowthRate, setDailyGrowthRate] = useState('0.001');
  const [compressionRatio, setCompressionRatio] = useState('1.0');

  const { simulationResult, simulationLoading, simulationError, runSimulation } = useLifecycleStore();

  const handleRunSimulation = () => {
    const days = parseInt(daysToSimulate, 10);
    const growth = parseFloat(dailyGrowthRate);
    const compression = parseFloat(compressionRatio);

    if (!database.trim() || !table.trim() || isNaN(days) || isNaN(growth) || isNaN(compression)) return;
    if (days < 1 || days > 3650) return;

    runSimulation(database.trim(), table.trim(), {
      days_to_simulate: days,
      daily_growth_rate: growth,
      compression_ratio: compression,
    });
  };

  const summaryCards = simulationResult
    ? [
        { icon: Trash2, label: '已删除大小', value: formatBytes(simulationResult.total_dropped_size), color: 'text-red-400', bg: 'bg-red-400/10' },
        { icon: Archive, label: '已归档大小', value: formatBytes(simulationResult.total_archived_size), color: 'text-violet-400', bg: 'bg-violet-400/10' },
        { icon: ArrowRightLeft, label: '已移动大小', value: formatBytes(simulationResult.total_moved_size), color: 'text-sky-400', bg: 'bg-sky-400/10' },
        { icon: DollarSign, label: '总节省', value: formatBytes(
            simulationResult.total_dropped_size +
            simulationResult.total_archived_size +
            simulationResult.total_moved_size
          ), color: 'text-green-400', bg: 'bg-green-400/10' },
      ]
    : [];

  const savings = useMemo(() => {
    if (!simulationResult?.daily_stats) return null;
    return calculateSavings(simulationResult.daily_stats);
  }, [simulationResult]);

  const chartData = useMemo(() => {
    if (!simulationResult?.daily_stats) return [];
    return simulationResult.daily_stats.map((stat: DailyStat) => ({
      date: stat.date,
      hot: stat.hot_size,
      cold: stat.cold_size,
      archived: stat.archived_size,
      dropped: stat.dropped_size,
    }));
  }, [simulationResult]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">生命周期模拟</h1>
        <p className="mt-1 text-sm text-slate-400">预测 TTL 策略执行后的存储变化趋势</p>
      </div>

      <div className="bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-5">
        <div className="grid grid-cols-5 gap-4 items-end">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">数据库</label>
            <input
              type="text"
              value={database}
              onChange={(e) => setDatabase(e.target.value)}
              placeholder="数据库名称"
              className="w-full rounded-lg border border-slate-600/50 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 outline-none transition-colors focus:border-sky-400/50 focus:ring-1 focus:ring-sky-400/20"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">表</label>
            <input
              type="text"
              value={table}
              onChange={(e) => setTable(e.target.value)}
              placeholder="表名称"
              className="w-full rounded-lg border border-slate-600/50 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 outline-none transition-colors focus:border-sky-400/50 focus:ring-1 focus:ring-sky-400/20"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">模拟天数 (1-3650)</label>
            <input
              type="number"
              value={daysToSimulate}
              onChange={(e) => setDaysToSimulate(e.target.value)}
              min="1"
              max="3650"
              className="w-full rounded-lg border border-slate-600/50 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 outline-none transition-colors focus:border-sky-400/50 focus:ring-1 focus:ring-sky-400/20"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">日增长率</label>
            <input
              type="number"
              value={dailyGrowthRate}
              onChange={(e) => setDailyGrowthRate(e.target.value)}
              step="0.001"
              className="w-full rounded-lg border border-slate-600/50 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 outline-none transition-colors focus:border-sky-400/50 focus:ring-1 focus:ring-sky-400/20"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">压缩比</label>
            <input
              type="number"
              value={compressionRatio}
              onChange={(e) => setCompressionRatio(e.target.value)}
              step="0.1"
              className="w-full rounded-lg border border-slate-600/50 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 outline-none transition-colors focus:border-sky-400/50 focus:ring-1 focus:ring-sky-400/20"
            />
          </div>
        </div>
        <div className="mt-4 flex items-center justify-end">
          <button
            onClick={handleRunSimulation}
            disabled={simulationLoading || !database.trim() || !table.trim()}
            className="flex items-center gap-2 rounded-lg bg-sky-400 px-6 py-2.5 text-sm font-medium text-slate-900 transition-colors hover:bg-sky-300 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {simulationLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {simulationLoading ? '模拟中...' : '运行模拟'}
          </button>
        </div>
      </div>

      {simulationError && (
        <div className="flex items-center gap-2 rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {simulationError}
        </div>
      )}

      {simulationResult && (
        <>
          <div>
            <h2 className="mb-4 text-lg font-semibold text-slate-100">模拟结果摘要</h2>
            <div className="grid grid-cols-4 gap-4">
              {summaryCards.map(({ icon: Icon, label, value, color, bg }) => (
                <div
                  key={label}
                  className="bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-5"
                >
                  <div className="flex items-center gap-3">
                    <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${bg}`}>
                      <Icon className={`h-5 w-5 ${color}`} />
                    </div>
                    <div>
                      <p className={`text-2xl font-bold ${color}`}>{value}</p>
                      <p className="text-sm text-slate-400">{label}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {savings && (
            <div className="bg-gradient-to-r from-sky-500/10 to-green-500/10 border border-sky-500/30 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <DollarSign className="h-5 w-5 text-sky-400" />
                <h2 className="text-lg font-semibold text-slate-100">节省分析</h2>
              </div>
              <div className="grid grid-cols-3 gap-6">
                <div className="text-center">
                  <p className="text-xs text-slate-500 mb-1">节省比例</p>
                  <p className="text-3xl font-bold text-green-400">{savings.savings_percent.toFixed(1)}%</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-slate-500 mb-1">无策略预测</p>
                  <p className="text-2xl font-bold text-slate-300">{formatBytes(savings.projected_without_policies)}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-slate-500 mb-1">有策略预测</p>
                  <p className="text-2xl font-bold text-sky-400">{formatBytes(savings.projected_with_policies)}</p>
                </div>
              </div>
            </div>
          )}

          <div className="bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-5">
            <h2 className="mb-4 text-lg font-semibold text-slate-100">存储时间线</h2>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorHot" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f97316" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorCold" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorArchived" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#a78bfa" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorDropped" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f87171" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="date"
                    stroke="#64748b"
                    tick={{ fill: '#64748b', fontSize: 11 }}
                    tickFormatter={(value) => {
                      const d = new Date(value);
                      return `${d.getMonth() + 1}/${d.getDate()}`;
                    }}
                  />
                  <YAxis
                    stroke="#64748b"
                    tick={{ fill: '#64748b', fontSize: 11 }}
                    tickFormatter={(value) => formatBytes(value)}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#f1f5f9',
                    }}
                    formatter={(value: number) => formatBytes(value)}
                  />
                  <Legend
                    wrapperStyle={{ color: '#94a3b8' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="hot"
                    stackId="1"
                    stroke="#f97316"
                    fillOpacity={1}
                    fill="url(#colorHot)"
                    name="热存储"
                  />
                  <Area
                    type="monotone"
                    dataKey="cold"
                    stackId="1"
                    stroke="#38bdf8"
                    fillOpacity={1}
                    fill="url(#colorCold)"
                    name="冷存储"
                  />
                  <Area
                    type="monotone"
                    dataKey="archived"
                    stackId="1"
                    stroke="#a78bfa"
                    fillOpacity={1}
                    fill="url(#colorArchived)"
                    name="已归档"
                  />
                  <Area
                    type="monotone"
                    dataKey="dropped"
                    stackId="2"
                    stroke="#f87171"
                    fillOpacity={1}
                    fill="url(#colorDropped)"
                    name="已删除"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-5">
            <h2 className="mb-4 text-lg font-semibold text-slate-100">每日统计</h2>
            <div className="overflow-x-auto max-h-64 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-slate-800">
                  <tr className="border-b border-slate-700/50 text-left text-slate-400">
                    <th className="pb-2 pr-4 font-medium">日期</th>
                    <th className="pb-2 pr-4 font-medium">热存储</th>
                    <th className="pb-2 pr-4 font-medium">冷存储</th>
                    <th className="pb-2 pr-4 font-medium">已归档</th>
                    <th className="pb-2 pr-4 font-medium">已删除</th>
                  </tr>
                </thead>
                <tbody>
                  {simulationResult.daily_stats.map((stat: DailyStat, idx: number) => (
                    <tr key={idx} className="border-b border-slate-700/30">
                      <td className="py-2 pr-4 text-slate-300">{stat.date}</td>
                      <td className="py-2 pr-4 text-orange-400">{formatBytes(stat.hot_size)}</td>
                      <td className="py-2 pr-4 text-sky-400">{formatBytes(stat.cold_size)}</td>
                      <td className="py-2 pr-4 text-violet-400">{formatBytes(stat.archived_size)}</td>
                      <td className="py-2 pr-4 text-red-400">{formatBytes(stat.dropped_size)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-5">
            <h2 className="mb-4 text-lg font-semibold text-slate-100">分区预测</h2>
            <div className="overflow-x-auto max-h-80 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-slate-800">
                  <tr className="border-b border-slate-700/50 text-left text-slate-400">
                    <th className="pb-2 pr-4 font-medium">分区</th>
                    <th className="pb-2 pr-4 font-medium">当前大小</th>
                    <th className="pb-2 pr-4 font-medium">预测大小</th>
                    <th className="pb-2 pr-4 font-medium">天数</th>
                    <th className="pb-2 pr-4 font-medium">操作</th>
                    <th className="pb-2 font-medium">已删除</th>
                  </tr>
                </thead>
                <tbody>
                  {simulationResult.partitions.map((partition: PartitionProjection, idx: number) => (
                    <tr key={idx} className="border-b border-slate-700/30">
                      <td className="py-2 pr-4 font-mono text-xs text-slate-400">{partition.partition}</td>
                      <td className="py-2 pr-4 text-slate-300">{formatBytes(partition.current_size)}</td>
                      <td className="py-2 pr-4 text-slate-300">{formatBytes(partition.projected_size)}</td>
                      <td className="py-2 pr-4 text-slate-300">{partition.age_days}</td>
                      <td className="py-2 pr-4">
                        <span className={`rounded px-2 py-0.5 text-xs font-medium ${ACTION_STYLES[partition.action] || ACTION_STYLES.keep}`}>
                          {partition.action}
                        </span>
                      </td>
                      <td className="py-2">
                        <span className={`text-xs font-medium ${partition.dropped ? 'text-red-400' : 'text-green-400'}`}>
                          {partition.dropped ? '是' : '否'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
