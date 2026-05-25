import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  BarChart3,
  Users,
  Target,
  TrendingUp,
  ArrowLeft,
  Loader2,
} from 'lucide-react'
import { Statistics, LABEL_COLORS, LABEL_NAMES, LabelType } from '@/types'
import { statisticsApi } from '@/services/api'

export default function StatisticsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!projectId) return

    const loadStatistics = async () => {
      try {
        const data = await statisticsApi.getByProjectId(projectId)
        setStatistics(data)
      } catch (error) {
        console.error('Failed to load statistics:', error)
      } finally {
        setLoading(false)
      }
    }
    loadStatistics()
  }, [projectId])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    )
  }

  if (!statistics) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <BarChart3 className="w-16 h-16 text-zinc-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-zinc-400 mb-2">
            暂无统计数据
          </h3>
          <Link
            to="/projects"
            className="text-primary-400 hover:text-primary-300 flex items-center justify-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            返回项目列表
          </Link>
        </div>
      </div>
    )
  }

  const labels = Object.keys(LABEL_NAMES) as LabelType[]
  const maxLabelCount = Math.max(...Object.values(statistics.labelDistribution))

  return (
    <div className="p-6 h-full overflow-auto">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white">统计分析</h1>
          <p className="text-zinc-400 mt-1">查看项目标注进度和用户贡献</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="glass-panel rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-primary-500/20 rounded-lg flex items-center justify-center">
                <Target className="w-6 h-6 text-primary-400" />
              </div>
              <span className="text-sm text-zinc-500">标注总数</span>
            </div>
            <div className="text-3xl font-bold text-white">
              {statistics.totalAnnotations}
            </div>
            <div className="mt-2 text-sm text-zinc-400">
              个标注对象
            </div>
          </div>

          <div className="glass-panel rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-green-500/20 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-green-400" />
              </div>
              <span className="text-sm text-zinc-500">完成进度</span>
            </div>
            <div className="text-3xl font-bold text-white">
              {statistics.progress.toFixed(1)}%
            </div>
            <div className="mt-2 h-2 bg-zinc-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 rounded-full transition-all"
                style={{ width: `${statistics.progress}%` }}
              />
            </div>
          </div>

          <div className="glass-panel rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center">
                <BarChart3 className="w-6 h-6 text-blue-400" />
              </div>
              <span className="text-sm text-zinc-500">总点数</span>
            </div>
            <div className="text-3xl font-bold text-white">
              {statistics.totalPoints.toLocaleString()}
            </div>
            <div className="mt-2 text-sm text-zinc-400">
              已标注点
            </div>
          </div>

          <div className="glass-panel rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center">
                <Users className="w-6 h-6 text-purple-400" />
              </div>
              <span className="text-sm text-zinc-500">参与用户</span>
            </div>
            <div className="text-3xl font-bold text-white">
              {statistics.userContributions.length}
            </div>
            <div className="mt-2 text-sm text-zinc-400">
              位协作用户
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="glass-panel rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-6">标签分布</h3>
            <div className="space-y-4">
              {labels.map((label) => {
                const count = statistics.labelDistribution[label] || 0
                const percentage = statistics.totalAnnotations
                  ? (count / statistics.totalAnnotations) * 100
                  : 0
                return (
                  <div key={label}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded"
                          style={{ backgroundColor: LABEL_COLORS[label] }}
                        />
                        <span className="text-sm text-zinc-300">
                          {LABEL_NAMES[label]}
                        </span>
                      </div>
                      <span className="text-sm text-zinc-400">
                        {count} ({percentage.toFixed(1)}%)
                      </span>
                    </div>
                    <div className="h-3 bg-zinc-700 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${maxLabelCount ? (count / maxLabelCount) * 100 : 0}%`,
                          backgroundColor: LABEL_COLORS[label],
                        }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          <div className="glass-panel rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-6">用户贡献</h3>
            <div className="space-y-4">
              {statistics.userContributions.map((user, index) => {
                const maxCount = Math.max(...statistics.userContributions.map(u => u.count))
                const percentage = maxCount ? (user.count / maxCount) * 100 : 0
                const colors = ['#165DFF', '#00B42A', '#F53F3F', '#FF7D00', '#722ED1']
                return (
                  <div key={user.userId}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center"
                          style={{ backgroundColor: colors[index % colors.length] + '33' }}
                        >
                          <span
                            className="text-sm font-medium"
                            style={{ color: colors[index % colors.length] }}
                          >
                            {user.username.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <span className="text-sm text-zinc-300">
                          {user.username}
                        </span>
                      </div>
                      <span className="text-sm text-zinc-400">
                        {user.count} 个标注
                      </span>
                    </div>
                    <div className="h-2 bg-zinc-700 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${percentage}%`,
                          backgroundColor: colors[index % colors.length],
                        }}
                      />
                    </div>
                  </div>
                )
              })}
              {statistics.userContributions.length === 0 && (
                <p className="text-center text-zinc-500 py-8">
                  暂无用户贡献数据
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
