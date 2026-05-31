import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Play, Trash2, ExternalLink, Package, GitMerge, ShieldAlert, Clock } from 'lucide-react';
import { useAppStore } from '@/stores/appStore';
import { Card, StatusBadge } from '@/components/ui';
import { cn, healthScoreColor, timeAgo } from '@/utils/helpers';

interface DialogState {
  type: 'add' | 'delete' | null;
  repoId?: number;
  repoName?: string;
}

export default function Repositories() {
  const { repositories, fetchRepositories, addRepository, removeRepository, triggerScan, loading } = useAppStore();
  const [search, setSearch] = useState('');
  const [dialog, setDialog] = useState<DialogState>({ type: null });
  const [newRepoFullName, setNewRepoFullName] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

  const filtered = repositories.filter(
    (r) => r.name.toLowerCase().includes(search.toLowerCase()) || r.fullName.toLowerCase().includes(search.toLowerCase())
  );

  const handleAdd = async () => {
    if (!newRepoFullName.trim()) return;
    setSubmitting(true);
    await addRepository(newRepoFullName.trim());
    setNewRepoFullName('');
    setSubmitting(false);
    setDialog({ type: null });
  };

  const handleDelete = async () => {
    if (!dialog.repoId) return;
    setSubmitting(true);
    await removeRepository(dialog.repoId);
    setSubmitting(false);
    setDialog({ type: null });
  };

  const handleScan = async (id: number) => {
    await triggerScan(id);
  };

  return (
    <div className="min-h-screen bg-dep-bg p-6 font-sans">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-dep-text">仓库管理</h1>
          <p className="mt-1 text-sm text-dep-muted">管理需要扫描的GitHub仓库</p>
        </div>
        <button
          onClick={() => setDialog({ type: 'add' })}
          className="inline-flex items-center gap-2 rounded-lg bg-dep-accent px-4 py-2 text-sm font-medium text-dep-bg transition-colors hover:bg-dep-accent/90"
        >
          <Plus className="h-4 w-4" />
          添加仓库
        </button>
      </div>

      <Card className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-dep-muted" />
          <input
            type="text"
            placeholder="搜索仓库名称..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-10 w-full rounded-lg border border-dep-border bg-dep-bg pl-9 pr-4 text-sm text-dep-text placeholder:text-dep-muted focus:border-dep-accent/50 focus:outline-none"
          />
        </div>
      </Card>

      {loading.repos ? (
        <div className="flex py-20 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-dep-accent border-t-transparent" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((repo) => (
            <Card
              key={repo.id}
              className="group hover:border-dep-accent/40 transition-all duration-300 hover:shadow-[0_0_20px_rgba(0,212,170,0.1)]"
            >
              <div className="mb-3 flex items-start justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="truncate text-base font-semibold text-dep-text">{repo.name}</h3>
                    <span className="shrink-0 rounded border border-dep-border px-1.5 py-0.5 text-[10px] text-dep-muted">
                      {repo.buildTool === 'MAVEN' ? 'Maven' : 'Gradle'}
                    </span>
                  </div>
                  <p className="mt-0.5 truncate text-xs text-dep-muted">{repo.fullName}</p>
                </div>
                <a
                  href={repo.htmlUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-2 text-dep-muted transition-colors hover:text-dep-accent"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              </div>

              <div className="mb-3">
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-xs text-dep-muted">健康评分</span>
                  <span className={cn('font-mono text-xs font-bold', healthScoreColor(repo.healthScore))}>
                    {repo.healthScore}
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-dep-border">
                  <div
                    className={cn('h-full rounded-full transition-all duration-500', {
                      'bg-dep-safe': repo.healthScore >= 80,
                      'bg-dep-medium': repo.healthScore >= 60 && repo.healthScore < 80,
                      'bg-dep-high': repo.healthScore >= 40 && repo.healthScore < 60,
                      'bg-dep-critical': repo.healthScore < 40,
                    })}
                    style={{ width: `${repo.healthScore}%` }}
                  />
                </div>
              </div>

              <div className="mb-4 grid grid-cols-2 gap-2">
                <div className="rounded-lg border border-dep-border bg-dep-bg p-2">
                  <div className="flex items-center gap-1.5 text-dep-muted">
                    <Package className="h-3 w-3" />
                    <span className="text-[10px]">依赖</span>
                  </div>
                  <p className="mt-0.5 font-mono text-sm font-semibold text-dep-text">28</p>
                </div>
                <div className="rounded-lg border border-dep-border bg-dep-bg p-2">
                  <div className="flex items-center gap-1.5 text-dep-muted">
                    <GitMerge className="h-3 w-3" />
                    <span className="text-[10px]">冲突</span>
                  </div>
                  <p className="mt-0.5 font-mono text-sm font-semibold text-dep-medium">3</p>
                </div>
                <div className="rounded-lg border border-dep-border bg-dep-bg p-2">
                  <div className="flex items-center gap-1.5 text-dep-muted">
                    <ShieldAlert className="h-3 w-3" />
                    <span className="text-[10px]">漏洞</span>
                  </div>
                  <p className="mt-0.5 font-mono text-sm font-semibold text-dep-critical">2</p>
                </div>
                <div className="rounded-lg border border-dep-border bg-dep-bg p-2">
                  <div className="flex items-center gap-1.5 text-dep-muted">
                    <Clock className="h-3 w-3" />
                    <span className="text-[10px]">过时</span>
                  </div>
                  <p className="mt-0.5 font-mono text-sm font-semibold text-dep-low">8</p>
                </div>
              </div>

              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <StatusBadge status={repo.scanStatus} />
                  {repo.lastScanTime && <span className="text-xs text-dep-muted">{timeAgo(repo.lastScanTime)}</span>}
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => handleScan(repo.id)}
                  disabled={repo.scanStatus === 'SCANNING'}
                  className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg border border-dep-border bg-dep-hover px-3 py-2 text-xs font-medium text-dep-text transition-colors hover:border-dep-accent/40 hover:text-dep-accent disabled:opacity-50"
                >
                  <Play className={cn('h-3.5 w-3.5', repo.scanStatus === 'SCANNING' && 'animate-spin')} />
                  {repo.scanStatus === 'SCANNING' ? '扫描中' : '扫描'}
                </button>
                <Link
                  to={`/services/${repo.id}`}
                  className="flex-1 inline-flex items-center justify-center rounded-lg border border-dep-accent/30 bg-dep-accent/10 px-3 py-2 text-xs font-medium text-dep-accent transition-colors hover:bg-dep-accent/20"
                >
                  查看详情
                </Link>
                <button
                  onClick={() => setDialog({ type: 'delete', repoId: repo.id, repoName: repo.name })}
                  className="inline-flex items-center justify-center rounded-lg border border-dep-border px-3 py-2 text-dep-muted transition-colors hover:border-dep-critical/40 hover:bg-dep-critical/10 hover:text-dep-critical"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </Card>
          ))}

          {filtered.length === 0 && (
            <div className="col-span-full py-20 text-center">
              <Package className="mx-auto h-12 w-12 text-dep-muted/30" />
              <p className="mt-4 text-sm text-dep-muted">
                {search ? '未找到匹配的仓库' : '暂无仓库，请添加第一个仓库'}
              </p>
            </div>
          )}
        </div>
      )}

      {dialog.type === 'add' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md animate-fade-in-up rounded-xl border border-dep-border bg-dep-card p-6">
            <h2 className="text-lg font-semibold text-dep-text">添加GitHub仓库</h2>
            <p className="mt-1 text-sm text-dep-muted">输入GitHub仓库的完整路径</p>

            <div className="mt-5">
              <label className="mb-1.5 block text-xs font-medium text-dep-muted">仓库路径</label>
              <input
                type="text"
                placeholder="owner/repo (例如: spring-projects/spring-boot)"
                value={newRepoFullName}
                onChange={(e) => setNewRepoFullName(e.target.value)}
                className="h-10 w-full rounded-lg border border-dep-border bg-dep-bg px-3 text-sm text-dep-text placeholder:text-dep-muted focus:border-dep-accent/50 focus:outline-none"
              />
              <p className="mt-2 text-xs text-dep-muted">
                我们将通过GitHub API访问该仓库，解析pom.xml或build.gradle文件
              </p>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setDialog({ type: null })}
                className="rounded-lg border border-dep-border px-4 py-2 text-sm text-dep-text transition-colors hover:bg-dep-hover"
              >
                取消
              </button>
              <button
                onClick={handleAdd}
                disabled={submitting || !newRepoFullName.trim()}
                className="inline-flex items-center gap-2 rounded-lg bg-dep-accent px-4 py-2 text-sm font-medium text-dep-bg transition-colors hover:bg-dep-accent/90 disabled:opacity-50"
              >
                {submitting ? '添加中...' : '添加'}
              </button>
            </div>
          </div>
        </div>
      )}

      {dialog.type === 'delete' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md animate-fade-in-up rounded-xl border border-dep-critical/30 bg-dep-card p-6">
            <h2 className="text-lg font-semibold text-dep-text">确认删除</h2>
            <p className="mt-1 text-sm text-dep-muted">
              确定要删除仓库 <span className="font-mono text-dep-critical">{dialog.repoName}</span> 吗？
            </p>
            <p className="mt-3 text-xs text-dep-muted">删除后该仓库的所有扫描记录和依赖数据将被清除，此操作不可撤销。</p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setDialog({ type: null })}
                className="rounded-lg border border-dep-border px-4 py-2 text-sm text-dep-text transition-colors hover:bg-dep-hover"
              >
                取消
              </button>
              <button
                onClick={handleDelete}
                disabled={submitting}
                className="inline-flex items-center gap-2 rounded-lg bg-dep-critical px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-dep-critical/90 disabled:opacity-50"
              >
                {submitting ? '删除中...' : '确认删除'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
