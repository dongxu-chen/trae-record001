import { useState, useEffect, useCallback } from 'react';
import { Archive as ArchiveIcon, Database, Eye, Upload, Trash2, Play, ChevronDown, ChevronUp } from 'lucide-react';
import * as api from '@/api/client';
import type { ArchiveJob, ArchiveConfig, ArchiveStatus } from '@/types';
import { cn } from '@/lib/utils';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

function formatRows(rows: number): string {
  if (rows === 0) return '0';
  if (rows >= 1000000) return `${(rows / 1000000).toFixed(1)}M`;
  if (rows >= 1000) return `${(rows / 1000).toFixed(1)}K`;
  return rows.toString();
}

const statusColorMap: Record<ArchiveStatus, string> = {
  pending: 'bg-amber-400/10 text-amber-400 border-amber-400/30',
  running: 'bg-sky-400/10 text-sky-400 border-sky-400/30',
  completed: 'bg-green-400/10 text-green-400 border-green-400/30',
  failed: 'bg-red-400/10 text-red-400 border-red-400/30',
  deleted: 'bg-slate-400/10 text-slate-400 border-slate-400/30',
};

const statusLabelMap: Record<ArchiveStatus, string> = {
  pending: '等待中',
  running: '进行中',
  completed: '已完成',
  failed: '失败',
  deleted: '已删除',
};

function StatusBadge({ status }: { status: ArchiveStatus }) {
  const isRunning = status === 'running';
  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium',
      statusColorMap[status]
    )}>
      <span className="relative flex">
        <span className={cn(
          'h-1.5 w-1.5 rounded-full',
          status === 'pending' && 'bg-amber-400',
          status === 'running' && 'bg-sky-400',
          status === 'completed' && 'bg-green-400',
          status === 'failed' && 'bg-red-400',
          status === 'deleted' && 'bg-slate-400',
        )} />
        {isRunning && (
          <span className={cn(
            'absolute inline-flex h-full w-full animate-ping rounded-full opacity-75',
            'bg-sky-400'
          )} />
        )}
      </span>
      {statusLabelMap[status]}
    </span>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 animate-pulse">
      <div className="flex items-start justify-between mb-3">
        <div className="h-5 w-24 bg-slate-700 rounded" />
        <div className="h-6 w-16 bg-slate-700 rounded-full" />
      </div>
      <div className="h-4 w-48 bg-slate-700 rounded mb-2" />
      <div className="h-3 w-64 bg-slate-700 rounded mb-3" />
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="h-8 bg-slate-700 rounded" />
        <div className="h-8 bg-slate-700 rounded" />
      </div>
      <div className="flex gap-2">
        <div className="h-8 w-8 bg-slate-700 rounded-lg" />
        <div className="h-8 w-8 bg-slate-700 rounded-lg" />
        <div className="h-8 w-8 bg-slate-700 rounded-lg" />
      </div>
    </div>
  );
}

function ArchiveCard({
  archive,
  onVerify,
  onRestore,
  onDelete,
  expandedSql,
  toggleSql,
}: {
  archive: ArchiveJob;
  onVerify: (id: string) => void;
  onRestore: (id: string) => void;
  onDelete: (id: string) => void;
  expandedSql: string | null;
  toggleSql: (id: string) => void;
}) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 transition-all hover:border-slate-600/50">
      <div className="flex items-start justify-between mb-3">
        <StatusBadge status={archive.status} />
        <span className="text-sm font-mono text-slate-400">
          {archive.database}.{archive.table}.{archive.partition}
        </span>
      </div>

      <div className="mb-3">
        <p className="font-mono text-xs text-slate-500 truncate" title={archive.object_path}>
          {archive.object_path}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="rounded-lg bg-slate-900/50 border border-slate-700/30 px-3 py-2">
          <p className="text-xs text-slate-500">大小</p>
          <p className="text-sm font-semibold text-sky-400">{formatBytes(archive.size_bytes)}</p>
        </div>
        <div className="rounded-lg bg-slate-900/50 border border-slate-700/30 px-3 py-2">
          <p className="text-xs text-slate-500">行数</p>
          <p className="text-sm font-semibold text-slate-200">{formatRows(archive.rows)}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3 text-xs text-slate-500">
        <div>
          <span className="text-slate-500">创建: </span>
          <span className="text-slate-400">{new Date(archive.created_at).toLocaleString()}</span>
        </div>
        {archive.completed_at && (
          <div>
            <span className="text-slate-500">完成: </span>
            <span className="text-slate-400">{new Date(archive.completed_at).toLocaleString()}</span>
          </div>
        )}
      </div>

      {archive.export_sql && (
        <div className="mb-3">
          <button
            onClick={() => toggleSql(archive.id)}
            className="flex items-center gap-1 text-xs text-sky-400 hover:text-sky-300 transition-colors"
          >
            {expandedSql === archive.id ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            导出 SQL
          </button>
          {expandedSql === archive.id && (
            <pre className="mt-2 rounded-lg bg-slate-900 border border-slate-700 p-3 text-xs text-slate-300 overflow-x-auto">
              <code>{archive.export_sql}</code>
            </pre>
          )}
        </div>
      )}

      {archive.error && (
        <div className="mb-3 rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2">
          <p className="text-xs text-red-400">{archive.error}</p>
        </div>
      )}

      <div className="flex items-center gap-2">
        <button
          onClick={() => onVerify(archive.id)}
          className="flex items-center gap-1.5 rounded-lg bg-slate-700/50 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:bg-slate-700 hover:text-white"
          title="验证归档"
        >
          <Eye className="h-3.5 w-3.5" />
          验证
        </button>
        <button
          onClick={() => onRestore(archive.id)}
          className="flex items-center gap-1.5 rounded-lg bg-sky-400/10 px-3 py-1.5 text-xs text-sky-400 transition-colors hover:bg-sky-400/20"
          title="恢复数据"
        >
          <Upload className="h-3.5 w-3.5" />
          恢复
        </button>
        <button
          onClick={() => onDelete(archive.id)}
          className="flex items-center gap-1.5 rounded-lg bg-red-500/10 px-3 py-1.5 text-xs text-red-400 transition-colors hover:bg-red-500/20"
          title="删除归档"
        >
          <Trash2 className="h-3.5 w-3.5" />
          删除
        </button>
      </div>
    </div>
  );
}

export default function Archive() {
  const [archives, setArchives] = useState<ArchiveJob[]>([]);
  const [config, setConfig] = useState<ArchiveConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [expandedSql, setExpandedSql] = useState<string | null>(null);

  const [form, setForm] = useState({
    database: '',
    table: '',
    partition: '',
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [archivesData, configData] = await Promise.all([
        api.getArchives(),
        api.getArchiveConfig(),
      ]);
      setArchives(archivesData);
      setConfig(configData);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreate = useCallback(async () => {
    if (!form.database || !form.table || !form.partition) return;
    setCreating(true);
    setError(null);
    try {
      await api.createArchive(form.database, form.table, form.partition);
      setForm({ database: '', table: '', partition: '' });
      await fetchData();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCreating(false);
    }
  }, [form, fetchData]);

  const handleVerify = useCallback(async (id: string) => {
    try {
      const result = await api.verifyArchive(id);
      if (result.verified) {
        alert('归档验证成功！');
      } else {
        alert('归档验证失败！');
      }
    } catch (e) {
      alert(`验证失败: ${(e as Error).message}`);
    }
  }, []);

  const handleRestore = useCallback(async (id: string) => {
    if (!confirm('确定要恢复此归档吗？这将把数据导回 ClickHouse。')) return;
    try {
      await api.restoreArchive(id);
      alert('恢复任务已启动');
      await fetchData();
    } catch (e) {
      setError((e as Error).message);
    }
  }, [fetchData]);

  const handleDelete = useCallback(async (id: string) => {
    if (!confirm('确定要删除此归档吗？此操作不可撤销。')) return;
    try {
      await api.deleteArchive(id);
      await fetchData();
    } catch (e) {
      setError((e as Error).message);
    }
  }, [fetchData]);

  const toggleSql = useCallback((id: string) => {
    setExpandedSql((prev) => (prev === id ? null : id));
  }, []);

  return (
    <div className="min-h-screen bg-slate-900 p-6">
      <div className="mx-auto max-w-5xl space-y-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-sky-400/10">
              <ArchiveIcon className="h-5 w-5 text-sky-400" />
            </div>
            <h1 className="text-2xl font-bold text-slate-100">数据归档</h1>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            将冷数据导出到对象存储（S3/OSS），节省本地存储空间，保留长期数据访问能力
          </p>
        </div>

        {error && (
          <div className="rounded-lg bg-red-500/10 border border-red-500/20 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {config && (
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5">
            <h2 className="mb-4 text-lg font-semibold text-slate-100">归档配置</h2>
            <div className="grid grid-cols-4 gap-4">
              <div className="rounded-lg bg-slate-900/50 border border-slate-700/30 px-4 py-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`h-2 w-2 rounded-full ${config.enabled ? 'bg-green-400' : 'bg-red-400'}`} />
                  <p className="text-xs text-slate-500">状态</p>
                </div>
                <p className={`text-sm font-semibold ${config.enabled ? 'text-green-400' : 'text-red-400'}`}>
                  {config.enabled ? '已启用' : '已禁用'}
                </p>
              </div>
              <div className="rounded-lg bg-slate-900/50 border border-slate-700/30 px-4 py-3">
                <p className="text-xs text-slate-500 mb-1">Endpoint</p>
                <p className="text-sm font-mono text-slate-300 truncate" title={config.endpoint}>
                  {config.endpoint}
                </p>
              </div>
              <div className="rounded-lg bg-slate-900/50 border border-slate-700/30 px-4 py-3">
                <p className="text-xs text-slate-500 mb-1">Bucket</p>
                <p className="text-sm font-mono text-slate-300">{config.bucket}</p>
              </div>
              <div className="rounded-lg bg-slate-900/50 border border-slate-700/30 px-4 py-3">
                <p className="text-xs text-slate-500 mb-1">导出格式</p>
                <p className="text-sm font-semibold text-sky-400">{config.export_format}</p>
              </div>
            </div>
          </div>
        )}

        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5">
          <h2 className="mb-4 text-lg font-semibold text-slate-100">创建归档</h2>
          <div className="grid grid-cols-4 gap-3">
            <div>
              <label className="mb-1 block text-sm text-slate-400">数据库</label>
              <input
                type="text"
                value={form.database}
                onChange={(e) => setForm((f) => ({ ...f, database: e.target.value }))}
                placeholder="default"
                className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-sky-400 transition-colors"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-slate-400">表</label>
              <input
                type="text"
                value={form.table}
                onChange={(e) => setForm((f) => ({ ...f, table: e.target.value }))}
                placeholder="events"
                className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-sky-400 transition-colors"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-slate-400">分区</label>
              <input
                type="text"
                value={form.partition}
                onChange={(e) => setForm((f) => ({ ...f, partition: e.target.value }))}
                placeholder="2024-01"
                className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-sky-400 transition-colors"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={handleCreate}
                disabled={creating || !form.database || !form.table || !form.partition}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-sky-400 px-4 py-2 text-sm font-medium text-slate-900 transition-colors hover:bg-sky-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="h-4 w-4" />
                导出
              </button>
            </div>
          </div>
        </div>

        <div>
          <h2 className="mb-4 text-lg font-semibold text-slate-100">归档任务</h2>
          {loading && archives.length === 0 ? (
            <div className="grid grid-cols-2 gap-4">
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </div>
          ) : archives.length === 0 ? (
            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl py-16 text-center">
              <Database className="h-12 w-12 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-500 text-sm">暂无归档任务</p>
              <p className="text-slate-600 text-xs mt-1">使用上方表单创建第一个数据归档</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {archives.map((archive) => (
                <ArchiveCard
                  key={archive.id}
                  archive={archive}
                  onVerify={handleVerify}
                  onRestore={handleRestore}
                  onDelete={handleDelete}
                  expandedSql={expandedSql}
                  toggleSql={toggleSql}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
