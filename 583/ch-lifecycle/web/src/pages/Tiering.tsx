import { useEffect } from 'react';
import { ArrowRightLeft, HardDrive, Play, Eye } from 'lucide-react';
import { useLifecycleStore } from '@/store';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

function getUsageColor(percent: number): string {
  if (percent > 90) return 'text-red-400';
  if (percent > 70) return 'text-amber-400';
  return 'text-sky-400';
}

function getRingColor(percent: number): string {
  if (percent > 90) return '#f87171';
  if (percent > 70) return '#fbbf24';
  return '#38bdf8';
}

function getRingTrack(percent: number): string {
  const color = getRingColor(percent);
  return `conic-gradient(${color} ${percent * 3.6}deg, rgb(51 65 85 / 0.5) ${percent * 3.6}deg)`;
}

function TierCard({ tier }: { tier: ReturnType<typeof useLifecycleStore.getState>['tierStatus'][number] }) {
  const freeSpace = tier.total_space - tier.free_space;
  const color = getUsageColor(tier.used_percent);

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 flex flex-col items-center gap-4">
      <div
        className="relative h-32 w-32 rounded-full flex items-center justify-center"
        style={{ background: getRingTrack(tier.used_percent) }}
      >
        <div className="absolute inset-2 rounded-full bg-slate-800 flex items-center justify-center">
          <div className="text-center">
            <p className={`text-2xl font-bold ${color}`}>{tier.used_percent.toFixed(0)}%</p>
            <p className="text-xs text-slate-400">已使用</p>
          </div>
        </div>
      </div>

      <div className="w-full space-y-2 text-center">
        <div className="flex items-center justify-center gap-2">
          <HardDrive className={`h-4 w-4 ${color}`} />
          <h3 className="text-lg font-semibold text-white">{tier.name}</h3>
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-left">
          <span className="text-slate-400">类型</span>
          <span className="text-slate-300">{tier.type}</span>
          <span className="text-slate-400">路径</span>
          <span className="text-slate-300 font-mono text-xs truncate" title={tier.path}>{tier.path}</span>
          <span className="text-slate-400">优先级</span>
          <span className="text-slate-300">{tier.priority}</span>
          <span className="text-slate-400">已用 / 总量</span>
          <span className={color}>{formatBytes(freeSpace)} / {formatBytes(tier.total_space)}</span>
          <span className="text-slate-400">可用空间</span>
          <span className="text-slate-300">{formatBytes(tier.free_space)}</span>
        </div>
      </div>
    </div>
  );
}

export default function Tiering() {
  const {
    tierStatus,
    tierLoading,
    tierError,
    tieringPlans,
    tieringResult,
    fetchTierStatus,
    planTiering,
    executeTiering,
  } = useLifecycleStore();

  useEffect(() => {
    fetchTierStatus();
  }, [fetchTierStatus]);

  const handlePlan = () => {
    planTiering();
  };

  const handleDryRun = () => {
    executeTiering(true);
  };

  const handleExecute = () => {
    executeTiering(false);
  };

  return (
    <div className="min-h-screen bg-slate-900 p-6">
      <div className="mx-auto max-w-5xl space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-white">存储分层</h1>
          <p className="mt-1 text-sm text-slate-400">
            基于 SSD → HDD 的数据自动迁移，将冷数据从高速存储迁移至低成本存储
          </p>
        </div>

        {tierError && (
          <div className="rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">{tierError}</div>
        )}

        <section>
          <h2 className="mb-4 text-lg font-semibold text-slate-100">层级状态</h2>
          {tierLoading && tierStatus.length === 0 ? (
            <div className="py-12 text-center text-slate-500">Loading...</div>
          ) : tierStatus.length === 0 ? (
            <div className="py-12 text-center text-slate-500">暂无层级数据</div>
          ) : (
            <div className="grid grid-cols-2 gap-6">
              {tierStatus.map((tier) => (
                <TierCard key={tier.name} tier={tier} />
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-100">迁移计划</h2>
            <button
              onClick={handlePlan}
              disabled={tierLoading}
              className="flex items-center gap-2 rounded-lg bg-sky-400 px-4 py-2 text-sm font-medium text-slate-900 transition-colors hover:bg-sky-300 disabled:opacity-50"
            >
              <ArrowRightLeft className="h-4 w-4" />
              生成计划
            </button>
          </div>

          {tieringPlans.length === 0 ? (
            <div className="rounded-xl border border-slate-700/50 bg-slate-800/50 py-12 text-center text-slate-500">
              暂无迁移计划，点击「生成计划」创建
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-700/50 bg-slate-800/50">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700/50 text-left text-slate-400">
                    <th className="px-4 py-3 font-medium">数据库</th>
                    <th className="px-4 py-3 font-medium">表</th>
                    <th className="px-4 py-3 font-medium">分区</th>
                    <th className="px-4 py-3 font-medium">源磁盘</th>
                    <th className="px-4 py-3 font-medium" />
                    <th className="px-4 py-3 font-medium">目标磁盘</th>
                    <th className="px-4 py-3 font-medium">天数</th>
                    <th className="px-4 py-3 font-medium">大小</th>
                    <th className="px-4 py-3 font-medium">原因</th>
                  </tr>
                </thead>
                <tbody>
                  {tieringPlans.map((plan, idx) => (
                    <tr key={idx} className="border-b border-slate-700/30">
                      <td className="px-4 py-2.5 text-slate-300">{plan.database}</td>
                      <td className="px-4 py-2.5 text-slate-300">{plan.table}</td>
                      <td className="px-4 py-2.5 font-mono text-xs text-slate-400">{plan.partition}</td>
                      <td className="px-4 py-2.5 text-sky-400 font-medium">{plan.from_disk}</td>
                      <td className="px-4 py-2.5 text-slate-500">→</td>
                      <td className="px-4 py-2.5 text-amber-400 font-medium">{plan.to_disk}</td>
                      <td className="px-4 py-2.5 text-slate-300">{plan.age_days}</td>
                      <td className="px-4 py-2.5 text-slate-300">{formatBytes(plan.size_bytes)}</td>
                      <td className="px-4 py-2.5 text-slate-400">{plan.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-100">执行迁移</h2>
            <div className="flex gap-3">
              <button
                onClick={handleDryRun}
                disabled={tierLoading || tieringPlans.length === 0}
                className="flex items-center gap-2 rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-300 transition-colors hover:bg-slate-700 disabled:opacity-50"
              >
                <Eye className="h-4 w-4" />
                Dry Run
              </button>
              <button
                onClick={handleExecute}
                disabled={tierLoading || tieringPlans.length === 0}
                className="flex items-center gap-2 rounded-lg bg-sky-400 px-4 py-2 text-sm font-medium text-slate-900 transition-colors hover:bg-sky-300 disabled:opacity-50"
              >
                <Play className="h-4 w-4" />
                执行迁移
              </button>
            </div>
          </div>

          {tieringResult ? (
            <div className="rounded-xl border border-slate-700/50 bg-slate-800/50 p-6 space-y-4">
              <div className="grid grid-cols-4 gap-4">
                <div className="rounded-lg bg-slate-900/50 border border-slate-700/30 p-4 text-center">
                  <p className="text-2xl font-bold text-sky-400">{tieringResult.planned}</p>
                  <p className="mt-1 text-xs text-slate-400">计划数</p>
                </div>
                <div className="rounded-lg bg-slate-900/50 border border-slate-700/30 p-4 text-center">
                  <p className="text-2xl font-bold text-green-400">{tieringResult.executed}</p>
                  <p className="mt-1 text-xs text-slate-400">已执行</p>
                </div>
                <div className="rounded-lg bg-slate-900/50 border border-slate-700/30 p-4 text-center">
                  <p className="text-2xl font-bold text-red-400">{tieringResult.errors?.length ?? 0}</p>
                  <p className="mt-1 text-xs text-slate-400">错误</p>
                </div>
                <div className="rounded-lg bg-slate-900/50 border border-slate-700/30 p-4 text-center">
                  <p className="text-2xl font-bold text-amber-400">{(tieringResult.duration / 1000).toFixed(2)}s</p>
                  <p className="mt-1 text-xs text-slate-400">耗时</p>
                </div>
              </div>

              {tieringResult.errors && tieringResult.errors.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-red-400">错误列表</h3>
                  <div className="space-y-2">
                    {tieringResult.errors.map((err, idx) => (
                      <div
                        key={idx}
                        className="rounded-lg bg-red-500/5 border border-red-500/20 px-4 py-3"
                      >
                        <div className="flex items-center gap-2 text-sm">
                          <span className="font-mono text-xs text-red-300">{err.partition}</span>
                          <span className="text-slate-500">|</span>
                          <span className="text-sky-400">{err.from_disk}</span>
                          <span className="text-slate-500">→</span>
                          <span className="text-amber-400">{err.to_disk}</span>
                        </div>
                        <p className="mt-1 text-xs text-red-400">{err.error}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-slate-700/50 bg-slate-800/50 py-12 text-center text-slate-500">
              执行迁移后查看结果
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
