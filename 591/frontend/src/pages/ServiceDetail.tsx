import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ExternalLink, RefreshCw, Package, GitMerge, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { useAppStore } from '@/stores/appStore';
import { Card, HealthScore, StatusBadge, SeverityBadge } from '@/components/ui';
import { cn, healthScoreColor, formatNumber, timeAgo } from '@/utils/helpers';

type Tab = 'dependencies' | 'conflicts';

export default function ServiceDetail() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<Tab>('dependencies');
  const {
    repositories,
    serviceDependencies,
    serviceConflicts,
    fetchServiceDependencies,
    fetchServiceConflicts,
    triggerScan,
    fetchRepositories,
    loading,
  } = useAppStore();

  const repoId = Number(id);
  const repo = repositories.find((r) => r.id === repoId);

  useEffect(() => {
    fetchRepositories();
    if (repoId) {
      fetchServiceDependencies(repoId);
      fetchServiceConflicts(repoId);
    }
  }, [repoId, fetchRepositories, fetchServiceDependencies, fetchServiceConflicts]);

  if (!repo) {
    return (
      <div className="p-6">
        <p className="text-dep-muted">仓库不存在</p>
        <Link to="/repositories" className="mt-4 inline-flex items-center gap-2 text-sm text-dep-accent hover:underline">
          <ArrowLeft className="h-4 w-4" />
          返回仓库管理
        </Link>
      </div>
    );
  }

  const directDeps = serviceDependencies.filter((d) => d.isDirect);
  const outdatedDeps = serviceDependencies.filter((d) => d.isOutdated);

  return (
    <div className="min-h-screen bg-dep-bg p-6 font-sans">
      <div className="mb-6">
        <Link to="/repositories" className="mb-3 inline-flex items-center gap-2 text-sm text-dep-muted hover:text-dep-text">
          <ArrowLeft className="h-4 w-4" />
          返回仓库管理
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-dep-text">{repo.name}</h1>
              <span className="rounded border border-dep-border bg-dep-card px-2 py-0.5 text-xs text-dep-muted">
                {repo.buildTool === 'MAVEN' ? 'Maven' : 'Gradle'}
              </span>
              <a
                href={repo.htmlUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-dep-accent hover:underline"
              >
                <ExternalLink className="h-4 w-4" />
                GitHub
              </a>
            </div>
            <p className="mt-1 text-sm text-dep-muted">{repo.fullName}</p>
            {repo.lastScanTime && (
              <p className="mt-1 text-xs text-dep-muted">
                上次扫描: {timeAgo(repo.lastScanTime)} · <StatusBadge status={repo.scanStatus} />
              </p>
            )}
          </div>
          <div className="flex items-center gap-4">
            <HealthScore score={repo.healthScore} size={80} strokeWidth={8} />
            <button
              onClick={() => triggerScan(repoId)}
              disabled={repo.scanStatus === 'SCANNING'}
              className="flex items-center gap-2 rounded-lg border border-dep-accent/30 bg-dep-accent/10 px-4 py-2 text-sm font-medium text-dep-accent transition-colors hover:bg-dep-accent/20 disabled:opacity-50"
            >
              <RefreshCw className={cn('h-4 w-4', repo.scanStatus === 'SCANNING' && 'animate-spin')} />
              {repo.scanStatus === 'SCANNING' ? '扫描中...' : '重新扫描'}
            </button>
          </div>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-4">
        <Card>
          <p className="text-xs text-dep-muted">总依赖数</p>
          <p className="mt-1 font-mono text-2xl font-bold text-dep-accent">{formatNumber(serviceDependencies.length)}</p>
        </Card>
        <Card>
          <p className="text-xs text-dep-muted">直接依赖</p>
          <p className="mt-1 font-mono text-2xl font-bold text-dep-text">{formatNumber(directDeps.length)}</p>
        </Card>
        <Card>
          <p className="text-xs text-dep-muted">过时依赖</p>
          <p className="mt-1 font-mono text-2xl font-bold text-dep-medium">{formatNumber(outdatedDeps.length)}</p>
        </Card>
        <Card>
          <p className="text-xs text-dep-muted">版本冲突</p>
          <p className="mt-1 font-mono text-2xl font-bold text-dep-critical">{formatNumber(serviceConflicts.length)}</p>
        </Card>
      </div>

      <div className="mb-4 flex gap-1 border-b border-dep-border">
        <button
          onClick={() => setActiveTab('dependencies')}
          className={cn(
            'relative px-4 py-2.5 text-sm font-medium transition-colors',
            activeTab === 'dependencies' ? 'text-dep-accent' : 'text-dep-muted hover:text-dep-text'
          )}
        >
          <span className="flex items-center gap-2">
            <Package className="h-4 w-4" />
            依赖列表
          </span>
          {activeTab === 'dependencies' && (
            <span className="absolute -bottom-px left-0 right-0 h-0.5 bg-dep-accent" />
          )}
        </button>
        <button
          onClick={() => setActiveTab('conflicts')}
          className={cn(
            'relative px-4 py-2.5 text-sm font-medium transition-colors',
            activeTab === 'conflicts' ? 'text-dep-accent' : 'text-dep-muted hover:text-dep-text'
          )}
        >
          <span className="flex items-center gap-2">
            <GitMerge className="h-4 w-4" />
            版本冲突
            {serviceConflicts.length > 0 && (
              <span className="rounded-full bg-dep-critical/20 px-1.5 text-xs text-dep-critical">
                {serviceConflicts.length}
              </span>
            )}
          </span>
          {activeTab === 'conflicts' && (
            <span className="absolute -bottom-px left-0 right-0 h-0.5 bg-dep-accent" />
          )}
        </button>
      </div>

      {activeTab === 'dependencies' && (
        <Card>
          {loading.serviceDeps ? (
            <div className="flex py-12 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-dep-accent border-t-transparent" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-dep-border">
                    <th className="px-4 py-3 text-left text-xs font-medium text-dep-muted">Group ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-dep-muted">Artifact ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-dep-muted">当前版本</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-dep-muted">最新版本</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-dep-muted">范围</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-dep-muted">状态</th>
                  </tr>
                </thead>
                <tbody>
                  {serviceDependencies.map((dep, i) => (
                    <tr
                      key={`${dep.groupId}-${dep.artifactId}-${i}`}
                      className={cn('border-b border-dep-border/50 transition-colors hover:bg-dep-hover', dep.isOutdated && 'bg-dep-medium/5')}
                    >
                      <td className="px-4 py-3 text-xs font-mono text-dep-muted">{dep.groupId}</td>
                      <td className="px-4 py-3 text-sm font-medium text-dep-text">{dep.artifactId}</td>
                      <td className="px-4 py-3 text-xs font-mono text-dep-text">{dep.version}</td>
                      <td className="px-4 py-3 text-xs font-mono text-dep-accent">{dep.latestVersion}</td>
                      <td className="px-4 py-3 text-xs text-dep-muted">{dep.scope || 'compile'}</td>
                      <td className="px-4 py-3">
                        {dep.isOutdated ? (
                          <span className="inline-flex items-center gap-1 text-xs text-dep-medium">
                            <AlertTriangle className="h-3.5 w-3.5" />
                            过时
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs text-dep-safe">
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            最新
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {serviceDependencies.length === 0 && (
                <p className="py-12 text-center text-sm text-dep-muted">暂无依赖数据</p>
              )}
            </div>
          )}
        </Card>
      )}

      {activeTab === 'conflicts' && (
        <div className="space-y-4">
          {serviceConflicts.length === 0 ? (
            <Card className="py-12 text-center">
              <CheckCircle2 className="mx-auto h-12 w-12 text-dep-safe" />
              <p className="mt-4 text-sm font-medium text-dep-text">没有检测到版本冲突</p>
              <p className="mt-1 text-xs text-dep-muted">该服务的所有依赖版本均一致</p>
            </Card>
          ) : (
            serviceConflicts.map((conflict, i) => (
              <Card
                key={`${conflict.groupId}-${conflict.artifactId}-${i}`}
                className={cn(
                  conflict.severity === 'HIGH'
                    ? 'border-dep-critical/30 bg-gradient-to-r from-dep-critical/5 to-transparent'
                    : conflict.severity === 'MEDIUM'
                    ? 'border-dep-medium/30 bg-gradient-to-r from-dep-medium/5 to-transparent'
                    : 'border-dep-low/30 bg-gradient-to-r from-dep-low/5 to-transparent'
                )}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold text-dep-text">
                        {conflict.groupId}:{conflict.artifactId}
                      </span>
                      <SeverityBadge severity={conflict.severity} />
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      {conflict.versions.map((v, j) => (
                        <div
                          key={j}
                          className="rounded-lg border border-dep-border bg-dep-bg px-3 py-1.5 text-xs"
                        >
                          <span className="text-dep-muted">{v.service}</span>
                          <span className="mx-1 text-dep-muted">·</span>
                          <span className="font-mono font-medium text-dep-text">{v.version}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-dep-muted">推荐版本</p>
                    <p className="font-mono text-sm font-bold text-dep-accent">{conflict.recommendedVersion}</p>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  );
}
