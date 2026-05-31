import { useEffect } from 'react';
import { Shield, HardDrive, Clock, Layers, Play } from 'lucide-react';
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

const JOB_TYPES = ['ttl_check', 'tiering', 'cleanup', 'optimize'] as const;

const JOB_LABELS: Record<string, string> = {
  ttl_check: 'TTL 检查',
  tiering: '分层存储',
  cleanup: '数据清理',
  optimize: '优化合并',
};

export default function Dashboard() {
  const {
    policies,
    disks,
    schedulerStatus,
    tierStatus,
    lifecycleResult,
    fetchPolicies,
    fetchDisks,
    fetchSchedulerStatus,
    fetchTierStatus,
    evaluateLifecycle,
    triggerJob,
  } = useLifecycleStore();

  useEffect(() => {
    fetchPolicies();
    fetchDisks();
    fetchSchedulerStatus();
    fetchTierStatus();
    evaluateLifecycle(true);
  }, [fetchPolicies, fetchDisks, fetchSchedulerStatus, fetchTierStatus, evaluateLifecycle]);

  const enabledPolicies = policies.filter((p) => p.enabled).length;
  const totalActions = lifecycleResult?.actions?.length ?? 0;

  const stats = [
    { icon: Shield, label: '活跃策略', value: enabledPolicies },
    { icon: HardDrive, label: '监控磁盘', value: disks.length },
    { icon: Clock, label: '调度任务', value: Object.keys(schedulerStatus).length },
    { icon: Layers, label: '分区操作', value: totalActions },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">仪表盘</h1>
        <p className="mt-1 text-sm text-slate-400">ClickHouse 数据生命周期管理概览</p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {stats.map(({ icon: Icon, label, value }) => (
          <div
            key={label}
            className="bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-5"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-sky-400/10">
                <Icon className="h-5 w-5 text-sky-400" />
              </div>
              <div>
                <p className="text-3xl font-bold text-sky-400">{value}</p>
                <p className="text-sm text-slate-400">{label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-5">
          <h2 className="mb-4 text-lg font-semibold text-slate-100">磁盘使用</h2>
          <div className="space-y-4">
            {tierStatus.map((tier) => (
              <div key={tier.name}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="text-slate-300">{tier.name}</span>
                  <span className="text-slate-400">
                    {formatBytes(tier.total_space - tier.free_space)} / {formatBytes(tier.total_space)}
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-700">
                  <div
                    className={`h-2 rounded-full transition-all ${getBarColor(tier.used_percent)}`}
                    style={{ width: `${Math.min(tier.used_percent, 100)}%` }}
                  />
                </div>
                <p className="mt-0.5 text-xs text-slate-500">{tier.used_percent.toFixed(1)}% 已使用</p>
              </div>
            ))}
            {tierStatus.length === 0 && (
              <p className="text-sm text-slate-500">暂无磁盘数据</p>
            )}
          </div>
        </div>

        <div className="bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-5">
          <h2 className="mb-4 text-lg font-semibold text-slate-100">调度状态</h2>
          <div className="space-y-3">
            {JOB_TYPES.map((jobType) => {
              const job = schedulerStatus[jobType];
              return (
                <div
                  key={jobType}
                  className="flex items-center justify-between rounded-lg bg-slate-900/50 border border-slate-700/30 px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <Clock className="h-4 w-4 text-slate-400" />
                    <div>
                      <p className="text-sm font-medium text-slate-200">{JOB_LABELS[jobType]}</p>
                      {job && (
                        <div className="mt-0.5 flex items-center gap-3 text-xs text-slate-500">
                          <StatusBadge status={job.status} size="sm" />
                          {job.last_run && (
                            <span>上次: {new Date(job.last_run).toLocaleString()}</span>
                          )}
                          {job.duration != null && (
                            <span>{(job.duration / 1000).toFixed(1)}s</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => triggerJob(jobType)}
                    className="flex items-center gap-1.5 rounded-lg bg-sky-400/10 px-3 py-1.5 text-xs font-medium text-sky-400 transition-colors hover:bg-sky-400/20"
                  >
                    <Play className="h-3 w-3" />
                    触发
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-5">
        <h2 className="mb-4 text-lg font-semibold text-slate-100">最近评估</h2>
        {lifecycleResult && lifecycleResult.actions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/50 text-left text-slate-400">
                  <th className="pb-2 pr-4 font-medium">数据库</th>
                  <th className="pb-2 pr-4 font-medium">表</th>
                  <th className="pb-2 pr-4 font-medium">分区</th>
                  <th className="pb-2 pr-4 font-medium">操作</th>
                  <th className="pb-2 pr-4 font-medium">天数</th>
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
                      <span className={`rounded px-2 py-0.5 text-xs font-medium ${action.shadow_move ? 'bg-violet-400/10 text-violet-400' : 'bg-sky-400/10 text-sky-400'}`}>
                        {action.action}{action.shadow_move ? ' (影子)' : ''}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-slate-300">{action.age_days}</td>
                    <td className="py-2 text-slate-400">{action.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-slate-500">暂无评估结果</p>
        )}
        {lifecycleResult && lifecycleResult.actions.length > 0 && (
          <p className="mt-3 text-xs text-slate-500">
            共评估 {lifecycleResult.total_evaluated} 个分区，耗时 {(lifecycleResult.duration / 1000).toFixed(2)}s
          </p>
        )}
      </div>
    </div>
  );
}
