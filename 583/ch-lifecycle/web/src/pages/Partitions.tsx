import { useState, useCallback } from 'react';
import { Search, AlertTriangle, Play, Eye } from 'lucide-react';
import { useLifecycleStore } from '@/store';
import * as api from '@/api/client';
import type { PartitionInfo } from '@/types';
import { cn } from '@/lib/utils';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

function getAgeDays(maxDate: string): number {
  const max = new Date(maxDate);
  const now = new Date();
  return Math.floor((now.getTime() - max.getTime()) / (1000 * 60 * 60 * 24));
}

function ageColor(ageDays: number): string {
  if (ageDays < 7) return 'text-green-400';
  if (ageDays < 30) return 'text-yellow-400';
  if (ageDays < 90) return 'text-orange-400';
  return 'text-red-400';
}

function ageBg(ageDays: number): string {
  if (ageDays < 7) return 'bg-green-400/10';
  if (ageDays < 30) return 'bg-yellow-400/10';
  if (ageDays < 90) return 'bg-orange-400/10';
  return 'bg-red-400/10';
}

type Tab = 'browse' | 'expired';

export default function Partitions() {
  const {
    expiredPartitions,
    lifecycleResult,
    lifecycleLoading,
    lifecycleError,
    fetchExpired,
    evaluateLifecycle,
    executeLifecycle,
  } = useLifecycleStore();

  const [database, setDatabase] = useState('');
  const [table, setTable] = useState('');
  const [retentionDays, setRetentionDays] = useState(90);
  const [activeTab, setActiveTab] = useState<Tab>('browse');
  const [partitions, setPartitions] = useState<PartitionInfo[]>([]);
  const [partitionsLoading, setPartitionsLoading] = useState(false);
  const [partitionsError, setPartitionsError] = useState<string | null>(null);

  const fetchPartitions = useCallback(async () => {
    if (!database || !table) return;
    setPartitionsLoading(true);
    setPartitionsError(null);
    try {
      const data = await api.getPartitions(database, table);
      setPartitions(data.partitions);
    } catch (e) {
      setPartitionsError((e as Error).message);
    } finally {
      setPartitionsLoading(false);
    }
  }, [database, table]);

  const handleFetchExpired = useCallback(() => {
    fetchExpired(database, table, retentionDays);
  }, [database, table, retentionDays, fetchExpired]);

  const handleDryRun = useCallback(() => {
    evaluateLifecycle(true);
  }, [evaluateLifecycle]);

  const handleExecute = useCallback(() => {
    if (window.confirm('确认执行生命周期操作？此操作将实际执行分区移动/删除等操作，不可撤销。')) {
      executeLifecycle(false);
    }
  }, [executeLifecycle]);

  return (
    <div className="min-h-screen bg-slate-900 p-6">
      <div className="mx-auto max-w-6xl">
        <h1 className="mb-6 text-2xl font-bold text-white">分区管理</h1>

        <div className="mb-6 flex flex-wrap items-end gap-3 rounded-xl border border-slate-700/50 bg-slate-800/50 p-4">
          <div>
            <label className="mb-1 block text-xs text-slate-400">Database</label>
            <input
              value={database}
              onChange={(e) => setDatabase(e.target.value)}
              placeholder="数据库名"
              className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white outline-none placeholder:text-slate-500 focus:border-sky-400"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-400">Table</label>
            <input
              value={table}
              onChange={(e) => setTable(e.target.value)}
              placeholder="表名"
              className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white outline-none placeholder:text-slate-500 focus:border-sky-400"
            />
          </div>
          <button
            onClick={fetchPartitions}
            disabled={!database || !table}
            className="flex items-center gap-2 rounded-lg bg-sky-400 px-4 py-2 text-sm font-medium text-slate-900 transition-colors hover:bg-sky-300 disabled:opacity-50"
          >
            <Search className="h-4 w-4" />
            查询
          </button>
          <div className="ml-auto">
            <label className="mb-1 block text-xs text-slate-400">保留天数</label>
            <input
              type="number"
              min={1}
              value={retentionDays}
              onChange={(e) => setRetentionDays(Number(e.target.value))}
              className="w-28 rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white outline-none focus:border-sky-400"
            />
          </div>
        </div>

        <div className="mb-6 flex gap-1 rounded-lg bg-slate-800/50 p-1">
          <button
            onClick={() => setActiveTab('browse')}
            className={cn(
              'flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors',
              activeTab === 'browse'
                ? 'bg-sky-400 text-slate-900'
                : 'text-slate-400 hover:text-white'
            )}
          >
            分区浏览
          </button>
          <button
            onClick={() => setActiveTab('expired')}
            className={cn(
              'flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors',
              activeTab === 'expired'
                ? 'bg-sky-400 text-slate-900'
                : 'text-slate-400 hover:text-white'
            )}
          >
            过期分区
          </button>
        </div>

        {lifecycleError && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            {lifecycleError}
          </div>
        )}

        {partitionsError && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            {partitionsError}
          </div>
        )}

        {activeTab === 'browse' && (
          <div className="rounded-xl border border-slate-700/50 bg-slate-800/50">
            {partitionsLoading ? (
              <div className="p-6">
                <div className="space-y-3">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="flex gap-4">
                      <div className="h-4 w-24 animate-pulse rounded bg-slate-700" />
                      <div className="h-4 w-32 animate-pulse rounded bg-slate-700" />
                      <div className="h-4 w-16 animate-pulse rounded bg-slate-700" />
                      <div className="h-4 w-20 animate-pulse rounded bg-slate-700" />
                      <div className="h-4 w-16 animate-pulse rounded bg-slate-700" />
                    </div>
                  ))}
                </div>
              </div>
            ) : partitions.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700/50 text-left text-slate-400">
                      <th className="px-4 py-3 font-medium">分区</th>
                      <th className="px-4 py-3 font-medium">名称</th>
                      <th className="px-4 py-3 font-medium">行数</th>
                      <th className="px-4 py-3 font-medium">大小</th>
                      <th className="px-4 py-3 font-medium">最小日期</th>
                      <th className="px-4 py-3 font-medium">最大日期</th>
                      <th className="px-4 py-3 font-medium">年龄</th>
                      <th className="px-4 py-3 font-medium">层级</th>
                      <th className="px-4 py-3 font-medium">路径</th>
                    </tr>
                  </thead>
                  <tbody>
                    {partitions.map((p, idx) => {
                      const ageDays = getAgeDays(p.max_date);
                      return (
                        <tr key={idx} className="border-b border-slate-700/30 hover:bg-slate-700/20">
                          <td className="px-4 py-2 font-mono text-xs text-slate-300">{p.partition}</td>
                          <td className="px-4 py-2 text-slate-300">{p.name}</td>
                          <td className="px-4 py-2 text-slate-300">{p.rows.toLocaleString()}</td>
                          <td className="px-4 py-2 text-slate-300">{formatBytes(p.bytes_on_disk)}</td>
                          <td className="px-4 py-2 text-slate-400">{p.min_date}</td>
                          <td className="px-4 py-2 text-slate-400">{p.max_date}</td>
                          <td className="px-4 py-2">
                            <span className={cn('rounded px-2 py-0.5 text-xs font-medium', ageColor(ageDays), ageBg(ageDays))}>
                              {ageDays}d
                            </span>
                          </td>
                          <td className="px-4 py-2 text-slate-300">{p.level}</td>
                          <td className="max-w-[200px] truncate px-4 py-2 font-mono text-xs text-slate-500" title={p.path}>
                            {p.path}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-16 text-center text-slate-500">
                输入数据库和表名后点击查询浏览分区
              </div>
            )}
          </div>
        )}

        {activeTab === 'expired' && (
          <div className="rounded-xl border border-slate-700/50 bg-slate-800/50">
            <div className="flex items-center justify-between border-b border-slate-700/50 px-4 py-3">
              <h2 className="text-sm font-medium text-slate-300">过期分区列表</h2>
              <button
                onClick={handleFetchExpired}
                disabled={!database || !table || lifecycleLoading}
                className="flex items-center gap-2 rounded-lg bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-400 transition-colors hover:bg-red-500/20 disabled:opacity-50"
              >
                <AlertTriangle className="h-3.5 w-3.5" />
                查询过期
              </button>
            </div>
            {expiredPartitions.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700/50 text-left text-slate-400">
                      <th className="px-4 py-3 font-medium">数据库</th>
                      <th className="px-4 py-3 font-medium">表</th>
                      <th className="px-4 py-3 font-medium">分区</th>
                      <th className="px-4 py-3 font-medium">操作</th>
                      <th className="px-4 py-3 font-medium">天数</th>
                      <th className="px-4 py-3 font-medium">大小</th>
                      <th className="px-4 py-3 font-medium">原因</th>
                    </tr>
                  </thead>
                  <tbody>
                    {expiredPartitions.map((ep, idx) => (
                      <tr key={idx} className="border-b border-slate-700/30 hover:bg-slate-700/20">
                        <td className="px-4 py-2 text-slate-300">{ep.database}</td>
                        <td className="px-4 py-2 text-slate-300">{ep.table}</td>
                        <td className="px-4 py-2 font-mono text-xs text-slate-400">{ep.partition}</td>
                        <td className="px-4 py-2">
                          <span className="rounded bg-red-400/10 px-2 py-0.5 text-xs font-medium text-red-400">
                            {ep.action}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-slate-300">{ep.age_days}</td>
                        <td className="px-4 py-2 text-slate-300">{formatBytes(ep.size_bytes)}</td>
                        <td className="px-4 py-2 text-slate-400">{ep.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-16 text-center text-slate-500">
                点击"查询过期"查找过期分区
              </div>
            )}
          </div>
        )}

        <div className="mt-8 rounded-xl border border-slate-700/50 bg-slate-800/50 p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">生命周期评估</h2>
            <div className="flex gap-3">
              <button
                onClick={handleDryRun}
                disabled={lifecycleLoading}
                className="flex items-center gap-2 rounded-lg bg-sky-400/10 px-4 py-2 text-sm font-medium text-sky-400 transition-colors hover:bg-sky-400/20 disabled:opacity-50"
              >
                <Eye className="h-4 w-4" />
                Dry Run
              </button>
              <button
                onClick={handleExecute}
                disabled={lifecycleLoading}
                className="flex items-center gap-2 rounded-lg bg-red-500/10 px-4 py-2 text-sm font-medium text-red-400 transition-colors hover:bg-red-500/20 disabled:opacity-50"
              >
                <Play className="h-4 w-4" />
                执行
              </button>
            </div>
          </div>

          {lifecycleLoading && (
            <div className="py-8 text-center text-slate-500">评估中...</div>
          )}

          {!lifecycleLoading && lifecycleResult && lifecycleResult.actions.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700/50 text-left text-slate-400">
                    <th className="pb-2 pr-4 font-medium">数据库</th>
                    <th className="pb-2 pr-4 font-medium">表</th>
                    <th className="pb-2 pr-4 font-medium">分区</th>
                    <th className="pb-2 pr-4 font-medium">操作</th>
                    <th className="pb-2 pr-4 font-medium">天数</th>
                    <th className="pb-2 pr-4 font-medium">大小</th>
                    <th className="pb-2 font-medium">原因</th>
                  </tr>
                </thead>
                <tbody>
                  {lifecycleResult.actions.map((action, idx) => (
                    <tr key={idx} className="border-b border-slate-700/30">
                      <td className="py-2 pr-4 text-slate-300">{action.database}</td>
                      <td className="py-2 pr-4 text-slate-300">{action.table}</td>
                      <td className="py-2 pr-4 font-mono text-xs text-slate-400">{action.partition}</td>
                      <td className="py-2 pr-4">
                        <span className="rounded bg-sky-400/10 px-2 py-0.5 text-xs font-medium text-sky-400">
                          {action.action}
                        </span>
                      </td>
                      <td className="py-2 pr-4 text-slate-300">{action.age_days}</td>
                      <td className="py-2 pr-4 text-slate-300">{formatBytes(action.size_bytes)}</td>
                      <td className="py-2 text-slate-400">{action.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-3 text-xs text-slate-500">
                共评估 {lifecycleResult.total_evaluated} 个分区，耗时 {(lifecycleResult.duration / 1000).toFixed(2)}s
              </p>
            </div>
          )}

          {!lifecycleLoading && lifecycleResult && lifecycleResult.actions.length === 0 && (
            <div className="py-8 text-center text-slate-500">无需执行的操作</div>
          )}

          {!lifecycleLoading && !lifecycleResult && (
            <div className="py-8 text-center text-slate-500">点击 Dry Run 预览生命周期操作</div>
          )}
        </div>
      </div>
    </div>
  );
}
