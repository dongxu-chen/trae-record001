import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Server, GitMerge, ShieldAlert, Clock } from 'lucide-react'
import { useAppStore } from '@/stores/appStore'
import { Card, HealthScore, StatusBadge, SeverityBadge } from '@/components/ui'
import { cn, formatNumber, timeAgo, healthScoreColor } from '@/utils/helpers'

const statCards = [
  { key: 'totalServices', label: '服务总数', icon: Server, color: '#00D4AA', glow: 'shadow-[0_0_15px_rgba(0,212,170,0.2)]' },
  { key: 'conflictCount', label: '版本冲突', icon: GitMerge, color: '#FFA502', glow: 'shadow-[0_0_15px_rgba(255,165,2,0.2)]' },
  { key: 'vulnerabilityCount', label: '安全漏洞', icon: ShieldAlert, color: '#FF4757', glow: 'shadow-[0_0_15px_rgba(255,71,87,0.2)]' },
  { key: 'outdatedCount', label: '过时依赖', icon: Clock, color: '#54A0FF', glow: 'shadow-[0_0_15px_rgba(84,160,255,0.2)]' },
] as const

function healthDescription(score: number): string {
  if (score >= 80) return '健康状态良好，依赖管理规范'
  if (score >= 60) return '存在一定风险，建议关注'
  if (score >= 40) return '风险较高，需要尽快处理'
  return '严重风险，需立即处理'
}

export default function Dashboard() {
  const { dashboardStats, repositories, fetchDashboardStats, fetchRepositories, loading } = useAppStore()

  useEffect(() => {
    fetchDashboardStats()
    fetchRepositories()
  }, [fetchDashboardStats, fetchRepositories])

  if (!dashboardStats) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-dep-accent border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-dep-bg p-6 font-sans">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-dep-text">仪表盘</h1>
        <p className="mt-1 text-sm text-dep-muted">DepGuard 依赖治理全景概览</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card, i) => {
          const Icon = card.icon
          const value = dashboardStats[card.key]
          return (
            <Card
              key={card.key}
              className={cn('animate-fade-in-up', card.glow)}
            >
              <div style={{ animationDelay: `${i * 50}ms` }} />
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-dep-muted">{card.label}</p>
                  <p className="mt-1 font-mono text-3xl font-bold" style={{ color: card.color }}>
                    {formatNumber(value)}
                  </p>
                </div>
                <div
                  className="flex h-10 w-10 items-center justify-center rounded-lg"
                  style={{ backgroundColor: `${card.color}15` }}
                >
                  <Icon size={20} style={{ color: card.color }} />
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <h2 className="mb-4 text-sm font-semibold text-dep-muted">整体健康评分</h2>
          <div className="flex flex-col items-center">
            <div className="relative">
              <HealthScore score={dashboardStats.healthScore} size={160} strokeWidth={12} />
            </div>
            <p className={cn('mt-4 text-sm font-medium', healthScoreColor(dashboardStats.healthScore))}>
              {healthDescription(dashboardStats.healthScore)}
            </p>
          </div>
        </Card>

        <Card className="lg:col-span-3">
          <h2 className="mb-4 text-sm font-semibold text-dep-muted">服务健康度概览</h2>
          <div className="space-y-3">
            {repositories.map((repo) => (
              <Link
                key={repo.id}
                to={`/services/${repo.id}`}
                className="flex items-center gap-3 rounded-lg border border-dep-border bg-dep-bg p-3 transition-colors hover:border-dep-accent/40 hover:bg-dep-hover"
              >
                <span className="min-w-0 flex-1 truncate text-sm text-dep-text">{repo.name}</span>
                <div className="flex items-center gap-3">
                  <div className="h-2 w-24 overflow-hidden rounded-full bg-dep-border">
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
                  <span className={cn('font-mono text-xs font-semibold', healthScoreColor(repo.healthScore))}>
                    {repo.healthScore}
                  </span>
                </div>
              </Link>
            ))}
            {repositories.length === 0 && (
              <p className="py-8 text-center text-sm text-dep-muted">暂无服务数据</p>
            )}
          </div>
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <h2 className="mb-4 text-sm font-semibold text-dep-muted">最近扫描活动</h2>
          <div className="space-y-4">
            {dashboardStats.recentScans.map((scan, i) => (
              <div key={i} className="flex items-start gap-3 border-l-2 border-dep-border pl-4">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-dep-text">{scan.repoName}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <span className="text-xs text-dep-muted">{timeAgo(scan.time)}</span>
                    <StatusBadge status={scan.status} />
                  </div>
                  <p className="mt-1 text-xs text-dep-muted">
                    发现 <span className="font-mono text-dep-accent">{scan.findings}</span> 个问题
                  </p>
                </div>
              </div>
            ))}
            {dashboardStats.recentScans.length === 0 && (
              <p className="py-8 text-center text-sm text-dep-muted">暂无扫描记录</p>
            )}
          </div>
        </Card>

        <Card className="lg:col-span-3" pulseRed={dashboardStats.topVulnerabilities.length > 0}>
          <h2 className="mb-4 text-sm font-semibold text-dep-muted">严重漏洞告警</h2>
          <div className="space-y-3">
            {dashboardStats.topVulnerabilities.slice(0, 3).map((vuln) => (
              <Link
                key={vuln.cveId}
                to={`/vulnerabilities/${vuln.cveId}`}
                className="block rounded-lg border border-dep-critical/20 bg-dep-critical/5 p-3 transition-colors hover:border-dep-critical/40 hover:bg-dep-critical/10"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-bold text-dep-critical">{vuln.cveId}</span>
                  <SeverityBadge severity={vuln.severity} />
                </div>
                <p className="mt-1.5 line-clamp-2 text-xs text-dep-muted">{vuln.description}</p>
              </Link>
            ))}
            {dashboardStats.topVulnerabilities.length === 0 && (
              <p className="py-8 text-center text-sm text-dep-muted">暂无严重漏洞</p>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
