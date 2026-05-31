import { useState, useEffect, useMemo } from 'react';
import { ChevronDown, ArrowRight, GitPullRequest, Check, AlertCircle, Loader2, Zap } from 'lucide-react';
import { useAppStore } from '@/stores/appStore';
import { api } from '@/utils/api';
import { cn } from '@/lib/utils';
import { riskColor, riskBg } from '@/utils/helpers';
import type { RiskLevel, UpgradeSuggestion, BuildVerificationResult } from '@/types';

function RiskBadge({ risk }: { risk: RiskLevel }) {
  return (
    <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border', riskBg(risk), riskColor(risk))}>
      {risk.replace('_', ' ')}
    </span>
  );
}

function UpgradeTypeBadge({ type }: { type: 'PATCH' | 'MINOR' | 'MAJOR' }) {
  const style = type === 'PATCH'
    ? 'bg-dep-safe/15 border-dep-safe/30 text-dep-safe'
    : type === 'MINOR'
      ? 'bg-dep-medium/15 border-dep-medium/30 text-dep-medium'
      : 'bg-dep-critical/15 border-dep-critical/30 text-dep-critical';
  return (
    <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border', style)}>
      {type}
    </span>
  );
}

function CompatibilityBar({ score }: { score: number }) {
  const color = score >= 80 ? '#00D4AA' : score >= 60 ? '#FFA502' : score >= 40 ? '#FF6B35' : '#FF4757';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-dep-border rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${score}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-mono font-semibold min-w-[32px] text-right" style={{ color }}>{Math.round(score)}</span>
    </div>
  );
}

function BuildStatusBadge({ status, buildSuccess, testsPassed }: {
  status: string;
  buildSuccess?: boolean;
  testsPassed?: boolean;
}) {
  if (status === 'RUNNING') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border border-dep-low/30 bg-dep-low/15 text-dep-low">
        <Loader2 className="h-3 w-3 animate-spin" />
        验证中
      </span>
    );
  }
  if (status === 'SUCCESS' && buildSuccess && testsPassed) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border border-dep-safe/30 bg-dep-safe/15 text-dep-safe">
        <Check className="h-3 w-3" />
        构建通过
      </span>
    );
  }
  if (status === 'FAILED') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border border-dep-critical/30 bg-dep-critical/15 text-dep-critical">
        <AlertCircle className="h-3 w-3" />
        构建失败
      </span>
    );
  }
  return null;
}

export default function Upgrades() {
  const { upgrades, fetchUpgrades, loading } = useAppStore();
  const [riskFilter, setRiskFilter] = useState<string>('ALL');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const [showPRModal, setShowPRModal] = useState(false);
  const [autoCreatePR, setAutoCreatePR] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [buildResults, setBuildResults] = useState<Map<number, BuildVerificationResult>>(new Map());
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    fetchUpgrades();
  }, [fetchUpgrades]);

  const filtered = useMemo(() => {
    return upgrades.filter((u) => {
      if (riskFilter !== 'ALL' && u.riskLevel !== riskFilter) return false;
      if (typeFilter !== 'ALL' && u.upgradeType !== typeFilter) return false;
      return true;
    });
  }, [upgrades, riskFilter, typeFilter]);

  function toggleSelect(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleExpand(id: number) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const selectedUpgrades = useMemo(() => upgrades.filter((u) => selectedIds.has(u.id)), [upgrades, selectedIds]);

  async function handleVerifyBuild() {
    if (selectedUpgrades.length === 0) return;
    setVerifying(true);

    const byRepo = new Map<number, number[]>();
    selectedUpgrades.forEach((u) => {
      if (!byRepo.has(u.repoId)) byRepo.set(u.repoId, []);
      byRepo.get(u.repoId)!.push(u.id);
    });

    const newResults = new Map(buildResults);
    for (const [repoId, upgradeIds] of byRepo) {
      try {
        const result = await api.upgrades.verifyBuild(repoId, upgradeIds);
        newResults.set(repoId, result);
      } catch (e) {
        console.error('Verify failed for repo', repoId, e);
      }
    }
    setBuildResults(newResults);
    setVerifying(false);
  }

  async function handleVerifyAndCreatePR() {
    if (selectedUpgrades.length === 0) return;
    setSubmitting(true);
    try {
      const result = await api.upgrades.verifyAndCreatePR(
        selectedUpgrades.map((u) => u.id),
        autoCreatePR
      );

      setShowPRModal(false);
      setSelectedIds(new Set());

      if (autoCreatePR && result.prResult && result.prResult.createdPRs.length > 0) {
        setToast(`✅ PR创建成功: ${result.prResult.createdPRs.length} 个PR已创建`);
      } else {
        setToast(`✅ 验证完成: ${result.verifiedCount} 通过, ${result.failedCount} 失败`);
      }
      setTimeout(() => setToast(null), 5000);
    } catch {
      setToast('验证或PR创建失败');
      setTimeout(() => setToast(null), 5000);
    } finally {
      setSubmitting(false);
    }
  }

  const hasBuildResults = buildResults.size > 0;
  const allBuildsPassed = hasBuildResults &&
    Array.from(buildResults.values()).every(r => r.buildSuccess && r.testsPassed);

  return (
    <div className="min-h-screen bg-dep-bg p-6 pb-32 font-sans">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-dep-text">升级建议</h1>
        <p className="text-sm text-dep-muted mt-1">依赖升级建议、兼容性评估与批量PR创建</p>
      </div>

      <div className="flex flex-wrap items-center gap-4 mb-6">
        <div className="relative">
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="appearance-none bg-dep-card border border-dep-border rounded-lg px-4 py-2 pr-8 text-sm text-dep-text focus:outline-none focus:border-dep-accent cursor-pointer"
          >
            <option value="ALL">All Risk Levels</option>
            <option value="SAFE">SAFE</option>
            <option value="LOW_RISK">LOW RISK</option>
            <option value="MEDIUM_RISK">MEDIUM RISK</option>
            <option value="HIGH_RISK">HIGH RISK</option>
          </select>
          <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-dep-muted pointer-events-none" />
        </div>

        <div className="relative">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="appearance-none bg-dep-card border border-dep-border rounded-lg px-4 py-2 pr-8 text-sm text-dep-text focus:outline-none focus:border-dep-accent cursor-pointer"
          >
            <option value="ALL">All Upgrade Types</option>
            <option value="PATCH">PATCH</option>
            <option value="MINOR">MINOR</option>
            <option value="MAJOR">MAJOR</option>
          </select>
          <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-dep-muted pointer-events-none" />
        </div>

        <div className="flex-1" />

        <button
          onClick={handleVerifyBuild}
          disabled={selectedUpgrades.length === 0 || verifying}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-dep-low/30 bg-dep-low/10 text-dep-low text-sm font-medium transition-colors hover:bg-dep-low/20 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {verifying ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
          {verifying ? '验证中...' : '验证构建'}
        </button>
      </div>

      {hasBuildResults && (
        <div className={cn(
          'mb-6 p-4 rounded-lg border',
          allBuildsPassed
            ? 'bg-dep-safe/10 border-dep-safe/30'
            : 'bg-dep-critical/10 border-dep-critical/30'
        )}>
          <div className="flex items-center gap-3">
            {allBuildsPassed ? (
              <Check className="h-5 w-5 text-dep-safe" />
            ) : (
              <AlertCircle className="h-5 w-5 text-dep-critical" />
            )}
            <div>
              <p className="text-sm font-medium text-dep-text">
                构建验证结果: {allBuildsPassed ? '全部通过 ✅' : '存在失败 ❌'}
              </p>
              <p className="text-xs text-dep-muted mt-0.5">
                {Array.from(buildResults.values()).filter(r => r.buildSuccess && r.testsPassed).length} / {buildResults.size} 服务通过
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {loading.upgrades ? (
          <div className="flex py-12 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-dep-accent border-t-transparent" />
          </div>
        ) : filtered.map((upgrade: UpgradeSuggestion, i: number) => (
          <div
            key={upgrade.id}
            className={cn(
              'bg-dep-card border rounded-xl p-4 transition-all duration-200',
              selectedIds.has(upgrade.id)
                ? 'border-dep-accent/50 shadow-[0_0_20px_rgba(0,212,170,0.1)]'
                : 'border-dep-border hover:border-dep-accent/30'
            )}
            style={{ animationDelay: `${i * 30}ms` }}
          >
            <div className="flex items-start gap-4">
              <div className="pt-1">
                <input
                  type="checkbox"
                  checked={selectedIds.has(upgrade.id)}
                  onChange={() => toggleSelect(upgrade.id)}
                  className="w-4 h-4 rounded border-dep-border bg-dep-card text-dep-accent focus:ring-dep-accent"
                />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-sm font-semibold text-dep-text">
                        {upgrade.groupId}:{upgrade.artifactId}
                      </span>
                      <UpgradeTypeBadge type={upgrade.upgradeType} />
                      <RiskBadge risk={upgrade.riskLevel} />
                      {buildResults.get(upgrade.repoId) && (
                        <BuildStatusBadge
                          status={buildResults.get(upgrade.repoId)!.status}
                          buildSuccess={buildResults.get(upgrade.repoId)!.buildSuccess}
                          testsPassed={buildResults.get(upgrade.repoId)!.testsPassed}
                        />
                      )}
                    </div>
                    <p className="text-xs text-dep-muted mt-1">服务: {upgrade.repoName}</p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span className="font-mono text-sm text-dep-muted">{upgrade.currentVersion}</span>
                    <ArrowRight className="h-4 w-4 text-dep-accent" />
                    <span className="font-mono text-sm font-semibold text-dep-accent">{upgrade.targetVersion}</span>
                  </div>
                </div>

                <div className="mt-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-dep-muted">兼容性评分</span>
                  </div>
                  <CompatibilityBar score={upgrade.compatibilityScore} />
                </div>

                <button
                  onClick={() => toggleExpand(upgrade.id)}
                  className="mt-3 text-xs text-dep-muted hover:text-dep-accent transition-colors inline-flex items-center gap-1"
                >
                  <ChevronDown
                    size={14}
                    className={cn('transition-transform', expandedIds.has(upgrade.id) && 'rotate-180')}
                  />
                  {expandedIds.has(upgrade.id) ? '收起详情' : '查看详情'}
                </button>

                {expandedIds.has(upgrade.id) && (
                  <div className="mt-3 pt-3 border-t border-dep-border/50">
                    {upgrade.breakingChanges && upgrade.breakingChanges.length > 0 && (
                      <div className="mb-3">
                        <p className="text-xs font-semibold text-dep-critical mb-2">⚠️ Breaking Changes</p>
                        <ul className="space-y-1">
                          {upgrade.breakingChanges.split('; ').map((change, j) => (
                            <li key={j} className="flex items-start gap-2 text-xs text-dep-muted">
                              <span className="text-dep-critical mt-0.5">•</span>
                              {change}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {upgrade.releaseNotes && (
                      <div>
                        <p className="text-xs font-semibold text-dep-text mb-1">Release Notes</p>
                        <p className="text-xs text-dep-muted">{upgrade.releaseNotes}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {filtered.length === 0 && !loading.upgrades && (
          <div className="py-16 text-center">
            <p className="text-sm text-dep-muted">没有匹配的升级建议</p>
          </div>
        )}
      </div>

      {selectedUpgrades.length > 0 && (
        <div className="fixed bottom-0 left-64 right-0 bg-dep-secondary/95 backdrop-blur border-t border-dep-border p-4">
          <div className="max-w-5xl mx-auto flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-dep-text">
                已选择 <span className="font-mono text-dep-accent">{selectedUpgrades.length}</span> 项升级
              </p>
              <p className="text-xs text-dep-muted">
                跨 {new Set(selectedUpgrades.map(u => u.repoId)).size} 个服务
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSelectedIds(new Set())}
                className="px-4 py-2 rounded-lg border border-dep-border text-sm text-dep-text transition-colors hover:bg-dep-hover"
              >
                取消选择
              </button>
              <button
                onClick={() => setShowPRModal(true)}
                className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-dep-accent text-dep-bg text-sm font-semibold transition-colors hover:bg-dep-accent/90"
              >
                <GitPullRequest className="h-4 w-4" />
                创建批量 PR
              </button>
            </div>
          </div>
        </div>
      )}

      {showPRModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-xl mx-4 bg-dep-card rounded-xl border border-dep-border animate-fade-in-up">
            <div className="p-5 border-b border-dep-border">
              <h2 className="text-lg font-semibold text-dep-text">创建批量升级 PR</h2>
              <p className="text-sm text-dep-muted mt-1">共 {selectedUpgrades.length} 项升级</p>
            </div>

            <div className="p-5 space-y-4">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-dep-bg border border-dep-border">
                <input
                  type="checkbox"
                  id="auto-create-pr"
                  checked={autoCreatePR}
                  onChange={(e) => setAutoCreatePR(e.target.checked)}
                  className="w-4 h-4 rounded border-dep-border bg-dep-card text-dep-accent focus:ring-dep-accent"
                />
                <label htmlFor="auto-create-pr" className="text-sm text-dep-text">
                  <span className="font-medium">先验证构建，通过后自动创建 PR</span>
                  <p className="text-xs text-dep-muted mt-0.5">验证构建兼容性，确保升级不会破坏现有功能</p>
                </label>
              </div>

              <div>
                <label className="block text-xs font-medium text-dep-muted mb-1.5">已选择的升级</label>
                <div className="max-h-40 overflow-y-auto rounded-lg border border-dep-border bg-dep-bg">
                  {selectedUpgrades.map((u) => (
                    <div
                      key={u.id}
                      className="px-3 py-2 border-b border-dep-border/50 last:border-b-0 flex items-center justify-between text-xs"
                    >
                      <span className="font-mono text-dep-text truncate">{u.groupId}:{u.artifactId}</span>
                      <span className="font-mono text-dep-accent shrink-0 ml-2">{u.currentVersion} → {u.targetVersion}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="p-5 border-t border-dep-border flex justify-end gap-3">
              <button
                onClick={() => setShowPRModal(false)}
                disabled={submitting}
                className="px-4 py-2 rounded-lg border border-dep-border text-sm text-dep-text transition-colors hover:bg-dep-hover disabled:opacity-50"
              >
                取消
              </button>
              <button
                onClick={handleVerifyAndCreatePR}
                disabled={submitting}
                className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-dep-accent text-dep-bg text-sm font-semibold transition-colors hover:bg-dep-accent/90 disabled:opacity-50"
              >
                {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                {submitting
                  ? (autoCreatePR ? '验证并创建中...' : '验证中...')
                  : (autoCreatePR ? '验证并创建 PR' : '执行验证')}
              </button>
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div className="fixed bottom-6 right-6 z-50 animate-slide-in">
          <div className="px-5 py-3 rounded-lg bg-dep-card border border-dep-accent/30 text-sm text-dep-text shadow-lg">
            {toast}
          </div>
        </div>
      )}
    </div>
  );
}
